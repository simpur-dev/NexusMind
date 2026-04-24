import json
import os
from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional


def _clamp(value: Any, low: float = 0.0, high: float = 1.0, default: float = 0.5) -> float:
    try:
        return max(low, min(high, float(value)))
    except (TypeError, ValueError):
        return default


def _safe_list(value: Any) -> List[Any]:
    return list(value) if isinstance(value, list) else []


def _safe_dict(value: Any) -> Dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


def _extract_profile_value(profile: Any, key: str, default: Any = None) -> Any:
    if profile is None:
        return default
    if isinstance(profile, dict):
        return profile.get(key, default)
    return getattr(profile, key, default)


def _build_dataclass(cls, raw: Any):
    if not isinstance(raw, dict):
        return cls()
    values = {}
    for name in cls.__dataclass_fields__.keys():
        if name in raw:
            values[name] = raw[name]
    return cls(**values)


def _level_text(value: float) -> str:
    if value >= 0.75:
        return "很高"
    if value >= 0.55:
        return "较高"
    if value >= 0.35:
        return "中等"
    if value >= 0.15:
        return "较低"
    return "很低"


def _default_identity_focus(entity_type: str, profession: str) -> List[str]:
    entity_type_lower = (entity_type or "Unknown").lower()
    if entity_type_lower in {"student", "alumni"}:
        return [profession or "学生身份", "同伴评价", "事件公平性"]
    if entity_type_lower in {"university", "governmentagency", "organization", "ngo"}:
        return [profession or "机构角色", "组织声誉", "秩序维护"]
    if entity_type_lower in {"mediaoutlet", "journalist"}:
        return [profession or "媒体角色", "信息可信度", "议题关注度"]
    if entity_type_lower in {"professor", "expert", "faculty", "official"}:
        return [profession or "专业角色", "公共影响力", "立场一致性"]
    return [profession or entity_type or "社会角色", "社会关系", "自我表达"]


def _default_goals(entity_type: str, stance: str) -> List[str]:
    entity_type_lower = (entity_type or "Unknown").lower()
    if entity_type_lower in {"university", "governmentagency", "organization", "ngo"}:
        return ["维护组织稳定", "控制风险扩散", "维持外部信任"]
    if entity_type_lower in {"mediaoutlet", "journalist"}:
        return ["追踪事件进展", "维持信息关注", "提升内容传播"]
    if entity_type_lower in {"student", "alumni"}:
        return ["表达自身立场", "保护所属群体", "争取舆论支持"]
    if entity_type_lower in {"professor", "expert", "faculty"}:
        return ["提供专业判断", "维持可信形象", "影响公共讨论"]
    if stance == "supportive":
        return ["维持秩序稳定", "减少误解扩散", "捍卫自身观点"]
    if stance == "opposing":
        return ["质疑现有叙事", "放大风险信号", "争取更多支持"]
    if stance == "observer":
        return ["持续观察局势", "搜集新增信息", "把握舆论走向"]
    return ["理解事件走向", "参与公共讨论", "保护自身位置"]


def _decision_style(entity_type: str, stance: str, utility_weights: Dict[str, float]) -> str:
    entity_type_lower = (entity_type or "Unknown").lower()
    truth_weight = _clamp(utility_weights.get("truth_seeking", 0.5))
    emotion_weight = _clamp(utility_weights.get("emotional_expression", 0.5))
    conformity = _clamp(utility_weights.get("social_conformity", 0.4))
    if entity_type_lower in {"university", "governmentagency", "organization", "ngo"}:
        return "institutional"
    if entity_type_lower in {"mediaoutlet", "journalist"}:
        return "monitoring"
    if truth_weight >= 0.7:
        return "analytical"
    if emotion_weight >= 0.65:
        return "expressive"
    if conformity >= 0.6:
        return "consensus"
    if stance == "opposing":
        return "skeptical"
    return "balanced"


def _goal_label(key: str) -> str:
    mapping = {
        "stability_guard": "维护秩序与稳定",
        "truth_verification": "核验信息真实性",
        "self_protection": "降低自身风险",
        "peer_alignment": "保持群体一致",
        "narrative_influence": "影响舆论走向",
        "emotional_release": "表达情绪立场",
    }
    return mapping.get(key, key)


def _strategy_label(key: str) -> str:
    mapping = {
        "observe": "继续观察",
        "verify": "优先核验",
        "stabilize": "偏向稳态表达",
        "challenge": "偏向质疑推进",
        "align": "偏向跟随群体",
        "clarify": "偏向澄清解释",
    }
    return mapping.get(key, key)


@dataclass
class AgentPrior:
    entity_type: str = "Unknown"
    profession: str = ""
    stance: str = "neutral"
    identity_focus: List[str] = field(default_factory=list)
    core_goals: List[str] = field(default_factory=list)
    interested_topics: List[str] = field(default_factory=list)
    utility_weights: Dict[str, float] = field(default_factory=lambda: {
        "self_interest": 0.5,
        "social_conformity": 0.3,
        "truth_seeking": 0.5,
        "emotional_expression": 0.5,
    })
    risk_tolerance: float = 0.5
    authority_trust: float = 0.5
    peer_trust: float = 0.5
    expressiveness: float = 0.5
    conformity: float = 0.5
    susceptibility: float = 0.5
    influence_need: float = 0.5
    decision_style: str = "balanced"
    initial_stance: str = ""  # 立场漂移追踪：原始立场（POSIM §3.3 慢信念层）


