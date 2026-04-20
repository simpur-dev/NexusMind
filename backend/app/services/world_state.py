"""
世界状态引擎（World State Engine）

基于论文 "From Individual to Society" (Mou et al., 2026) §4.1.1 Environment State：
"environment states record instant information from the environment during the scenario.
 They directly influence the agents' decision-making and behavior."

核心功能：
1. 每轮从 Agent 动作中提取观测信号
2. 基于规则 + LLM 混合策略计算 6 维世界状态
3. 检测关键世界事件（对应论文 §5.1.3 Social Influence 中的信息级联）
4. 持久化状态历史和事件到本地文件（JSONL）
"""

import os
import json
import re
import uuid
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field, asdict
from datetime import datetime
from collections import Counter

from ..config import Config
from ..utils.logger import get_logger

logger = get_logger('nexusmind.world_state')


# ============== 数据结构 ==============

@dataclass
class WorldStateSnapshot:
    """
    世界状态快照
    
    对应论文 §4.1.1 Environment State：
    即时环境状态，直接影响 Agent 决策与行为。
    
    6 维核心状态变量，取值范围 [0.0, 1.0]：
    - attention_level:    关注度/热度
    - panic_level:        恐慌/负面情绪扩散
    - trust_level:        对权威/官方的信任程度
    - polarization_level: 立场极化程度
    - risk_level:         综合风险等级
    - stability_level:    系统稳定性
    """
    round_num: int
    timestamp: str
    
    # 核心状态变量（6 维）
    attention_level: float = 0.1
    panic_level: float = 0.1
    trust_level: float = 0.6
    polarization_level: float = 0.1
    risk_level: float = 0.1
    stability_level: float = 0.8
    
    # 观测信号（用于推导状态变量）
    total_posts: int = 0
    total_comments: int = 0
    total_reposts: int = 0
    total_likes: int = 0
    active_agent_count: int = 0
    top_keywords: List[str] = field(default_factory=list)
    sentiment_distribution: Dict[str, float] = field(
        default_factory=lambda: {"positive": 0.33, "negative": 0.33, "neutral": 0.34}
    )
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'WorldStateSnapshot':
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})
    
    def get_state_vector(self) -> Dict[str, float]:
        """返回 6 维状态向量"""
        return {
            "attention_level": self.attention_level,
            "panic_level": self.panic_level,
            "trust_level": self.trust_level,
            "polarization_level": self.polarization_level,
            "risk_level": self.risk_level,
            "stability_level": self.stability_level,
        }
    
    def get_state_summary_text(self) -> str:
        """
        生成可注入 Agent prompt 的状态摘要文本
        
        对应论文 §4.1.1：环境状态需要可被 Agent 感知
        """
        level_desc = {
            (0.0, 0.2): "很低",
            (0.2, 0.4): "较低",
            (0.4, 0.6): "中等",
            (0.6, 0.8): "较高",
            (0.8, 1.01): "很高",
        }
        
        def describe(val: float) -> str:
            for (lo, hi), desc in level_desc.items():
                if lo <= val < hi:
                    return desc
            return "未知"
        
        return (
            f"当前环境状态（第{self.round_num}轮）：\n"
            f"- 舆论关注度: {describe(self.attention_level)}（{self.attention_level:.2f}）\n"
            f"- 恐慌程度: {describe(self.panic_level)}（{self.panic_level:.2f}）\n"
            f"- 公众信任度: {describe(self.trust_level)}（{self.trust_level:.2f}）\n"
            f"- 立场极化度: {describe(self.polarization_level)}（{self.polarization_level:.2f}）\n"
            f"- 风险等级: {describe(self.risk_level)}（{self.risk_level:.2f}）\n"
            f"- 系统稳定性: {describe(self.stability_level)}（{self.stability_level:.2f}）"
        )


@dataclass
class WorldEvent:
    """
    世界事件
    
    对应论文 §5.1.3 Social Influence 中的信息级联与群体涌现：
    从 Agent 动作流中抽象出的关键状态变化事件。
    """
    event_id: str
    round_num: int
    timestamp: str
    event_type: str     # topic_outbreak / heat_spike / sentiment_shift /
                        # official_response / trust_drop / stabilization / 
                        # polarization_surge / calm_restored
    description: str
    severity: float     # [0, 1]
    affected_variables: Dict[str, float] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'WorldEvent':
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


# ============== 负面/正面关键词表 ==============

