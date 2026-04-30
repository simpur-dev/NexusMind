"""
模拟洞察聚合服务（Simulation Insight Service）

只读聚合层，将世界模型（WorldStateEngine）、因果图谱（CausalGraphEngine）、
量化评估（SimulationEvaluator）的结果整理为 ReportAgent 可直接消费的结构化证据。

核心职责：
1. 聚合 6 维世界状态、事件、因果链、评估指标
2. 计算综合态势评分卡（Reputation Scorecard）
3. 识别关键转折点与风险/机会信号
4. 生成决策支持简报
5. 提供模拟证据检索能力

所有方法返回双格式：JSON 结构 + LLM 友好文本。
"""

import json
import math
import os
from collections import defaultdict
from typing import Dict, Any, List, Optional

from ..config import Config
from ..utils.logger import get_logger

logger = get_logger('nexusmind.simulation_insight')

# 数据目录
DATA_DIR = os.path.join(os.path.dirname(__file__), '../../uploads/simulations')

# 6 维状态变量名
STATE_VARS = [
    "attention_level", "panic_level", "trust_level",
    "polarization_level", "risk_level", "stability_level",
]

STATE_VAR_CN = {
    "attention_level": "舆论关注度",
    "panic_level": "恐慌/负面情绪",
    "trust_level": "公众信任度",
    "polarization_level": "立场极化度",
    "risk_level": "综合风险等级",
    "stability_level": "系统稳定性",
}

LEVEL_DESC = {
    (0.0, 0.2): "很低",
    (0.2, 0.4): "较低",
    (0.4, 0.6): "中等",
    (0.6, 0.8): "较高",
    (0.8, 1.01): "很高",
}


def _describe_level(val: float) -> str:
    for (lo, hi), desc in LEVEL_DESC.items():
        if lo <= val < hi:
            return desc
    return "未知"


def _load_jsonl(path: str) -> List[Dict]:
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