@dataclass
class AgentCognitiveState:
    round_num: int = 0
    attention_focus: str = "事件全貌"
    emotional_arousal: float = 0.3
    perceived_risk: float = 0.25
    certainty: float = 0.5
    trust_in_authority: float = 0.5
    trust_in_peers: float = 0.5
    goal_salience: Dict[str, float] = field(default_factory=dict)
    active_goals: List[str] = field(default_factory=list)
    last_strategy: str = "observe"
    last_action_type: str = ""
    reflection_hint: str = ""
    stance_drift_pressure: float = 0.0  # 立场漂移压力累积（POSIM §3.3）
    attribution_events: List[Dict[str, Any]] = field(default_factory=list)  # 认知归因事件（POSIM §6 mechanism layer）
    reflection_log: List[str] = field(default_factory=list)  # 反思日志（Generative Agents §4.3）


@dataclass
class AgentBrain:
    agent_id: int
    entity_name: str
    version: int = 1
    prior: AgentPrior = field(default_factory=AgentPrior)
    current_state: AgentCognitiveState = field(default_factory=AgentCognitiveState)
    memory_scaffold: Dict[str, Any] = field(default_factory=lambda: {
        "recent_actions": [],
        "episodic": [],
        "semantic": [],
        "reflection_log": [],
    })
    planner_scaffold: Dict[str, Any] = field(default_factory=lambda: {
        "current_plan": "",
        "plan_candidates": [],
        "policy": "reactive",
    })

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, raw: Dict[str, Any]) -> "AgentBrain":
        memory_scaffold = _safe_dict(raw.get("memory_scaffold"))
        planner_scaffold = _safe_dict(raw.get("planner_scaffold"))
        memory_scaffold.setdefault("recent_actions", [])
        memory_scaffold.setdefault("episodic", [])
        memory_scaffold.setdefault("semantic", [])
        memory_scaffold.setdefault("reflection_log", [])
        planner_scaffold.setdefault("current_plan", "")
        planner_scaffold.setdefault("plan_candidates", [])
        planner_scaffold.setdefault("policy", "reactive")
        return cls(
            agent_id=int(raw.get("agent_id", 0)),
            entity_name=raw.get("entity_name", ""),
            version=int(raw.get("version", 1)),
            prior=_build_dataclass(AgentPrior, raw.get("prior", {})),
            current_state=_build_dataclass(AgentCognitiveState, raw.get("current_state", {})),
            memory_scaffold=memory_scaffold,
            planner_scaffold=planner_scaffold,
        )


def _compute_goal_salience(prior: AgentPrior, state: AgentCognitiveState, ws_data: Optional[Dict[str, Any]] = None) -> Dict[str, float]:
    ws_data = ws_data or {}
    truth_weight = _clamp(prior.utility_weights.get("truth_seeking", 0.5))
    self_interest = _clamp(prior.utility_weights.get("self_interest", 0.5))
    emotional_expression = _clamp(prior.utility_weights.get("emotional_expression", 0.5))
    conformity = _clamp(prior.utility_weights.get("social_conformity", 0.3))
    attention = _clamp(ws_data.get("attention_level", 0.1), default=0.1)
    trust = _clamp(ws_data.get("trust_level", state.trust_in_authority), default=state.trust_in_authority)
    return {
        "stability_guard": _clamp((1.0 - state.perceived_risk) * 0.15 + state.trust_in_authority * 0.35 + (0.2 if prior.stance == "supportive" else 0.0) + (0.15 if prior.decision_style == "institutional" else 0.0), default=0.4),
        "truth_verification": _clamp(truth_weight * 0.45 + (1.0 - state.certainty) * 0.35 + (0.15 if prior.decision_style in {"analytical", "monitoring"} else 0.0), default=0.4),
        "self_protection": _clamp(self_interest * 0.3 + state.perceived_risk * 0.45 + prior.susceptibility * 0.15, default=0.4),
        "peer_alignment": _clamp(conformity * 0.4 + state.trust_in_peers * 0.3 + attention * 0.1 + (0.15 if prior.decision_style == "consensus" else 0.0), default=0.4),
        "narrative_influence": _clamp(prior.influence_need * 0.45 + attention * 0.25 + trust * 0.1 + (0.15 if prior.stance in {"supportive", "opposing"} else 0.0), default=0.4),
        "emotional_release": _clamp(emotional_expression * 0.35 + state.emotional_arousal * 0.4 + (0.1 if prior.stance == "opposing" else 0.0), default=0.4),
    }


def _select_strategy(prior: AgentPrior, state: AgentCognitiveState) -> str:
    if state.perceived_risk >= 0.7 and state.certainty <= 0.45:
        return "verify"
    if prior.decision_style == "institutional" and state.trust_in_authority >= 0.55:
        return "clarify"
    if prior.stance == "supportive" and state.trust_in_authority >= 0.6:
        return "stabilize"
    if prior.stance == "opposing" and state.emotional_arousal >= 0.55:
        return "challenge"
    if prior.conformity >= 0.6 and state.trust_in_peers >= 0.55:
        return "align"
    return "observe"


def _infer_attention_focus(prior: AgentPrior, ws_data: Dict[str, Any]) -> str:
    signals = {
        "事件热度变化": _clamp(ws_data.get("attention_level", 0.1), default=0.1),
        "风险与不确定性": _clamp(ws_data.get("risk_level", 0.1), default=0.1),
        "权威信息可信度": 1.0 - _clamp(ws_data.get("trust_level", 0.6), default=0.6),
        "群体立场分化": _clamp(ws_data.get("polarization_level", 0.1), default=0.1),
    }
    if prior.decision_style == "institutional":
        signals["秩序稳定与声誉"] = _clamp(1.0 - ws_data.get("stability_level", 0.8), default=0.2)
    if prior.decision_style == "monitoring":
        signals["新增信息线索"] = _clamp(ws_data.get("attention_level", 0.1), default=0.1) * 0.9
    return max(signals.items(), key=lambda item: item[1])[0]