NEGATIVE_KEYWORDS = [
    # 情绪类
    "恐慌", "愤怒", "失望", "害怕", "担心", "紧张", "焦虑", "不满", "抗议",
    "愤慨", "气愤", "震惊", "悲愤", "痛心", "寒心", "心寒", "无语", "荒谬",
    # 舆论场常见表达
    "质疑", "不公", "不公正", "黑幕", "内幕", "包庇", "纵容", "失职", "渎职",
    "推诿", "甩锅", "敷衍", "欺骗", "隐瞒", "造假", "弄虚作假", "走过场",
    # 需求/诉求类（在舆情爆发期表达的是不满，不是正面情绪）
    "问责", "要求问责", "追责", "维权", "讨说法",
    "反思", "深刻反思", "引以为戒",
    "还原真相", "真相是什么", "凭什么", "为什么",
    "不合理", "不透明", "不规范", "不当",
    # 校园/学术争议
    "处分", "冤枉", "不当处分", "学术不端", "抄袭", "论文造假", "学术造假",
    "学术腐败", "学阀", "打压", "霸凌", "校园霸凌",
    # 网络舆论
    "网暴", "人肉搜索", "带节奏", "反转", "打脸", "翻车", "塌房",
    "谣言", "假消息", "骗局", "造谣", "传谣", "不实信息",
    # 社会事件
    "危险", "崩溃", "混乱", "暴力", "冲突", "歧视", "不作为", "乱作为",
    "scandal", "fear", "anger", "panic", "fake", "rumor", "crisis", "danger",
    "corrupt", "riot", "violence", "protest", "collapse", "chaos",
    "controversy", "outrage", "backlash", "misconduct", "injustice",
    "accountability", "why", "unfair", "demand",
]

POSITIVE_KEYWORDS = [
    # 情绪类（真正的正面情绪）
    "支持", "赞同", "感谢", "信任", "希望", "安心", "稳定", "改善", "帮助",
    "欣慰", "点赞", "认可", "肯定", "赞扬", "表扬", "鼓励",
    # 官方实际纠正行动（已发生的正面事实，非诉求）
    "官方回应", "澄清", "辟谣", "解决", "改进", "合作", "团结",
    "纠错", "纠正", "撤销处分", "道歉", "致歉", "整改",
    "有错必纠", "公开透明", "依法处理",
    # 理性讨论（真正的正向信号）
    "理性", "客观", "就事论事", "进步", "改革",
    "法治", "制度完善",
    "support", "trust", "hope", "stable", "improve", "help", "official",
    "clarify", "resolve", "cooperate", "reform", "progress",
]

AUTHORITY_KEYWORDS = [
    "官方", "通知", "声明", "公告", "通报", "回应", "政策", "规定", "措施",
    "official", "statement", "announcement", "policy", "response", "authority",
]


# ============== 世界状态引擎 ==============

