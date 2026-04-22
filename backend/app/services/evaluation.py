"""
量化评估框架（Quantitative Evaluation Framework）

对模拟结果进行事后量化分析，从已有的数据文件中提取指标：
- 情感演化时序（sentiment_timeline）
- Agent 行为多样性（behavior_diversity）
- 世界状态演化摘要（state_evolution）
- 影响力分析（influence_analysis）

本模块为只读分析，不修改任何现有模块或数据文件。
"""

import json
import math
import os
from collections import Counter, defaultdict
from dataclasses import dataclass, field, asdict
from typing import Dict, Any, List, Optional, Tuple

from ..utils.logger import get_logger

logger = get_logger('nexusmind.evaluation')


# ============== 数据结构 ==============

@dataclass
class SentimentTimelinePoint:
    """单轮情感分布"""
    round_num: int
    positive: float
    negative: float
    neutral: float

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class StatePeakInfo:
    """状态变量的峰值/谷值信息"""
    round_num: int
    value: float

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class TurningPoint:
    """关键转折点"""
    round_num: int
    event_type: str
    description: str
    severity: float

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class AgentInfluence:
    """Agent 影响力信息"""
    agent_id: int
    agent_name: str
    posts: int = 0
    comments: int = 0
    reposts: int = 0
    likes: int = 0
    influence_score: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class EvaluationReport:
    """完整评估报告"""
    simulation_id: str
    total_rounds: int = 0
    total_actions: int = 0
    total_agents: int = 0

    # 情感演化
    sentiment_timeline: List[SentimentTimelinePoint] = field(default_factory=list)
    sentiment_summary: Dict[str, Any] = field(default_factory=dict)

    # 行为多样性
    behavior_diversity: Dict[str, Any] = field(default_factory=dict)

    # 世界状态演化
    state_evolution: Dict[str, Any] = field(default_factory=dict)

    # 影响力分析
    influence_analysis: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["sentiment_timeline"] = [p.to_dict() if hasattr(p, 'to_dict') else p
                                   for p in self.sentiment_timeline]
        return d


# ============== 评估引擎 ==============