def _build_reflection_hint(prior: AgentPrior, state: AgentCognitiveState, ws_data: Dict[str, Any]) -> str:
    recent_events = _safe_list(ws_data.get("recent_events"))
    event_desc = ""
    if recent_events:
        last_event = recent_events[-1]
        if isinstance(last_event, dict):
            event_desc = str(last_event.get("description", "")).strip()
    if state.last_strategy == "verify":
        base = "当前更适合先核验新增信息，再决定是否表态。"
    elif state.last_strategy == "clarify":
        base = "当前更适合做解释、澄清或降温型表达。"
    elif state.last_strategy == "challenge":
        base = "当前更容易采取质疑、追问或推进议题的表达。"
    elif state.last_strategy == "align":
        base = "当前更容易参考同伴反应后再行动。"
    elif state.last_strategy == "stabilize":
        base = "当前更偏向稳态表达，避免局势继续升级。"
    else:
        base = "当前更适合保持观察，等待更明确的信号。"
    if event_desc:
        return f"最近显著变化是：{event_desc} {base}"
    return base


# ────────── Feature ②: 立场漂移（POSIM §3.3 慢信念层 B_psy / B_id） ──────────
# 只允许相邻档位间漂移，慢信念层不应轻易改变
_STANCE_ADJACENCY = {
    "supportive": ["neutral"],
    "neutral": ["supportive", "opposing"],
    "opposing": ["neutral"],
}
_STANCE_DRIFT_THRESHOLD = 0.6  # 累积压力超过此值才触发漂移


def _compute_drift_pressure(brain: "AgentBrain", ws_data: Dict[str, Any]) -> float:
    """
    计算立场漂移压力。正值 → 偏向 opposing，负值 → 偏向 supportive。

    论文依据:
      - POSIM §3.3: 快信念层(B_evt/B_emo)累积影响慢信念层(B_psy/B_id)
      - Rumor Spreading: belief state 受曝光和社会影响累积变化
      - AgentSociety: Cognition 层包含信念更新机制
    """
    state = brain.current_state
    prior = brain.prior
    panic = _clamp(ws_data.get("panic_level", 0.1), default=0.1)
    trust = _clamp(ws_data.get("trust_level", 0.6), default=0.6)
    polarization = _clamp(ws_data.get("polarization_level", 0.1), default=0.1)

    # 高情绪 + 低信任 → 向 opposing 方向施压
    pressure = 0.0
    pressure += (state.emotional_arousal - 0.5) * 0.3
    pressure += (0.5 - state.trust_in_authority) * 0.35
    pressure += (state.perceived_risk - 0.4) * 0.2
    pressure += polarization * 0.15
    # 高易感性放大压力
    pressure *= (0.7 + prior.susceptibility * 0.6)
    return pressure


def _apply_stance_drift(brain: "AgentBrain", ws_data: Dict[str, Any], round_num: int) -> Optional[str]:
    """
    应用立场漂移逻辑，返回漂移事件描述（无漂移返回 None）。

    论文依据:
      - POSIM §3.3: B_psy/B_id 是慢信念层，在累积压力下漂移
      - 综述 §8.3: agent populations should replicate human social dynamics
    """
    state = brain.current_state
    prior = brain.prior
    pressure = _compute_drift_pressure(brain, ws_data)
    # 累积压力（带衰减）
    state.stance_drift_pressure = state.stance_drift_pressure * 0.85 + pressure * 0.15
    current_stance = prior.stance
    adjacent = _STANCE_ADJACENCY.get(current_stance, [])
    if not adjacent:
        return None

    drift_target = None
    if state.stance_drift_pressure >= _STANCE_DRIFT_THRESHOLD and "opposing" in adjacent:
        drift_target = "opposing"
    elif state.stance_drift_pressure >= _STANCE_DRIFT_THRESHOLD and "neutral" in adjacent and current_stance == "supportive":
        drift_target = "neutral"
    elif state.stance_drift_pressure <= -_STANCE_DRIFT_THRESHOLD and "supportive" in adjacent:
        drift_target = "supportive"
    elif state.stance_drift_pressure <= -_STANCE_DRIFT_THRESHOLD and "neutral" in adjacent and current_stance == "opposing":
        drift_target = "neutral"

    if drift_target and drift_target != current_stance:
        old_stance = current_stance
        prior.stance = drift_target
        state.stance_drift_pressure *= 0.3  # 漂移后压力重置
        event_desc = f"第{round_num}轮: {brain.entity_name} 立场从 {old_stance} 漂移至 {drift_target}"
        state.attribution_events.append({
            "round": round_num,
            "dimension": "stance_drift",
            "old": old_stance,
            "new": drift_target,
            "delta": round(state.stance_drift_pressure, 3),
            "primary_driver": f"累积漂移压力={round(state.stance_drift_pressure, 3)}",
        })
        return event_desc
    return None


# ────────── Feature ④: 反思机制（Generative Agents §4.3） ──────────
_REFLECTION_INTERVAL = 3  # 每 N 轮触发一次反思