class WorldStateEngine:
    """
    世界状态引擎
    
    采用"规则为主 + LLM 为辅"的混合策略：
    - 规则层：基于动作统计和关键词匹配，快速计算状态变量（每轮调用）
    - LLM 层：每 N 轮做一次深层语义判断（可选，降低 API 开销）
    """
    
    # LLM 评估间隔（每隔多少轮调用一次 LLM 做深层判断）
    LLM_EVAL_INTERVAL = 5
    
    # 状态变化的平滑系数（越小越平滑，防止剧烈波动）
    SMOOTHING_FACTOR = 0.3
    
    # 事件检测阈值
    EVENT_THRESHOLDS = {
        "heat_spike": 0.15,           # attention 单轮上升超过此值
        "sentiment_shift": 0.12,      # panic 单轮变化超过此值
        "trust_drop": 0.10,           # trust 单轮下降超过此值
        "polarization_surge": 0.12,   # polarization 单轮上升超过此值
        "stabilization": 0.10,        # stability 单轮上升超过此值
    }
    
    INJECTED_EVENTS_FILE = "injected_events.json"
    
    def __init__(self, sim_dir: str, use_llm: bool = True):
        """
        初始化世界状态引擎
        
        Args:
            sim_dir: 模拟数据目录路径
            use_llm: 是否启用 LLM 辅助判断
        """
        self.sim_dir = sim_dir
        self.use_llm = use_llm
        self.state_history_path = os.path.join(sim_dir, "world_state_history.jsonl")
        self.events_path = os.path.join(sim_dir, "events.jsonl")
        self.injected_events_path = os.path.join(sim_dir, self.INJECTED_EVENTS_FILE)
        
        # 内存中的状态历史
        self._state_history: List[WorldStateSnapshot] = []
        self._events: List[WorldEvent] = []
        
        # 基线统计（用于相对变化计算）
        self._baseline_posts_per_round: float = 0.0
        self._baseline_comments_per_round: float = 0.0
        self._rounds_observed: int = 0
        
        # 因果图谱引擎（延迟初始化）
        self._causal_engine = None
        
        # 加载已有历史
        self._load_history()
    
    def _load_history(self):
        """从文件加载已有状态历史"""
        if os.path.exists(self.state_history_path):
            try:
                with open(self.state_history_path, 'r', encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()
                        if line:
                            self._state_history.append(
                                WorldStateSnapshot.from_dict(json.loads(line))
                            )
                logger.info(f"已加载 {len(self._state_history)} 条世界状态历史")
            except Exception as e:
                logger.warning(f"加载世界状态历史失败: {e}")
        
        if os.path.exists(self.events_path):
            try:
                with open(self.events_path, 'r', encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()
                        if line:
                            self._events.append(
                                WorldEvent.from_dict(json.loads(line))
                            )
                logger.info(f"已加载 {len(self._events)} 条世界事件")
            except Exception as e:
                logger.warning(f"加载世界事件失败: {e}")
    
    @property
    def current_state(self) -> Optional[WorldStateSnapshot]:
        """获取当前最新状态"""
        return self._state_history[-1] if self._state_history else None
    
    @property
    def state_history(self) -> List[WorldStateSnapshot]:
        """获取完整状态历史"""
        return self._state_history
    
    @property
    def events(self) -> List[WorldEvent]:
        """获取完整事件列表"""
        return self._events
    
    @property
    def causal_graph(self):
        """获取因果图谱引擎（延迟初始化）"""
        if self._causal_engine is None:
            from .causal_graph import CausalGraphEngine
            self._causal_engine = CausalGraphEngine(
                sim_dir=self.sim_dir, use_llm=self.use_llm
            )
        return self._causal_engine
    
    # ============== 核心方法：状态更新 ==============
    
    def update_state(
        self,
        round_num: int,
        actions: List[Dict[str, Any]],
        prev_state: Optional[WorldStateSnapshot] = None
    ) -> Tuple[WorldStateSnapshot, List[WorldEvent]]:
        """
        基于本轮动作和上一轮状态，计算新的世界状态
        
        Args:
            round_num: 当前轮次
            actions: 本轮所有 Agent 动作（字典列表）
            prev_state: 上一轮状态（None 则取内存历史中最新的）
            
        Returns:
            (新状态快照, 本轮检测到的事件列表)
        """
        if prev_state is None:
            prev_state = self.current_state
        
        # 1. 提取观测信号
        observations = self._extract_observations(actions)
        
        # 2. 更新基线统计
        self._update_baseline(observations)
        
        # 3. 计算新状态（规则层）
        new_state = self._compute_state_by_rules(round_num, observations, prev_state)
        
        # 4. LLM 辅助判断（每 N 轮）
        if self.use_llm and round_num > 0 and round_num % self.LLM_EVAL_INTERVAL == 0:
            new_state = self._refine_state_by_llm(new_state, actions, prev_state)
        
        # 5. 消费注入事件（上帝视角）
        injected_events = self._consume_injected_events(round_num, new_state)
        
        # 6. 检测自然事件
        new_events = self._detect_events(new_state, prev_state, observations)
        
        # 合并注入事件和自然事件
        new_events = injected_events + new_events
        
        # 7. 持久化
        self._append_state(new_state)
        for event in new_events:
            self._append_event(event)
        
        # 7. 因果推断
        if new_events:
            try:
                cg = self.causal_graph
                cg.infer_causal_edges(new_events, self._events, self._state_history)
            except Exception as e:
                logger.warning(f"[Round {round_num}] 因果推断失败: {e}")
        
        if new_events:
            logger.info(
                f"[Round {round_num}] 世界状态已更新，检测到 {len(new_events)} 个事件: "
                f"{[e.event_type for e in new_events]}"
            )
        else:
            logger.debug(f"[Round {round_num}] 世界状态已更新，无新事件")
        
        return new_state, new_events
    
    # ============== 注入事件消费 ==============
    
    def _consume_injected_events(
        self,
        round_num: int,
        state: WorldStateSnapshot
    ) -> List[WorldEvent]:
        """
        读取并消费 injected_events.json 队列中的注入事件（上帝视角）
        
        流程：
        1. 读取队列文件
        2. 将每个注入事件的 affected_variables 增量应用到 state
        3. 将每个注入事件转换为 WorldEvent
        4. 清空队列文件
        
        Args:
            round_num: 当前轮次
            state: 当前计算出的世界状态（将被就地修改）
            
        Returns:
            转换后的 WorldEvent 列表
        """
        if not os.path.exists(self.injected_events_path):
            return []
        
        try:
            with open(self.injected_events_path, 'r', encoding='utf-8') as f:
                raw_events = json.load(f)
        except (json.JSONDecodeError, OSError):
            return []
        
        if not raw_events:
            return []
        
        # 清空队列（原子写入空列表）
        try:
            tmp_path = self.injected_events_path + ".tmp"
            with open(tmp_path, 'w', encoding='utf-8') as f:
                json.dump([], f)
            os.replace(tmp_path, self.injected_events_path)
        except OSError as e:
            logger.warning(f"清空注入事件队列失败: {e}")
        
        # 状态变量名集合（用于验证 affected_variables）
        state_vars = {
            "attention_level", "panic_level", "trust_level",
            "polarization_level", "risk_level", "stability_level"
        }
        
        world_events: List[WorldEvent] = []
        
        for raw in raw_events:
            event_type = raw.get("event_type", "custom")
            description = raw.get("description", "")
            severity = max(0.0, min(1.0, raw.get("severity", 0.7)))
            affected = raw.get("affected_variables", {})
            
            # 应用状态变量增量
            applied_deltas = {}
            for var_name, delta in affected.items():
                if var_name in state_vars and isinstance(delta, (int, float)):
                    old_val = getattr(state, var_name, 0.5)
                    new_val = max(0.0, min(1.0, old_val + delta))
                    setattr(state, var_name, new_val)
                    applied_deltas[var_name] = delta
            
            # 转换为 WorldEvent
            we = WorldEvent(
                event_id=f"inject_{uuid.uuid4().hex[:8]}",
                round_num=round_num,
                timestamp=raw.get("timestamp", datetime.now().isoformat()),
                event_type=f"injected_{event_type}",
                description=f"[上帝视角] {description}",
                severity=severity,
                affected_variables=applied_deltas
            )
            world_events.append(we)
            
            logger.info(
                f"[Round {round_num}] 消费注入事件: type={event_type}, "
                f"severity={severity:.2f}, deltas={applied_deltas}"
            )
        
        return world_events
    
    # ============== 观测信号提取 ==============
    
    def _extract_observations(self, actions: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        从本轮动作中提取观测信号
        
        对应论文 §4.1.1：环境观测 = 环境变化 + 当前实体状态
        """
        posts = 0
        comments = 0
        reposts = 0
        likes = 0
        active_agents = set()
        all_text = []
        
        for action in actions:
            action_type = action.get("action_type", "").upper()
            agent_id = action.get("agent_id")
            args = action.get("action_args", {})
            
            if agent_id is not None:
                active_agents.add(agent_id)
            
            # 统计动作类型
            if "POST" in action_type or "CREATE" in action_type:
                posts += 1
                content = args.get("content", "") or args.get("text", "")
                if content:
                    all_text.append(content)
            elif "COMMENT" in action_type or "REPLY" in action_type:
                comments += 1
                content = args.get("content", "") or args.get("text", "")
                if content:
                    all_text.append(content)
            elif "REPOST" in action_type or "RETWEET" in action_type or "SHARE" in action_type:
                reposts += 1
            elif "LIKE" in action_type or "UPVOTE" in action_type:
                likes += 1
        
        # 关键词分析
        combined_text = " ".join(all_text)
        neg_count = sum(1 for kw in NEGATIVE_KEYWORDS if kw in combined_text.lower())
        pos_count = sum(1 for kw in POSITIVE_KEYWORDS if kw in combined_text.lower())
        auth_count = sum(1 for kw in AUTHORITY_KEYWORDS if kw in combined_text.lower())
        total_kw = max(neg_count + pos_count, 1)
        
        # 情感分布估计
        neg_ratio = neg_count / total_kw
        pos_ratio = pos_count / total_kw
        neutral_ratio = max(0, 1.0 - neg_ratio - pos_ratio)
        
        # 提取高频词（中文按 2-4 字符 n-gram 切分，英文按单词）
        cn_chars = re.findall(r'[\u4e00-\u9fff]+', combined_text)
        cn_ngrams = []
        for seg in cn_chars:
            for n in (2, 3, 4):
                for i in range(len(seg) - n + 1):
                    cn_ngrams.append(seg[i:i+n])
        en_words = re.findall(r'[a-zA-Z]{2,}', combined_text)
        word_counts = Counter(cn_ngrams + en_words)
        # 过滤掉过于常见的停用词
        stopwords = {'的', '了', '是', '在', '我', '有', '和', '就', '不', '人', '都', '一', '一个', '上', '也', '很', '到', '说', '要', '去', '你', '会', '着', '没有', '看', '好', '自己', '这'}
        top_keywords = [
            w for w, _ in word_counts.most_common(30) if w not in stopwords
        ][:10]
        
        return {
            "posts": posts,
            "comments": comments,
            "reposts": reposts,
            "likes": likes,
            "active_agent_count": len(active_agents),
            "neg_ratio": neg_ratio,
            "pos_ratio": pos_ratio,
            "neutral_ratio": neutral_ratio,
            "auth_count": auth_count,
            "top_keywords": top_keywords,
            "text_count": len(all_text),
            "combined_text_sample": combined_text[:500],
        }
    
    def _update_baseline(self, obs: Dict[str, Any]):
        """更新基线统计（滑动平均）"""
        self._rounds_observed += 1
        alpha = 0.2  # 滑动平均系数
        
        if self._rounds_observed == 1:
            self._baseline_posts_per_round = obs["posts"]
            self._baseline_comments_per_round = obs["comments"]
        else:
            self._baseline_posts_per_round = (
                (1 - alpha) * self._baseline_posts_per_round + alpha * obs["posts"]
            )
            self._baseline_comments_per_round = (
                (1 - alpha) * self._baseline_comments_per_round + alpha * obs["comments"]
            )
    
    # ============== 规则层状态计算 ==============
    
    def _compute_state_by_rules(
        self,
        round_num: int,
        obs: Dict[str, Any],
        prev: Optional[WorldStateSnapshot]
    ) -> WorldStateSnapshot:
        """
        基于规则计算世界状态
        
        规则设计依据：
        - attention ← 发帖/评论量相对基线的偏移
        - panic ← 负面关键词占比 + 转发加速
        - trust ← 权威关键词出现 + 正面情感
        - polarization ← 正负情感比例的方差
        - risk ← attention × panic × (1 - trust) 的综合
        - stability ← 1 - (attention_delta + panic_delta + polarization_delta) / 3
        """
        if prev is None:
            # 初始状态：基于首轮动作计算，不硬编码
            init_activity = obs["posts"] + obs["comments"] + obs["reposts"]
            init_attention = min(1.0, init_activity * 0.05)
            init_panic = min(1.0, obs["neg_ratio"] * 0.6)
            init_auth = min(obs.get("auth_count", 0) * 0.05, 0.2)
            init_neg_erosion = obs["neg_ratio"] * 0.3
            init_trust = min(1.0, max(0.1, 0.3 + obs["pos_ratio"] * 0.3 + init_auth - init_neg_erosion))
            init_polar = min(1.0, min(obs["pos_ratio"], obs["neg_ratio"]) * 2 * 0.6)
            init_risk = min(1.0, init_attention * 0.3 + init_panic * 0.4 + (1 - init_trust) * 0.3)
            init_stab = max(0.0, 1.0 - init_panic * 0.5 - init_polar * 0.3)
            return WorldStateSnapshot(
                round_num=round_num,
                timestamp=datetime.now().isoformat(),
                attention_level=init_attention,
                panic_level=init_panic,
                trust_level=init_trust,
                polarization_level=init_polar,
                risk_level=init_risk,
                stability_level=init_stab,
                total_posts=obs["posts"],
                total_comments=obs["comments"],
                total_reposts=obs["reposts"],
                total_likes=obs["likes"],
                active_agent_count=obs["active_agent_count"],
                top_keywords=obs["top_keywords"],
                sentiment_distribution={
                    "positive": obs["pos_ratio"],
                    "negative": obs["neg_ratio"],
                    "neutral": obs["neutral_ratio"],
                },
            )
        
        # --- 计算各状态变量的原始目标值 ---
        
        # attention: 基于活动量相对基线的偏移
        baseline = max(self._baseline_posts_per_round + self._baseline_comments_per_round, 1)
        current_activity = obs["posts"] + obs["comments"] + obs["reposts"]
        activity_ratio = current_activity / baseline
        attention_target = min(1.0, activity_ratio * 0.4)
        
        # panic: 基于负面情感比例 + 转发量
        repost_boost = min(obs["reposts"] / max(baseline, 1), 0.3)
        panic_target = min(1.0, obs["neg_ratio"] * 0.8 + repost_boost)
        
        # trust: 基线降低 + 负面情绪会侥蚀信任
        auth_boost = min(obs["auth_count"] * 0.05, 0.2)
        neg_erosion = obs["neg_ratio"] * 0.3  # 负面情绪侥蚀信任
        trust_target = min(1.0, max(0.1, 0.2 + obs["pos_ratio"] * 0.4 + auth_boost - neg_erosion))
        
        # polarization: 衡量群体内部分歧（双方都有声量时才算极化）
        # 用 min(pos, neg) 衡量"对立双方中较弱一方的强度"，双方都强=高极化
        minority_ratio = min(obs["pos_ratio"], obs["neg_ratio"])
        # minority_ratio 接近 0.5 = 最极化；接近 0 = 一边倒（低极化）
        polarization_target = min(1.0, minority_ratio * 2 * 0.8)
        # 极化有惯性：如果之前已极化，不会立刻消失
        if prev.polarization_level > polarization_target:
            polarization_target = prev.polarization_level * 0.85 + polarization_target * 0.15
        
        # risk: 综合指标
        risk_target = min(1.0, attention_target * 0.3 + panic_target * 0.4 + (1 - trust_target) * 0.3)
        
        # stability: 区分正向变化和负向变化
        # 恐慌下降、信任上升是"好的变化"，不应拉低稳定性
        negative_deltas = []  # 只统计"恶化方向"的变化
        if attention_target > prev.attention_level:
            negative_deltas.append(attention_target - prev.attention_level)
        if panic_target > prev.panic_level:
            negative_deltas.append(panic_target - prev.panic_level)
        if polarization_target > prev.polarization_level:
            negative_deltas.append(polarization_target - prev.polarization_level)
        if trust_target < prev.trust_level:
            negative_deltas.append(prev.trust_level - trust_target)
        
        # 正向变化给稳定性加分
        positive_signals = []
        if panic_target < prev.panic_level:
            positive_signals.append(prev.panic_level - panic_target)
        if trust_target > prev.trust_level:
            positive_signals.append(trust_target - prev.trust_level)
        
        neg_avg = sum(negative_deltas) / max(len(negative_deltas), 1)
        pos_avg = sum(positive_signals) / max(len(positive_signals), 1)
        stability_target = max(0.0, min(1.0, 1.0 - neg_avg * 3 + pos_avg * 1.5))
        
        # --- 平滑更新 ---
        s = self.SMOOTHING_FACTOR
        
        new_state = WorldStateSnapshot(
            round_num=round_num,
            timestamp=datetime.now().isoformat(),
            attention_level=self._clamp(prev.attention_level * (1 - s) + attention_target * s),
            panic_level=self._clamp(prev.panic_level * (1 - s) + panic_target * s),
            trust_level=self._clamp(prev.trust_level * (1 - s) + trust_target * s),
            polarization_level=self._clamp(prev.polarization_level * (1 - s) + polarization_target * s),
            risk_level=self._clamp(prev.risk_level * (1 - s) + risk_target * s),
            stability_level=self._clamp(prev.stability_level * (1 - s) + stability_target * s),
            total_posts=obs["posts"],
            total_comments=obs["comments"],
            total_reposts=obs["reposts"],
            total_likes=obs["likes"],
            active_agent_count=obs["active_agent_count"],
            top_keywords=obs["top_keywords"],
            sentiment_distribution={
                "positive": obs["pos_ratio"],
                "negative": obs["neg_ratio"],
                "neutral": obs["neutral_ratio"],
            },
        )
        
        return new_state
    
    # ============== LLM 辅助判断 ==============
    
    def _refine_state_by_llm(
        self,
        state: WorldStateSnapshot,
        actions: List[Dict[str, Any]],
        prev_state: Optional[WorldStateSnapshot]
    ) -> WorldStateSnapshot:
        """
        使用 LLM 对规则层计算的状态做修正
        
        每 N 轮调用一次，避免 API 开销过大。
        LLM 负责判断规则难以捕捉的深层语义（如隐含讽刺、话题转向等）。
        """
        try:
            from openai import OpenAI
            
            client = OpenAI(
                api_key=Config.LLM_API_KEY,
                base_url=Config.LLM_BASE_URL
            )
            
            # 构造动作摘要（限制长度）
            action_summaries = []
            for a in actions[:30]:
                atype = a.get("action_type", "")
                agent = a.get("agent_name", "")
                content = a.get("action_args", {}).get("content", "")
                if content:
                    content = content[:100]
                action_summaries.append(f"[{agent}] {atype}: {content}")
            actions_text = "\n".join(action_summaries)
            
            prev_desc = ""
            if prev_state:
                prev_desc = prev_state.get_state_summary_text()
            
            prompt = f"""你是一个社会模拟世界状态评估器。请根据以下本轮Agent动作摘要和上一轮状态，对当前世界状态做微调。

上一轮状态：
{prev_desc}

当前规则计算状态：
{state.get_state_summary_text()}

本轮关键动作（最多30条）：
{actions_text}

请评估规则计算是否合理，输出 JSON 格式的微调量（每个变量的调整值在 -0.1 到 +0.1 之间，0 表示不调整）：
```json
{{
  "attention_adj": 0.0,
  "panic_adj": 0.0,
  "trust_adj": 0.0,
  "polarization_adj": 0.0,
  "risk_adj": 0.0,
  "stability_adj": 0.0,
  "reasoning": "简要说明调整理由"
}}
```

只输出 JSON，不要输出其他内容。"""

            response = client.chat.completions.create(
                model=Config.LLM_MODEL_NAME,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=300,
            )
            
            result_text = response.choices[0].message.content.strip()
            # 提取 JSON
            json_match = re.search(r'\{[^{}]+\}', result_text, re.DOTALL)
            if json_match:
                adjustments = json.loads(json_match.group())
                
                state.attention_level = self._clamp(
                    state.attention_level + adjustments.get("attention_adj", 0)
                )
                state.panic_level = self._clamp(
                    state.panic_level + adjustments.get("panic_adj", 0)
                )
                state.trust_level = self._clamp(
                    state.trust_level + adjustments.get("trust_adj", 0)
                )
                state.polarization_level = self._clamp(
                    state.polarization_level + adjustments.get("polarization_adj", 0)
                )
                state.risk_level = self._clamp(
                    state.risk_level + adjustments.get("risk_adj", 0)
                )
                state.stability_level = self._clamp(
                    state.stability_level + adjustments.get("stability_adj", 0)
                )
                
                reasoning = adjustments.get("reasoning", "")
                if reasoning:
                    logger.info(f"[LLM 状态修正] {reasoning}")
                    
        except Exception as e:
            logger.warning(f"LLM 状态修正失败，使用规则计算结果: {e}")
        
        return state
    
    # ============== 事件检测 ==============
    
    def _detect_events(
        self,
        curr: WorldStateSnapshot,
        prev: Optional[WorldStateSnapshot],
        obs: Dict[str, Any]
    ) -> List[WorldEvent]:
        """
        检测本轮是否发生了关键世界事件
        
        对应论文 §5.1.3 Social Influence：
        从状态变化中识别信息级联、观点转向等涌现现象
        """
        events = []
        
        if prev is None:
            return events
        
        now = datetime.now().isoformat()
        
        # 热度飙升
        attention_delta = curr.attention_level - prev.attention_level
        if attention_delta > self.EVENT_THRESHOLDS["heat_spike"]:
            events.append(WorldEvent(
                event_id=self._gen_event_id(),
                round_num=curr.round_num,
                timestamp=now,
                event_type="heat_spike",
                description=f"舆论热度急剧上升 ({prev.attention_level:.2f} → {curr.attention_level:.2f})",
                severity=min(1.0, attention_delta * 3),
                affected_variables={"attention_level": attention_delta},
            ))
        
        # 恐慌/负面情绪变化
        panic_delta = curr.panic_level - prev.panic_level
        if abs(panic_delta) > self.EVENT_THRESHOLDS["sentiment_shift"]:
            event_type = "sentiment_shift"
            if panic_delta > 0:
                desc = f"负面情绪扩散加剧 ({prev.panic_level:.2f} → {curr.panic_level:.2f})"
            else:
                desc = f"负面情绪有所缓解 ({prev.panic_level:.2f} → {curr.panic_level:.2f})"
            events.append(WorldEvent(
                event_id=self._gen_event_id(),
                round_num=curr.round_num,
                timestamp=now,
                event_type=event_type,
                description=desc,
                severity=min(1.0, abs(panic_delta) * 3),
                affected_variables={"panic_level": panic_delta},
            ))
        
        # 信任度下降
        trust_delta = curr.trust_level - prev.trust_level
        if trust_delta < -self.EVENT_THRESHOLDS["trust_drop"]:
            events.append(WorldEvent(
                event_id=self._gen_event_id(),
                round_num=curr.round_num,
                timestamp=now,
                event_type="trust_drop",
                description=f"公众信任度显著下降 ({prev.trust_level:.2f} → {curr.trust_level:.2f})",
                severity=min(1.0, abs(trust_delta) * 3),
                affected_variables={"trust_level": trust_delta},
            ))
        
        # 权威回应（基于关键词检测）
        if obs.get("auth_count", 0) >= 2 and trust_delta > 0:
            events.append(WorldEvent(
                event_id=self._gen_event_id(),
                round_num=curr.round_num,
                timestamp=now,
                event_type="official_response",
                description=f"检测到权威/官方回应，信任度回升 ({prev.trust_level:.2f} → {curr.trust_level:.2f})",
                severity=0.5,
                affected_variables={"trust_level": trust_delta},
            ))
        
        # 极化飙升
        polar_delta = curr.polarization_level - prev.polarization_level
        if polar_delta > self.EVENT_THRESHOLDS["polarization_surge"]:
            events.append(WorldEvent(
                event_id=self._gen_event_id(),
                round_num=curr.round_num,
                timestamp=now,
                event_type="polarization_surge",
                description=f"立场极化加剧 ({prev.polarization_level:.2f} → {curr.polarization_level:.2f})",
                severity=min(1.0, polar_delta * 3),
                affected_variables={"polarization_level": polar_delta},
            ))
        
        # 系统趋稳
        stab_delta = curr.stability_level - prev.stability_level
        if stab_delta > self.EVENT_THRESHOLDS["stabilization"]:
            events.append(WorldEvent(
                event_id=self._gen_event_id(),
                round_num=curr.round_num,
                timestamp=now,
                event_type="stabilization",
                description=f"系统趋于稳定 ({prev.stability_level:.2f} → {curr.stability_level:.2f})",
                severity=min(1.0, stab_delta * 2),
                affected_variables={"stability_level": stab_delta},
            ))
        
        return events
    
    # ============== 持久化 ==============
    
    def _append_state(self, state: WorldStateSnapshot):
        """追加状态到历史"""
        self._state_history.append(state)
        
        try:
            os.makedirs(os.path.dirname(self.state_history_path), exist_ok=True)
            with open(self.state_history_path, 'a', encoding='utf-8') as f:
                f.write(json.dumps(state.to_dict(), ensure_ascii=False) + '\n')
        except Exception as e:
            logger.error(f"保存世界状态失败: {e}")
    
    def _append_event(self, event: WorldEvent):
        """追加事件"""
        self._events.append(event)
        
        try:
            os.makedirs(os.path.dirname(self.events_path), exist_ok=True)
            with open(self.events_path, 'a', encoding='utf-8') as f:
                f.write(json.dumps(event.to_dict(), ensure_ascii=False) + '\n')
        except Exception as e:
            logger.error(f"保存世界事件失败: {e}")
    
    # ============== 查询接口 ==============
    
    def get_state_at_round(self, round_num: int) -> Optional[WorldStateSnapshot]:
        """获取指定轮次的状态"""
        for state in reversed(self._state_history):
            if state.round_num == round_num:
                return state
        return None
    
    def get_events_in_range(self, from_round: int, to_round: int) -> List[WorldEvent]:
        """获取指定轮次范围内的事件"""
        return [e for e in self._events if from_round <= e.round_num <= to_round]
    
    def get_state_trend(self, variable: str, last_n: int = 20) -> List[Tuple[int, float]]:
        """获取某个状态变量的趋势数据"""
        history = self._state_history[-last_n:] if last_n else self._state_history
        return [(s.round_num, getattr(s, variable, 0.0)) for s in history]
    
    # ============== 工具方法 ==============
    
    @staticmethod
    def _clamp(value: float, lo: float = 0.0, hi: float = 1.0) -> float:
        return max(lo, min(hi, value))
    
    @staticmethod
    def _gen_event_id() -> str:
        return f"evt_{uuid.uuid4().hex[:12]}"
