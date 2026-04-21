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

    # ════════════════ 8. 报告规划上下文包 ════════════════

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

        return {
            "scorecard": scorecard,
            "brief": brief,
            "evolution_summary": {
                "total_rounds": evolution.get("total_rounds", 0),
                "total_events": evolution.get("total_events", 0),
                "turning_points": tps,
            },
            "causal_summary": {"total_edges": total_edges},
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