def _generate_reflection(brain: "AgentBrain", round_num: int) -> Optional[str]:
    """
    基于最近行动和认知变化生成反思摘要（规则驱动，非 LLM）。

    论文依据:
      - Generative Agents §4.3: Reflection 是 believable agent 的三大支柱之一
        (Perception → Memory → Reflection → Planning → Action)
      - POSIM §6: 理性认知干预本质上是让 agent 进行自我反思
      - AgentSociety: Cognition 层包含周期性自我评估
    """
    state = brain.current_state
    prior = brain.prior

    recent_actions = _safe_list(brain.memory_scaffold.get("recent_actions"))
    if not recent_actions:
        return None

    # 分析最近几轮的行动模式
    recent_window = recent_actions[-_REFLECTION_INTERVAL:]
    action_types = [a.get("action_type", "") for a in recent_window]
    action_summaries = [a.get("summary", "") for a in recent_window if a.get("summary")]

    parts = []

    # 检测行为一致性
    create_count = sum(1 for t in action_types if t in {"CREATE_POST", "CREATE_COMMENT", "QUOTE_POST"})
    passive_count = sum(1 for t in action_types if t in {"DO_NOTHING", "LIKE_POST", "LIKE_COMMENT"})
    if create_count >= 2:
        parts.append(f"我连续{create_count}轮在主动发表内容")
    elif passive_count >= 2:
        parts.append(f"我连续{passive_count}轮选择被动观望")

    # 检测认知变化趋势
    attributions = [a for a in state.attribution_events if a.get("round", 0) >= round_num - _REFLECTION_INTERVAL]
    if attributions:
        dims_changed = list({a["dimension"] for a in attributions if "dimension" in a})
        dim_labels = {
            "emotional_arousal": "情绪", "perceived_risk": "风险感知",
            "trust_in_authority": "权威信任", "trust_in_peers": "同侪信任",
            "certainty": "判断确定性", "stance_drift": "立场",
        }
        changed_labels = [dim_labels.get(d, d) for d in dims_changed[:3]]
        if changed_labels:
            parts.append(f"近期我的{'/'.join(changed_labels)}发生了变化")

    # 策略-目标一致性检查
    strategy = state.last_strategy
    goals = state.active_goals[:2]
    if strategy == "challenge" and any("稳定" in g for g in goals):
        parts.append("我的质疑行为与维稳目标之间存在张力，可能需要调整")
    elif strategy == "stabilize" and any("质疑" in g or "推进" in g for g in goals):
        parts.append("我的稳态表达与推进目标之间存在张力")

    # 信任-行为错位检查
    if state.trust_in_authority <= 0.35 and strategy in {"stabilize", "clarify"}:
        parts.append("我对权威的信任较低，但仍在做维稳表达——需要重新审视")
    elif state.trust_in_authority >= 0.65 and strategy == "challenge":
        parts.append("我对权威信任度较高，但仍在质疑——可能需要重新评估")

    if not parts:
        return None

    reflection = "；".join(parts) + "。"
    return reflection


def _summarize_action(action_type: str, action_args: Dict[str, Any]) -> str:
    if action_type == "CREATE_POST":
        content = str((action_args or {}).get("content", "")).strip()
        return f"发布帖子：{content[:40]}" if content else "发布了一条帖子"
    if action_type == "CREATE_COMMENT":
        content = str((action_args or {}).get("content", "")).strip()
        return f"发表评论：{content[:40]}" if content else "发表了评论"
    if action_type == "REPOST":
        return "转发了他人内容"
    if action_type == "QUOTE_POST":
        return "引用并评论了帖子"
    if action_type == "LIKE_POST":
        return "点赞了帖子"
    if action_type == "DISLIKE_POST":
        return "踩了帖子"
    if action_type == "LIKE_COMMENT":
        return "点赞了评论"
    if action_type == "DISLIKE_COMMENT":
        return "踩了评论"
    if action_type == "FOLLOW":
        return "关注了其他用户"
    if action_type == "MUTE":
        return "屏蔽了其他用户"
    if action_type == "SEARCH_POSTS":
        return "搜索了相关帖子"
    if action_type == "SEARCH_USER":
        return "搜索了相关用户"
    if action_type == "DO_NOTHING":
        return "选择暂不行动"
    return action_type or "执行了一次动作"


