"""
动态因果图谱引擎（Causal Graph Engine）

基于论文 "From Individual to Society" (Mou et al., 2026)：
- §5.1.3 Social Influence：信息级联、观点动力学、群体涌现
- §8.3 Challenge (3)："LLM interpretability poses difficulty — the black-box nature 
  of LLMs makes it hard to provide rigorous causal explanations for individual 
  behaviors or collective outcomes"

本引擎提供可解释的因果链：回答"什么事件导致了什么状态变化"。

核心功能：
1. 从事件序列和状态变化中推断因果边（规则层）
2. 可选 LLM 辅助推断深层因果关系
3. 构建可查询的因果图（本地 JSON 存储）
4. 支持因果链追踪和影响路径查询
"""

import os
import json
import uuid
from typing import Dict, Any, List, Optional, Tuple, Set
from dataclasses import dataclass, field, asdict
from datetime import datetime
from collections import defaultdict

from ..config import Config
from ..utils.logger import get_logger
from .world_state import WorldStateSnapshot, WorldEvent

logger = get_logger('nexusmind.causal_graph')


# ============== 数据结构 ==============

@dataclass
class CausalEdge:
    """
    因果边
    
    表达"事件 A → 事件 B"或"事件 A → 状态变化"的因果关系。
    对应论文 §5.1.3 中信息级联的可追踪表示。
    """
    edge_id: str
    source_event_id: str        # 原因事件 ID
    target_event_id: str        # 结果事件 ID
    relation_type: str          # triggered / amplified / suppressed / correlated
    strength: float             # 因果强度 [0, 1]
    evidence: str               # 推断依据（文本解释）
    round_num: int              # 在哪一轮推断出的
    timestamp: str
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'CausalEdge':
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class CausalChain:
    """
    因果链：从某个根事件出发的完整因果路径
    """
    root_event_id: str
    chain: List[CausalEdge]
    total_strength: float       # 链上所有边强度的乘积
    description: str            # 链的文本描述
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "root_event_id": self.root_event_id,
            "chain": [e.to_dict() for e in self.chain],
            "total_strength": self.total_strength,
            "description": self.description,
        }


# ============== 因果关系类型定义 ==============

RELATION_TYPES = {
    "triggered": "直接触发",      # A 发生后直接导致 B
    "amplified": "放大效应",      # A 加剧了 B 的影响
    "suppressed": "抑制效应",     # A 抑制/缓解了 B
    "correlated": "关联效应",     # A 和 B 相关但因果方向不确定
}

# 事件类型之间的先验因果模板
# 格式: (source_type, target_type) -> (relation_type, base_strength)
CAUSAL_TEMPLATES = {
    # ── 热度飙升 ──
    ("heat_spike", "sentiment_shift"): ("triggered", 0.7),
    ("heat_spike", "trust_drop"): ("triggered", 0.5),
    ("heat_spike", "polarization_surge"): ("amplified", 0.6),
    ("heat_spike", "topic_outbreak"): ("triggered", 0.6),
    ("heat_spike", "official_response"): ("triggered", 0.5),
    
    # ── 情绪转折 ──
    ("sentiment_shift", "trust_drop"): ("triggered", 0.6),
    ("sentiment_shift", "polarization_surge"): ("amplified", 0.5),
    ("sentiment_shift", "official_response"): ("triggered", 0.4),
    ("sentiment_shift", "stabilization"): ("triggered", 0.4),
    
    # ── 信任下滑 ──
    ("trust_drop", "sentiment_shift"): ("amplified", 0.4),
    ("trust_drop", "polarization_surge"): ("amplified", 0.5),
    ("trust_drop", "official_response"): ("triggered", 0.5),
    
    # ── 官方回应 ──
    ("official_response", "sentiment_shift"): ("suppressed", 0.6),
    ("official_response", "trust_drop"): ("suppressed", 0.7),
    ("official_response", "stabilization"): ("triggered", 0.8),
    ("official_response", "calm_restored"): ("triggered", 0.7),
    ("official_response", "polarization_surge"): ("suppressed", 0.5),
    
    # ── 系统稳定 ──
    ("stabilization", "polarization_surge"): ("suppressed", 0.5),
    ("stabilization", "calm_restored"): ("triggered", 0.7),
    ("stabilization", "stabilization"): ("amplified", 0.6),
    
    # ── 极化加剧 ──
    ("polarization_surge", "stabilization"): ("suppressed", 0.4),
    ("polarization_surge", "trust_drop"): ("triggered", 0.5),
    ("polarization_surge", "official_response"): ("triggered", 0.4),
    ("polarization_surge", "sentiment_shift"): ("amplified", 0.4),
    
    # ── 恢复平稳 ──
    ("calm_restored", "stabilization"): ("triggered", 0.7),
    ("calm_restored", "calm_restored"): ("amplified", 0.5),
    ("calm_restored", "topic_outbreak"): ("suppressed", 0.4),
    ("calm_restored", "heat_spike"): ("suppressed", 0.4),
    
    # ── 议题爆发 ──
    ("topic_outbreak", "heat_spike"): ("triggered", 0.7),
    ("topic_outbreak", "sentiment_shift"): ("triggered", 0.6),
    ("topic_outbreak", "polarization_surge"): ("amplified", 0.5),
    ("topic_outbreak", "official_response"): ("triggered", 0.5),
    ("topic_outbreak", "trust_drop"): ("triggered", 0.4),
}

