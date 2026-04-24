"""
干预动作模板库（Intervention Library）

为高校舆情场景提供结构化干预动作模板，
每个模板包含：预期效果、副作用、前置条件、监测指标、
以及对 6 维世界状态变量的预期影响向量。

蓝图 §5.6.5 实现。
"""

from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field, asdict

from ..utils.logger import get_logger

logger = get_logger("nexusmind.intervention_library")


# ============================================================
# 数据结构
# ============================================================

@dataclass
class InterventionTemplate:
    """干预动作模板"""
    action_id: str
    title: str
    category: str                    # response / investigation / communication / suspension / reform
    why_now: str                     # 何时/为何适用
    target_groups: List[str]         # 作用目标群体
    expected_effects: List[str]      # 预期正面效果
    possible_side_effects: List[str] # 潜在副作用
    required_prerequisites: List[str]  # 前置条件
    monitoring_metrics: List[str]    # 执行后需监测的指标
    estimated_delay_hours: float     # 效果显现预估时间（小时）
    confidence: float                # 模板适用置信度基准 [0, 1]

    # 对 6 维世界状态的预期影响方向与幅度 (正值=增加, 负值=减少)
    state_effects: Dict[str, float] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ============================================================
# 高校舆情场景预置模板库
# ============================================================

UNIVERSITY_INCIDENT_TEMPLATES: List[InterventionTemplate] = [
    InterventionTemplate(
        action_id="act_preliminary_response",
        title="发布初步回应",
        category="response",
        why_now="事件曝光初期（0-6h），公众关注急剧上升但信息真空时，应在第一时间发声定调",
        target_groups=["学生群体", "媒体", "公众"],
        expected_effects=[
            "填补信息真空，抑制谣言扩散",
            "展示机构责任感",
            "降低恐慌指数",
        ],
        possible_side_effects=[
            "表态过早可能被后续事实推翻",
            "措辞不当可能引发二次争议",
        ],
        required_prerequisites=[
            "基本事实初步核实",
            "发言人/责任部门确定",
        ],
        monitoring_metrics=[
            "24h 内公众信任度变化",
            "初步回应传播覆盖率",
            "谣言新增量",
        ],
        estimated_delay_hours=2,
        confidence=0.85,
        state_effects={
            "trust_level": +0.08,
            "panic_level": -0.10,
            "attention_level": -0.03,
            "polarization_level": -0.02,
            "risk_level": -0.06,
            "stability_level": +0.05,
        },
    ),
    InterventionTemplate(
        action_id="act_full_disclosure",
        title="发布完整通报",
        category="response",
        why_now="初步回应后 12-48h，已完成事实调查，公众期待完整信息",
        target_groups=["学生群体", "教职工", "媒体", "校友", "公众"],
        expected_effects=[
            "大幅提升信任度",
            "消除信息不对称",
            "为后续处置建立事实基础",
        ],
        possible_side_effects=[
            "完整信息可能暴露更多问题",
            "如与初步回应矛盾会严重损害信誉",
        ],
        required_prerequisites=[
            "事实调查基本完成",
            "法律合规审查",
            "各利益相关方知情",
        ],
        monitoring_metrics=[
            "信任度回升幅度",
            "媒体报道调性变化",
            "新增质疑话题数",
        ],
        estimated_delay_hours=6,
        confidence=0.80,
        state_effects={
            "trust_level": +0.15,
            "panic_level": -0.12,
            "attention_level": +0.05,
            "polarization_level": -0.05,
            "risk_level": -0.10,
            "stability_level": +0.10,
        },
    ),
    InterventionTemplate(
        action_id="act_third_party_investigation",
        title="启动第三方调查",
        category="investigation",
        why_now="公众对当事方自查不信任时，引入独立调查重建公信力",
        target_groups=["公众", "媒体", "监管部门"],
        expected_effects=[
            "显著提升调查可信度",
            "减少极化对立",
            "转移舆论焦点到程序正义",
        ],
        possible_side_effects=[
            "调查周期长，公众可能失去耐心",
            "调查结论可能对机构不利",
            "调查成本较高",
        ],
        required_prerequisites=[
            "上级部门或董事会授权",
            "第三方机构确定",
            "调查范围和时间表明确",
        ],
        monitoring_metrics=[
            "极化度变化",
            "信任度趋势",
            "对调查公正性的评价",
        ],
        estimated_delay_hours=48,
        confidence=0.75,
        state_effects={
            "trust_level": +0.12,
            "panic_level": -0.05,
            "attention_level": 0.0,
            "polarization_level": -0.10,
            "risk_level": -0.08,
            "stability_level": +0.08,
        },
    ),
    InterventionTemplate(
        action_id="act_townhall_meeting",
        title="召开说明会 / 恳谈会",
        category="communication",
        why_now="事件发展中期，公众情绪有所回落但仍有疑虑，适合面对面沟通",
        target_groups=["学生群体", "教职工", "家长"],
        expected_effects=[
            "直接回应关切问题",
            "展示诚意和透明度",
            "收集利益相关方真实诉求",
        ],
        possible_side_effects=[
            "现场情绪失控风险",
            "可能产生新的争议性片段/视频",
            "如回应不力反而加剧不满",
        ],
        required_prerequisites=[
            "完整通报已发布",
            "发言人充分准备",
            "现场安全预案",
        ],
        monitoring_metrics=[
            "参与者满意度",
            "会后舆论调性变化",
            "新增投诉量",
        ],
        estimated_delay_hours=12,
        confidence=0.70,
        state_effects={
            "trust_level": +0.10,
            "panic_level": -0.08,
            "attention_level": +0.03,
            "polarization_level": -0.07,
            "risk_level": -0.05,
            "stability_level": +0.06,
        },
    ),
    InterventionTemplate(
        action_id="act_hold_response_12h",
        title="暂缓回应 12 小时",
        category="response",
        why_now="事实不清、信息混乱时，贸然回应风险大于沉默风险",
        target_groups=["内部决策层"],
        expected_effects=[
            "避免仓促表态被事实推翻",
            "争取调查时间",
        ],
        possible_side_effects=[
            "信息真空可能被谣言填充",
            "公众可能解读为逃避",
            "关注度持续攀升",
        ],
        required_prerequisites=[
            "内部研判：仓促回应的风险 > 沉默的风险",
        ],
        monitoring_metrics=[
            "12h 内谣言增长量",
            "关注度峰值",
            "信任度下降幅度",
        ],
        estimated_delay_hours=12,
        confidence=0.60,
        state_effects={
            "trust_level": -0.04,
            "panic_level": +0.06,
            "attention_level": +0.08,
            "polarization_level": +0.03,
            "risk_level": +0.04,
            "stability_level": -0.03,
        },
    ),
    InterventionTemplate(
        action_id="act_suspend_involved",
        title="暂停涉事人员相关资格/权限",
        category="suspension",
        why_now="涉事人员继续在岗会持续刺激公众情绪，暂停可降低对立",
        target_groups=["公众", "学生群体", "媒体"],
        expected_effects=[
            "展示问责态度",
            "降低持续刺激",
            "为调查排除干扰",
        ],
        possible_side_effects=[
            "暂停不等于定性，需避免被解读为已定罪",
            "涉事人员可能反诉或公开喊冤",
        ],
        required_prerequisites=[
            "初步调查有充分依据",
            "法律/劳动合规审查",
            "保密措施",
        ],
        monitoring_metrics=[
            "公众情绪反馈",
            "涉事人员动态",
            "极化度变化",
        ],
        estimated_delay_hours=4,
        confidence=0.75,
        state_effects={
            "trust_level": +0.10,
            "panic_level": -0.08,
            "attention_level": -0.02,
            "polarization_level": -0.06,
            "risk_level": -0.07,
            "stability_level": +0.05,
        },
    ),
    InterventionTemplate(
        action_id="act_institutional_reform",
        title="启动制度整改说明",
        category="reform",
        why_now="事件进入收尾期，公众期待看到根源性改进而非仅仅处罚个人",
        target_groups=["学生群体", "教职工", "校友", "公众", "监管部门"],
        expected_effects=[
            "展示长效改进决心",
            "恢复机构形象",
            "预防同类事件再发",
        ],
        possible_side_effects=[
            "如整改浮于表面可能被质疑",
            "可能暴露更多制度缺陷",
        ],
        required_prerequisites=[
            "调查结论已出",
            "改进方案经过专家论证",
            "资源保障到位",
        ],
        monitoring_metrics=[
            "制度落实进度",
            "公众评价变化",
            "类似事件再发率",
        ],
        estimated_delay_hours=72,
        confidence=0.70,
        state_effects={
            "trust_level": +0.12,
            "panic_level": -0.03,
            "attention_level": -0.05,
            "polarization_level": -0.04,
            "risk_level": -0.10,
            "stability_level": +0.12,
        },
    ),
    InterventionTemplate(
        action_id="act_expert_endorsement",
        title="组织权威背书与专家评估",
        category="communication",
        why_now="公众不信任当事方单方面说法时，需引入权威第三方增信",
        target_groups=["公众", "媒体", "学术圈"],
        expected_effects=[
            "借助外部权威提升可信度",
            "提供专业视角降低极化",
            "为后续处置方案背书",
        ],
        possible_side_effects=[
            "如专家立场被质疑为'站台'会适得其反",
            "专家意见可能与机构预期不一致",
        ],
        required_prerequisites=[
            "合适的权威专家/机构已确定",
            "专家了解完整事实",
            "双方就信息披露达成共识",
        ],
        monitoring_metrics=[
            "专家观点传播覆盖率",
            "公众对专家公正性的评价",
            "信任度变化",
        ],
        estimated_delay_hours=24,
        confidence=0.70,
        state_effects={
            "trust_level": +0.10,
            "panic_level": -0.05,
            "attention_level": 0.0,
            "polarization_level": -0.08,
            "risk_level": -0.06,
            "stability_level": +0.07,
        },
    ),
]