def create_agent_brain_profile(
    agent_id: int,
    entity_name: str,
    entity_type: str,
    entity_summary: str,
    simulation_requirement: str,
    activity_config: Dict[str, Any],
    profile: Any = None,
) -> Dict[str, Any]:
    utility_weights_raw = _safe_dict(_extract_profile_value(profile, "utility_weights", {}))
    utility_weights = {
        "self_interest": _clamp(utility_weights_raw.get("self_interest", 0.5)),
        "social_conformity": _clamp(utility_weights_raw.get("social_conformity", 0.3)),
        "truth_seeking": _clamp(utility_weights_raw.get("truth_seeking", 0.5)),
        "emotional_expression": _clamp(utility_weights_raw.get("emotional_expression", 0.5)),
    }
    stance = str(activity_config.get("stance", "neutral") or "neutral")
    activity_level = _clamp(activity_config.get("activity_level", 0.5))
    influence_weight = _clamp(activity_config.get("influence_weight", 1.0), low=0.0, high=3.0, default=1.0)
    susceptibility = _clamp(_extract_profile_value(profile, "susceptibility", activity_level), default=activity_level)
    profession = str(_extract_profile_value(profile, "profession", entity_type) or entity_type)
    authority_bias = 0.52
    if stance == "supportive":
        authority_bias += 0.15
    elif stance == "opposing":
        authority_bias -= 0.15
    if (entity_type or "").lower() in {"university", "governmentagency", "organization", "ngo"}:
        authority_bias += 0.1
    authority_trust = _clamp(authority_bias, default=0.5)
    peer_trust = _clamp(0.4 + activity_level * 0.2 + utility_weights["social_conformity"] * 0.2 - authority_trust * 0.1, default=0.5)
    risk_tolerance = _clamp(0.45 + activity_level * 0.15 + influence_weight * 0.08 - susceptibility * 0.18, default=0.5)
    prior = AgentPrior(
        entity_type=entity_type or "Unknown",
        profession=profession,
        stance=stance,
        identity_focus=_default_identity_focus(entity_type, profession),
        core_goals=_safe_list(_extract_profile_value(profile, "internal_goals", None)) or _default_goals(entity_type, stance),
        interested_topics=_safe_list(_extract_profile_value(profile, "interested_topics", [])),
        utility_weights=utility_weights,
        risk_tolerance=risk_tolerance,
        authority_trust=authority_trust,
        peer_trust=peer_trust,
        expressiveness=utility_weights["emotional_expression"],
        conformity=utility_weights["social_conformity"],
        susceptibility=susceptibility,
        influence_need=_clamp(0.25 + influence_weight / 3.0 * 0.55, default=0.4),
        decision_style=_decision_style(entity_type, stance, utility_weights),
        initial_stance=stance,
    )
    state = AgentCognitiveState(
        round_num=0,
        attention_focus="事件全貌",
        emotional_arousal=_clamp(0.2 + abs(_clamp(_extract_profile_value(profile, "emotional_tendency", 0.0), low=-1.0, high=1.0, default=0.0)) * 0.35 + susceptibility * 0.2, default=0.3),
        perceived_risk=_clamp(0.18 + (1.0 - risk_tolerance) * 0.4, default=0.3),
        certainty=_clamp(0.42 + utility_weights["truth_seeking"] * 0.18 - susceptibility * 0.08, default=0.5),
        trust_in_authority=authority_trust,
        trust_in_peers=peer_trust,
    )
    state.goal_salience = _compute_goal_salience(prior, state)
    ranked_goals = sorted(state.goal_salience.items(), key=lambda item: item[1], reverse=True)
    state.active_goals = [_goal_label(name) for name, _ in ranked_goals[:2]]
    state.last_strategy = _select_strategy(prior, state)
    state.reflection_hint = _build_reflection_hint(prior, state, {})
    brain = AgentBrain(
        agent_id=agent_id,
        entity_name=entity_name,
        prior=prior,
        current_state=state,
        memory_scaffold={
            "recent_actions": [],
            "episodic": [],
            "semantic": [entity_summary[:200]] if entity_summary else [],
            "reflection_log": [],
        },
        planner_scaffold={
            "current_plan": "",
            "plan_candidates": [],
            "policy": "reactive",
            "simulation_requirement": (simulation_requirement or "")[:300],
        },
    )
    return brain.to_dict()