# 事件类型中文名
EVENT_TYPE_CN = {
    "heat_spike": "舆论热度飙升",
    "sentiment_shift": "公众情绪变化",
    "trust_drop": "公众信任下降",
    "official_response": "官方回应",
    "polarization_surge": "立场极化加剧",
    "stabilization": "系统趋于稳定",
    "calm_restored": "舆情平息",
    "topic_outbreak": "新话题爆发",
}

# 同轮或相邻轮次才考虑因果关系
MAX_ROUND_GAP = 4


# ============== 因果图谱引擎 ==============

class CausalGraphEngine:
    """
    动态因果图谱引擎
    
    采用"模板匹配 + 状态变化验证 + LLM 可选补充"的三层推断策略：
    
    1. 模板层：基于事件类型对的先验因果模板，快速匹配潜在因果边
    2. 验证层：通过状态变量的实际变化方向验证因果关系是否成立
    3. LLM 层：可选，对模板未覆盖的事件对做深层推断
    """
    
    def __init__(self, sim_dir: str, use_llm: bool = False):
        self.sim_dir = sim_dir
        self.use_llm = use_llm
        self.edges_path = os.path.join(sim_dir, "causal_edges.jsonl")
        
        # 内存存储
        self._edges: List[CausalEdge] = []
        self._adjacency: Dict[str, List[CausalEdge]] = defaultdict(list)  # event_id -> outgoing edges
        self._reverse_adj: Dict[str, List[CausalEdge]] = defaultdict(list)  # event_id -> incoming edges
        
        # 事件缓存（用于查找事件详情）
        self._events_cache: Dict[str, WorldEvent] = {}
        
        self._load_edges()
    
    def _load_edges(self):
        """从文件加载已有因果边"""
        if os.path.exists(self.edges_path):
            try:
                with open(self.edges_path, 'r', encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()
                        if line:
                            edge = CausalEdge.from_dict(json.loads(line))
                            self._edges.append(edge)
                            self._adjacency[edge.source_event_id].append(edge)
                            self._reverse_adj[edge.target_event_id].append(edge)
                logger.info(f"已加载 {len(self._edges)} 条因果边")
            except Exception as e:
                logger.warning(f"加载因果边失败: {e}")
    
    @property
    def edges(self) -> List[CausalEdge]:
        return self._edges
    
    # ============== 核心方法：因果推断 ==============
    
    def infer_causal_edges(
        self,
        new_events: List[WorldEvent],
        all_events: List[WorldEvent],
        state_history: List[WorldStateSnapshot]
    ) -> List[CausalEdge]:
        """
        从新增事件中推断因果边
        
        Args:
            new_events: 本轮新检测到的事件
            all_events: 所有历史事件
            state_history: 状态历史
            
        Returns:
            新推断出的因果边列表
        """
        # 缓存事件
        for evt in all_events:
            self._events_cache[evt.event_id] = evt
        
        new_edges = []
        
        # 1. 模板匹配 + 状态验证
        for new_evt in new_events:
            # 在历史事件中查找可能的原因事件
            for hist_evt in all_events:
                if hist_evt.event_id == new_evt.event_id:
                    continue
                
                # 时间窗口约束
                round_gap = new_evt.round_num - hist_evt.round_num
                if round_gap < 0 or round_gap > MAX_ROUND_GAP:
                    continue
                
                # 同一轮的事件也可以有因果关系（先发生的触发后发生的）
                edge = self._try_match_template(hist_evt, new_evt, state_history)
                if edge:
                    new_edges.append(edge)
        
        # 2. LLM 辅助（可选）
        if self.use_llm and new_events:
            llm_edges = self._infer_by_llm(new_events, all_events, state_history)
            # 去重：不重复已有的 source-target 对
            existing_pairs = {(e.source_event_id, e.target_event_id) for e in new_edges}
            for edge in llm_edges:
                if (edge.source_event_id, edge.target_event_id) not in existing_pairs:
                    new_edges.append(edge)
        
        # 3. 持久化
        for edge in new_edges:
            self._add_edge(edge)
        
        if new_edges:
            logger.info(f"推断出 {len(new_edges)} 条新因果边")
        
        return new_edges
    
    def _try_match_template(
        self,
        source: WorldEvent,
        target: WorldEvent,
        state_history: List[WorldStateSnapshot]
    ) -> Optional[CausalEdge]:
        """
        基于因果模板匹配 + 状态变化验证
        """
        key = (source.event_type, target.event_type)
        template = CAUSAL_TEMPLATES.get(key)
        
        if not template:
            return None
        
        relation_type, base_strength = template
        
        # 验证：检查状态变化方向是否与因果关系一致
        verified, confidence = self._verify_by_state_change(
            source, target, relation_type, state_history
        )
        
        if not verified:
            return None
        
        # 调整强度：基础强度 × 验证置信度
        final_strength = min(1.0, base_strength * confidence)
        
        # 生成证据文本
        evidence = self._generate_evidence_text(source, target, relation_type)
        
        return CausalEdge(
            edge_id=f"ce_{uuid.uuid4().hex[:12]}",
            source_event_id=source.event_id,
            target_event_id=target.event_id,
            relation_type=relation_type,
            strength=round(final_strength, 3),
            evidence=evidence,
            round_num=target.round_num,
            timestamp=datetime.now().isoformat(),
        )
    
    def _verify_by_state_change(
        self,
        source: WorldEvent,
        target: WorldEvent,
        relation_type: str,
        state_history: List[WorldStateSnapshot]
    ) -> Tuple[bool, float]:
        """
        通过状态变量变化验证因果关系
        
        Returns:
            (是否验证通过, 置信度 0-1)
        """
        if len(state_history) < 2:
            return True, 0.5  # 数据不足，给默认置信度
        
        # 找到 source 和 target 对应轮次的状态
        # 如果同一轮，比较"本轮 vs 上一轮"才能看到变化
        source_state = None
        target_state = None
        prev_state = None  # source 轮次的前一轮状态
        
        for s in state_history:
            if s.round_num == source.round_num:
                source_state = s
            if s.round_num == target.round_num:
                target_state = s
            if s.round_num == source.round_num - 1:
                prev_state = s
        
        if not source_state or not target_state:
            return True, 0.5
        
        # 同轮事件：用上一轮作为基线
        if source.round_num == target.round_num and prev_state:
            source_state = prev_state
        
        # 检查 target 事件影响的变量是否按预期方向变化
        confidence = 0.5
        
        for var_name, delta in target.affected_variables.items():
            source_val = getattr(source_state, var_name, None)
            target_val = getattr(target_state, var_name, None)
            
            if source_val is None or target_val is None:
                continue
            
            actual_delta = target_val - source_val
            
            if relation_type in ("triggered", "amplified"):
                # 触发/放大：变化方向应一致
                if (delta > 0 and actual_delta > 0) or (delta < 0 and actual_delta < 0):
                    confidence = min(1.0, confidence + 0.3)
                else:
                    confidence = max(0.0, confidence - 0.3)
            
            elif relation_type == "suppressed":
                # 抑制：变化方向应相反或减弱
                if (delta > 0 and actual_delta < 0) or (delta < 0 and actual_delta > 0):
                    confidence = min(1.0, confidence + 0.3)
                elif abs(actual_delta) < abs(delta) * 0.5:
                    confidence = min(1.0, confidence + 0.2)
        
        return confidence > 0.3, confidence
    
    def _generate_evidence_text(
        self,
        source: WorldEvent,
        target: WorldEvent,
        relation_type: str
    ) -> str:
        """生成通俗易懂的中文因果解释文本，面向非技术评委"""
        src_type_cn = EVENT_TYPE_CN.get(source.event_type, source.event_type)
        tgt_type_cn = EVENT_TYPE_CN.get(target.event_type, target.event_type)

        # 提取关键数值变化（从 description 中）
        src_desc = source.description or src_type_cn
        tgt_desc = target.description or tgt_type_cn

        if source.round_num == target.round_num:
            time_ctx = f"在第{source.round_num}轮"
        else:
            time_ctx = f"第{source.round_num}轮至第{target.round_num}轮"

        # 根据 relation_type 生成不同风格的解释
        if relation_type == "triggered":
            return (
                f"{time_ctx}，{src_desc}直接引发了{tgt_desc}。"
                f"前一事件的发生为后续变化创造了条件，两者在时间上紧密衔接、因果关系明确。"
            )
        elif relation_type == "amplified":
            return (
                f"{time_ctx}，{src_desc}进一步放大了{tgt_desc}的影响程度。"
                f"前序事件积累的效应使后续变化更加剧烈，呈现出逐步升级的趋势。"
            )
        elif relation_type == "suppressed":
            return (
                f"{time_ctx}，{src_desc}对{tgt_desc}起到了抑制或缓解作用。"
                f"干预措施的介入有效减弱了负面趋势的进一步扩散。"
            )
        else:  # correlated
            return (
                f"{time_ctx}，{src_desc}与{tgt_desc}存在显著关联。"
                f"两者在时间窗口内同步变化，具有统计上的相关性。"
            )
    
    # ============== LLM 辅助推断 ==============
    
    def _infer_by_llm(
        self,
        new_events: List[WorldEvent],
        all_events: List[WorldEvent],
        state_history: List[WorldStateSnapshot]
    ) -> List[CausalEdge]:
        """使用 LLM 推断模板未覆盖的因果关系"""
        edges = []
        
        try:
            from openai import OpenAI
            import re
            
            client = OpenAI(
                api_key=Config.LLM_API_KEY,
                base_url=Config.LLM_BASE_URL
            )
            
            # 构造事件列表（全中文，隐藏原始 ID）
            id_alias = {}  # evt_xxx -> "事件A" 映射
            events_desc = []
            for i, evt in enumerate(all_events[-15:]):
                alias = f"事件{chr(65 + i)}"  # 事件A, 事件B, ...
                id_alias[evt.event_id] = alias
                type_cn = EVENT_TYPE_CN.get(evt.event_type, evt.event_type)
                sev_label = "高" if evt.severity > 0.6 else ("中" if evt.severity > 0.3 else "低")
                events_desc.append(
                    f"[{alias}] 第{evt.round_num}轮 | "
                    f"类型：{type_cn} | {evt.description} | 严重程度：{sev_label}"
                )
            events_text = "\n".join(events_desc)

            new_ids = {e.event_id for e in new_events}
            new_aliases = [id_alias.get(eid, eid) for eid in new_ids]
            existing_pairs = {(e.source_event_id, e.target_event_id) for e in self._edges}
            existing_alias_pairs = [
                f"{id_alias.get(e.source_event_id, '?')} -> {id_alias.get(e.target_event_id, '?')}"
                for e in self._edges[-10:]
                if e.source_event_id in id_alias or e.target_event_id in id_alias
            ]

            prompt = f"""你是一位面向政府决策者和学术评委的舆情因果分析专家。请用通俗易懂的中文分析以下事件之间的因果关系。

事件列表（按时间顺序）：
{events_text}

本轮新增事件：{new_aliases}

已知因果关系（请勿重复）：
{existing_alias_pairs}

请找出新增事件与历史事件之间的因果关系。输出JSON数组：
```json
[
  {{
    "source_id": "原因事件别名，如事件A",
    "target_id": "结果事件别名，如事件C",
    "relation": "triggered/amplified/suppressed/correlated",
    "strength": 0.0到1.0,
    "evidence": "通俗中文因果解释"
  }}
]
```

严格规则：
1. 只输出有较高把握的因果关系（strength >= 0.4）
2. target_id必须是本轮新增事件之一
3. 不要重复已有的因果关系
4. evidence字段要求：
   - 全部使用中文，严禁出现任何英文单词、事件ID、技术代号
   - 用日常用语解释因果逻辑，让非专业人士也能读懂
   - 说明"因为什么→所以什么"的逻辑链条
   - 适当引用具体数值变化来佐证（如"信任度从0.4上升到0.6"）
5. 只输出JSON数组，不要其他内容"""

            response = client.chat.completions.create(
                model=Config.LLM_MODEL_NAME,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=500,
            )
            
            result_text = response.choices[0].message.content.strip()
            json_match = re.search(r'\[.*\]', result_text, re.DOTALL)
            
            if json_match:
                inferred = json.loads(json_match.group())
                for item in inferred:
                    src_id = item.get("source_id", "")
                    tgt_id = item.get("target_id", "")
                    
                    if not src_id or not tgt_id:
                        continue
                    if tgt_id not in new_ids:
                        continue
                    if (src_id, tgt_id) in existing_pairs:
                        continue
                    
                    relation = item.get("relation", "correlated")
                    if relation not in RELATION_TYPES:
                        relation = "correlated"
                    
                    # 将别名映射回真实 event_id
                    real_src = None
                    real_tgt = None
                    for real_id, alias in id_alias.items():
                        if alias == src_id:
                            real_src = real_id
                        if alias == tgt_id:
                            real_tgt = real_id
                    if not real_src or not real_tgt:
                        continue
                    if real_tgt not in new_ids:
                        continue
                    if (real_src, real_tgt) in existing_pairs:
                        continue

                    # 二次清洗 evidence：移除可能残留的英文
                    raw_evidence = item.get("evidence", "模型推断的因果关系")
                    import re as re2
                    raw_evidence = re2.sub(r'\b(?:evt_|ce_)[a-f0-9]+\b', '', raw_evidence)
                    raw_evidence = re2.sub(r'\b(?:Round|round|severity|strength)\b', '', raw_evidence)
                    raw_evidence = re2.sub(r'\s{2,}', ' ', raw_evidence).strip()

                    edges.append(CausalEdge(
                        edge_id=f"ce_{uuid.uuid4().hex[:12]}",
                        source_event_id=real_src,
                        target_event_id=real_tgt,
                        relation_type=relation,
                        strength=min(1.0, max(0.0, float(item.get("strength", 0.5)))),
                        evidence=raw_evidence or "模型推断的因果关系",
                        round_num=max(e.round_num for e in new_events),
                        timestamp=datetime.now().isoformat(),
                    ))
                    
        except Exception as e:
            logger.warning(f"LLM 因果推断失败: {e}")
        
        return edges
    
    # ============== 查询接口 ==============
    
    def get_causal_chain(self, event_id: str, max_depth: int = 5) -> List[CausalChain]:
        """
        获取以某事件为根的因果链（正向：该事件导致了什么）
        """
        chains = []
        self._dfs_forward(event_id, [], set(), chains, max_depth)
        return chains
    
    def get_cause_chain(self, event_id: str, max_depth: int = 5) -> List[CausalChain]:
        """
        获取某事件的原因链（反向：什么导致了该事件）
        """
        chains = []
        self._dfs_backward(event_id, [], set(), chains, max_depth)
        return chains
    
    def _dfs_forward(
        self, 
        event_id: str, 
        path: List[CausalEdge], 
        visited: Set[str],
        chains: List[CausalChain],
        max_depth: int
    ):
        """正向 DFS 遍历因果图"""
        if len(path) >= max_depth:
            return
        
        outgoing = self._adjacency.get(event_id, [])
        if not outgoing and path:
            # 叶节点，生成链
            total_strength = 1.0
            for e in path:
                total_strength *= e.strength
            chains.append(CausalChain(
                root_event_id=path[0].source_event_id,
                chain=list(path),
                total_strength=round(total_strength, 3),
                description=self._describe_chain(path),
            ))
            return
        
        for edge in outgoing:
            if edge.target_event_id not in visited:
                visited.add(edge.target_event_id)
                path.append(edge)
                self._dfs_forward(edge.target_event_id, path, visited, chains, max_depth)
                path.pop()
                visited.discard(edge.target_event_id)
        
        # 如果有分支但也有路径，记录当前路径
        if path and not outgoing:
            pass  # 已在上面处理
    
    def _dfs_backward(
        self, 
        event_id: str, 
        path: List[CausalEdge], 
        visited: Set[str],
        chains: List[CausalChain],
        max_depth: int
    ):
        """反向 DFS 遍历因果图"""
        if len(path) >= max_depth:
            return
        
        incoming = self._reverse_adj.get(event_id, [])
        if not incoming and path:
            total_strength = 1.0
            for e in path:
                total_strength *= e.strength
            chains.append(CausalChain(
                root_event_id=path[-1].source_event_id,
                chain=list(reversed(path)),
                total_strength=round(total_strength, 3),
                description=self._describe_chain(list(reversed(path))),
            ))
            return
        
        for edge in incoming:
            if edge.source_event_id not in visited:
                visited.add(edge.source_event_id)
                path.append(edge)
                self._dfs_backward(edge.source_event_id, path, visited, chains, max_depth)
                path.pop()
                visited.discard(edge.source_event_id)
    
    def _describe_chain(self, chain: List[CausalEdge]) -> str:
        """生成因果链的通俗中文描述"""
        if not chain:
            return ""
        
        parts = []
        for i, edge in enumerate(chain):
            src_evt = self._events_cache.get(edge.source_event_id)
            tgt_evt = self._events_cache.get(edge.target_event_id)
            
            src_type_cn = EVENT_TYPE_CN.get(src_evt.event_type, '') if src_evt else ''
            tgt_type_cn = EVENT_TYPE_CN.get(tgt_evt.event_type, '') if tgt_evt else ''
            src_desc = src_type_cn or (src_evt.description[:20] if src_evt else '未知事件')
            tgt_desc = tgt_type_cn or (tgt_evt.description[:20] if tgt_evt else '未知事件')
            relation_cn = RELATION_TYPES.get(edge.relation_type, edge.relation_type)
            
            if i == 0:
                src_round = f"第{src_evt.round_num}轮" if src_evt else ''
                parts.append(f"{src_round}{src_desc}")
            tgt_round = f"第{tgt_evt.round_num}轮" if tgt_evt else ''
            parts.append(f" →({relation_cn})→ {tgt_round}{tgt_desc}")
        
        return "".join(parts)
    
    def get_edges_in_range(self, from_round: int, to_round: int) -> List[CausalEdge]:
        """获取指定轮次范围内的因果边"""
        return [e for e in self._edges if from_round <= e.round_num <= to_round]
    
    def get_graph_summary(self) -> Dict[str, Any]:
        """获取因果图摘要"""
        type_counts = defaultdict(int)
        for edge in self._edges:
            type_counts[edge.relation_type] += 1
        
        return {
            "total_edges": len(self._edges),
            "total_events": len(self._events_cache),
            "relation_type_counts": dict(type_counts),
            "edges": [e.to_dict() for e in self._edges],
        }
    
    # ============== 持久化 ==============
    
    def _add_edge(self, edge: CausalEdge):
        """添加因果边"""
        self._edges.append(edge)
        self._adjacency[edge.source_event_id].append(edge)
        self._reverse_adj[edge.target_event_id].append(edge)
        
        try:
            os.makedirs(os.path.dirname(self.edges_path) or '.', exist_ok=True)
            with open(self.edges_path, 'a', encoding='utf-8') as f:
                f.write(json.dumps(edge.to_dict(), ensure_ascii=False) + '\n')
        except Exception as e:
            logger.error(f"保存因果边失败: {e}")