# ============================================================
# 查询与推荐接口
# ============================================================

class InterventionLibrary:
    """干预动作模板库管理器"""

    def __init__(self, templates: List[InterventionTemplate] | None = None):
        self._templates: Dict[str, InterventionTemplate] = {}
        for t in (templates or UNIVERSITY_INCIDENT_TEMPLATES):
            self._templates[t.action_id] = t

    # ---------- 基础查询 ----------

    def list_all(self) -> List[Dict[str, Any]]:
        return [t.to_dict() for t in self._templates.values()]

    def get_template(self, action_id: str) -> InterventionTemplate | None:
        return self._templates.get(action_id)

    def get_by_category(self, category: str) -> List[InterventionTemplate]:
        return [t for t in self._templates.values() if t.category == category]

    # ---------- 智能推荐 ----------

    # 不同阶段对不同类别动作的优先级加成（大幅拉开差距）
    STAGE_ACTION_BOOST: Dict[str, Dict[str, float]] = {
        "爆发期": {
            "act_preliminary_response": 0.5,   # 爆发期首要：初步回应
            "act_hold_response_12h": 0.3,       # 可暂缓等事实清楚
            "act_suspend_involved": 0.2,        # 快速止血
            "act_full_disclosure": -0.2,        # 爆发期信息不全，不宜完整通报
            "act_institutional_reform": -0.3,   # 太早谈制度整改不合时宜
        },
        "发酵期": {
            "act_full_disclosure": 0.4,         # 发酵期核心：信息透明
            "act_third_party_investigation": 0.3,
            "act_townhall_meeting": 0.2,
            "act_preliminary_response": -0.3,   # 已过初步回应时机
            "act_hold_response_12h": -0.4,      # 发酵期沉默有害
        },
        "平台期": {
            "act_townhall_meeting": 0.4,        # 平台期适合对话
            "act_expert_endorsement": 0.3,      # 引入权威背书
            "act_institutional_reform": 0.2,
            "act_preliminary_response": -0.4,
        },
        "消退期": {
            "act_institutional_reform": 0.5,    # 消退期核心：长效整改
            "act_expert_endorsement": 0.3,
            "act_townhall_meeting": 0.2,
            "act_preliminary_response": -0.5,
            "act_suspend_involved": -0.3,
        },
    }

    def recommend_actions(
        self,
        current_state: Dict[str, float],
        max_results: int = 3,
        stage: str = "",
    ) -> List[Dict[str, Any]]:
        """
        根据当前世界状态推荐最合适的干预动作。

        评分逻辑：
        - 对每个模板计算 "预期改善分"：
          sum( |negative_effect_on_bad_vars| + |positive_effect_on_good_vars| )
        - 加权考虑当前状态偏离程度
        - 根据事件阶段（stage）给予大幅加减分
        """
        # 定义"期望方向"：这些变量越低越好
        lower_is_better = {"panic_level", "polarization_level", "risk_level", "attention_level"}
        # 这些变量越高越好
        higher_is_better = {"trust_level", "stability_level"}

        # 查找阶段加成表
        stage_boost = {}
        if stage:
            for key, boosts in self.STAGE_ACTION_BOOST.items():
                if key in stage:
                    stage_boost = boosts
                    break

        scored = []
        for t in self._templates.values():
            score = 0.0
            for var, effect in t.state_effects.items():
                current_val = current_state.get(var, 0.5)
                if var in lower_is_better:
                    # 当前值高 + 模板能降 → 好
                    urgency = max(0, current_val - 0.3)
                    if effect < 0:
                        score += abs(effect) * (1 + urgency * 2)
                    else:
                        score -= abs(effect) * (0.5 + urgency)
                elif var in higher_is_better:
                    # 当前值低 + 模板能升 → 好
                    urgency = max(0, 0.7 - current_val)
                    if effect > 0:
                        score += abs(effect) * (1 + urgency * 2)
                    else:
                        score -= abs(effect) * (0.5 + urgency)

            score *= t.confidence
            # 阶段加成
            score += stage_boost.get(t.action_id, 0)
            scored.append((score, t))

        scored.sort(key=lambda x: x[0], reverse=True)

        results = []
        for rank, (sc, t) in enumerate(scored[:max_results], 1):
            d = t.to_dict()
            d["recommendation_score"] = round(sc, 4)
            d["recommendation_rank"] = rank
            results.append(d)

        return results

    def evaluate_intervention_plan(
        self,
        action_ids: List[str],
        current_state: Dict[str, float],
    ) -> Dict[str, Any]:
        """
        评估一组干预动作的组合效果。

        返回：
        - 各动作独立预期效果
        - 组合后 6 维状态预期变化
        - 可能的冲突/叠加效应
        """
        actions_detail = []
        combined_effects: Dict[str, float] = {}

        for aid in action_ids:
            t = self._templates.get(aid)
            if not t:
                actions_detail.append({"action_id": aid, "error": "模板不存在"})
                continue
            actions_detail.append(t.to_dict())
            for var, eff in t.state_effects.items():
                combined_effects[var] = combined_effects.get(var, 0) + eff

        # 预期新状态
        projected_state = {}
        for var in ["attention_level", "panic_level", "trust_level",
                     "polarization_level", "risk_level", "stability_level"]:
            base = current_state.get(var, 0.5)
            delta = combined_effects.get(var, 0)
            projected_state[var] = round(max(0.0, min(1.0, base + delta)), 3)

        # 冲突检测：同一变量有相反方向的效果
        conflicts = []
        for var in combined_effects:
            effects_on_var = []
            for aid in action_ids:
                t = self._templates.get(aid)
                if t and var in t.state_effects:
                    effects_on_var.append((aid, t.state_effects[var]))
            if len(effects_on_var) >= 2:
                signs = [e[1] > 0 for e in effects_on_var]
                if any(signs) and not all(signs):
                    conflicts.append({
                        "variable": var,
                        "actions": [(a, round(e, 3)) for a, e in effects_on_var],
                        "warning": f"对 {var} 存在方向冲突",
                    })

        return {
            "actions": actions_detail,
            "combined_effects": {k: round(v, 4) for k, v in combined_effects.items()},
            "current_state": current_state,
            "projected_state": projected_state,
            "conflicts": conflicts,
            "total_actions": len([a for a in actions_detail if "error" not in a]),
        }