class AgentBrainRuntime:
    def __init__(self, brains: Optional[Dict[int, AgentBrain]] = None, storage_path: Optional[str] = None):
        self._brains = brains or {}
        self.storage_path = storage_path

    def __len__(self) -> int:
        return len(self._brains)

    @classmethod
    def from_simulation_config(cls, config: Dict[str, Any], storage_path: Optional[str] = None) -> "AgentBrainRuntime":
        brains: Dict[int, AgentBrain] = {}
        for agent_config in config.get("agent_configs", []):
            agent_id = agent_config.get("agent_id")
            if agent_id is None:
                continue
            raw_brain = agent_config.get("brain_profile")
            if not isinstance(raw_brain, dict) or not raw_brain:
                raw_brain = create_agent_brain_profile(
                    agent_id=int(agent_id),
                    entity_name=agent_config.get("entity_name", f"Agent_{agent_id}"),
                    entity_type=agent_config.get("entity_type", "Unknown"),
                    entity_summary="",
                    simulation_requirement=config.get("simulation_requirement", ""),
                    activity_config=agent_config,
                    profile=None,
                )
            brains[int(agent_id)] = AgentBrain.from_dict(raw_brain)
        return cls(brains=brains, storage_path=storage_path)

    @classmethod
    def load_or_create(cls, config: Dict[str, Any], simulation_dir: str) -> "AgentBrainRuntime":
        storage_path = os.path.join(simulation_dir, "agent_brain_state.json")
        if os.path.exists(storage_path):
            try:
                with open(storage_path, "r", encoding="utf-8") as f:
                    raw = json.load(f)
                brains_raw = _safe_dict(raw.get("brains"))
                brains = {int(agent_id): AgentBrain.from_dict(brain_raw) for agent_id, brain_raw in brains_raw.items()}
                if brains:
                    return cls(brains=brains, storage_path=storage_path)
            except (OSError, json.JSONDecodeError, ValueError, TypeError):
                pass
        runtime = cls.from_simulation_config(config, storage_path=storage_path)
        runtime.save()
        return runtime

    def save(self) -> None:
        if not self.storage_path:
            return
        payload = {
            "updated_at": datetime.now().isoformat(),
            "brains": {str(agent_id): brain.to_dict() for agent_id, brain in self._brains.items()},
        }
        with open(self.storage_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)

    def apply_world_state(self, round_num: int, ws_data: Dict[str, Any]) -> None:
        attention = _clamp(ws_data.get("attention_level", 0.1), default=0.1)
        panic = _clamp(ws_data.get("panic_level", 0.1), default=0.1)
        trust = _clamp(ws_data.get("trust_level", 0.6), default=0.6)
        polarization = _clamp(ws_data.get("polarization_level", 0.1), default=0.1)
        risk = _clamp(ws_data.get("risk_level", 0.1), default=0.1)
        stability = _clamp(ws_data.get("stability_level", 0.8), default=0.8)
        for brain in self._brains.values():
            prior = brain.prior
            state = brain.current_state
            state.round_num = round_num

            # ── 保存旧值用于认知归因（Feature ③） ──
            old_values = {
                "emotional_arousal": state.emotional_arousal,
                "perceived_risk": state.perceived_risk,
                "trust_in_authority": state.trust_in_authority,
                "trust_in_peers": state.trust_in_peers,
                "certainty": state.certainty,
            }

            # ── 认知自然衰减：无强刺激时向个体基线回归 ──
            # 信号强度：世界状态偏离平静基线的程度
            _signal_strength = (abs(panic - 0.1) + abs(trust - 0.6) + abs(attention - 0.1)) / 3.0
            _decay = max(0.0, 0.08 * (1.0 - min(_signal_strength / 0.3, 1.0)))
            if _decay > 0.005:
                # 情绪向基线回落（基线 = 初始值附近）
                _ea_base = _clamp(0.2 + prior.susceptibility * 0.15, default=0.3)
                state.emotional_arousal += _decay * (_ea_base - state.emotional_arousal)
                _pr_base = _clamp(0.2 + (1.0 - prior.risk_tolerance) * 0.2, default=0.3)
                state.perceived_risk += _decay * (_pr_base - state.perceived_risk)

            # ── 认知状态更新（原有逻辑） ──
            state.emotional_arousal = _clamp(state.emotional_arousal * 0.55 + panic * (0.25 + prior.susceptibility * 0.35) + attention * 0.12 + polarization * 0.08, default=state.emotional_arousal)
            state.perceived_risk = _clamp(risk * 0.55 + panic * 0.2 + (1.0 - trust) * 0.15 + (1.0 - prior.risk_tolerance) * 0.1, default=state.perceived_risk)
            state.trust_in_authority = _clamp(state.trust_in_authority * 0.45 + trust * 0.35 + prior.authority_trust * 0.2, default=state.trust_in_authority)
            state.trust_in_peers = _clamp(state.trust_in_peers * 0.45 + prior.peer_trust * 0.25 + (1.0 - polarization) * 0.15 + attention * 0.15, default=state.trust_in_peers)
            state.certainty = _clamp(state.certainty * 0.4 + (1.0 - polarization) * 0.22 + stability * 0.18 + prior.utility_weights.get("truth_seeking", 0.5) * 0.12 - panic * 0.12, default=state.certainty)

            # ── Feature ③: 认知归因（POSIM §6 mechanism layer） ──
            _ATTRIBUTION_THRESHOLD = 0.08
            _DRIVER_MAP = {
                "emotional_arousal": [("panic_level", panic), ("attention_level", attention), ("polarization_level", polarization)],
                "perceived_risk": [("risk_level", risk), ("panic_level", panic), ("trust_level", trust)],
                "trust_in_authority": [("trust_level", trust), ("panic_level", panic)],
                "trust_in_peers": [("polarization_level", polarization), ("attention_level", attention)],
                "certainty": [("polarization_level", polarization), ("stability_level", stability), ("panic_level", panic)],
            }
            round_attributions: List[Dict[str, Any]] = []
            for dim, old_val in old_values.items():
                new_val = getattr(state, dim)
                delta = new_val - old_val
                if abs(delta) >= _ATTRIBUTION_THRESHOLD:
                    drivers = _DRIVER_MAP.get(dim, [])
                    primary = max(drivers, key=lambda d: abs(d[1] - 0.5)) if drivers else ("unknown", 0)
                    round_attributions.append({
                        "round": round_num,
                        "dimension": dim,
                        "old": round(old_val, 3),
                        "new": round(new_val, 3),
                        "delta": round(delta, 3),
                        "primary_driver": f"{primary[0]}={round(primary[1], 3)}",
                    })
            if round_attributions:
                state.attribution_events.extend(round_attributions)
                if len(state.attribution_events) > 30:
                    state.attribution_events = state.attribution_events[-30:]

            # ── Feature ②: 立场漂移（POSIM §3.3 慢信念层） ──
            _apply_stance_drift(brain, ws_data, round_num)

            state.attention_focus = _infer_attention_focus(prior, ws_data)
            state.goal_salience = _compute_goal_salience(prior, state, ws_data)
            ranked_goals = sorted(state.goal_salience.items(), key=lambda item: item[1], reverse=True)
            state.active_goals = [_goal_label(name) for name, _ in ranked_goals[:2]]
            state.last_strategy = _select_strategy(prior, state)
            state.reflection_hint = _build_reflection_hint(prior, state, ws_data)
        self.save()

    def record_actions(self, round_num: int, actual_actions: List[Dict[str, Any]]) -> None:
        changed = False
        for action in actual_actions:
            agent_id = action.get("agent_id")
            if agent_id is None:
                continue
            brain = self._brains.get(int(agent_id))
            if not brain:
                continue
            changed = True
            summary = _summarize_action(action.get("action_type", ""), _safe_dict(action.get("action_args")))
            recent_actions = brain.memory_scaffold.setdefault("recent_actions", [])
            recent_actions.append({
                "round_num": round_num,
                "action_type": action.get("action_type", ""),
                "summary": summary,
            })
            if len(recent_actions) > 8:
                del recent_actions[:-8]
            brain.current_state.last_action_type = action.get("action_type", "")
            if summary:
                brain.current_state.reflection_hint = f"你上一轮刚刚{summary}，下一轮行动应继续服务于当前优先目标。"
        if changed:
            self.save()

    # ────────── Feature ④: 反思机制（Generative Agents §4.3） ──────────

    def trigger_reflection(self, round_num: int) -> Dict[int, str]:
        """
        每 _REFLECTION_INTERVAL 轮为所有 Agent 触发反思。
        返回 {agent_id: reflection_text} 映射（只含有反思内容的 Agent）。

        论文依据:
          - Generative Agents §4.3: Reflection — 周期性高层抽象
          - POSIM §6: Rational Cognition 让 agent 识别自身状态
        """
        if round_num % _REFLECTION_INTERVAL != 0 or round_num == 0:
            return {}
        results: Dict[int, str] = {}
        for agent_id, brain in self._brains.items():
            reflection = _generate_reflection(brain, round_num)
            if reflection:
                results[agent_id] = reflection
                brain.current_state.reflection_log.append(reflection)
                if len(brain.current_state.reflection_log) > 10:
                    brain.current_state.reflection_log = brain.current_state.reflection_log[-10:]
                brain.memory_scaffold.setdefault("reflection_log", []).append({
                    "round_num": round_num,
                    "reflection": reflection,
                })
                if len(brain.memory_scaffold["reflection_log"]) > 10:
                    brain.memory_scaffold["reflection_log"] = brain.memory_scaffold["reflection_log"][-10:]
        if results:
            self.save()
        return results

    # ────────── 认知轨迹持久化 ──────────

    def write_cognition_snapshot(self, round_num: int) -> None:
        """每轮结束后追加一行 agent_cognition_history.jsonl，供 InsightService / 报告 / 证据检索使用"""
        if not self.storage_path:
            return
        history_path = os.path.join(os.path.dirname(self.storage_path), "agent_cognition_history.jsonl")
        snapshots = []
        for agent_id, brain in self._brains.items():
            s = brain.current_state
            p = brain.prior
            recent = _safe_list(brain.memory_scaffold.get("recent_actions"))
            last_action = recent[-1] if recent else {}
            snapshots.append({
                "agent_id": agent_id,
                "entity_name": brain.entity_name,
                "entity_type": p.entity_type,
                "stance": p.stance,
                "decision_style": p.decision_style,
                "emotional_arousal": round(s.emotional_arousal, 3),
                "perceived_risk": round(s.perceived_risk, 3),
                "certainty": round(s.certainty, 3),
                "trust_in_authority": round(s.trust_in_authority, 3),
                "trust_in_peers": round(s.trust_in_peers, 3),
                "attention_focus": s.attention_focus,
                "active_goals": s.active_goals[:2],
                "strategy": s.last_strategy,
                "last_action_type": last_action.get("action_type", ""),
                "last_action_summary": last_action.get("summary", ""),
                "initial_stance": p.initial_stance or p.stance,
                "stance_drift_pressure": round(s.stance_drift_pressure, 3),
                "latest_reflection": s.reflection_log[-1] if s.reflection_log else "",
                "attribution_count": len(s.attribution_events),
            })
        record = {
            "round_num": round_num,
            "timestamp": datetime.now().isoformat(),
            "agents": snapshots,
        }
        try:
            with open(history_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(record, ensure_ascii=False) + "\n")
        except OSError:
            pass

    def generate_cognition_summary(self) -> Dict[str, Any]:
        """模拟结束后生成全局认知摘要 JSON，写入 agent_cognition_summary.json"""
        agent_summaries = []
        for agent_id, brain in self._brains.items():
            s = brain.current_state
            p = brain.prior
            recent = _safe_list(brain.memory_scaffold.get("recent_actions"))
            agent_summaries.append({
                "agent_id": agent_id,
                "entity_name": brain.entity_name,
                "entity_type": p.entity_type,
                "stance": p.stance,
                "decision_style": p.decision_style,
                "profession": p.profession,
                "core_goals": p.core_goals[:3],
                "initial_stance": p.initial_stance or p.stance,
                "final_state": {
                    "round_num": s.round_num,
                    "emotional_arousal": round(s.emotional_arousal, 3),
                    "perceived_risk": round(s.perceived_risk, 3),
                    "certainty": round(s.certainty, 3),
                    "trust_in_authority": round(s.trust_in_authority, 3),
                    "trust_in_peers": round(s.trust_in_peers, 3),
                    "attention_focus": s.attention_focus,
                    "active_goals": s.active_goals[:2],
                    "strategy": s.last_strategy,
                    "stance_drift_pressure": round(s.stance_drift_pressure, 3),
                },
                "stance_drifted": p.stance != (p.initial_stance or p.stance),
                "attribution_events": s.attribution_events[-10:],
                "reflections": s.reflection_log[-5:],
                "recent_actions": [
                    {"round": a.get("round_num", 0), "summary": a.get("summary", "")}
                    for a in recent[-5:]
                ],
                "total_actions": len(recent),
            })
        summary = {
            "generated_at": datetime.now().isoformat(),
            "total_agents": len(self._brains),
            "agents": agent_summaries,
        }
        if self.storage_path:
            summary_path = os.path.join(os.path.dirname(self.storage_path), "agent_cognition_summary.json")
            try:
                with open(summary_path, "w", encoding="utf-8") as f:
                    json.dump(summary, f, ensure_ascii=False, indent=2)
            except OSError:
                pass
        return summary

    # ────────── 采访上下文增强 ──────────

    def render_interview_context(self, agent_id: int) -> str:
        """为采访注入认知上下文前缀，使回答一致于模拟中的内部状态"""
        brain = self._brains.get(int(agent_id))
        if not brain:
            return ""
        p = brain.prior
        s = brain.current_state
        parts = [
            f"[系统提示 - 你的当前内部状态，请在回答采访时保持一致]",
            f"你是 {brain.entity_name}（{p.profession or p.entity_type}），立场: {p.stance}。",
            f"你当前关注: {s.attention_focus}，优先目标: {'、'.join(s.active_goals[:2]) if s.active_goals else '观察'}。",
            f"风险感知: {_level_text(s.perceived_risk)}，情绪: {_level_text(s.emotional_arousal)}，"
            f"对权威信任: {_level_text(s.trust_in_authority)}。",
            f"策略倾向: {_strategy_label(s.last_strategy)}。",
        ]
        recent = _safe_list(brain.memory_scaffold.get("recent_actions"))
        if recent:
            snippets = [a.get("summary", "") for a in recent[-3:] if a.get("summary")]
            if snippets:
                parts.append(f"你最近的行动: {'；'.join(snippets)}。")
        if s.reflection_hint:
            parts.append(f"内心想法: {s.reflection_hint}")
        return "\n".join(parts)

    # ────────── 个性化感知渲染（SocioVerse §2.1 Personalized Context） ──────────

    def render_personalized_perception(self, agent_id: int, ws_data: Dict[str, Any]) -> str:
        """
        为指定 Agent 生成个性化世界状态感知描述。
        同一世界状态对不同 Agent 呈现不同侧重，基于其 prior 特征。

        论文依据:
          - SocioVerse §2.1: Personalized Context — 同一环境对不同 agent 的渲染不同
          - POSIM §3.2: BDI Belief Filter — agents perceive through belief lens
          - OASIS / MOSAIC: 环境感知必须个性化
        """
        brain = self._brains.get(int(agent_id))
        if not brain or not ws_data:
            return ""
        prior = brain.prior
        state = brain.current_state

        panic = _clamp(ws_data.get("panic_level", 0.1), default=0.1)
        trust = _clamp(ws_data.get("trust_level", 0.6), default=0.6)
        risk = _clamp(ws_data.get("risk_level", 0.1), default=0.1)
        polarization = _clamp(ws_data.get("polarization_level", 0.1), default=0.1)
        attention = _clamp(ws_data.get("attention_level", 0.1), default=0.1)
        stability = _clamp(ws_data.get("stability_level", 0.8), default=0.8)

        parts: List[str] = []

        # 高易感性 Agent: 放大不确定性和风险信号
        if prior.susceptibility >= 0.6:
            if panic >= 0.4:
                parts.append("当前讨论中未经验证的说法较多，不确定性较高。")
            if risk >= 0.5:
                parts.append("部分关键细节尚待核实，潜在影响仍不明朗。")

        # 高求真倾向 Agent: 强调证据缺口
        truth_weight = _clamp(prior.utility_weights.get("truth_seeking", 0.5))
        if truth_weight >= 0.65:
            if trust <= 0.45:
                parts.append("现有信息来源的可交叉验证程度不足。")
            if polarization >= 0.4:
                parts.append("对同一事实的解读存在较大分歧，证据链尚不完整。")

        # 机构/媒体角色: 强调秩序与程序
        etype = (prior.entity_type or "").lower()
        if etype in {"university", "governmentagency", "organization", "ngo"}:
            if stability <= 0.5:
                parts.append("讨论的议题结构仍在变化，组织层面的稳定预期尚未形成。")
            if attention >= 0.5:
                parts.append("该议题目前处于较高关注度，后续回应可能影响各方评价。")
        elif etype in {"mediaoutlet", "journalist"}:
            if attention >= 0.4:
                parts.append("该话题的信息流入速度较快，存在多个值得追踪的线索。")

        # 高从众性 Agent: 强调群体信号
        if prior.conformity >= 0.6:
            if polarization >= 0.4:
                parts.append("群体中正在形成较为清晰的多数意见。")

        # 高风险厌恶 Agent: 强调风险
        if prior.risk_tolerance <= 0.35:
            if risk >= 0.4:
                parts.append("当前形势中存在可能扩大的风险因素。")

        # 如果无个性化信号，返回空
        if not parts:
            return ""
        return "[你注意到的环境信号]\n" + "\n".join(parts)

    # ────────── Prompt 渲染 ──────────

    def render_prompt(self, agent_id: Optional[int]) -> str:
        if agent_id is None:
            return ""
        brain = self._brains.get(int(agent_id))
        if not brain:
            return ""
        prior = brain.prior
        state = brain.current_state
        lines = [
            "当前你的内部认知框架：",
            f"- 身份角色: {brain.entity_name}（{prior.profession or prior.entity_type}）",
            f"- 稳定立场: {prior.stance}",
            f"- 决策风格: {prior.decision_style}",
        ]
        if prior.identity_focus:
            lines.append(f"- 身份关注: {'、'.join(prior.identity_focus[:3])}")
        if prior.core_goals:
            lines.append(f"- 长期目标: {'、'.join(prior.core_goals[:3])}")
        lines.extend([
            "当前你的内部状态：",
            f"- 注意焦点: {state.attention_focus}",
            f"- 当前优先目标: {'、'.join(state.active_goals[:2]) if state.active_goals else '继续观察'}",
            f"- 风险感知: {_level_text(state.perceived_risk)}",
            f"- 情绪唤醒: {_level_text(state.emotional_arousal)}",
            f"- 对权威信息信任: {_level_text(state.trust_in_authority)}",
            f"- 对同侪意见依赖: {_level_text(state.trust_in_peers)}",
            f"- 判断确定性: {_level_text(state.certainty)}",
            f"- 当前策略倾向: {_strategy_label(state.last_strategy)}",
        ])
        recent_actions = _safe_list(brain.memory_scaffold.get("recent_actions"))
        if recent_actions:
            snippets = [item.get("summary", "") for item in recent_actions[-2:] if isinstance(item, dict) and item.get("summary")]
            if snippets:
                lines.append(f"- 最近动作: {'；'.join(snippets)}")
        if state.reflection_hint:
            lines.append(f"- 当前自我提醒: {state.reflection_hint}")
        if state.reflection_log:
            lines.append(f"- 近期自我反思: {state.reflection_log[-1]}")
        lines.append("请保持与你的稳定倾向、近期经历和当前状态一致。")
        return "\n".join(lines)