class SimulationInsightService:
    """模拟洞察聚合服务"""

    def __init__(self, simulation_id: str):
        self.simulation_id = simulation_id
        self.sim_dir = os.path.join(DATA_DIR, simulation_id)

        if not os.path.isdir(self.sim_dir):
            raise ValueError(f"模拟目录不存在: {simulation_id}")

        # 延迟加载
        self._states: Optional[List[Dict]] = None
        self._events: Optional[List[Dict]] = None
        self._causal_edges: Optional[List[Dict]] = None
        self._actions: Optional[List[Dict]] = None
        self._cognition_history: Optional[List[Dict]] = None
        self._cognition_summary: Optional[Dict] = None

    # ════════════════ 数据加载（带缓存） ════════════════

    @property
    def states(self) -> List[Dict]:
        if self._states is None:
            self._states = _load_jsonl(os.path.join(self.sim_dir, "world_state_history.jsonl"))
        return self._states

    @property
    def events(self) -> List[Dict]:
        if self._events is None:
            self._events = _load_jsonl(os.path.join(self.sim_dir, "events.jsonl"))
        return self._events

    @property
    def causal_edges(self) -> List[Dict]:
        if self._causal_edges is None:
            self._causal_edges = _load_jsonl(os.path.join(self.sim_dir, "causal_edges.jsonl"))
        return self._causal_edges

    @property
    def actions(self) -> List[Dict]:
        if self._actions is None:
            acts = []
            for platform in ("twitter", "reddit"):
                path = os.path.join(self.sim_dir, platform, "actions.jsonl")
                for item in _load_jsonl(path):
                    if "event_type" in item or "agent_id" not in item:
                        continue
                    item["platform"] = platform
                    acts.append(item)
            self._actions = acts
        return self._actions

    @property
    def cognition_history(self) -> List[Dict]:
        if self._cognition_history is None:
            self._cognition_history = _load_jsonl(os.path.join(self.sim_dir, "agent_cognition_history.jsonl"))
        return self._cognition_history

    @property
    def cognition_summary(self) -> Dict:
        if self._cognition_summary is None:
            path = os.path.join(self.sim_dir, "agent_cognition_summary.json")
            if os.path.exists(path):
                try:
                    with open(path, 'r', encoding='utf-8') as f:
                        self._cognition_summary = json.load(f)
                except (json.JSONDecodeError, OSError):
                    self._cognition_summary = {}
            else:
                self._cognition_summary = {}
        return self._cognition_summary

    # ════════════════ 1. 世界模型简报 ════════════════

    def get_world_model_brief(self) -> Dict[str, Any]:
        """
        返回当前世界状态 + 最近趋势 + 异常维度。
        ReportAgent 工具: world_model_brief
        """
        states = self.states
        if not states:
            return {"error": "暂无世界状态数据", "text": "暂无世界状态数据。"}

        # 按 round_num 去重取最新
        by_round: Dict[int, Dict] = {}
        for s in states:
            rn = s.get("round_num", 0)
            by_round[rn] = s
        sorted_rounds = sorted(by_round.keys())
        ordered = [by_round[r] for r in sorted_rounds]

        current = ordered[-1]
        total_rounds = len(ordered)

        # 当前状态
        current_state = {v: round(current.get(v, 0.0), 3) for v in STATE_VARS}

        # 最近 5 轮趋势（斜率）
        recent_n = min(5, total_rounds)
        recent = ordered[-recent_n:]
        trends = {}
        for v in STATE_VARS:
            vals = [s.get(v, 0.0) for s in recent]
            if len(vals) >= 2:
                slope = (vals[-1] - vals[0]) / max(len(vals) - 1, 1)
                trends[v] = round(slope, 4)
            else:
                trends[v] = 0.0

        # 最显著异常维度（偏离 0.5 最远）
        anomalies = sorted(
            STATE_VARS,
            key=lambda v: abs(current.get(v, 0.5) - 0.5),
            reverse=True,
        )[:3]

        # 文本摘要
        lines = [f"## 世界模型状态简报（共 {total_rounds} 轮）\n"]
        lines.append(f"**当前状态（第 {current.get('round_num', '?')} 轮）**\n")
        for v in STATE_VARS:
            val = current_state[v]
            trend_val = trends[v]
            arrow = "↑" if trend_val > 0.01 else ("↓" if trend_val < -0.01 else "→")
            lines.append(f"- {STATE_VAR_CN[v]}: {_describe_level(val)}（{val:.2f}）{arrow}")

        lines.append(f"\n**最显著异常维度**: {', '.join(STATE_VAR_CN[v] for v in anomalies)}")

        # 情绪分布
        sent = current.get("sentiment_distribution", {})
        if sent:
            lines.append(
                f"\n**情绪分布**: 正面 {sent.get('positive', 0):.1%} / "
                f"负面 {sent.get('negative', 0):.1%} / "
                f"中性 {sent.get('neutral', 0):.1%}"
            )

        result = {
            "current_round": current.get("round_num", 0),
            "total_rounds": total_rounds,
            "current_state": current_state,
            "trends": trends,
            "anomaly_dimensions": anomalies,
            "sentiment_distribution": sent,
        }
        result["text"] = "\n".join(lines)
        return result

    # ════════════════ 2. 状态演化分析 ════════════════

    def get_state_evolution_analysis(self) -> Dict[str, Any]:
        """
        返回峰值/谷值/波动率/初始→最终对比/转折点。
        ReportAgent 工具: state_evolution_analysis
        """
        states = self.states
        events = self.events
        if not states:
            return {"error": "暂无世界状态数据", "text": "暂无世界状态数据。"}

        # 去重排序
        by_round: Dict[int, Dict] = {}
        for s in states:
            by_round[s.get("round_num", 0)] = s
        sorted_rounds = sorted(by_round.keys())
        ordered = [by_round[r] for r in sorted_rounds]

        peaks, mins, volatilities = {}, {}, {}
        for v in STATE_VARS:
            values = [(s.get("round_num", 0), s.get(v, 0.0)) for s in ordered]
            max_item = max(values, key=lambda x: x[1])
            min_item = min(values, key=lambda x: x[1])
            peaks[v] = {"round": max_item[0], "value": round(max_item[1], 4)}
            mins[v] = {"round": min_item[0], "value": round(min_item[1], 4)}
            vals = [x[1] for x in values]
            mean = sum(vals) / len(vals)
            volatilities[v] = round(math.sqrt(sum((x - mean)**2 for x in vals) / len(vals)), 4)

        initial = {v: round(ordered[0].get(v, 0.0), 4) for v in STATE_VARS}
        final = {v: round(ordered[-1].get(v, 0.0), 4) for v in STATE_VARS}

        # 转折点
        turning_points = sorted(events, key=lambda e: e.get("severity", 0), reverse=True)[:8]

        # 文本
        lines = ["## 状态演化分析\n"]
        lines.append(f"**总轮次**: {len(ordered)}  **总事件数**: {len(events)}\n")
        lines.append("**初始 → 最终状态变化**\n")
        for v in STATE_VARS:
            delta = final[v] - initial[v]
            direction = "上升" if delta > 0.02 else ("下降" if delta < -0.02 else "稳定")
            lines.append(f"- {STATE_VAR_CN[v]}: {initial[v]:.2f} → {final[v]:.2f}（{direction} {delta:+.2f}）")

        lines.append("\n**峰值时刻**\n")
        for v in STATE_VARS:
            lines.append(f"- {STATE_VAR_CN[v]}: 第 {peaks[v]['round']} 轮达峰值 {peaks[v]['value']:.2f}")

        if turning_points:
            lines.append("\n**关键转折点**\n")
            for tp in turning_points[:5]:
                lines.append(
                    f"- 第 {tp.get('round_num', '?')} 轮 [{tp.get('event_type', '')}] "
                    f"{tp.get('description', '')} (严重度 {tp.get('severity', 0):.2f})"
                )

        result = {
            "total_rounds": len(ordered),
            "total_events": len(events),
            "peaks": peaks,
            "mins": mins,
            "volatilities": volatilities,
            "initial_state": initial,
            "final_state": final,
            "turning_points": [
                {
                    "round": tp.get("round_num", 0),
                    "event_type": tp.get("event_type", ""),
                    "description": tp.get("description", ""),
                    "severity": round(tp.get("severity", 0), 4),
                }
                for tp in turning_points
            ],
        }
        result["text"] = "\n".join(lines)
        return result

    # ════════════════ 3. 因果链分析 ════════════════

    def get_causal_chain_analysis(self) -> Dict[str, Any]:
        """
        返回因果边列表 + 关键因果链文本。
        ReportAgent 工具: causal_chain_analysis
        """
        edges = self.causal_edges
        events = self.events

        if not edges:
            return {"total_edges": 0, "text": "暂无因果关系数据。推演轮次不足或未触发因果推断。"}

        # 事件 ID → 描述
        event_map = {e.get("event_id", ""): e for e in events}

        RELATION_CN = {
            "triggered": "直接触发",
            "amplified": "放大效应",
            "suppressed": "抑制效应",
            "correlated": "关联效应",
        }

        # 按强度排序
        sorted_edges = sorted(edges, key=lambda e: e.get("strength", 0), reverse=True)

        lines = [f"## 因果链分析（共 {len(edges)} 条因果边）\n"]
        for i, edge in enumerate(sorted_edges[:12]):
            src = event_map.get(edge.get("source_event_id", ""), {})
            tgt = event_map.get(edge.get("target_event_id", ""), {})
            rel = RELATION_CN.get(edge.get("relation_type", ""), edge.get("relation_type", ""))
            lines.append(
                f"{i+1}. [{rel}] "
                f"「{src.get('description', edge.get('source_event_id', '?'))[:40]}」"
                f" → 「{tgt.get('description', edge.get('target_event_id', '?'))[:40]}」"
                f"（强度 {edge.get('strength', 0):.2f}，第 {edge.get('round_num', '?')} 轮）"
            )
            evidence = edge.get("evidence", "")
            if evidence:
                lines.append(f"   证据: {evidence[:80]}")

        result = {
            "total_edges": len(edges),
            "top_edges": sorted_edges[:12],
        }
        result["text"] = "\n".join(lines)
        return result

    # ════════════════ 4. 评估摘要 ════════════════

    def get_evaluation_summary(self) -> Dict[str, Any]:
        """
        聚合 SimulationEvaluator 的量化结果。
        ReportAgent 工具: evaluation_summary
        """
        try:
            from .evaluation import SimulationEvaluator
            evaluator = SimulationEvaluator(self.simulation_id)
            report = evaluator.generate_report()
            data = report.to_dict()
        except Exception as e:
            logger.warning(f"评估报告生成失败: {e}")
            return {"error": str(e), "text": f"评估数据获取失败: {e}"}

        lines = ["## 量化评估摘要\n"]

        # 情感
        sent_summary = data.get("sentiment_summary", {})
        if sent_summary:
            avg = sent_summary.get("average", {})
            neg_peak = sent_summary.get("negative_peak", {})
            lines.append("**情感分析**\n")
            lines.append(
                f"- 平均正面 {avg.get('positive', 0):.1%} / 负面 {avg.get('negative', 0):.1%} / "
                f"中性 {avg.get('neutral', 0):.1%}"
            )
            lines.append(f"- 负面情绪峰值: 第 {neg_peak.get('round', '?')} 轮（{neg_peak.get('value', 0):.1%}）")
            lines.append(f"- 负面主导轮数占比: {sent_summary.get('negative_dominant_ratio', 0):.1%}")

        # 行为多样性
        bd = data.get("behavior_diversity", {})
        if bd:
            lines.append("\n**行为多样性**\n")
            lines.append(f"- 总动作数: {bd.get('total_actions', 0)}")
            lines.append(f"- 活跃Agent比例: {bd.get('unique_active_ratio', 0):.1%}")
            lines.append(f"- 基尼系数: {bd.get('agent_activity_gini', 0):.3f}")
            dist = bd.get("action_type_distribution", {})
            if dist:
                top3 = list(dist.items())[:3]
                lines.append(f"- 主要行为: {', '.join(f'{k}({v:.1%})' for k, v in top3)}")

        # 状态演化
        se = data.get("state_evolution", {})
        if se:
            lines.append(f"\n**世界状态演化**\n")
            lines.append(f"- 总轮次: {se.get('total_rounds', 0)}  事件数: {se.get('total_events', 0)}")
            lines.append(f"- 平均波动率: {se.get('avg_volatility', 0):.4f}")

        # 影响力
        ia = data.get("influence_analysis", {})
        if ia:
            lines.append(f"\n**影响力分析**\n")
            lines.append(f"- 总Agent数: {ia.get('total_agents', 0)}")
            conc_desc = ia.get("concentration_description", "")
            if conc_desc:
                lines.append(f"- {conc_desc}")
            top_agents = ia.get("top_agents", [])[:5]
            if top_agents:
                lines.append("- Top 5 影响力Agent:")
                for ag in top_agents:
                    lines.append(
                        f"  - {ag.get('agent_name', 'Unknown')} "
                        f"(帖子 {ag.get('posts', 0)}, 影响力 {ag.get('influence_score', 0):.1f})"
                    )

        result = {
            "sentiment_summary": sent_summary,
            "behavior_diversity": bd,
            "state_evolution": se,
            "influence_analysis": ia,
            "total_rounds": data.get("total_rounds", 0),
            "total_actions": data.get("total_actions", 0),
            "total_agents": data.get("total_agents", 0),
        }
        result["text"] = "\n".join(lines)
        return result

    # ════════════════ 5. 态势评分卡 ════════════════

    def get_reputation_scorecard(self) -> Dict[str, Any]:
        """
        基于世界模型 6 维状态计算综合态势评分卡。
        ReportAgent 工具: reputation_scorecard
        """
        states = self.states
        if not states:
            return {"error": "暂无数据", "text": "暂无世界状态数据，无法生成评分卡。"}

        by_round: Dict[int, Dict] = {}
        for s in states:
            by_round[s.get("round_num", 0)] = s
        ordered = [by_round[r] for r in sorted(by_round.keys())]
        current = ordered[-1]

        trust = current.get("trust_level", 0.5)
        stability = current.get("stability_level", 0.5)
        panic = current.get("panic_level", 0.3)
        risk = current.get("risk_level", 0.3)
        polarization = current.get("polarization_level", 0.3)
        attention = current.get("attention_level", 0.3)

        # 负面主导比例
        sent = current.get("sentiment_distribution", {})
        neg_ratio = sent.get("negative", 0.33)

        # 事件密度
        events = self.events
        total_rounds = len(ordered) or 1
        event_density = min(1.0, len(events) / total_rounds / 2.0)

        # 综合健康评分
        reputation_health = (
            0.28 * trust
            + 0.20 * stability
            + 0.16 * (1 - panic)
            + 0.14 * (1 - risk)
            + 0.12 * (1 - polarization)
            + 0.10 * (1 - neg_ratio)
        )

        # 风险升级评分
        risk_escalation = (
            0.24 * attention
            + 0.22 * panic
            + 0.18 * polarization
            + 0.18 * risk
            + 0.10 * (1 - trust)
            + 0.08 * event_density
        )

        # 信任修复评分（高信任 + 稳定 + 低极化 = 修复潜力大）
        trust_recovery = (
            0.35 * trust
            + 0.25 * stability
            + 0.20 * (1 - polarization)
            + 0.20 * (1 - panic)
        )

        # 极化压力评分
        polarization_pressure = (
            0.35 * polarization
            + 0.25 * (1 - trust)
            + 0.20 * panic
            + 0.20 * attention
        )

        scores = {
            "reputation_health": round(reputation_health, 3),
            "risk_escalation": round(risk_escalation, 3),
            "trust_recovery": round(trust_recovery, 3),
            "polarization_pressure": round(polarization_pressure, 3),
        }

        # 整体状态判定
        if reputation_health < 0.35:
            overall_status = "高压脆弱"
        elif reputation_health < 0.50:
            overall_status = "风险积累"
        elif reputation_health < 0.65:
            overall_status = "修复中"
        else:
            overall_status = "相对稳定"

        lines = ["## 综合态势评分卡\n"]
        lines.append(f"**整体状态**: {overall_status}\n")
        lines.append(f"- 综合健康评分: {scores['reputation_health']:.2f}/1.00")
        lines.append(f"- 风险升级评分: {scores['risk_escalation']:.2f}/1.00")
        lines.append(f"- 信任修复潜力: {scores['trust_recovery']:.2f}/1.00")
        lines.append(f"- 极化压力评分: {scores['polarization_pressure']:.2f}/1.00")
        lines.append(f"\n**底层状态变量**\n")
        for v in STATE_VARS:
            val = current.get(v, 0.0)
            lines.append(f"- {STATE_VAR_CN[v]}: {_describe_level(val)}（{val:.2f}）")

        result = {
            "overall_status": overall_status,
            "scores": scores,
            "current_state": {v: round(current.get(v, 0.0), 3) for v in STATE_VARS},
            "current_round": current.get("round_num", 0),
        }
        result["text"] = "\n".join(lines)
        return result

    # ════════════════ 6. 决策支持简报 ════════════════

    def get_decision_support_brief(self) -> Dict[str, Any]:
        """
        综合声誉评分卡 + 事件 + 趋势，生成风险/机会/建议摘要。
        ReportAgent 工具: decision_support_brief
        """
        scorecard = self.get_reputation_scorecard()
        if "error" in scorecard:
            return scorecard

        evolution = self.get_state_evolution_analysis()
        causal = self.get_causal_chain_analysis()

        scores = scorecard.get("scores", {})
        overall = scorecard.get("overall_status", "未知")
        current_state = scorecard.get("current_state", {})

        # ── 风险信号 ──
        risks = []
        if current_state.get("trust_level", 1) < 0.4:
            risks.append({
                "title": "信任塌缩风险",
                "severity": "high",
                "explanation": f"公众信任度仅 {current_state['trust_level']:.2f}，低于安全阈值 0.4",
            })
        if current_state.get("panic_level", 0) > 0.6:
            risks.append({
                "title": "恐慌蔓延风险",
                "severity": "high",
                "explanation": f"恐慌水平 {current_state['panic_level']:.2f}，已进入高恐慌区间",
            })
        if current_state.get("polarization_level", 0) > 0.6:
            risks.append({
                "title": "极化对立加剧",
                "severity": "medium",
                "explanation": f"极化度 {current_state['polarization_level']:.2f}，群体对立趋势明显",
            })
        if scores.get("risk_escalation", 0) > 0.6:
            risks.append({
                "title": "风险升级预警",
                "severity": "high",
                "explanation": f"风险升级综合评分 {scores['risk_escalation']:.2f}，事态有继续恶化可能",
            })
        if current_state.get("attention_level", 0) > 0.7 and current_state.get("trust_level", 1) < 0.5:
            risks.append({
                "title": "高关注+低信任危险组合",
                "severity": "high",
                "explanation": "高曝光度叠加低信任度，任何新刺激都可能引发二次危机",
            })

        # ── 机会信号 ──
        opportunities = []
        if current_state.get("stability_level", 0) > 0.5 and current_state.get("panic_level", 1) < 0.4:
            opportunities.append({
                "title": "修复型沟通窗口",
                "confidence": scores.get("trust_recovery", 0.5),
                "explanation": "系统稳定性尚可且恐慌有所回落，适合进入修复型沟通阶段",
            })
        if current_state.get("trust_level", 0) > 0.5:
            opportunities.append({
                "title": "信任基础尚存",
                "confidence": current_state["trust_level"],
                "explanation": f"信任度 {current_state['trust_level']:.2f}，仍有公信力资源可调动",
            })

        # 趋势判断
        trends = self._compute_recent_trends()
        if trends.get("trust_level", 0) > 0.01:
            opportunities.append({
                "title": "信任回升趋势",
                "confidence": 0.65,
                "explanation": "最近轮次信任度呈上升趋势，回应策略正在见效",
            })

        # ── 建议 ──
        recommendations = {
            "within_24h": [],
            "within_72h": [],
            "within_2_weeks": [],
        }

        if any(r["severity"] == "high" for r in risks):
            recommendations["within_24h"].append("发布事实澄清声明，明确回应核心争议点")
            recommendations["within_24h"].append("启动舆情实时监控，捕捉二次爆发苗头")

        if current_state.get("polarization_level", 0) > 0.5:
            recommendations["within_72h"].append("推动理性讨论框架，邀请权威第三方提供独立评估")
            recommendations["within_72h"].append("分群体精准沟通：学生群体、教职工、校友、媒体")

        recommendations["within_2_weeks"].append("开展制度修复叙事，展示整改措施和长效机制")
        recommendations["within_2_weeks"].append("策划正面议题，逐步完成舆论注意力转移")

        # 文本
        lines = ["## 决策支持简报\n"]
        lines.append(f"**综合诊断**: {overall}\n")
        lines.append(f"综合健康 {scores.get('reputation_health', 0):.2f} | "
                     f"风险升级 {scores.get('risk_escalation', 0):.2f} | "
                     f"修复潜力 {scores.get('trust_recovery', 0):.2f} | "
                     f"极化压力 {scores.get('polarization_pressure', 0):.2f}\n")

        if risks:
            lines.append("**⚠ 主要风险**\n")
            for r in risks:
                lines.append(f"- [{r['severity'].upper()}] {r['title']}: {r['explanation']}")

        if opportunities:
            lines.append("\n**✅ 机会窗口**\n")
            for o in opportunities:
                lines.append(f"- {o['title']}（置信度 {o.get('confidence', 0):.2f}）: {o['explanation']}")

        lines.append("\n**📋 分阶段行动建议**\n")
        for period, rec_actions in recommendations.items():
            if rec_actions:
                period_cn = {"within_24h": "24 小时内", "within_72h": "72 小时内", "within_2_weeks": "2 周内"}
                lines.append(f"\n*{period_cn.get(period, period)}*")
                for a in rec_actions:
                    lines.append(f"- {a}")

        result = {
            "diagnosis": {"overall_status": overall, "scores": scores},
            "risks": risks,
            "opportunities": opportunities,
            "recommendations": recommendations,
            "causal_summary": f"共 {causal.get('total_edges', 0)} 条因果边",
        }
        result["text"] = "\n".join(lines)
        return result

    # ════════════════ 7. 模拟证据检索 ════════════════

    def search_simulation_evidence(self, query: str, limit: int = 15) -> Dict[str, Any]:
        """
        在动作日志/事件/状态变化中检索证据。
        ReportAgent 工具: simulation_evidence_search
        """
        query_lower = query.lower()
        results = []

        # 搜索事件
        for evt in self.events:
            desc = evt.get("description", "")
            if query_lower in desc.lower() or query_lower in evt.get("event_type", "").lower():
                results.append({
                    "type": "event",
                    "round": evt.get("round_num", 0),
                    "content": desc,
                    "severity": evt.get("severity", 0),
                    "event_type": evt.get("event_type", ""),
                })

        # 搜索动作（content 字段）
        action_matches = []
        for act in self.actions:
            content = act.get("content", "")
            if query_lower in content.lower():
                action_matches.append({
                    "type": "action",
                    "round": act.get("round", 0),
                    "platform": act.get("platform", ""),
                    "agent_name": act.get("agent_name", ""),
                    "action_type": act.get("action_type", ""),
                    "content": content[:200],
                })
        # 按 round 排序，取前 N
        action_matches.sort(key=lambda x: x["round"])
        results.extend(action_matches[:limit])

        # 搜索因果证据
        for edge in self.causal_edges:
            ev = edge.get("evidence", "")
            if query_lower in ev.lower():
                results.append({
                    "type": "causal_edge",
                    "round": edge.get("round_num", 0),
                    "content": ev,
                    "relation_type": edge.get("relation_type", ""),
                    "strength": edge.get("strength", 0),
                })

        # 搜索 Agent 认知轨迹（策略转换、动作摘要）
        for record in self.cognition_history:
            rn = record.get("round_num", 0)
            for agent in record.get("agents", []):
                name = agent.get("entity_name", "")
                action_summary = agent.get("last_action_summary", "")
                focus = agent.get("attention_focus", "")
                text = f"{name} {action_summary} {focus}"
                if query_lower in text.lower() or query_lower in name.lower():
                    results.append({
                        "type": "cognition",
                        "round": rn,
                        "content": f"{name}: 策略={agent.get('strategy', '?')}, "
                                   f"情绪={agent.get('emotional_arousal', 0):.2f}, "
                                   f"信任={agent.get('trust_in_authority', 0):.2f}, "
                                   f"动作={action_summary}",
                        "agent_name": name,
                    })

        results.sort(key=lambda x: x.get("severity", 0) or 0, reverse=True)
        results = results[:limit]

        lines = [f"## 模拟证据检索: \"{query}\"（找到 {len(results)} 条）\n"]
        for i, r in enumerate(results):
            tag = r["type"].upper()
            lines.append(f"{i+1}. [{tag}] 第 {r.get('round', '?')} 轮: {r.get('content', '')[:120]}")

        return {
            "query": query,
            "total_results": len(results),
            "results": results,
            "text": "\n".join(lines),
        }

    # ════════════════ 8. Agent 认知动态分析 ════════════════

    def get_agent_cognition_analysis(self) -> Dict[str, Any]:
        """
        分析 Agent 群体认知动态：情绪轨迹、策略转换、立场分化、信任演变。
        ReportAgent 工具: agent_cognition_analysis
        """
        history = self.cognition_history
        summary = self.cognition_summary

        if not history and not summary:
            return {"error": "无Agent认知数据", "text": "无Agent认知数据（模拟未启用Agent Brain或数据缺失）。"}

        total_rounds = len(history)
        agents_data = summary.get("agents", []) if summary else []
        total_agents = len(agents_data)

        # 从历史中提取策略转换和情绪峰值
        strategy_shifts = []  # (轮次, agent_name, old_strategy, new_strategy)
        emotion_peaks = []    # (轮次, agent_name, arousal)
        trust_drops = []      # (轮次, agent_name, trust_in_authority)

        prev_strategies = {}  # agent_id -> strategy
        for record in history:
            rn = record.get("round_num", 0)
            for agent in record.get("agents", []):
                aid = agent.get("agent_id")
                name = agent.get("entity_name", f"Agent_{aid}")
                strat = agent.get("strategy", "observe")
                ea = agent.get("emotional_arousal", 0)
                ta = agent.get("trust_in_authority", 0.5)

                # 策略转换
                if aid in prev_strategies and prev_strategies[aid] != strat:
                    strategy_shifts.append({
                        "round": rn, "agent_name": name,
                        "from": prev_strategies[aid], "to": strat,
                    })
                prev_strategies[aid] = strat

                # 情绪峰值
                if ea >= 0.7:
                    emotion_peaks.append({"round": rn, "agent_name": name, "arousal": ea})

                # 信任下降
                if ta <= 0.3:
                    trust_drops.append({"round": rn, "agent_name": name, "trust": ta})

        # 统计策略分布（最后一轮）
        final_strategy_dist = defaultdict(int)
        final_emotion_mean = 0.0
        final_trust_mean = 0.0
        if history:
            last_round = history[-1]
            for agent in last_round.get("agents", []):
                final_strategy_dist[agent.get("strategy", "observe")] += 1
                final_emotion_mean += agent.get("emotional_arousal", 0)
                final_trust_mean += agent.get("trust_in_authority", 0.5)
            n = max(len(last_round.get("agents", [])), 1)
            final_emotion_mean /= n
            final_trust_mean /= n

        # 文本生成
        lines = [f"## Agent 认知动态分析（{total_agents} 个 Agent，{total_rounds} 轮）\n"]

        lines.append("**最终策略分布**")
        for strat, count in sorted(final_strategy_dist.items(), key=lambda x: -x[1]):
            lines.append(f"  - {strat}: {count} 个 Agent")

        lines.append(f"\n**群体情绪均值**: {final_emotion_mean:.2f} | **群体权威信任均值**: {final_trust_mean:.2f}")

        if strategy_shifts:
            lines.append(f"\n**策略转换事件**（共 {len(strategy_shifts)} 次，展示前 10）")
            for ss in strategy_shifts[:10]:
                lines.append(f"  - 第 {ss['round']} 轮: {ss['agent_name']} {ss['from']} → {ss['to']}")

        if emotion_peaks:
            lines.append(f"\n**情绪峰值事件**（共 {len(emotion_peaks)} 次，展示前 5）")
            for ep in sorted(emotion_peaks, key=lambda x: -x["arousal"])[:5]:
                lines.append(f"  - 第 {ep['round']} 轮: {ep['agent_name']} 情绪 {ep['arousal']:.2f}")

        if trust_drops:
            lines.append(f"\n**信任崩塌事件**（共 {len(trust_drops)} 次，展示前 5）")
            for td in sorted(trust_drops, key=lambda x: x["trust"])[:5]:
                lines.append(f"  - 第 {td['round']} 轮: {td['agent_name']} 信任度 {td['trust']:.2f}")

        # 代表性 Agent 摘要（从 summary 中提取）
        if agents_data:
            lines.append("\n**代表性 Agent 最终状态**")
            for ag in agents_data[:8]:
                fs = ag.get("final_state", {})
                goals_str = "、".join(fs.get("active_goals", []))
                lines.append(
                    f"  - {ag.get('entity_name', '?')}({ag.get('entity_type', '?')}/{ag.get('stance', '?')}): "
                    f"情绪 {fs.get('emotional_arousal', 0):.2f}, "
                    f"信任 {fs.get('trust_in_authority', 0):.2f}, "
                    f"策略={fs.get('strategy', '?')}, "
                    f"目标={goals_str}"
                )

        result = {
            "total_agents": total_agents,
            "total_rounds": total_rounds,
            "final_strategy_distribution": dict(final_strategy_dist),
            "final_emotion_mean": round(final_emotion_mean, 3),
            "final_trust_mean": round(final_trust_mean, 3),
            "strategy_shifts_count": len(strategy_shifts),
            "emotion_peaks_count": len(emotion_peaks),
            "trust_drops_count": len(trust_drops),
            "strategy_shifts": strategy_shifts[:20],
            "emotion_peaks": sorted(emotion_peaks, key=lambda x: -x["arousal"])[:10],
            "trust_drops": sorted(trust_drops, key=lambda x: x["trust"])[:10],
        }
        result["text"] = "\n".join(lines)
        return result

    # ════════════════ 9. 报告规划上下文包 ════════════════

    def get_report_context_bundle(self) -> Dict[str, Any]:
        """
        为 plan_outline() 提供世界模型增强上下文。
        包含：当前状态、评分卡、关键事件、关键因果链、评估亮点。
        """
        brief = self.get_world_model_brief()
        scorecard = self.get_reputation_scorecard()
        evolution = self.get_state_evolution_analysis()
        causal = self.get_causal_chain_analysis()

        # 精简版用于规划
        lines = []
        lines.append("═══ 世界模型推演结果摘要 ═══\n")

        # 评分卡
        if "scores" in scorecard:
            lines.append(f"综合态势: {scorecard.get('overall_status', '未知')}")
            s = scorecard["scores"]
            lines.append(
                f"综合健康 {s.get('reputation_health', 0):.2f} | "
                f"风险升级 {s.get('risk_escalation', 0):.2f} | "
                f"修复潜力 {s.get('trust_recovery', 0):.2f}"
            )

        # 当前状态
        if "current_state" in brief:
            lines.append(f"\n当前世界状态（第 {brief.get('current_round', '?')} 轮）:")
            for v in STATE_VARS:
                val = brief["current_state"].get(v, 0)
                lines.append(f"  {STATE_VAR_CN[v]}: {_describe_level(val)}（{val:.2f}）")

        # 关键转折点
        tps = evolution.get("turning_points", [])[:5]
        if tps:
            lines.append(f"\n关键转折点（Top {len(tps)}）:")
            for tp in tps:
                lines.append(f"  第 {tp['round']} 轮: [{tp['event_type']}] {tp['description'][:50]}")

        # 因果链概要
        total_edges = causal.get("total_edges", 0)
        if total_edges > 0:
            lines.append(f"\n因果关系: 共 {total_edges} 条因果边")
            top_edges = causal.get("top_edges", [])[:3]
            for edge in top_edges:
                lines.append(f"  {edge.get('evidence', '')[:60]}")

        # Agent 认知概览
        cognition = self.get_agent_cognition_analysis()
        if "error" not in cognition:
            lines.append(f"\nAgent 认知动态: {cognition.get('total_agents', 0)} 个 Agent, "
                         f"情绪均值 {cognition.get('final_emotion_mean', 0):.2f}, "
                         f"信任均值 {cognition.get('final_trust_mean', 0):.2f}, "
                         f"策略转换 {cognition.get('strategy_shifts_count', 0)} 次")

        return {
            "scorecard": scorecard,
            "brief": brief,
            "evolution_summary": {
                "total_rounds": evolution.get("total_rounds", 0),
                "total_events": evolution.get("total_events", 0),
                "turning_points": tps,
            },
            "causal_summary": {"total_edges": total_edges},
            "cognition_summary": {
                "total_agents": cognition.get("total_agents", 0),
                "emotion_mean": cognition.get("final_emotion_mean", 0),
                "trust_mean": cognition.get("final_trust_mean", 0),
                "strategy_shifts": cognition.get("strategy_shifts_count", 0),
            } if "error" not in cognition else {},
            "text": "\n".join(lines),
        }

    # ════════════════ 内部工具 ════════════════

    def _compute_recent_trends(self, window: int = 5) -> Dict[str, float]:
        """计算最近 N 轮的状态斜率"""
        states = self.states
        if len(states) < 2:
            return {v: 0.0 for v in STATE_VARS}

        by_round: Dict[int, Dict] = {}
        for s in states:
            by_round[s.get("round_num", 0)] = s
        ordered = [by_round[r] for r in sorted(by_round.keys())]

        recent = ordered[-min(window, len(ordered)):]
        trends = {}
        for v in STATE_VARS:
            vals = [s.get(v, 0.0) for s in recent]
            if len(vals) >= 2:
                trends[v] = round((vals[-1] - vals[0]) / max(len(vals) - 1, 1), 4)
            else:
                trends[v] = 0.0
        return trends

    # ════════════════ 10. 结构化决策简报（Phase 3 新增） ════════════════

    def get_structured_decision_brief(self, baseline_context: Optional[Dict] = None) -> Dict[str, Any]:
        """
        升级版决策简报，对应蓝图 §5.6.3 DecisionBrief 结构。

        Args:
            baseline_context: 可选的基线快照 dict，包含 confirmed_facts, key_actors,
                              current_risks, current_stage 等。传入后将用于增强简报内容。

        输出字段：
        - current_diagnosis
        - top_risks
        - top_opportunities
        - recommended_actions（来自 InterventionLibrary）
        - action_alternatives
        - supporting_evidence
        - monitoring_signals
        - no_action_risk
        - forecast_paths
        """
        # 复用已有能力
        base_brief = self.get_decision_support_brief()
        if "error" in base_brief:
            return base_brief

        scorecard = self.get_reputation_scorecard()
        scores = scorecard.get("scores", {})
        current_state = scorecard.get("current_state", {})
        trends = self._compute_recent_trends()

        # 引入干预动作库
        from .intervention_library import InterventionLibrary
        lib = InterventionLibrary()

        # 基线阶段（如有）
        bl_stage = baseline_context.get("current_stage", "") if baseline_context else ""

        # 推荐 Top-3 动作（传入阶段以差异化排序）
        recommended = lib.recommend_actions(current_state, max_results=3, stage=bl_stage)

        # 替代方案 = 推荐排名 4~6
        alternatives = lib.recommend_actions(current_state, max_results=6, stage=bl_stage)[3:]

        # 基线风险列表（用于不作为风险 + 监测信号）
        bl_risks = baseline_context.get("current_risks", []) if baseline_context else []

        # 不作为风险评估
        no_action_risk = self._assess_no_action_risk(current_state, trends, baseline_risks=bl_risks, stage=bl_stage)

        # 预测路径摘要（基于当前趋势外推）
        forecast_paths = self._extrapolate_forecast_paths(current_state, trends, stage=bl_stage)

        # 监测信号
        monitoring_signals = self._derive_monitoring_signals(current_state, trends, baseline_risks=bl_risks, stage=bl_stage)

        # 支持证据
        evidence = []
        for r in base_brief.get("risks", []):
            evidence.append({
                "claim": r["title"],
                "evidence_type": "world_state",
                "detail": r["explanation"],
            })

        # ── 基线增强：基线数据实质性改变简报内容 ──
        baseline_summary = None
        top_risks = list(base_brief.get("risks", []))

        if baseline_context:
            bl_facts = baseline_context.get("confirmed_facts", [])
            bl_risks = baseline_context.get("current_risks", [])
            bl_actors = baseline_context.get("key_actors", [])
            bl_stage = baseline_context.get("current_stage", "")
            bl_topics = baseline_context.get("key_topics", [])

            # 1) 将基线风险合并到 top_risks（真正显示出来）
            existing_titles = {r.get("title", "") for r in top_risks}
            for br in bl_risks:
                if br and br not in existing_titles:
                    top_risks.append({
                        "title": br,
                        "severity": "medium",
                        "explanation": f"基线分析识别的风险（阶段：{bl_stage or '未知'}）",
                        "source": "baseline",
                    })
                    evidence.append({
                        "claim": br,
                        "evidence_type": "baseline",
                        "detail": f"基线识别的风险: {br}",
                    })

            # 2) 根据基线阶段调整世界状态权重，让推荐动作差异化
            stage_state_modifier = self._get_stage_state_modifier(bl_stage)
            if stage_state_modifier:
                modified_state = {k: max(0, min(1, v + stage_state_modifier.get(k, 0)))
                                  for k, v in current_state.items()}
                # 用调整后的状态重新计算推荐动作
                recommended = lib.recommend_actions(modified_state, max_results=3, stage=bl_stage)
                alternatives = lib.recommend_actions(modified_state, max_results=6, stage=bl_stage)[3:]
                no_action_risk = self._assess_no_action_risk(modified_state, trends, baseline_risks=bl_risks, stage=bl_stage)
                forecast_paths = self._extrapolate_forecast_paths(modified_state, trends, stage=bl_stage)
                monitoring_signals = self._derive_monitoring_signals(modified_state, trends, baseline_risks=bl_risks, stage=bl_stage)
                # 用修正后的状态替换展示数据，让态势图反映基线阶段
                current_state = modified_state

            # 3) 将基线事实添加到证据中
            for fact in bl_facts[:5]:
                evidence.append({
                    "claim": fact,
                    "evidence_type": "baseline_fact",
                    "detail": f"基线已确认事实",
                })

            baseline_summary = {
                "stage": bl_stage,
                "confirmed_facts": bl_facts[:10],
                "key_actors": bl_actors[:10],
                "key_topics": bl_topics[:10],
                "identified_risks": bl_risks[:5],
                "baseline_id": baseline_context.get("baseline_id"),
            }

        result = {
            "current_diagnosis": {
                "overall_status": scorecard.get("overall_status", "未知"),
                "scores": scores,
                "current_state": current_state,
                "trends": trends,
            },
            "top_risks": top_risks,
            "top_opportunities": base_brief.get("opportunities", []),
            "recommended_actions": recommended,
            "action_alternatives": alternatives,
            "supporting_evidence": evidence,
            "monitoring_signals": monitoring_signals,
            "no_action_risk": no_action_risk,
            "forecast_paths": forecast_paths,
            "phased_recommendations": base_brief.get("recommendations", {}),
        }
        if baseline_summary:
            result["baseline_context"] = baseline_summary
        return result

    @staticmethod
    def _get_stage_state_modifier(stage: str) -> Optional[Dict[str, float]]:
        """
        根据事件阶段返回世界状态修正量。
        不同阶段的关注重点不同，修正量会改变推荐动作的优先级排序。
        """
        if not stage:
            return None
        stage_lower = stage.strip().lower()
        modifiers = {
            "爆发期": {"attention_level": 0.15, "panic_level": 0.12, "trust_level": -0.1, "risk_level": 0.1},
            "发酵期": {"polarization_level": 0.12, "attention_level": 0.08, "stability_level": -0.1, "panic_level": 0.05},
            "平台期": {"attention_level": -0.05, "stability_level": 0.05, "polarization_level": 0.05},
            "消退期": {"attention_level": -0.1, "panic_level": -0.08, "stability_level": 0.1, "trust_level": 0.05},
            "二次爆发": {"attention_level": 0.2, "panic_level": 0.15, "trust_level": -0.15, "risk_level": 0.15},
        }
        for key, mod in modifiers.items():
            if key in stage_lower:
                return mod
        return None

    def _assess_no_action_risk(
        self, state: Dict[str, float], trends: Dict[str, float],
        baseline_risks: Optional[List[str]] = None, stage: str = ""
    ) -> Dict[str, Any]:
        """评估"不采取任何行动"的风险，综合世界状态 + 基线风险"""
        risk_score = 0.0
        reasons = []

        # 基于世界状态的风险因子
        panic = state.get("panic_level", 0)
        trust = state.get("trust_level", 1)
        attention = state.get("attention_level", 0)
        polarization = state.get("polarization_level", 0)
        risk_level = state.get("risk_level", 0)

        if panic > 0.15:
            risk_score += min(0.3, panic * 0.4)
            reasons.append(f"恐慌水平 {panic:.0%}，不干预可能继续攀升")
        if trust < 0.5:
            risk_score += min(0.25, (0.5 - trust) * 0.5)
            reasons.append(f"信任度仅 {trust:.0%}，低于安全线")
        if attention > 0.15:
            risk_score += min(0.2, attention * 0.3)
            reasons.append(f"关注度 {attention:.0%}，信息真空易被谣言填充")
        if polarization > 0.2:
            risk_score += min(0.15, polarization * 0.3)
            reasons.append(f"极化度 {polarization:.0%}，不干预可能固化对立")
        if risk_level > 0.2:
            risk_score += min(0.15, risk_level * 0.3)
            reasons.append(f"风险等级 {risk_level:.0%}")

        # 基于基线阶段的额外风险
        stage_risk_boost = {
            "爆发期": (0.25, "事件处于爆发期，不回应将严重损害公信力"),
            "发酵期": (0.15, "事件正在发酵，延迟行动将扩大负面影响范围"),
            "二次爆发": (0.3, "事件二次爆发，紧迫性极高"),
        }
        if stage:
            for key, (boost, reason) in stage_risk_boost.items():
                if key in stage:
                    risk_score += boost
                    reasons.append(reason)
                    break

        # 基于基线识别的风险数量（按阶段衰减：消退期/平台期风险贡献降低）
        if baseline_risks:
            n = len(baseline_risks)
            stage_decay = 1.0
            if stage:
                if "消退" in stage:
                    stage_decay = 0.4
                elif "平台" in stage:
                    stage_decay = 0.7
            risk_contribution = min(0.2, n * 0.05) * stage_decay
            risk_score += risk_contribution
            if n >= 3 and stage_decay >= 0.7:
                reasons.append(f"基线已识别 {n} 项风险，不作为将放任风险累积")

        risk_score = min(1.0, risk_score)
        severity = "low" if risk_score < 0.2 else ("medium" if risk_score < 0.5 else "high")

        return {
            "risk_score": round(risk_score, 3),
            "risk_percent": f"{int(risk_score * 100)}%",
            "severity": severity,
            "reasons": reasons,
            "recommendation": "强烈建议立即采取行动" if severity == "high" else (
                "建议在 24h 内采取行动" if severity == "medium" else "可观望，但需持续监测"
            ),
        }

    def _extrapolate_forecast_paths(
        self, state: Dict[str, float], trends: Dict[str, float],
        stage: str = ""
    ) -> List[Dict[str, Any]]:
        """基于当前趋势 + 阶段特征外推 3 种路径"""
        CN = {"attention_level": "关注度", "panic_level": "恐慌度", "trust_level": "信任度",
              "polarization_level": "极化度", "risk_level": "风险等级", "stability_level": "稳定性"}
        BAD = {"panic_level", "polarization_level", "risk_level", "attention_level"}
        GOOD = {"trust_level", "stability_level"}

        def _risk_cn(score):
            if score > 0.6: return "高"
            if score > 0.3: return "中"
            return "低"

        def _key_changes(projected):
            """找出与当前状态差异最大的 2-3 个维度"""
            diffs = []
            for v in STATE_VARS:
                d = projected.get(v, 0.5) - state.get(v, 0.5)
                if abs(d) > 0.02:
                    direction = "↑" if d > 0 else "↓"
                    good = (v in BAD and d < 0) or (v in GOOD and d > 0)
                    diffs.append((abs(d), CN.get(v, v), direction, f"{abs(d)*100:.0f}%", good))
            diffs.sort(reverse=True)
            return diffs[:3]

        def _prob_label(p):
            if p >= 0.6: return "较大"
            if p >= 0.35: return "中等"
            return "较小"

        paths = []

        # ── 路径 A：自然演化（不干预） ──
        natural = {}
        for v in STATE_VARS:
            natural[v] = round(max(0, min(1, state.get(v, 0.5) + trends.get(v, 0) * 10)), 3)
        nat_risk = natural.get("risk_level", 0.5)
        nat_changes = _key_changes(natural)
        nat_prob = 0.5 if not stage else (0.3 if "爆发" in stage else 0.45)
        paths.append({
            "path_id": "natural",
            "label": "自然演化（不干预）",
            "risk_level": _risk_cn(nat_risk),
            "probability": _prob_label(nat_prob),
            "description": "不采取任何措施，事态按当前趋势自然发展",
            "key_changes": [f"{c[1]} {c[2]}{c[3]}" for c in nat_changes],
            "outcome": "风险持续累积，可能错过最佳干预窗口" if nat_risk > 0.4 else "态势相对平稳，但仍需密切监测",
            "projected_state_10_rounds": natural,
        })

        # ── 路径 B：积极干预 ──
        active = {}
        for v in STATE_VARS:
            if v in BAD:
                active[v] = round(max(0, state.get(v, 0.5) - 0.15), 3)
            else:
                active[v] = round(min(1, state.get(v, 0.5) + 0.12), 3)
        act_risk = active.get("risk_level", 0.3)
        act_changes = _key_changes(active)
        act_prob = 0.35 if not stage else (0.5 if "爆发" in stage else 0.35)
        paths.append({
            "path_id": "active_intervention",
            "label": "积极干预",
            "risk_level": _risk_cn(act_risk),
            "probability": _prob_label(act_prob),
            "description": "迅速采取公开回应、第三方调查等组合措施",
            "key_changes": [f"{c[1]} {c[2]}{c[3]}" for c in act_changes],
            "outcome": "有望在短期内控制态势，恢复公众信任" if act_risk < 0.3 else "可降低风险但需持续跟进",
            "projected_state_10_rounds": active,
        })

        # ── 路径 C：保守应对 ──
        conservative = {}
        for v in STATE_VARS:
            if v in BAD:
                conservative[v] = round(max(0, state.get(v, 0.5) - 0.05), 3)
            else:
                conservative[v] = round(min(1, state.get(v, 0.5) + 0.04), 3)
        con_risk = conservative.get("risk_level", 0.4)
        con_changes = _key_changes(conservative)
        con_prob = 0.3 if not stage else (0.2 if "爆发" in stage else 0.35)
        paths.append({
            "path_id": "conservative",
            "label": "保守应对",
            "risk_level": _risk_cn(con_risk),
            "probability": _prob_label(con_prob),
            "description": "采取最小限度回应，观察事态变化后再决策",
            "key_changes": [f"{c[1]} {c[2]}{c[3]}" for c in con_changes],
            "outcome": "短期风险可控但恢复缓慢，可能丧失主动权" if con_risk > 0.25 else "风险较低，适合观望阶段",
            "projected_state_10_rounds": conservative,
        })

        return paths

    def _derive_monitoring_signals(
        self, state: Dict[str, float], trends: Dict[str, float],
        baseline_risks: Optional[List[str]] = None, stage: str = ""
    ) -> List[Dict[str, Any]]:
        """根据当前状态 + 基线信息派生关键监测信号"""
        signals = []

        if state.get("trust_level", 1) < 0.5:
            signals.append({
                "signal": "信任度低于安全线",
                "current_value": state.get("trust_level", 0),
                "threshold": 0.5,
                "direction": "below",
                "priority": "high",
            })
        if trends.get("panic_level", 0) > 0.03:
            signals.append({
                "signal": "恐慌水平持续上升",
                "trend_per_round": trends.get("panic_level", 0),
                "priority": "high",
            })
        if state.get("polarization_level", 0) > 0.2:
            signals.append({
                "signal": "极化趋势需关注",
                "current_value": state.get("polarization_level", 0),
                "threshold": 0.2,
                "direction": "above",
                "priority": "medium",
            })
        if trends.get("attention_level", 0) > 0.05:
            signals.append({
                "signal": "关注度快速上升（可能二次爆发）",
                "trend_per_round": trends.get("attention_level", 0),
                "priority": "high",
            })
        if state.get("stability_level", 1) < 0.8:
            signals.append({
                "signal": f"稳定性 {state.get('stability_level', 0):.0%}，需持续关注",
                "current_value": state.get("stability_level", 0),
                "threshold": 0.8,
                "direction": "below",
                "priority": "medium",
            })
        if state.get("risk_level", 0) > 0.2:
            signals.append({
                "signal": f"风险等级 {state.get('risk_level', 0):.0%}",
                "current_value": state.get("risk_level", 0),
                "threshold": 0.2,
                "direction": "above",
                "priority": "medium",
            })

        # 基线阶段相关的监测信号
        stage_signals = {
            "爆发期": [
                {"signal": "事件处于爆发期，需密切监测舆情扩散速度", "priority": "high"},
                {"signal": "关注官方回应时效（黄金6小时）", "priority": "high"},
            ],
            "发酵期": [
                {"signal": "监测二次传播渠道和意见领袖动态", "priority": "high"},
                {"signal": "关注极化趋势和对立阵营形成", "priority": "medium"},
            ],
            "平台期": [
                {"signal": "关注公众疲劳度和注意力转移", "priority": "medium"},
            ],
            "消退期": [
                {"signal": "关注长尾效应和制度改进落实", "priority": "low"},
            ],
        }
        if stage:
            for key, sigs in stage_signals.items():
                if key in stage:
                    signals.extend(sigs)
                    break

        # 基线风险转为监测信号
        if baseline_risks:
            for br in baseline_risks[:3]:
                signals.append({
                    "signal": f"基线风险: {br[:30]}",
                    "priority": "medium",
                    "source": "baseline",
                })

        return signals