class SimulationEvaluator:
    """
    模拟量化评估引擎

    从已有的磁盘数据中计算各项量化指标，纯只读操作。
    """

    # 数据目录（与 SimulationRunner.RUN_STATE_DIR 一致）
    DATA_DIR = os.path.join(
        os.path.dirname(__file__),
        '../../uploads/simulations'
    )

    def __init__(self, simulation_id: str):
        self.simulation_id = simulation_id
        self.sim_dir = os.path.join(self.DATA_DIR, simulation_id)

        if not os.path.isdir(self.sim_dir):
            raise ValueError(f"模拟目录不存在: {simulation_id}")

    # ==================== 完整报告 ====================

    def generate_report(self) -> EvaluationReport:
        """生成完整评估报告"""
        report = EvaluationReport(simulation_id=self.simulation_id)

        # 1) 情感演化
        timeline = self._compute_sentiment_timeline()
        report.sentiment_timeline = timeline
        report.sentiment_summary = self._compute_sentiment_summary(timeline)

        # 2) 行为多样性
        actions = self._load_all_actions()
        report.total_actions = len(actions)
        report.behavior_diversity = self._compute_behavior_diversity(actions)

        # 3) 世界状态演化
        states = self._load_world_state_history()
        events = self._load_events()
        dedup_states = self._deduplicate_states(states)
        report.total_rounds = len(dedup_states)
        report.state_evolution = self._compute_state_evolution(states, events)

        # 4) 影响力分析
        report.influence_analysis = self._compute_influence(actions)
        report.total_agents = report.influence_analysis.get("total_agents", 0)

        # ---- 扩展数据（面向评委展示世界模型） ----

        # 5) 世界状态六维演化时序（供折线图绘制）
        report.state_evolution["world_state_timeline"] = self._build_world_state_timeline(dedup_states)

        # 6) 平台分离统计
        report.state_evolution["platform_breakdown"] = self._compute_platform_breakdown(actions)

        # 7) 因果图谱统计
        report.state_evolution["causal_graph_stats"] = self._compute_causal_stats()

        # 8) 世界模型反馈环统计
        report.state_evolution["feedback_loop_stats"] = self._compute_feedback_stats(dedup_states)

        return report

    # ==================== 新增：世界状态时序 ====================

    def _build_world_state_timeline(self, states: list) -> list:
        """构建六维世界状态时序数据（供前端折线图）"""
        dims = [
            "attention_level", "panic_level", "trust_level",
            "polarization_level", "risk_level", "stability_level"
        ]
        result = []
        for s in states:
            point = {"round_num": s.get("round_num", 0)}
            for d in dims:
                point[d] = round(s.get(d, 0.0), 4)
            # 同时带上活跃Agent数、总帖子数
            point["active_agent_count"] = s.get("active_agent_count", 0)
            point["total_posts"] = s.get("total_posts", 0)
            result.append(point)
        return result

    # ==================== 新增：平台分离统计 ====================

    def _compute_platform_breakdown(self, actions: list) -> dict:
        """按平台拆分动作统计"""
        platforms = defaultdict(lambda: {"total": 0, "posts": 0, "comments": 0, "reposts": 0, "likes": 0, "searches": 0})
        for a in actions:
            p = a.get("platform", "unknown")
            atype = a.get("action_type", "").upper()
            platforms[p]["total"] += 1
            if "CREATE_POST" in atype:
                platforms[p]["posts"] += 1
            elif "COMMENT" in atype:
                platforms[p]["comments"] += 1
            elif "REPOST" in atype or "QUOTE" in atype:
                platforms[p]["reposts"] += 1
            elif "LIKE" in atype or "UPVOTE" in atype or "DOWNVOTE" in atype:
                platforms[p]["likes"] += 1
            elif "SEARCH" in atype:
                platforms[p]["searches"] += 1
        return dict(platforms)

    # ==================== 新增：因果图谱统计 ====================

    def _compute_causal_stats(self) -> dict:
        """加载 causal_edges.jsonl 并统计"""
        path = os.path.join(self.sim_dir, "causal_edges.jsonl")
        edges = self._load_jsonl(path)
        if not edges:
            return {"total_edges": 0, "edge_types": {}, "top_causes": [], "top_effects": []}

        edge_types = Counter(e.get("relation", "unknown") for e in edges)
        cause_counter = Counter(e.get("source", "") for e in edges)
        effect_counter = Counter(e.get("target", "") for e in edges)

        return {
            "total_edges": len(edges),
            "edge_types": dict(edge_types.most_common(10)),
            "top_causes": [{"name": k, "count": v} for k, v in cause_counter.most_common(5)],
            "top_effects": [{"name": k, "count": v} for k, v in effect_counter.most_common(5)],
        }

    # ==================== 新增：反馈环统计 ====================

    def _compute_feedback_stats(self, states: list) -> dict:
        """分析世界模型反馈环的作用：哪些轮次触发了干预"""
        if len(states) < 2:
            return {"injection_rounds": 0, "avg_deviation": 0.0, "max_deviation_round": 0}
        dims = ["attention_level", "panic_level", "trust_level",
                "polarization_level", "risk_level", "stability_level"]
        # 用相邻轮次变化量作为 proxy
        deltas = []
        for i in range(1, len(states)):
            prev, curr = states[i - 1], states[i]
            d = sum(abs(curr.get(k, 0) - prev.get(k, 0)) for k in dims) / len(dims)
            deltas.append({"round_num": curr.get("round_num", i), "delta": round(d, 4)})
        # 超过阈值 0.15 视为"有干预"
        injection_rounds = [d for d in deltas if d["delta"] > 0.03]
        max_d = max(deltas, key=lambda x: x["delta"]) if deltas else {"round_num": 0, "delta": 0}
        avg_d = sum(d["delta"] for d in deltas) / len(deltas) if deltas else 0
        return {
            "round_deltas": deltas,
            "injection_rounds": len(injection_rounds),
            "avg_deviation": round(avg_d, 4),
            "max_deviation_round": max_d["round_num"],
            "max_deviation": round(max_d["delta"], 4),
        }

    # ==================== 情感演化 ====================

    def get_sentiment_timeline(self) -> Dict[str, Any]:
        """获取情感时序数据"""
        timeline = self._compute_sentiment_timeline()
        return {
            "timeline": [p.to_dict() for p in timeline],
            "summary": self._compute_sentiment_summary(timeline),
        }

    def _compute_sentiment_timeline(self) -> List[SentimentTimelinePoint]:
        """从 world_state_history.jsonl 提取情感分布时序（去重 + 排序）"""
        states = self._load_world_state_history()

        # 按 round_num 聚合（同一轮可能出现多次，取均值）
        round_agg: Dict[int, List[Dict[str, float]]] = defaultdict(list)
        for s in states:
            rn = s.get("round_num", 0)
            dist = s.get("sentiment_distribution", {})
            round_agg[rn].append({
                "positive": dist.get("positive", 0.0),
                "negative": dist.get("negative", 0.0),
                "neutral": dist.get("neutral", 0.0),
            })

        timeline = []
        for rn in sorted(round_agg.keys()):
            entries = round_agg[rn]
            n = len(entries)
            timeline.append(SentimentTimelinePoint(
                round_num=rn,
                positive=round(sum(e["positive"] for e in entries) / n, 4),
                negative=round(sum(e["negative"] for e in entries) / n, 4),
                neutral=round(sum(e["neutral"] for e in entries) / n, 4),
            ))
        return timeline

    def _compute_sentiment_summary(
        self, timeline: List[SentimentTimelinePoint]
    ) -> Dict[str, Any]:
        """计算情感摘要统计"""
        if not timeline:
            return {}

        positives = [p.positive for p in timeline]
        negatives = [p.negative for p in timeline]
        neutrals = [p.neutral for p in timeline]

        # 峰值轮次
        neg_peak_idx = max(range(len(negatives)), key=lambda i: negatives[i])
        pos_peak_idx = max(range(len(positives)), key=lambda i: positives[i])

        # 整体均值
        avg_pos = sum(positives) / len(positives)
        avg_neg = sum(negatives) / len(negatives)
        avg_neu = sum(neutrals) / len(neutrals)

        return {
            "average": {"positive": round(avg_pos, 4), "negative": round(avg_neg, 4), "neutral": round(avg_neu, 4)},
            "negative_peak": {"round": timeline[neg_peak_idx].round_num, "value": round(negatives[neg_peak_idx], 4)},
            "positive_peak": {"round": timeline[pos_peak_idx].round_num, "value": round(positives[pos_peak_idx], 4)},
            "total_rounds": len(timeline),
            # 负面情绪主导轮数占比
            "negative_dominant_ratio": round(
                sum(1 for p in timeline if p.negative > p.positive and p.negative > p.neutral) / len(timeline), 4
            ),
        }

    # ==================== 行为多样性 ====================

    def get_behavior_diversity(self) -> Dict[str, Any]:
        """获取行为多样性指标"""
        actions = self._load_all_actions()
        return self._compute_behavior_diversity(actions)

    def _compute_behavior_diversity(self, actions: List[Dict]) -> Dict[str, Any]:
        """计算行为多样性指标"""
        if not actions:
            return {"action_type_distribution": {}, "agent_activity_gini": 0.0,
                    "unique_active_ratio": 0.0, "per_round_active_agents": []}

        # 动作类型分布
        type_counter = Counter(a.get("action_type", "UNKNOWN") for a in actions)
        total = sum(type_counter.values())
        type_distribution = {k: round(v / total, 4) for k, v in type_counter.most_common()}

        # 每个 Agent 的动作数
        agent_action_counts = Counter(a.get("agent_id", -1) for a in actions)
        all_agent_ids = set(agent_action_counts.keys())

        # 加载 profiles 获取总 Agent 数
        profiles = self._load_profiles()
        total_agents = max(len(profiles), len(all_agent_ids))

        # 活跃 Agent 占比
        unique_active = len(all_agent_ids)
        unique_active_ratio = round(unique_active / max(total_agents, 1), 4)

        # 基尼系数（衡量活跃度不均匀程度）
        gini = self._gini_coefficient(list(agent_action_counts.values()))

        # 每轮活跃 Agent 数
        round_agents: Dict[int, set] = defaultdict(set)
        for a in actions:
            r = a.get("round", 0)
            aid = a.get("agent_id", -1)
            round_agents[r].add(aid)

        max_round = max(round_agents.keys()) if round_agents else 0
        per_round = []
        for r in range(1, max_round + 1):
            per_round.append({"round": r, "active_agents": len(round_agents.get(r, set()))})

        return {
            "action_type_distribution": type_distribution,
            "agent_activity_gini": round(gini, 4),
            "unique_active_agents": unique_active,
            "total_agents": total_agents,
            "unique_active_ratio": unique_active_ratio,
            "total_actions": total,
            "per_round_active_agents": per_round,
        }

    # ==================== 世界状态演化 ====================

    def get_state_evolution(self) -> Dict[str, Any]:
        """获取世界状态演化摘要"""
        states = self._load_world_state_history()
        events = self._load_events()
        return self._compute_state_evolution(states, events)

    def _compute_state_evolution(
        self, states: List[Dict], events: List[Dict]
    ) -> Dict[str, Any]:
        """计算世界状态演化摘要"""
        if not states:
            return {}

        # 去重：按 round_num 聚合（取均值），保证有序
        states = self._deduplicate_states(states)

        state_vars = [
            "attention_level", "panic_level", "trust_level",
            "polarization_level", "risk_level", "stability_level"
        ]

        # 峰值/谷值
        peaks: Dict[str, Dict] = {}
        mins: Dict[str, Dict] = {}
        for var in state_vars:
            values = [(s.get("round_num", 0), s.get(var, 0.0)) for s in states]
            max_item = max(values, key=lambda x: x[1])
            min_item = min(values, key=lambda x: x[1])
            peaks[var] = {"round": max_item[0], "value": round(max_item[1], 4)}
            mins[var] = {"round": min_item[0], "value": round(min_item[1], 4)}

        # 波动率（每个变量的标准差平均）
        volatilities = {}
        for var in state_vars:
            values = [s.get(var, 0.0) for s in states]
            if len(values) > 1:
                mean = sum(values) / len(values)
                variance = sum((v - mean) ** 2 for v in values) / len(values)
                volatilities[var] = round(math.sqrt(variance), 4)
            else:
                volatilities[var] = 0.0
        avg_volatility = round(sum(volatilities.values()) / len(volatilities), 4) if volatilities else 0.0

        # 初始状态 & 最终状态
        initial = {var: round(states[0].get(var, 0.0), 4) for var in state_vars}
        final = {var: round(states[-1].get(var, 0.0), 4) for var in state_vars}

        # 关键转折点（从 events.jsonl）
        turning_points = []
        for e in sorted(events, key=lambda x: x.get("severity", 0), reverse=True)[:10]:
            turning_points.append({
                "round": e.get("round_num", 0),
                "event_type": e.get("event_type", ""),
                "description": e.get("description", ""),
                "severity": round(e.get("severity", 0.0), 4),
            })

        return {
            "total_rounds": len(states),
            "peaks": peaks,
            "mins": mins,
            "initial_state": initial,
            "final_state": final,
            "volatilities": volatilities,
            "avg_volatility": avg_volatility,
            "turning_points": turning_points,
            "total_events": len(events),
        }

    # ==================== 影响力分析 ====================

    def get_influence_analysis(self) -> Dict[str, Any]:
        """获取影响力分析"""
        actions = self._load_all_actions()
        return self._compute_influence(actions)

    def _compute_influence(self, actions: List[Dict]) -> Dict[str, Any]:
        """计算 Agent 影响力排行"""
        if not actions:
            return {"top_agents": [], "total_agents": 0, "information_concentration": 0.0}

        # 按 agent 统计
        agent_stats: Dict[int, Dict[str, Any]] = defaultdict(lambda: {
            "agent_id": 0, "agent_name": "", "posts": 0, "comments": 0,
            "reposts": 0, "likes": 0, "total_actions": 0
        })

        for a in actions:
            aid = a.get("agent_id", -1)
            atype = a.get("action_type", "").upper()
            stats = agent_stats[aid]
            stats["agent_id"] = aid
            stats["agent_name"] = a.get("agent_name", f"Agent_{aid}")
            stats["total_actions"] += 1

            if "POST" in atype and "COMMENT" not in atype:
                stats["posts"] += 1
            elif "COMMENT" in atype:
                stats["comments"] += 1
            elif "REPOST" in atype or "RETWEET" in atype:
                stats["reposts"] += 1
            elif "LIKE" in atype or "UPVOTE" in atype or "DOWNVOTE" in atype:
                stats["likes"] += 1

        # 计算影响力得分（帖子权重最高）
        for stats in agent_stats.values():
            stats["influence_score"] = round(
                stats["posts"] * 3.0
                + stats["comments"] * 1.5
                + stats["reposts"] * 2.0
                + stats["likes"] * 0.5,
                2
            )

        # 排序
        sorted_agents = sorted(
            agent_stats.values(),
            key=lambda x: x["influence_score"],
            reverse=True
        )

        total_agents = len(sorted_agents)

        # 信息集中度：前 20% Agent 的发帖占比
        top_n = max(1, int(total_agents * 0.2))
        total_posts = sum(s["posts"] for s in sorted_agents)
        top_posts = sum(s["posts"] for s in sorted_agents[:top_n])
        concentration = round(top_posts / max(total_posts, 1), 4)

        return {
            "top_agents": sorted_agents[:20],  # 返回前 20 名
            "total_agents": total_agents,
            "information_concentration": concentration,
            "concentration_description": f"前{top_n}名Agent（{round(top_n/max(total_agents,1)*100)}%）贡献了{round(concentration*100,1)}%的帖子",
        }

    # ==================== 数据加载 ====================

    def _load_world_state_history(self) -> List[Dict]:
        """从 world_state_history.jsonl 加载"""
        path = os.path.join(self.sim_dir, "world_state_history.jsonl")
        return self._load_jsonl(path)

    def _load_events(self) -> List[Dict]:
        """从 events.jsonl 加载"""
        path = os.path.join(self.sim_dir, "events.jsonl")
        return self._load_jsonl(path)

    def _load_all_actions(self) -> List[Dict]:
        """加载所有平台的动作日志"""
        actions = []
        for platform in ("twitter", "reddit"):
            path = os.path.join(self.sim_dir, platform, "actions.jsonl")
            if not os.path.exists(path):
                continue
            for item in self._load_jsonl(path):
                # 跳过事件类型条目（round_start/round_end/simulation_start 等）
                if "event_type" in item:
                    continue
                # 跳过没有 agent_id 的记录
                if "agent_id" not in item:
                    continue
                item["platform"] = platform
                actions.append(item)
        return actions

    def _load_profiles(self) -> List[Dict]:
        """加载 Agent 人设"""
        for fname in ("reddit_profiles.json", "twitter_profiles.csv"):
            path = os.path.join(self.sim_dir, fname)
            if os.path.exists(path) and fname.endswith('.json'):
                try:
                    with open(path, 'r', encoding='utf-8') as f:
                        return json.load(f)
                except Exception:
                    pass
        return []

    @staticmethod
    def _load_jsonl(path: str) -> List[Dict]:
        """通用 JSONL 加载"""
        results = []
        if not os.path.exists(path):
            return results
        try:
            with open(path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if line:
                        try:
                            results.append(json.loads(line))
                        except json.JSONDecodeError:
                            continue
        except Exception as e:
            logger.warning(f"加载 {path} 失败: {e}")
        return results

    # ==================== 工具函数 ====================

    @staticmethod
    def _deduplicate_states(states: List[Dict]) -> List[Dict]:
        """按 round_num 去重（多次出现取均值），返回排序后的列表"""
        agg: Dict[int, List[Dict]] = defaultdict(list)
        numeric_keys = [
            "attention_level", "panic_level", "trust_level",
            "polarization_level", "risk_level", "stability_level",
            "total_posts", "total_comments", "total_reposts",
            "total_likes", "active_agent_count",
        ]
        for s in states:
            agg[s.get("round_num", 0)].append(s)

        result = []
        for rn in sorted(agg.keys()):
            entries = agg[rn]
            if len(entries) == 1:
                result.append(entries[0])
            else:
                merged = {"round_num": rn}
                for k in numeric_keys:
                    vals = [e.get(k, 0.0) for e in entries]
                    merged[k] = round(sum(vals) / len(vals), 4)
                # 情感分布也取均值
                dists = [e.get("sentiment_distribution", {}) for e in entries]
                merged["sentiment_distribution"] = {
                    sk: round(sum(d.get(sk, 0.0) for d in dists) / len(dists), 4)
                    for sk in ("positive", "negative", "neutral")
                }
                result.append(merged)
        return result

    @staticmethod
    def _gini_coefficient(values: List[float]) -> float:
        """计算基尼系数（衡量分布不均匀程度）"""
        if not values or len(values) < 2:
            return 0.0
        sorted_vals = sorted(values)
        n = len(sorted_vals)
        total = sum(sorted_vals)
        if total == 0:
            return 0.0
        cumulative = 0.0
        gini_sum = 0.0
        for i, v in enumerate(sorted_vals):
            cumulative += v
            gini_sum += (2 * (i + 1) - n - 1) * v
        return gini_sum / (n * total)

    # ==================== 列出可评估的模拟 ====================

    @classmethod
    def list_evaluable_simulations(cls) -> List[Dict[str, Any]]:
        """列出所有有数据可供评估的模拟"""
        results = []
        if not os.path.isdir(cls.DATA_DIR):
            return results

        for name in sorted(os.listdir(cls.DATA_DIR)):
            sim_dir = os.path.join(cls.DATA_DIR, name)
            if not os.path.isdir(sim_dir):
                continue

            history_path = os.path.join(sim_dir, "world_state_history.jsonl")
            has_history = os.path.isfile(history_path) and os.path.getsize(history_path) > 0

            # 检查动作日志
            has_actions = False
            for platform in ("twitter", "reddit"):
                action_path = os.path.join(sim_dir, platform, "actions.jsonl")
                if os.path.isfile(action_path) and os.path.getsize(action_path) > 0:
                    has_actions = True
                    break

            if has_history or has_actions:
                results.append({
                    "simulation_id": name,
                    "has_world_state": has_history,
                    "has_actions": has_actions,
                })

        return results
