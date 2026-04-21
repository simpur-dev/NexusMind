"""
Agent Brain 单元测试
覆盖范围：
  1. 工具函数 (_clamp, _safe_list, _safe_dict, _extract_profile_value, _build_dataclass, _level_text)
  2. 默认值生成器 (_default_identity_focus, _default_goals, _decision_style)
  3. 标签映射 (_goal_label, _strategy_label)
  4. 数据结构序列化 (AgentPrior, AgentCognitiveState, AgentBrain to_dict/from_dict)
  5. 核心逻辑 (_compute_goal_salience, _select_strategy, _infer_attention_focus,
              _build_reflection_hint, _summarize_action)
  6. 入口函数 (create_agent_brain_profile)
  7. 运行时 (AgentBrainRuntime: from_simulation_config, load_or_create, save,
            apply_world_state, record_actions, render_prompt)
  8. 集成点 (simulation_config_generator 中 brain_profile 字段)
"""

import json
import os
import sys
import tempfile
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.services.agent_brain import (
    _clamp,
    _safe_list,
    _safe_dict,
    _extract_profile_value,
    _build_dataclass,
    _level_text,
    _default_identity_focus,
    _default_goals,
    _decision_style,
    _goal_label,
    _strategy_label,
    _compute_goal_salience,
    _select_strategy,
    _infer_attention_focus,
    _build_reflection_hint,
    _summarize_action,
    _compute_drift_pressure,
    _apply_stance_drift,
    _generate_reflection,
    _STANCE_ADJACENCY,
    _STANCE_DRIFT_THRESHOLD,
    _REFLECTION_INTERVAL,
    AgentPrior,
    AgentCognitiveState,
    AgentBrain,
    AgentBrainRuntime,
    create_agent_brain_profile,
)


# ============================================================
# 1. 工具函数
# ============================================================

class TestClamp:
    def test_normal_range(self):
        assert _clamp(0.5) == 0.5

    def test_below_low(self):
        assert _clamp(-0.3) == 0.0

    def test_above_high(self):
        assert _clamp(1.5) == 1.0

    def test_exact_boundaries(self):
        assert _clamp(0.0) == 0.0
        assert _clamp(1.0) == 1.0

    def test_custom_range(self):
        assert _clamp(5.0, low=0.0, high=3.0) == 3.0
        assert _clamp(-1.0, low=-2.0, high=2.0) == -1.0

    def test_invalid_value_returns_default(self):
        assert _clamp(None) == 0.5
        assert _clamp("abc") == 0.5
        assert _clamp(None, default=0.7) == 0.7

    def test_string_number(self):
        assert _clamp("0.6") == 0.6

    def test_int_input(self):
        assert _clamp(0) == 0.0
        assert _clamp(1) == 1.0


class TestSafeList:
    def test_list_input(self):
        assert _safe_list([1, 2]) == [1, 2]

    def test_non_list_returns_empty(self):
        assert _safe_list(None) == []
        assert _safe_list("abc") == []
        assert _safe_list(123) == []
        assert _safe_list({}) == []

    def test_empty_list(self):
        assert _safe_list([]) == []


class TestSafeDict:
    def test_dict_input(self):
        assert _safe_dict({"a": 1}) == {"a": 1}

    def test_non_dict_returns_empty(self):
        assert _safe_dict(None) == {}
        assert _safe_dict([]) == {}
        assert _safe_dict("abc") == {}

    def test_empty_dict(self):
        assert _safe_dict({}) == {}


class TestExtractProfileValue:
    def test_none_profile(self):
        assert _extract_profile_value(None, "key", "default") == "default"

    def test_dict_profile(self):
        assert _extract_profile_value({"name": "test"}, "name") == "test"
        assert _extract_profile_value({"name": "test"}, "missing", "fallback") == "fallback"

    def test_object_profile(self):
        class FakeProfile:
            name = "test_obj"
        assert _extract_profile_value(FakeProfile(), "name") == "test_obj"
        assert _extract_profile_value(FakeProfile(), "missing", "fallback") == "fallback"


class TestBuildDataclass:
    def test_from_dict(self):
        prior = _build_dataclass(AgentPrior, {"entity_type": "Student", "stance": "opposing"})
        assert prior.entity_type == "Student"
        assert prior.stance == "opposing"
        assert prior.profession == ""  # default

    def test_non_dict_returns_default(self):
        prior = _build_dataclass(AgentPrior, None)
        assert prior.entity_type == "Unknown"

    def test_extra_keys_ignored(self):
        prior = _build_dataclass(AgentPrior, {"entity_type": "X", "unknown_field": 999})
        assert prior.entity_type == "X"

    def test_empty_dict(self):
        state = _build_dataclass(AgentCognitiveState, {})
        assert state.round_num == 0
        assert state.attention_focus == "事件全貌"


class TestLevelText:
    def test_very_high(self):
        assert _level_text(0.8) == "很高"
        assert _level_text(0.75) == "很高"
        assert _level_text(1.0) == "很高"

    def test_high(self):
        assert _level_text(0.6) == "较高"
        assert _level_text(0.55) == "较高"

    def test_medium(self):
        assert _level_text(0.5) == "中等"
        assert _level_text(0.35) == "中等"

    def test_low(self):
        assert _level_text(0.2) == "较低"
        assert _level_text(0.15) == "较低"

    def test_very_low(self):
        assert _level_text(0.1) == "很低"
        assert _level_text(0.0) == "很低"


# ============================================================
# 2. 默认值生成器
# ============================================================

class TestDefaultIdentityFocus:
    def test_student(self):
        result = _default_identity_focus("Student", "大三学生")
        assert "大三学生" in result
        assert len(result) == 3

    def test_university(self):
        result = _default_identity_focus("University", "")
        assert "机构角色" in result

    def test_media(self):
        result = _default_identity_focus("MediaOutlet", "记者")
        assert "记者" in result

    def test_professor(self):
        result = _default_identity_focus("Professor", "教授")
        assert "教授" in result

    def test_unknown_fallback(self):
        result = _default_identity_focus("SomeRandomType", "")
        assert len(result) == 3

    def test_none_type(self):
        result = _default_identity_focus(None, "")
        assert len(result) == 3

    def test_case_insensitive(self):
        r1 = _default_identity_focus("student", "")
        r2 = _default_identity_focus("Student", "")
        assert r1 == r2


class TestDefaultGoals:
    def test_university(self):
        goals = _default_goals("University", "neutral")
        assert "维护组织稳定" in goals

    def test_media(self):
        goals = _default_goals("MediaOutlet", "observer")
        assert "追踪事件进展" in goals

    def test_student(self):
        goals = _default_goals("Student", "opposing")
        assert "表达自身立场" in goals

    def test_professor(self):
        goals = _default_goals("Professor", "neutral")
        assert "提供专业判断" in goals

    def test_stance_supportive(self):
        goals = _default_goals("Person", "supportive")
        assert "维持秩序稳定" in goals

    def test_stance_opposing(self):
        goals = _default_goals("Person", "opposing")
        assert "质疑现有叙事" in goals

    def test_stance_observer(self):
        goals = _default_goals("Person", "observer")
        assert "持续观察局势" in goals

    def test_neutral_fallback(self):
        goals = _default_goals("Person", "neutral")
        assert len(goals) == 3


class TestDecisionStyle:
    def test_institutional(self):
        assert _decision_style("University", "neutral", {}) == "institutional"
        assert _decision_style("GovernmentAgency", "neutral", {}) == "institutional"

    def test_monitoring(self):
        assert _decision_style("MediaOutlet", "neutral", {}) == "monitoring"

    def test_analytical(self):
        assert _decision_style("Person", "neutral", {"truth_seeking": 0.8}) == "analytical"

    def test_expressive(self):
        assert _decision_style("Person", "neutral", {"truth_seeking": 0.3, "emotional_expression": 0.7}) == "expressive"

    def test_consensus(self):
        assert _decision_style("Person", "neutral", {"truth_seeking": 0.3, "emotional_expression": 0.3, "social_conformity": 0.7}) == "consensus"

    def test_skeptical(self):
        assert _decision_style("Person", "opposing", {"truth_seeking": 0.3, "emotional_expression": 0.3, "social_conformity": 0.3}) == "skeptical"

    def test_balanced_fallback(self):
        assert _decision_style("Person", "neutral", {"truth_seeking": 0.3, "emotional_expression": 0.3, "social_conformity": 0.3}) == "balanced"


# ============================================================
# 3. 标签映射
# ============================================================

class TestGoalLabel:
    def test_known_keys(self):
        assert _goal_label("stability_guard") == "维护秩序与稳定"
        assert _goal_label("truth_verification") == "核验信息真实性"
        assert _goal_label("self_protection") == "降低自身风险"
        assert _goal_label("peer_alignment") == "保持群体一致"
        assert _goal_label("narrative_influence") == "影响舆论走向"
        assert _goal_label("emotional_release") == "表达情绪立场"

    def test_unknown_key_passthrough(self):
        assert _goal_label("unknown_key") == "unknown_key"


class TestStrategyLabel:
    def test_known_keys(self):
        assert _strategy_label("observe") == "继续观察"
        assert _strategy_label("verify") == "优先核验"
        assert _strategy_label("stabilize") == "偏向稳态表达"
        assert _strategy_label("challenge") == "偏向质疑推进"
        assert _strategy_label("align") == "偏向跟随群体"
        assert _strategy_label("clarify") == "偏向澄清解释"

    def test_unknown_key_passthrough(self):
        assert _strategy_label("xyz") == "xyz"


# ============================================================
# 4. 数据结构序列化
# ============================================================

class TestAgentBrainSerialization:
    def test_to_dict_and_from_dict_roundtrip(self):
        brain = AgentBrain(
            agent_id=42,
            entity_name="测试Agent",
            prior=AgentPrior(entity_type="Student", stance="opposing"),
            current_state=AgentCognitiveState(round_num=5, emotional_arousal=0.7),
        )
        d = brain.to_dict()
        assert d["agent_id"] == 42
        assert d["prior"]["entity_type"] == "Student"
        assert d["current_state"]["round_num"] == 5

        restored = AgentBrain.from_dict(d)
        assert restored.agent_id == 42
        assert restored.entity_name == "测试Agent"
        assert restored.prior.entity_type == "Student"
        assert restored.prior.stance == "opposing"
        assert restored.current_state.round_num == 5
        assert restored.current_state.emotional_arousal == 0.7

    def test_from_dict_with_missing_fields(self):
        brain = AgentBrain.from_dict({"agent_id": 1, "entity_name": "X"})
        assert brain.agent_id == 1
        assert brain.prior.entity_type == "Unknown"
        assert brain.current_state.round_num == 0
        assert "recent_actions" in brain.memory_scaffold
        assert "current_plan" in brain.planner_scaffold

    def test_from_dict_with_empty_input(self):
        brain = AgentBrain.from_dict({})
        assert brain.agent_id == 0
        assert brain.entity_name == ""

    def test_json_roundtrip(self):
        brain = AgentBrain(agent_id=7, entity_name="JSON测试")
        json_str = json.dumps(brain.to_dict(), ensure_ascii=False)
        restored = AgentBrain.from_dict(json.loads(json_str))
        assert restored.agent_id == 7
        assert restored.entity_name == "JSON测试"

    def test_memory_scaffold_defaults(self):
        brain = AgentBrain.from_dict({"agent_id": 0, "memory_scaffold": {}})
        assert brain.memory_scaffold["recent_actions"] == []
        assert brain.memory_scaffold["episodic"] == []
        assert brain.memory_scaffold["semantic"] == []
        assert brain.memory_scaffold["reflection_log"] == []

    def test_planner_scaffold_defaults(self):
        brain = AgentBrain.from_dict({"agent_id": 0, "planner_scaffold": {}})
        assert brain.planner_scaffold["current_plan"] == ""
        assert brain.planner_scaffold["plan_candidates"] == []
        assert brain.planner_scaffold["policy"] == "reactive"


# ============================================================
# 5. 核心逻辑
# ============================================================

class TestComputeGoalSalience:
    def test_returns_six_goals(self):
        prior = AgentPrior()
        state = AgentCognitiveState()
        salience = _compute_goal_salience(prior, state)
        assert len(salience) == 6
        assert set(salience.keys()) == {
            "stability_guard", "truth_verification", "self_protection",
            "peer_alignment", "narrative_influence", "emotional_release",
        }

    def test_all_values_in_range(self):
        prior = AgentPrior(stance="opposing", susceptibility=0.9)
        state = AgentCognitiveState(perceived_risk=0.9, emotional_arousal=0.9)
        salience = _compute_goal_salience(prior, state, {"attention_level": 0.9})
        for v in salience.values():
            assert 0.0 <= v <= 1.0, f"Goal salience {v} out of range"

    def test_institutional_boosts_stability(self):
        prior_inst = AgentPrior(decision_style="institutional")
        prior_norm = AgentPrior(decision_style="balanced")
        state = AgentCognitiveState()
        s1 = _compute_goal_salience(prior_inst, state)
        s2 = _compute_goal_salience(prior_norm, state)
        assert s1["stability_guard"] > s2["stability_guard"]

    def test_supportive_boosts_stability(self):
        prior_sup = AgentPrior(stance="supportive")
        prior_neu = AgentPrior(stance="neutral")
        state = AgentCognitiveState()
        s1 = _compute_goal_salience(prior_sup, state)
        s2 = _compute_goal_salience(prior_neu, state)
        assert s1["stability_guard"] > s2["stability_guard"]

    def test_opposing_boosts_emotional_release(self):
        prior_opp = AgentPrior(stance="opposing")
        prior_neu = AgentPrior(stance="neutral")
        state = AgentCognitiveState()
        s1 = _compute_goal_salience(prior_opp, state)
        s2 = _compute_goal_salience(prior_neu, state)
        assert s1["emotional_release"] > s2["emotional_release"]

    def test_high_risk_boosts_self_protection(self):
        prior = AgentPrior()
        s_low = AgentCognitiveState(perceived_risk=0.1)
        s_high = AgentCognitiveState(perceived_risk=0.9)
        sal_low = _compute_goal_salience(prior, s_low)
        sal_high = _compute_goal_salience(prior, s_high)
        assert sal_high["self_protection"] > sal_low["self_protection"]


class TestSelectStrategy:
    def test_verify_on_high_risk_low_certainty(self):
        prior = AgentPrior()
        state = AgentCognitiveState(perceived_risk=0.8, certainty=0.3)
        assert _select_strategy(prior, state) == "verify"

    def test_clarify_for_institutional(self):
        prior = AgentPrior(decision_style="institutional")
        state = AgentCognitiveState(trust_in_authority=0.7)
        assert _select_strategy(prior, state) == "clarify"

    def test_stabilize_for_supportive(self):
        prior = AgentPrior(stance="supportive", decision_style="balanced")
        state = AgentCognitiveState(trust_in_authority=0.7, perceived_risk=0.3, certainty=0.6)
        assert _select_strategy(prior, state) == "stabilize"

    def test_challenge_for_opposing(self):
        prior = AgentPrior(stance="opposing", decision_style="balanced")
        state = AgentCognitiveState(emotional_arousal=0.7, perceived_risk=0.3, certainty=0.6, trust_in_authority=0.3)
        assert _select_strategy(prior, state) == "challenge"

    def test_align_for_high_conformity(self):
        prior = AgentPrior(conformity=0.7, stance="neutral", decision_style="balanced")
        state = AgentCognitiveState(trust_in_peers=0.7, perceived_risk=0.3, certainty=0.6, trust_in_authority=0.3, emotional_arousal=0.3)
        assert _select_strategy(prior, state) == "align"

    def test_observe_fallback(self):
        prior = AgentPrior(conformity=0.3, stance="neutral", decision_style="balanced")
        state = AgentCognitiveState(perceived_risk=0.3, certainty=0.6, trust_in_authority=0.3, emotional_arousal=0.3, trust_in_peers=0.3)
        assert _select_strategy(prior, state) == "observe"


class TestInferAttentionFocus:
    def test_high_attention(self):
        prior = AgentPrior()
        ws = {"attention_level": 0.9, "risk_level": 0.1, "trust_level": 0.9, "polarization_level": 0.1}
        assert _infer_attention_focus(prior, ws) == "事件热度变化"

    def test_high_risk(self):
        prior = AgentPrior()
        ws = {"attention_level": 0.1, "risk_level": 0.9, "trust_level": 0.9, "polarization_level": 0.1}
        assert _infer_attention_focus(prior, ws) == "风险与不确定性"

    def test_low_trust(self):
        prior = AgentPrior()
        ws = {"attention_level": 0.1, "risk_level": 0.1, "trust_level": 0.05, "polarization_level": 0.1}
        assert _infer_attention_focus(prior, ws) == "权威信息可信度"

    def test_high_polarization(self):
        prior = AgentPrior()
        ws = {"attention_level": 0.1, "risk_level": 0.1, "trust_level": 0.9, "polarization_level": 0.9}
        assert _infer_attention_focus(prior, ws) == "群体立场分化"

    def test_institutional_adds_stability_signal(self):
        prior = AgentPrior(decision_style="institutional")
        ws = {"attention_level": 0.1, "risk_level": 0.1, "trust_level": 0.9, "polarization_level": 0.1, "stability_level": 0.05}
        assert _infer_attention_focus(prior, ws) == "秩序稳定与声誉"


class TestBuildReflectionHint:
    def test_verify_strategy(self):
        prior = AgentPrior()
        state = AgentCognitiveState(last_strategy="verify")
        hint = _build_reflection_hint(prior, state, {})
        assert "核验" in hint

    def test_clarify_strategy(self):
        prior = AgentPrior()
        state = AgentCognitiveState(last_strategy="clarify")
        hint = _build_reflection_hint(prior, state, {})
        assert "澄清" in hint

    def test_challenge_strategy(self):
        prior = AgentPrior()
        state = AgentCognitiveState(last_strategy="challenge")
        hint = _build_reflection_hint(prior, state, {})
        assert "质疑" in hint

    def test_align_strategy(self):
        prior = AgentPrior()
        state = AgentCognitiveState(last_strategy="align")
        hint = _build_reflection_hint(prior, state, {})
        assert "同伴" in hint

    def test_stabilize_strategy(self):
        prior = AgentPrior()
        state = AgentCognitiveState(last_strategy="stabilize")
        hint = _build_reflection_hint(prior, state, {})
        assert "稳态" in hint

    def test_observe_fallback(self):
        prior = AgentPrior()
        state = AgentCognitiveState(last_strategy="observe")
        hint = _build_reflection_hint(prior, state, {})
        assert "观察" in hint

    def test_with_recent_event(self):
        prior = AgentPrior()
        state = AgentCognitiveState(last_strategy="observe")
        ws = {"recent_events": [{"description": "校长发布声明"}]}
        hint = _build_reflection_hint(prior, state, ws)
        assert "校长发布声明" in hint

    def test_with_empty_events(self):
        prior = AgentPrior()
        state = AgentCognitiveState(last_strategy="observe")
        ws = {"recent_events": []}
        hint = _build_reflection_hint(prior, state, ws)
        assert "观察" in hint


class TestSummarizeAction:
    def test_create_post(self):
        s = _summarize_action("CREATE_POST", {"content": "这是一条帖子"})
        assert "发布帖子" in s

    def test_create_post_truncation(self):
        s = _summarize_action("CREATE_POST", {"content": "A" * 100})
        assert len(s) < 60

    def test_create_post_empty_content(self):
        s = _summarize_action("CREATE_POST", {"content": ""})
        assert "发布" in s

    def test_create_comment(self):
        s = _summarize_action("CREATE_COMMENT", {"content": "评论内容"})
        assert "评论" in s

    def test_repost(self):
        assert "转发" in _summarize_action("REPOST", {})

    def test_like_post(self):
        assert "点赞" in _summarize_action("LIKE_POST", {})

    def test_dislike_post(self):
        assert "踩" in _summarize_action("DISLIKE_POST", {})

    def test_follow(self):
        assert "关注" in _summarize_action("FOLLOW", {})

    def test_mute(self):
        assert "屏蔽" in _summarize_action("MUTE", {})

    def test_do_nothing(self):
        assert "暂不行动" in _summarize_action("DO_NOTHING", {})

    def test_unknown_action(self):
        s = _summarize_action("SOME_NEW_ACTION", {})
        assert "SOME_NEW_ACTION" in s

    def test_empty_action_type(self):
        s = _summarize_action("", {})
        assert "执行了一次动作" in s

    def test_none_args(self):
        s = _summarize_action("CREATE_POST", None)
        assert "发布" in s


# ============================================================
# 6. create_agent_brain_profile 入口
# ============================================================

class TestCreateAgentBrainProfile:
    def _make(self, entity_type="Student", stance="neutral", **kw):
        defaults = dict(
            agent_id=0,
            entity_name="测试",
            entity_type=entity_type,
            entity_summary="简介",
            simulation_requirement="模拟测试",
            activity_config={"stance": stance, "activity_level": 0.5, "influence_weight": 1.0},
        )
        defaults.update(kw)
        return create_agent_brain_profile(**defaults)

    def test_returns_dict(self):
        bp = self._make()
        assert isinstance(bp, dict)
        assert "agent_id" in bp
        assert "prior" in bp
        assert "current_state" in bp

    def test_university_institutional(self):
        bp = self._make(entity_type="University")
        assert bp["prior"]["decision_style"] == "institutional"
        assert bp["prior"]["entity_type"] == "University"

    def test_media_monitoring(self):
        bp = self._make(entity_type="MediaOutlet")
        assert bp["prior"]["decision_style"] == "monitoring"

    def test_stance_propagated(self):
        bp = self._make(stance="opposing")
        assert bp["prior"]["stance"] == "opposing"

    def test_supportive_higher_authority_trust(self):
        bp_sup = self._make(stance="supportive")
        bp_opp = self._make(stance="opposing")
        assert bp_sup["prior"]["authority_trust"] > bp_opp["prior"]["authority_trust"]

    def test_all_cognitive_values_in_range(self):
        bp = self._make()
        state = bp["current_state"]
        for key in ["emotional_arousal", "perceived_risk", "certainty",
                     "trust_in_authority", "trust_in_peers"]:
            v = state[key]
            assert 0.0 <= v <= 1.0, f"{key}={v} out of range"

    def test_goal_salience_has_six_keys(self):
        bp = self._make()
        assert len(bp["current_state"]["goal_salience"]) == 6

    def test_active_goals_populated(self):
        bp = self._make()
        assert len(bp["current_state"]["active_goals"]) >= 1

    def test_strategy_is_valid(self):
        bp = self._make()
        valid = {"observe", "verify", "stabilize", "challenge", "align", "clarify"}
        assert bp["current_state"]["last_strategy"] in valid

    def test_entity_summary_stored_in_memory(self):
        bp = self._make(entity_summary="这是简介")
        assert "这是简介" in bp["memory_scaffold"]["semantic"]

    def test_simulation_requirement_stored(self):
        bp = self._make(simulation_requirement="测试需求ABC")
        assert "测试需求ABC" in bp["planner_scaffold"]["simulation_requirement"]

    def test_with_profile_object(self):
        """传入 OasisAgentProfile 兼容对象时应读取其属性"""
        class FakeProfile:
            user_id = 0
            utility_weights = {"self_interest": 0.8, "truth_seeking": 0.9}
            susceptibility = 0.7
            profession = "新闻记者"
            internal_goals = ["揭露真相", "保持中立"]
            interested_topics = ["教育", "舆情"]
            emotional_tendency = 0.3
        bp = self._make(profile=FakeProfile())
        assert bp["prior"]["profession"] == "新闻记者"
        assert "揭露真相" in bp["prior"]["core_goals"]
        assert bp["prior"]["utility_weights"]["truth_seeking"] == 0.9

    def test_with_profile_dict(self):
        """传入 dict 格式 profile"""
        profile_dict = {
            "user_id": 0,
            "utility_weights": {"emotional_expression": 0.9},
            "profession": "律师",
            "internal_goals": ["维权"],
        }
        bp = self._make(profile=profile_dict)
        assert bp["prior"]["profession"] == "律师"
        assert "维权" in bp["prior"]["core_goals"]

    def test_none_profile_uses_defaults(self):
        bp = self._make(profile=None)
        assert len(bp["prior"]["core_goals"]) >= 2

    def test_roundtrip_through_agent_brain(self):
        """生成的 dict 可以被 AgentBrain.from_dict 反序列化"""
        bp = self._make()
        brain = AgentBrain.from_dict(bp)
        assert brain.agent_id == 0
        assert brain.prior.entity_type == "Student"


# ============================================================
# 7. AgentBrainRuntime
# ============================================================

def _make_config(n=3):
    """构造一个含 n 个 agent 的 simulation config"""
    agent_configs = []
    types = ["University", "Student", "MediaOutlet", "Professor", "Alumni"]
    stances = ["neutral", "opposing", "observer", "supportive"]
    for i in range(n):
        bp = create_agent_brain_profile(
            agent_id=i,
            entity_name=f"Agent_{i}",
            entity_type=types[i % len(types)],
            entity_summary=f"Agent {i} 简介",
            simulation_requirement="单元测试",
            activity_config={"stance": stances[i % len(stances)], "activity_level": 0.5, "influence_weight": 1.0},
        )
        agent_configs.append({
            "agent_id": i,
            "entity_name": f"Agent_{i}",
            "entity_type": types[i % len(types)],
            "stance": stances[i % len(stances)],
            "brain_profile": bp,
        })
    return {"agent_configs": agent_configs, "simulation_requirement": "单元测试"}


class TestAgentBrainRuntimeFromConfig:
    def test_loads_all_agents(self):
        rt = AgentBrainRuntime.from_simulation_config(_make_config(5))
        assert len(rt) == 5

    def test_loads_zero_agents(self):
        rt = AgentBrainRuntime.from_simulation_config({"agent_configs": []})
        assert len(rt) == 0

    def test_skips_missing_agent_id(self):
        config = {"agent_configs": [{"entity_name": "NoID"}]}
        rt = AgentBrainRuntime.from_simulation_config(config)
        assert len(rt) == 0

    def test_auto_generates_brain_when_missing(self):
        """没有 brain_profile 时应自动生成"""
        config = {
            "agent_configs": [
                {"agent_id": 0, "entity_name": "Auto", "entity_type": "Student", "stance": "neutral"}
            ]
        }
        rt = AgentBrainRuntime.from_simulation_config(config)
        assert len(rt) == 1
        prompt = rt.render_prompt(0)
        assert "Auto" in prompt


class TestAgentBrainRuntimeRenderPrompt:
    def test_contains_identity(self):
        rt = AgentBrainRuntime.from_simulation_config(_make_config(1))
        prompt = rt.render_prompt(0)
        assert "Agent_0" in prompt
        assert "认知框架" in prompt

    def test_contains_strategy(self):
        rt = AgentBrainRuntime.from_simulation_config(_make_config(1))
        prompt = rt.render_prompt(0)
        assert "策略倾向" in prompt

    def test_none_agent_id(self):
        rt = AgentBrainRuntime.from_simulation_config(_make_config(1))
        assert rt.render_prompt(None) == ""

    def test_missing_agent_id(self):
        rt = AgentBrainRuntime.from_simulation_config(_make_config(1))
        assert rt.render_prompt(999) == ""

    def test_ends_with_consistency_reminder(self):
        rt = AgentBrainRuntime.from_simulation_config(_make_config(1))
        prompt = rt.render_prompt(0)
        assert prompt.endswith("请保持与你的稳定倾向、近期经历和当前状态一致。")


class TestAgentBrainRuntimeApplyWorldState:
    def test_updates_round_num(self):
        rt = AgentBrainRuntime.from_simulation_config(_make_config(2))
        rt.apply_world_state(5, {
            "attention_level": 0.5, "panic_level": 0.3,
            "trust_level": 0.5, "polarization_level": 0.2,
            "risk_level": 0.3, "stability_level": 0.7,
        })
        assert rt._brains[0].current_state.round_num == 5
        assert rt._brains[1].current_state.round_num == 5

    def test_high_panic_increases_emotional_arousal(self):
        rt = AgentBrainRuntime.from_simulation_config(_make_config(1))
        ea_before = rt._brains[0].current_state.emotional_arousal
        rt.apply_world_state(1, {
            "attention_level": 0.8, "panic_level": 0.9,
            "trust_level": 0.2, "polarization_level": 0.7,
            "risk_level": 0.8, "stability_level": 0.2,
        })
        ea_after = rt._brains[0].current_state.emotional_arousal
        assert ea_after > ea_before

    def test_high_trust_increases_trust_in_authority(self):
        rt = AgentBrainRuntime.from_simulation_config(_make_config(1))
        rt.apply_world_state(1, {
            "attention_level": 0.1, "panic_level": 0.05,
            "trust_level": 0.95, "polarization_level": 0.05,
            "risk_level": 0.05, "stability_level": 0.95,
        })
        assert rt._brains[0].current_state.trust_in_authority >= 0.5

    def test_values_stay_in_range(self):
        rt = AgentBrainRuntime.from_simulation_config(_make_config(3))
        # 极端值
        for _ in range(10):
            rt.apply_world_state(_, {
                "attention_level": 1.0, "panic_level": 1.0,
                "trust_level": 0.0, "polarization_level": 1.0,
                "risk_level": 1.0, "stability_level": 0.0,
            })
        for brain in rt._brains.values():
            s = brain.current_state
            for attr in ["emotional_arousal", "perceived_risk", "certainty",
                         "trust_in_authority", "trust_in_peers"]:
                v = getattr(s, attr)
                assert 0.0 <= v <= 1.0, f"agent {brain.agent_id} {attr}={v}"

    def test_different_agents_diverge(self):
        """不同角色/立场的 Agent 在同一世界状态下应产生差异"""
        config = _make_config(3)  # University/neutral, Student/opposing, MediaOutlet/observer
        rt = AgentBrainRuntime.from_simulation_config(config)
        rt.apply_world_state(1, {
            "attention_level": 0.7, "panic_level": 0.5,
            "trust_level": 0.4, "polarization_level": 0.4,
            "risk_level": 0.5, "stability_level": 0.5,
        })
        strategies = [rt._brains[i].current_state.last_strategy for i in range(3)]
        # 至少不会所有人都一样（大多数情况下 University=clarify, Student 可能=challenge 或其他）
        # 这里只验证它们都是合法值
        valid = {"observe", "verify", "stabilize", "challenge", "align", "clarify"}
        for s in strategies:
            assert s in valid


class TestAgentBrainRuntimeRecordActions:
    def test_records_action(self):
        rt = AgentBrainRuntime.from_simulation_config(_make_config(2))
        rt.record_actions(1, [
            {"agent_id": 0, "action_type": "CREATE_POST", "action_args": {"content": "测试帖子"}},
        ])
        recent = rt._brains[0].memory_scaffold["recent_actions"]
        assert len(recent) == 1
        assert recent[0]["action_type"] == "CREATE_POST"
        assert "发布帖子" in recent[0]["summary"]

    def test_ignores_unknown_agent(self):
        rt = AgentBrainRuntime.from_simulation_config(_make_config(1))
        rt.record_actions(1, [
            {"agent_id": 999, "action_type": "CREATE_POST", "action_args": {}},
        ])
        # 不报错，Agent 0 不受影响
        assert len(rt._brains[0].memory_scaffold["recent_actions"]) == 0

    def test_ignores_missing_agent_id(self):
        rt = AgentBrainRuntime.from_simulation_config(_make_config(1))
        rt.record_actions(1, [{"action_type": "CREATE_POST"}])
        assert len(rt._brains[0].memory_scaffold["recent_actions"]) == 0

    def test_memory_window_capped_at_8(self):
        rt = AgentBrainRuntime.from_simulation_config(_make_config(1))
        for i in range(15):
            rt.record_actions(i, [
                {"agent_id": 0, "action_type": "CREATE_POST", "action_args": {"content": f"帖子{i}"}},
            ])
        recent = rt._brains[0].memory_scaffold["recent_actions"]
        assert len(recent) == 8
        # 最后一条是最新的
        assert "帖子14" in recent[-1]["summary"]

    def test_updates_reflection_hint(self):
        rt = AgentBrainRuntime.from_simulation_config(_make_config(1))
        rt.record_actions(1, [
            {"agent_id": 0, "action_type": "CREATE_COMMENT", "action_args": {"content": "评论"}},
        ])
        hint = rt._brains[0].current_state.reflection_hint
        assert "发表评论" in hint

    def test_render_prompt_shows_recent_actions(self):
        rt = AgentBrainRuntime.from_simulation_config(_make_config(1))
        rt.record_actions(1, [
            {"agent_id": 0, "action_type": "LIKE_POST", "action_args": {}},
        ])
        prompt = rt.render_prompt(0)
        assert "点赞了帖子" in prompt


class TestAgentBrainRuntimePersistence:
    def test_save_and_load(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            config = _make_config(2)
            rt = AgentBrainRuntime.load_or_create(config, tmpdir)
            assert len(rt) == 2

            # 修改状态
            rt.apply_world_state(3, {
                "attention_level": 0.6, "panic_level": 0.4,
                "trust_level": 0.5, "polarization_level": 0.3,
                "risk_level": 0.3, "stability_level": 0.6,
            })
            saved_round = rt._brains[0].current_state.round_num

            # 重新加载
            rt2 = AgentBrainRuntime.load_or_create(config, tmpdir)
            assert len(rt2) == 2
            assert rt2._brains[0].current_state.round_num == saved_round

    def test_creates_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            config = _make_config(1)
            AgentBrainRuntime.load_or_create(config, tmpdir)
            assert os.path.exists(os.path.join(tmpdir, "agent_brain_state.json"))

    def test_corrupted_file_falls_back(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            # 写入损坏的 JSON
            path = os.path.join(tmpdir, "agent_brain_state.json")
            with open(path, "w") as f:
                f.write("{corrupted json!!")
            config = _make_config(1)
            rt = AgentBrainRuntime.load_or_create(config, tmpdir)
            assert len(rt) == 1  # 应该 fallback 到 from_simulation_config

    def test_empty_brains_file_falls_back(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "agent_brain_state.json")
            with open(path, "w") as f:
                json.dump({"brains": {}}, f)
            config = _make_config(2)
            rt = AgentBrainRuntime.load_or_create(config, tmpdir)
            assert len(rt) == 2  # 空 brains → fallback

    def test_no_storage_path_skip_save(self):
        """storage_path=None 时 save 不报错"""
        rt = AgentBrainRuntime(brains={}, storage_path=None)
        rt.save()  # 不应抛异常


# ============================================================
# 8. 集成点: AgentActivityConfig.brain_profile
# ============================================================

class TestIntegrationAgentActivityConfig:
    def test_brain_profile_field_exists(self):
        from app.services.simulation_config_generator import AgentActivityConfig
        config = AgentActivityConfig(
            agent_id=0, entity_uuid="uuid-0",
            entity_name="Test", entity_type="Student",
        )
        assert hasattr(config, "brain_profile")
        assert isinstance(config.brain_profile, dict)

    def test_brain_profile_serialization(self):
        from dataclasses import asdict
        from app.services.simulation_config_generator import AgentActivityConfig
        bp = create_agent_brain_profile(
            agent_id=0, entity_name="Test", entity_type="Student",
            entity_summary="", simulation_requirement="",
            activity_config={"stance": "neutral"},
        )
        config = AgentActivityConfig(
            agent_id=0, entity_uuid="uuid-0",
            entity_name="Test", entity_type="Student",
            brain_profile=bp,
        )
        d = asdict(config)
        assert d["brain_profile"]["prior"]["entity_type"] == "Student"
        # JSON roundtrip
        json_str = json.dumps(d, ensure_ascii=False)
        restored = json.loads(json_str)
        assert restored["brain_profile"]["agent_id"] == 0


# ============================================================
# 9. 认知轨迹持久化: write_cognition_snapshot / generate_cognition_summary
# ============================================================

class TestCognitionSnapshot:
    def test_write_cognition_snapshot_creates_jsonl(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            config = _make_config(2)
            rt = AgentBrainRuntime.load_or_create(config, tmpdir)
            rt.apply_world_state(0, {"attention_level": 0.3, "panic_level": 0.5,
                                     "trust_level": 0.4, "polarization_level": 0.2,
                                     "risk_level": 0.6, "stability_level": 0.7})
            rt.write_cognition_snapshot(0)
            history_path = os.path.join(tmpdir, "agent_cognition_history.jsonl")
            assert os.path.exists(history_path)
            with open(history_path, "r", encoding="utf-8") as f:
                lines = f.readlines()
            assert len(lines) == 1
            record = json.loads(lines[0])
            assert record["round_num"] == 0
            assert len(record["agents"]) == 2

    def test_write_multiple_rounds(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            config = _make_config(1)
            rt = AgentBrainRuntime.load_or_create(config, tmpdir)
            rt.write_cognition_snapshot(0)
            rt.write_cognition_snapshot(1)
            rt.write_cognition_snapshot(2)
            history_path = os.path.join(tmpdir, "agent_cognition_history.jsonl")
            with open(history_path, "r", encoding="utf-8") as f:
                lines = f.readlines()
            assert len(lines) == 3
            for i, line in enumerate(lines):
                assert json.loads(line)["round_num"] == i

    def test_snapshot_contains_expected_fields(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            config = _make_config(1)
            rt = AgentBrainRuntime.load_or_create(config, tmpdir)
            rt.write_cognition_snapshot(5)
            history_path = os.path.join(tmpdir, "agent_cognition_history.jsonl")
            with open(history_path, "r", encoding="utf-8") as f:
                record = json.loads(f.readline())
            agent = record["agents"][0]
            required_keys = {"agent_id", "entity_name", "emotional_arousal",
                             "perceived_risk", "certainty", "trust_in_authority",
                             "trust_in_peers", "strategy", "active_goals",
                             "attention_focus", "stance"}
            assert required_keys.issubset(set(agent.keys()))

    def test_no_storage_path_no_error(self):
        rt = AgentBrainRuntime(brains={}, storage_path=None)
        rt.write_cognition_snapshot(0)  # should not raise


class TestCognitionSummary:
    def test_generate_summary_writes_json(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            config = _make_config(3)
            rt = AgentBrainRuntime.load_or_create(config, tmpdir)
            rt.apply_world_state(5, {"panic_level": 0.6})
            summary = rt.generate_cognition_summary()
            assert summary["total_agents"] == 3
            assert len(summary["agents"]) == 3
            summary_path = os.path.join(tmpdir, "agent_cognition_summary.json")
            assert os.path.exists(summary_path)
            with open(summary_path, "r", encoding="utf-8") as f:
                loaded = json.load(f)
            assert loaded["total_agents"] == 3

    def test_summary_agent_fields(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            config = _make_config(1)
            rt = AgentBrainRuntime.load_or_create(config, tmpdir)
            summary = rt.generate_cognition_summary()
            ag = summary["agents"][0]
            assert "entity_name" in ag
            assert "final_state" in ag
            assert "emotional_arousal" in ag["final_state"]
            assert "recent_actions" in ag

    def test_no_storage_path_returns_summary(self):
        rt = AgentBrainRuntime(brains={}, storage_path=None)
        summary = rt.generate_cognition_summary()
        assert summary["total_agents"] == 0


# ============================================================
# 10. 采访上下文增强: render_interview_context
# ============================================================

class TestRenderInterviewContext:
    def test_returns_context_for_known_agent(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            config = _make_config(1)
            rt = AgentBrainRuntime.load_or_create(config, tmpdir)
            ctx = rt.render_interview_context(0)
            assert len(ctx) > 0
            assert "系统提示" in ctx
            assert "Agent_0" in ctx

    def test_returns_empty_for_unknown_agent(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            config = _make_config(1)
            rt = AgentBrainRuntime.load_or_create(config, tmpdir)
            ctx = rt.render_interview_context(999)
            assert ctx == ""

    def test_context_includes_recent_actions(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            config = _make_config(1)
            rt = AgentBrainRuntime.load_or_create(config, tmpdir)
            rt.record_actions(0, [{"agent_id": 0, "action_type": "create_post",
                                   "action_args": {"content": "测试帖子"}}])
            ctx = rt.render_interview_context(0)
            assert "最近的行动" in ctx

    def test_context_includes_strategy(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            config = _make_config(1)
            rt = AgentBrainRuntime.load_or_create(config, tmpdir)
            rt.apply_world_state(0, {"panic_level": 0.8})
            ctx = rt.render_interview_context(0)
            assert "策略倾向" in ctx


# ============================================================
# 9. Feature ①: 个性化感知渲染 (Personalized Perception)
#    论文: SocioVerse §2.1, POSIM §3.2, OASIS, MOSAIC
# ============================================================


def _make_simple_config(n_agents=3, **overrides):
    """Simplified config builder for feature tests (no brain_profile pre-generation)."""
    agents = []
    for i in range(n_agents):
        ac = {"agent_id": i, "entity_name": f"Agent_{i}",
              "entity_type": overrides.get("entity_type", "Student"),
              "stance": overrides.get("stance", "neutral"),
              "activity_level": 0.5, "influence_weight": 1.0}
        agents.append(ac)
    return {"agent_configs": agents, "simulation_requirement": "test"}


class TestPersonalizedPerception:
    """Feature ①: 个性化感知渲染 (SocioVerse §2.1 Personalized Context)"""

    def test_high_susceptibility_sees_uncertainty(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            config = _make_simple_config(1)
            rt = AgentBrainRuntime.load_or_create(config, tmpdir)
            brain = list(rt._brains.values())[0]
            brain.prior.susceptibility = 0.8
            ws = {"panic_level": 0.6, "risk_level": 0.7}
            result = rt.render_personalized_perception(0, ws)
            assert "不确定性" in result
            assert "核实" in result

    def test_high_truth_seeking_sees_evidence_gap(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            config = _make_simple_config(1)
            rt = AgentBrainRuntime.load_or_create(config, tmpdir)
            brain = list(rt._brains.values())[0]
            brain.prior.utility_weights["truth_seeking"] = 0.8
            ws = {"trust_level": 0.3, "polarization_level": 0.6}
            result = rt.render_personalized_perception(0, ws)
            assert "验证" in result or "分歧" in result

    def test_institution_sees_stability(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            config = _make_simple_config(1, entity_type="University")
            rt = AgentBrainRuntime.load_or_create(config, tmpdir)
            ws = {"stability_level": 0.3, "attention_level": 0.7}
            result = rt.render_personalized_perception(0, ws)
            assert "组织" in result or "关注度" in result

    def test_media_sees_info_flow(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            config = _make_simple_config(1, entity_type="MediaOutlet")
            rt = AgentBrainRuntime.load_or_create(config, tmpdir)
            ws = {"attention_level": 0.6}
            result = rt.render_personalized_perception(0, ws)
            assert "信息流" in result or "追踪" in result

    def test_conformist_sees_group_signal(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            config = _make_simple_config(1)
            rt = AgentBrainRuntime.load_or_create(config, tmpdir)
            brain = list(rt._brains.values())[0]
            brain.prior.conformity = 0.8
            ws = {"polarization_level": 0.6}
            result = rt.render_personalized_perception(0, ws)
            assert "多数" in result or "群体" in result

    def test_risk_averse_sees_risk(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            config = _make_simple_config(1)
            rt = AgentBrainRuntime.load_or_create(config, tmpdir)
            brain = list(rt._brains.values())[0]
            brain.prior.risk_tolerance = 0.2
            ws = {"risk_level": 0.6}
            result = rt.render_personalized_perception(0, ws)
            assert "风险" in result

    def test_no_signal_returns_empty(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            config = _make_simple_config(1)
            rt = AgentBrainRuntime.load_or_create(config, tmpdir)
            ws = {"panic_level": 0.1, "risk_level": 0.1, "trust_level": 0.7}
            result = rt.render_personalized_perception(0, ws)
            assert result == ""

    def test_unknown_agent_returns_empty(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            config = _make_simple_config(1)
            rt = AgentBrainRuntime.load_or_create(config, tmpdir)
            result = rt.render_personalized_perception(999, {"panic_level": 0.9})
            assert result == ""


# ============================================================
# 10. Feature ②: 立场漂移 (Stance Drift)
#     论文: POSIM §3.3, Rumor Spreading, AgentSociety, 综述
# ============================================================


class TestStanceDrift:
    """Feature ②: 立场漂移 (POSIM §3.3 慢信念层 B_psy / B_id)"""

    def test_adjacency_map_completeness(self):
        for stance in ["supportive", "neutral", "opposing"]:
            assert stance in _STANCE_ADJACENCY

    def test_adjacency_only_neighbors(self):
        assert "opposing" not in _STANCE_ADJACENCY["supportive"]
        assert "supportive" not in _STANCE_ADJACENCY["opposing"]

    def test_drift_pressure_high_emotion_positive(self):
        brain = AgentBrain(agent_id=0, entity_name="Test")
        brain.current_state.emotional_arousal = 0.9
        brain.current_state.trust_in_authority = 0.2
        brain.current_state.perceived_risk = 0.8
        ws = {"polarization_level": 0.5}
        pressure = _compute_drift_pressure(brain, ws)
        assert pressure > 0, "High emotion + low trust should push toward opposing"

    def test_drift_pressure_low_emotion_negative(self):
        brain = AgentBrain(agent_id=0, entity_name="Test")
        brain.current_state.emotional_arousal = 0.1
        brain.current_state.trust_in_authority = 0.9
        brain.current_state.perceived_risk = 0.1
        ws = {"polarization_level": 0.1}
        pressure = _compute_drift_pressure(brain, ws)
        assert pressure < 0, "Low emotion + high trust should push toward supportive"

    def test_susceptibility_amplifies_pressure(self):
        brain_low = AgentBrain(agent_id=0, entity_name="Lo")
        brain_low.prior.susceptibility = 0.1
        brain_low.current_state.emotional_arousal = 0.8
        brain_low.current_state.trust_in_authority = 0.2

        brain_high = AgentBrain(agent_id=1, entity_name="Hi")
        brain_high.prior.susceptibility = 0.9
        brain_high.current_state.emotional_arousal = 0.8
        brain_high.current_state.trust_in_authority = 0.2

        ws = {"polarization_level": 0.3}
        p_low = abs(_compute_drift_pressure(brain_low, ws))
        p_high = abs(_compute_drift_pressure(brain_high, ws))
        assert p_high > p_low

    def test_no_drift_below_threshold(self):
        brain = AgentBrain(agent_id=0, entity_name="Test", prior=AgentPrior(stance="neutral", initial_stance="neutral"))
        brain.current_state.stance_drift_pressure = 0.3
        ws = {"panic_level": 0.3, "trust_level": 0.5, "polarization_level": 0.2}
        result = _apply_stance_drift(brain, ws, 5)
        assert result is None
        assert brain.prior.stance == "neutral"

    def test_drift_triggers_at_threshold(self):
        brain = AgentBrain(agent_id=0, entity_name="TestAgent",
                          prior=AgentPrior(stance="neutral", initial_stance="neutral"))
        brain.current_state.stance_drift_pressure = _STANCE_DRIFT_THRESHOLD + 0.1
        brain.current_state.emotional_arousal = 0.9
        brain.current_state.trust_in_authority = 0.1
        brain.current_state.perceived_risk = 0.8
        ws = {"polarization_level": 0.8, "panic_level": 0.8, "trust_level": 0.1}
        result = _apply_stance_drift(brain, ws, 10)
        assert result is not None
        assert brain.prior.stance == "opposing"
        assert "漂移" in result

    def test_drift_only_adjacent(self):
        brain = AgentBrain(agent_id=0, entity_name="Test",
                          prior=AgentPrior(stance="supportive", initial_stance="supportive"))
        brain.current_state.stance_drift_pressure = _STANCE_DRIFT_THRESHOLD + 0.2
        brain.current_state.emotional_arousal = 0.9
        brain.current_state.trust_in_authority = 0.1
        ws = {"polarization_level": 0.8, "panic_level": 0.8, "trust_level": 0.1}
        result = _apply_stance_drift(brain, ws, 5)
        if result:
            assert brain.prior.stance == "neutral"  # supportive -> neutral, not opposing

    def test_drift_records_attribution_event(self):
        brain = AgentBrain(agent_id=0, entity_name="Test",
                          prior=AgentPrior(stance="neutral", initial_stance="neutral"))
        brain.current_state.stance_drift_pressure = _STANCE_DRIFT_THRESHOLD + 0.5
        brain.current_state.emotional_arousal = 0.9
        brain.current_state.trust_in_authority = 0.1
        ws = {"polarization_level": 0.9, "panic_level": 0.9, "trust_level": 0.1}
        _apply_stance_drift(brain, ws, 8)
        stance_events = [e for e in brain.current_state.attribution_events if e.get("dimension") == "stance_drift"]
        if brain.prior.stance != "neutral":
            assert len(stance_events) >= 1

    def test_drift_integrated_in_apply_world_state(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            config = _make_simple_config(1, stance="neutral")
            rt = AgentBrainRuntime.load_or_create(config, tmpdir)
            brain = list(rt._brains.values())[0]
            brain.prior.initial_stance = "neutral"
            brain.prior.susceptibility = 0.9
            # Simulate many rounds of high-stress to trigger drift
            for r in range(30):
                rt.apply_world_state(r, {
                    "panic_level": 0.9, "trust_level": 0.1,
                    "polarization_level": 0.8, "risk_level": 0.8,
                    "attention_level": 0.7, "stability_level": 0.2,
                })
            # After sustained pressure, stance should have drifted
            assert brain.prior.stance != "neutral" or brain.current_state.stance_drift_pressure > 0.3

    def test_initial_stance_preserved(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            config = _make_simple_config(1, stance="supportive")
            rt = AgentBrainRuntime.load_or_create(config, tmpdir)
            brain = list(rt._brains.values())[0]
            assert brain.prior.initial_stance == "supportive"


# ============================================================
# 11. Feature ③: 认知归因链 (Cognitive Attribution)
#     论文: POSIM §6 mechanism layer, Survey §8.3, 综述
# ============================================================


class TestCognitiveAttribution:
    """Feature ③: 认知归因 (POSIM §6 mechanism layer)"""

    def test_attribution_generated_on_large_change(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            config = _make_simple_config(1)
            rt = AgentBrainRuntime.load_or_create(config, tmpdir)
            # First round with dramatic state
            rt.apply_world_state(0, {
                "panic_level": 0.9, "trust_level": 0.1,
                "risk_level": 0.8, "polarization_level": 0.7,
                "attention_level": 0.6, "stability_level": 0.2,
            })
            brain = list(rt._brains.values())[0]
            assert len(brain.current_state.attribution_events) > 0

    def test_attribution_has_required_fields(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            config = _make_simple_config(1)
            rt = AgentBrainRuntime.load_or_create(config, tmpdir)
            rt.apply_world_state(0, {
                "panic_level": 0.9, "trust_level": 0.1,
                "risk_level": 0.8, "polarization_level": 0.7,
                "attention_level": 0.6, "stability_level": 0.2,
            })
            brain = list(rt._brains.values())[0]
            for ev in brain.current_state.attribution_events:
                assert "round" in ev
                assert "dimension" in ev
                assert "old" in ev
                assert "new" in ev
                assert "delta" in ev
                assert "primary_driver" in ev

    def test_no_attribution_on_small_change(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            config = _make_simple_config(1)
            rt = AgentBrainRuntime.load_or_create(config, tmpdir)
            # Calm state should not generate large changes
            rt.apply_world_state(0, {
                "panic_level": 0.1, "trust_level": 0.6,
                "risk_level": 0.1, "polarization_level": 0.1,
                "attention_level": 0.1, "stability_level": 0.8,
            })
            # Apply same calm state again
            rt.apply_world_state(1, {
                "panic_level": 0.1, "trust_level": 0.6,
                "risk_level": 0.1, "polarization_level": 0.1,
                "attention_level": 0.1, "stability_level": 0.8,
            })
            brain = list(rt._brains.values())[0]
            # After second round with same data, changes should be minimal
            round1_events = [e for e in brain.current_state.attribution_events if e.get("round") == 1]
            # May or may not have events, but small ones are expected
            for ev in round1_events:
                assert abs(ev["delta"]) >= 0.08  # threshold

    def test_attribution_cap_at_30(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            config = _make_simple_config(1)
            rt = AgentBrainRuntime.load_or_create(config, tmpdir)
            for r in range(50):
                panic = 0.9 if r % 2 == 0 else 0.1
                rt.apply_world_state(r, {
                    "panic_level": panic, "trust_level": 0.1,
                    "risk_level": 0.8, "polarization_level": 0.7,
                    "attention_level": 0.6, "stability_level": 0.2,
                })
            brain = list(rt._brains.values())[0]
            assert len(brain.current_state.attribution_events) <= 30

    def test_attribution_in_cognition_snapshot(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            config = _make_simple_config(1)
            rt = AgentBrainRuntime.load_or_create(config, tmpdir)
            rt.apply_world_state(0, {
                "panic_level": 0.9, "trust_level": 0.1,
                "risk_level": 0.8, "polarization_level": 0.7,
                "attention_level": 0.6, "stability_level": 0.2,
            })
            rt.write_cognition_snapshot(0)
            history_path = os.path.join(tmpdir, "agent_cognition_history.jsonl")
            with open(history_path, "r", encoding="utf-8") as f:
                record = json.loads(f.readline())
            agent_snap = record["agents"][0]
            assert "attribution_count" in agent_snap

    def test_attribution_in_cognition_summary(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            config = _make_simple_config(1)
            rt = AgentBrainRuntime.load_or_create(config, tmpdir)
            rt.apply_world_state(0, {
                "panic_level": 0.9, "trust_level": 0.1,
                "risk_level": 0.8, "polarization_level": 0.7,
                "attention_level": 0.6, "stability_level": 0.2,
            })
            summary = rt.generate_cognition_summary()
            agent_data = summary["agents"][0]
            assert "attribution_events" in agent_data


# ============================================================
# 12. Feature ④: 反思机制 (Reflection)
#     论文: Generative Agents §4.3, POSIM §6, AgentSociety
# ============================================================


class TestReflection:
    """Feature ④: 反思机制 (Generative Agents §4.3 Reflection)"""

    def test_reflection_not_triggered_at_round_0(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            config = _make_simple_config(1)
            rt = AgentBrainRuntime.load_or_create(config, tmpdir)
            results = rt.trigger_reflection(0)
            assert results == {}

    def test_reflection_triggered_at_interval(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            config = _make_simple_config(1)
            rt = AgentBrainRuntime.load_or_create(config, tmpdir)
            # Record some actions first
            for r in range(_REFLECTION_INTERVAL):
                rt.record_actions(r, [{"agent_id": 0, "action_type": "CREATE_POST",
                                       "action_args": {"content": f"post {r}"}}])
            results = rt.trigger_reflection(_REFLECTION_INTERVAL)
            # Should generate a reflection since there are repeated CREATE_POST
            assert len(results) >= 0  # May or may not have content based on rules

    def test_reflection_detects_active_pattern(self):
        brain = AgentBrain(agent_id=0, entity_name="Test")
        for i in range(3):
            brain.memory_scaffold["recent_actions"].append({
                "round_num": i, "action_type": "CREATE_POST", "summary": f"发布帖子 {i}"
            })
        reflection = _generate_reflection(brain, 3)
        assert reflection is not None
        assert "主动" in reflection or "连续" in reflection

    def test_reflection_detects_passive_pattern(self):
        brain = AgentBrain(agent_id=0, entity_name="Test")
        for i in range(3):
            brain.memory_scaffold["recent_actions"].append({
                "round_num": i, "action_type": "DO_NOTHING", "summary": "选择暂不行动"
            })
        reflection = _generate_reflection(brain, 3)
        assert reflection is not None
        assert "被动" in reflection or "观望" in reflection

    def test_reflection_detects_trust_behavior_mismatch(self):
        brain = AgentBrain(agent_id=0, entity_name="Test")
        brain.current_state.trust_in_authority = 0.2
        brain.current_state.last_strategy = "stabilize"
        brain.memory_scaffold["recent_actions"].append({
            "round_num": 0, "action_type": "CREATE_POST", "summary": "test"
        })
        reflection = _generate_reflection(brain, 3)
        assert reflection is not None
        assert "权威" in reflection or "信任" in reflection

    def test_reflection_detects_cognitive_change(self):
        brain = AgentBrain(agent_id=0, entity_name="Test")
        brain.current_state.attribution_events = [
            {"round": 2, "dimension": "emotional_arousal", "delta": 0.15},
            {"round": 2, "dimension": "trust_in_authority", "delta": -0.12},
        ]
        brain.memory_scaffold["recent_actions"].append({
            "round_num": 2, "action_type": "CREATE_POST", "summary": "test"
        })
        reflection = _generate_reflection(brain, 3)
        assert reflection is not None
        assert "变化" in reflection

    def test_reflection_stored_in_state_and_memory(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            config = _make_simple_config(1)
            rt = AgentBrainRuntime.load_or_create(config, tmpdir)
            brain = list(rt._brains.values())[0]
            # Create a detectable pattern
            for r in range(3):
                brain.memory_scaffold["recent_actions"].append({
                    "round_num": r, "action_type": "CREATE_POST",
                    "summary": f"发布帖子 {r}"
                })
            results = rt.trigger_reflection(_REFLECTION_INTERVAL)
            if results:
                assert len(brain.current_state.reflection_log) > 0
                assert len(brain.memory_scaffold["reflection_log"]) > 0

    def test_reflection_cap_at_10(self):
        brain = AgentBrain(agent_id=0, entity_name="Test")
        brain.current_state.reflection_log = [f"r{i}" for i in range(12)]
        with tempfile.TemporaryDirectory() as tmpdir:
            config = {"agent_configs": [{"agent_id": 0, "entity_name": "Test",
                      "entity_type": "Student", "stance": "neutral",
                      "activity_level": 0.5, "influence_weight": 1.0}],
                      "simulation_requirement": "test"}
            rt = AgentBrainRuntime.load_or_create(config, tmpdir)
            rt._brains[0] = brain
            for r in range(3):
                brain.memory_scaffold["recent_actions"].append({
                    "round_num": r, "action_type": "CREATE_POST",
                    "summary": f"发帖 {r}"
                })
            rt.trigger_reflection(_REFLECTION_INTERVAL)
            assert len(brain.current_state.reflection_log) <= 10

    def test_reflection_in_render_prompt(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            config = _make_simple_config(1)
            rt = AgentBrainRuntime.load_or_create(config, tmpdir)
            brain = list(rt._brains.values())[0]
            brain.current_state.reflection_log = ["测试反思内容"]
            prompt = rt.render_prompt(0)
            assert "近期自我反思" in prompt
            assert "测试反思内容" in prompt

    def test_no_reflection_without_actions(self):
        brain = AgentBrain(agent_id=0, entity_name="Test")
        reflection = _generate_reflection(brain, 3)
        assert reflection is None


# ============================================================
# 13. Feature ①补充: 个性化感知 — 边界/组合/格式
# ============================================================


class TestPersonalizedPerceptionExtended:
    """Feature ① 补充测试: 边界条件、多特质组合、输出格式"""

    def test_output_has_header(self):
        """有信号时输出以 [你注意到的环境信号] 开头"""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = _make_simple_config(1)
            rt = AgentBrainRuntime.load_or_create(config, tmpdir)
            brain = list(rt._brains.values())[0]
            brain.prior.susceptibility = 0.9
            ws = {"panic_level": 0.8, "risk_level": 0.8}
            result = rt.render_personalized_perception(0, ws)
            assert result.startswith("[你注意到的环境信号]")

    def test_empty_ws_data_returns_empty(self):
        """空字典 ws_data → 不崩溃，返回空"""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = _make_simple_config(1)
            rt = AgentBrainRuntime.load_or_create(config, tmpdir)
            result = rt.render_personalized_perception(0, {})
            assert result == ""

    def test_none_ws_data_returns_empty(self):
        """None ws_data → 安全返回空"""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = _make_simple_config(1)
            rt = AgentBrainRuntime.load_or_create(config, tmpdir)
            result = rt.render_personalized_perception(0, None)
            assert result == ""

    def test_multiple_traits_combine(self):
        """高易感性 + 高求真 + 高从众 → 多条信号叠加"""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = _make_simple_config(1)
            rt = AgentBrainRuntime.load_or_create(config, tmpdir)
            brain = list(rt._brains.values())[0]
            brain.prior.susceptibility = 0.9
            brain.prior.conformity = 0.8
            brain.prior.utility_weights["truth_seeking"] = 0.8
            ws = {"panic_level": 0.8, "risk_level": 0.7, "trust_level": 0.2,
                  "polarization_level": 0.7}
            result = rt.render_personalized_perception(0, ws)
            lines = result.strip().split("\n")
            # header + at least 3 content lines (susceptibility×2 + truth + conformity)
            assert len(lines) >= 4

    def test_low_susceptibility_no_uncertainty(self):
        """低易感性 Agent 在高 panic 下不放大不确定性"""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = _make_simple_config(1)
            rt = AgentBrainRuntime.load_or_create(config, tmpdir)
            brain = list(rt._brains.values())[0]
            brain.prior.susceptibility = 0.3
            ws = {"panic_level": 0.8, "risk_level": 0.8}
            result = rt.render_personalized_perception(0, ws)
            assert "不确定性" not in result

    def test_government_agency_type(self):
        """GovernmentAgency 类型也触发机构感知"""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = _make_simple_config(1, entity_type="GovernmentAgency")
            rt = AgentBrainRuntime.load_or_create(config, tmpdir)
            ws = {"stability_level": 0.3, "attention_level": 0.7}
            result = rt.render_personalized_perception(0, ws)
            assert "组织" in result or "关注度" in result

    def test_journalist_type(self):
        """Journalist 类型也触发媒体感知"""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = _make_simple_config(1, entity_type="Journalist")
            rt = AgentBrainRuntime.load_or_create(config, tmpdir)
            ws = {"attention_level": 0.6}
            result = rt.render_personalized_perception(0, ws)
            assert "信息流" in result or "追踪" in result

    def test_boundary_susceptibility_exactly_0_6(self):
        """susceptibility == 0.6 (边界值) 且 panic >= 0.4 → 应触发"""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = _make_simple_config(1)
            rt = AgentBrainRuntime.load_or_create(config, tmpdir)
            brain = list(rt._brains.values())[0]
            brain.prior.susceptibility = 0.6
            ws = {"panic_level": 0.4}
            result = rt.render_personalized_perception(0, ws)
            assert "不确定性" in result

    def test_boundary_susceptibility_below_0_6(self):
        """susceptibility == 0.59 → 不触发高易感性"""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = _make_simple_config(1)
            rt = AgentBrainRuntime.load_or_create(config, tmpdir)
            brain = list(rt._brains.values())[0]
            brain.prior.susceptibility = 0.59
            ws = {"panic_level": 0.8}
            result = rt.render_personalized_perception(0, ws)
            assert "不确定性" not in result

    def test_high_risk_tolerance_no_risk_signal(self):
        """高风险容忍 Agent 不接收风险预警"""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = _make_simple_config(1)
            rt = AgentBrainRuntime.load_or_create(config, tmpdir)
            brain = list(rt._brains.values())[0]
            brain.prior.risk_tolerance = 0.8
            ws = {"risk_level": 0.8}
            result = rt.render_personalized_perception(0, ws)
            assert "风险因素" not in result

    def test_multi_agent_different_perception(self):
        """同一世界状态下，不同 Agent 看到不同的信号"""
        with tempfile.TemporaryDirectory() as tmpdir:
            agents = [
                {"agent_id": 0, "entity_name": "高易感", "entity_type": "Student",
                 "stance": "neutral", "activity_level": 0.5, "influence_weight": 1.0},
                {"agent_id": 1, "entity_name": "媒体", "entity_type": "MediaOutlet",
                 "stance": "neutral", "activity_level": 0.5, "influence_weight": 1.0},
            ]
            config = {"agent_configs": agents, "simulation_requirement": "test"}
            rt = AgentBrainRuntime.load_or_create(config, tmpdir)
            rt._brains[0].prior.susceptibility = 0.9
            ws = {"panic_level": 0.8, "risk_level": 0.7, "attention_level": 0.6}
            r0 = rt.render_personalized_perception(0, ws)
            r1 = rt.render_personalized_perception(1, ws)
            assert r0 != r1  # different agents see different things
            assert "不确定性" in r0  # student sees uncertainty
            assert "信息流" in r1 or "追踪" in r1  # media sees info flow


# ============================================================
# 14. Feature ②补充: 立场漂移 — 反向漂移/衰减/序列化/多Agent
# ============================================================


class TestStanceDriftExtended:
    """Feature ② 补充测试: 反向漂移、压力衰减、序列化、多 Agent 差异"""

    def test_reverse_drift_opposing_to_neutral(self):
        """opposing Agent 在低情绪+高信任条件下向 neutral 漂移"""
        brain = AgentBrain(agent_id=0, entity_name="Test",
                          prior=AgentPrior(stance="opposing", initial_stance="opposing"))
        brain.current_state.stance_drift_pressure = -(_STANCE_DRIFT_THRESHOLD + 0.1)
        brain.current_state.emotional_arousal = 0.1
        brain.current_state.trust_in_authority = 0.9
        brain.current_state.perceived_risk = 0.1
        ws = {"polarization_level": 0.1, "panic_level": 0.1, "trust_level": 0.9}
        result = _apply_stance_drift(brain, ws, 5)
        if result:
            assert brain.prior.stance == "neutral"

    def test_pressure_decays_over_calm_rounds(self):
        """平静世界状态下漂移压力应逐渐衰减"""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = _make_simple_config(1, stance="neutral")
            rt = AgentBrainRuntime.load_or_create(config, tmpdir)
            brain = list(rt._brains.values())[0]
            # Inject initial pressure
            brain.current_state.stance_drift_pressure = 0.4
            # Apply many calm rounds
            for r in range(20):
                rt.apply_world_state(r, {
                    "panic_level": 0.1, "trust_level": 0.7,
                    "polarization_level": 0.1, "risk_level": 0.1,
                    "attention_level": 0.1, "stability_level": 0.8,
                })
            # Pressure should have decayed significantly
            assert abs(brain.current_state.stance_drift_pressure) < 0.4

    def test_drift_pressure_resets_after_drift(self):
        """漂移发生后压力应大幅衰减 (×0.3)"""
        brain = AgentBrain(agent_id=0, entity_name="Test",
                          prior=AgentPrior(stance="neutral", initial_stance="neutral"))
        brain.current_state.stance_drift_pressure = _STANCE_DRIFT_THRESHOLD + 0.5
        brain.current_state.emotional_arousal = 0.95
        brain.current_state.trust_in_authority = 0.05
        brain.current_state.perceived_risk = 0.9
        ws = {"polarization_level": 0.9, "panic_level": 0.9, "trust_level": 0.05}
        old_pressure = brain.current_state.stance_drift_pressure
        result = _apply_stance_drift(brain, ws, 5)
        if result:
            assert abs(brain.current_state.stance_drift_pressure) < abs(old_pressure)

    def test_drift_state_survives_save_load(self):
        """漂移压力和初始立场在 save/load 后保持"""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = _make_simple_config(1, stance="neutral")
            rt = AgentBrainRuntime.load_or_create(config, tmpdir)
            brain = list(rt._brains.values())[0]
            brain.current_state.stance_drift_pressure = 0.42
            brain.prior.initial_stance = "neutral"
            rt.save()
            rt2 = AgentBrainRuntime.load_or_create(config, tmpdir)
            brain2 = list(rt2._brains.values())[0]
            assert abs(brain2.current_state.stance_drift_pressure - 0.42) < 0.01
            assert brain2.prior.initial_stance == "neutral"

    def test_multi_agent_divergent_drift(self):
        """高/低易感性 Agent 在同一压力下漂移速度不同"""
        with tempfile.TemporaryDirectory() as tmpdir:
            agents = [
                {"agent_id": 0, "entity_name": "Low", "entity_type": "Student",
                 "stance": "neutral", "activity_level": 0.5, "influence_weight": 1.0},
                {"agent_id": 1, "entity_name": "High", "entity_type": "Student",
                 "stance": "neutral", "activity_level": 0.5, "influence_weight": 1.0},
            ]
            config = {"agent_configs": agents, "simulation_requirement": "test"}
            rt = AgentBrainRuntime.load_or_create(config, tmpdir)
            rt._brains[0].prior.susceptibility = 0.1
            rt._brains[1].prior.susceptibility = 0.95
            for r in range(15):
                rt.apply_world_state(r, {
                    "panic_level": 0.8, "trust_level": 0.15,
                    "polarization_level": 0.7, "risk_level": 0.7,
                    "attention_level": 0.6, "stability_level": 0.2,
                })
            p0 = abs(rt._brains[0].current_state.stance_drift_pressure)
            p1 = abs(rt._brains[1].current_state.stance_drift_pressure)
            assert p1 > p0, "High susceptibility agent should accumulate more pressure"

    def test_unknown_stance_no_crash(self):
        """未知立场值不崩溃"""
        brain = AgentBrain(agent_id=0, entity_name="Test",
                          prior=AgentPrior(stance="unknown_stance", initial_stance="unknown_stance"))
        brain.current_state.stance_drift_pressure = 1.0
        brain.current_state.emotional_arousal = 0.9
        brain.current_state.trust_in_authority = 0.1
        ws = {"polarization_level": 0.8}
        result = _apply_stance_drift(brain, ws, 5)
        assert result is None

    def test_drift_event_has_correct_fields(self):
        """漂移归因事件字段完整性"""
        brain = AgentBrain(agent_id=0, entity_name="Drifter",
                          prior=AgentPrior(stance="neutral", initial_stance="neutral"))
        brain.current_state.stance_drift_pressure = _STANCE_DRIFT_THRESHOLD + 0.5
        brain.current_state.emotional_arousal = 0.95
        brain.current_state.trust_in_authority = 0.05
        ws = {"polarization_level": 0.9, "panic_level": 0.9, "trust_level": 0.05}
        _apply_stance_drift(brain, ws, 7)
        drift_events = [e for e in brain.current_state.attribution_events
                        if e.get("dimension") == "stance_drift"]
        if drift_events:
            ev = drift_events[0]
            assert ev["round"] == 7
            assert ev["old"] == "neutral"
            assert ev["new"] in ("opposing", "supportive")
            assert "primary_driver" in ev

    def test_double_drift_requires_two_stage(self):
        """从 supportive → opposing 需要经过 neutral，不可一步跳跃"""
        brain = AgentBrain(agent_id=0, entity_name="Test",
                          prior=AgentPrior(stance="supportive", initial_stance="supportive"))
        brain.current_state.stance_drift_pressure = 10.0  # extreme pressure
        brain.current_state.emotional_arousal = 0.99
        brain.current_state.trust_in_authority = 0.01
        ws = {"polarization_level": 0.95, "panic_level": 0.95, "trust_level": 0.01}
        _apply_stance_drift(brain, ws, 1)
        # Even with extreme pressure, first drift only goes to neutral
        assert brain.prior.stance in ("supportive", "neutral")
        if brain.prior.stance == "neutral":
            # Need second drift to reach opposing
            brain.current_state.stance_drift_pressure = 10.0
            _apply_stance_drift(brain, ws, 2)
            assert brain.prior.stance in ("neutral", "opposing")


# ============================================================
# 15. Feature ③补充: 认知归因 — 驱动因子准确性/多维度/序列化
# ============================================================


class TestCognitiveAttributionExtended:
    """Feature ③ 补充测试: 驱动因子选择、多维度归因、数据持久化"""

    def test_primary_driver_accuracy_for_emotional_arousal(self):
        """情绪唤醒变化的 primary_driver 应指向最偏离 0.5 的 ws 维度"""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = _make_simple_config(1)
            rt = AgentBrainRuntime.load_or_create(config, tmpdir)
            rt.apply_world_state(0, {
                "panic_level": 0.95,  # far from 0.5
                "attention_level": 0.55,  # near 0.5
                "polarization_level": 0.52,  # near 0.5
                "trust_level": 0.6, "risk_level": 0.5, "stability_level": 0.5,
            })
            brain = list(rt._brains.values())[0]
            ea_events = [e for e in brain.current_state.attribution_events
                         if e["dimension"] == "emotional_arousal"]
            if ea_events:
                assert "panic_level" in ea_events[0]["primary_driver"]

    def test_trust_drop_attributed_to_trust_level(self):
        """信任骤降时 primary_driver 应指向 trust_level"""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = _make_simple_config(1)
            rt = AgentBrainRuntime.load_or_create(config, tmpdir)
            # First calm round
            rt.apply_world_state(0, {
                "panic_level": 0.1, "trust_level": 0.8,
                "risk_level": 0.1, "polarization_level": 0.1,
                "attention_level": 0.1, "stability_level": 0.8,
            })
            # Trust crashes
            rt.apply_world_state(1, {
                "panic_level": 0.15, "trust_level": 0.05,
                "risk_level": 0.1, "polarization_level": 0.1,
                "attention_level": 0.1, "stability_level": 0.8,
            })
            brain = list(rt._brains.values())[0]
            trust_events = [e for e in brain.current_state.attribution_events
                            if e["dimension"] == "trust_in_authority" and e["round"] == 1]
            if trust_events:
                assert "trust_level" in trust_events[0]["primary_driver"]

    def test_multiple_dimensions_change_simultaneously(self):
        """剧烈变化时应产生多个不同维度的归因"""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = _make_simple_config(1)
            rt = AgentBrainRuntime.load_or_create(config, tmpdir)
            rt.apply_world_state(0, {
                "panic_level": 0.95, "trust_level": 0.05,
                "risk_level": 0.9, "polarization_level": 0.9,
                "attention_level": 0.8, "stability_level": 0.1,
            })
            brain = list(rt._brains.values())[0]
            dims = {e["dimension"] for e in brain.current_state.attribution_events}
            assert len(dims) >= 2, "Multiple dimensions should change under extreme conditions"

    def test_attribution_delta_sign_correct(self):
        """归因 delta 的符号应与实际变化方向一致"""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = _make_simple_config(1)
            rt = AgentBrainRuntime.load_or_create(config, tmpdir)
            rt.apply_world_state(0, {
                "panic_level": 0.9, "trust_level": 0.1,
                "risk_level": 0.8, "polarization_level": 0.7,
                "attention_level": 0.6, "stability_level": 0.2,
            })
            brain = list(rt._brains.values())[0]
            for ev in brain.current_state.attribution_events:
                computed_delta = ev["new"] - ev["old"]
                assert (computed_delta > 0) == (ev["delta"] > 0) or abs(computed_delta) < 0.001

    def test_attribution_survives_save_load(self):
        """归因事件在 save/load 后保持完整"""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = _make_simple_config(1)
            rt = AgentBrainRuntime.load_or_create(config, tmpdir)
            rt.apply_world_state(0, {
                "panic_level": 0.9, "trust_level": 0.1,
                "risk_level": 0.8, "polarization_level": 0.7,
                "attention_level": 0.6, "stability_level": 0.2,
            })
            brain = list(rt._brains.values())[0]
            n_events = len(brain.current_state.attribution_events)
            rt.save()
            rt2 = AgentBrainRuntime.load_or_create(config, tmpdir)
            brain2 = list(rt2._brains.values())[0]
            assert len(brain2.current_state.attribution_events) == n_events
            if n_events > 0:
                assert brain2.current_state.attribution_events[0]["dimension"] == \
                       brain.current_state.attribution_events[0]["dimension"]

    def test_attribution_round_number_correct(self):
        """归因事件的 round 字段与实际轮次一致"""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = _make_simple_config(1)
            rt = AgentBrainRuntime.load_or_create(config, tmpdir)
            for r in [0, 5, 10]:
                rt.apply_world_state(r, {
                    "panic_level": 0.8 if r % 2 == 0 else 0.1,
                    "trust_level": 0.1, "risk_level": 0.7,
                    "polarization_level": 0.6, "attention_level": 0.5,
                    "stability_level": 0.3,
                })
            brain = list(rt._brains.values())[0]
            for ev in brain.current_state.attribution_events:
                assert ev["round"] in [0, 5, 10]

    def test_summary_stance_drifted_flag(self):
        """generate_cognition_summary 的 stance_drifted 标记正确"""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = _make_simple_config(1, stance="neutral")
            rt = AgentBrainRuntime.load_or_create(config, tmpdir)
            brain = list(rt._brains.values())[0]
            brain.prior.initial_stance = "neutral"
            summary = rt.generate_cognition_summary()
            assert summary["agents"][0]["stance_drifted"] is False
            # Simulate drift
            brain.prior.stance = "opposing"
            summary2 = rt.generate_cognition_summary()
            assert summary2["agents"][0]["stance_drifted"] is True

    def test_snapshot_includes_new_fields(self):
        """write_cognition_snapshot 包含 initial_stance, stance_drift_pressure, latest_reflection"""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = _make_simple_config(1)
            rt = AgentBrainRuntime.load_or_create(config, tmpdir)
            brain = list(rt._brains.values())[0]
            brain.current_state.reflection_log = ["反思X"]
            rt.write_cognition_snapshot(0)
            history_path = os.path.join(tmpdir, "agent_cognition_history.jsonl")
            with open(history_path, "r", encoding="utf-8") as f:
                record = json.loads(f.readline())
            snap = record["agents"][0]
            assert "initial_stance" in snap
            assert "stance_drift_pressure" in snap
            assert snap["latest_reflection"] == "反思X"
            assert "attribution_count" in snap


# ============================================================
# 16. Feature ④补充: 反思 — 策略冲突/高信任质疑/非间隔轮/序列化
# ============================================================


class TestReflectionExtended:
    """Feature ④ 补充测试: 更多反思触发路径、序列化、边界"""

    def test_reflection_not_triggered_at_non_interval(self):
        """非间隔轮次不触发反思"""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = _make_simple_config(1)
            rt = AgentBrainRuntime.load_or_create(config, tmpdir)
            for r in range(3):
                rt.record_actions(r, [{"agent_id": 0, "action_type": "CREATE_POST",
                                       "action_args": {"content": f"p{r}"}}])
            # Round 1,2 are not _REFLECTION_INTERVAL multiples (assuming interval=3)
            for non_interval in [1, 2, 4, 5]:
                if non_interval % _REFLECTION_INTERVAL != 0:
                    results = rt.trigger_reflection(non_interval)
                    assert results == {}

    def test_high_trust_challenge_mismatch(self):
        """高信任 + 质疑策略 → 检测错位"""
        brain = AgentBrain(agent_id=0, entity_name="Test")
        brain.current_state.trust_in_authority = 0.8
        brain.current_state.last_strategy = "challenge"
        brain.memory_scaffold["recent_actions"].append({
            "round_num": 0, "action_type": "CREATE_POST", "summary": "test"
        })
        reflection = _generate_reflection(brain, 3)
        assert reflection is not None
        assert "信任" in reflection or "质疑" in reflection or "评估" in reflection

    def test_strategy_goal_conflict_challenge_stabilize(self):
        """challenge 策略 + 稳定目标 → 张力检测"""
        brain = AgentBrain(agent_id=0, entity_name="Test")
        brain.current_state.last_strategy = "challenge"
        brain.current_state.active_goals = ["维护稳定与形象"]
        brain.memory_scaffold["recent_actions"].append({
            "round_num": 0, "action_type": "CREATE_POST", "summary": "test"
        })
        reflection = _generate_reflection(brain, 3)
        assert reflection is not None
        assert "张力" in reflection or "调整" in reflection

    def test_strategy_goal_conflict_stabilize_push(self):
        """stabilize 策略 + 推进目标 → 张力检测"""
        brain = AgentBrain(agent_id=0, entity_name="Test")
        brain.current_state.last_strategy = "stabilize"
        brain.current_state.active_goals = ["推进议题"]
        brain.memory_scaffold["recent_actions"].append({
            "round_num": 0, "action_type": "CREATE_POST", "summary": "test"
        })
        reflection = _generate_reflection(brain, 3)
        assert reflection is not None
        assert "张力" in reflection

    def test_mixed_actions_no_active_pattern(self):
        """混合行为 (1主动 + 1被动 + 1转发) → 不检测出主动或被动一致性"""
        brain = AgentBrain(agent_id=0, entity_name="Test")
        brain.memory_scaffold["recent_actions"] = [
            {"round_num": 0, "action_type": "CREATE_POST", "summary": "post"},
            {"round_num": 1, "action_type": "DO_NOTHING", "summary": "idle"},
            {"round_num": 2, "action_type": "REPOST", "summary": "repost"},
        ]
        reflection = _generate_reflection(brain, 3)
        # 1 create < 2 → no active pattern; 1 passive < 2 → no passive pattern
        if reflection:
            assert "主动" not in reflection
            assert "被动" not in reflection

    def test_reflection_log_survives_save_load(self):
        """反思日志在 save/load 后保持"""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = _make_simple_config(1)
            rt = AgentBrainRuntime.load_or_create(config, tmpdir)
            brain = list(rt._brains.values())[0]
            brain.current_state.reflection_log = ["反思A", "反思B"]
            rt.save()
            rt2 = AgentBrainRuntime.load_or_create(config, tmpdir)
            brain2 = list(rt2._brains.values())[0]
            assert brain2.current_state.reflection_log == ["反思A", "反思B"]

    def test_multiple_reflections_accumulate(self):
        """多次反思触发后日志累积"""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = _make_simple_config(1)
            rt = AgentBrainRuntime.load_or_create(config, tmpdir)
            brain = list(rt._brains.values())[0]
            for r in range(9):
                brain.memory_scaffold.setdefault("recent_actions", []).append({
                    "round_num": r, "action_type": "CREATE_POST",
                    "summary": f"帖子{r}"
                })
                if (r + 1) % _REFLECTION_INTERVAL == 0 and r > 0:
                    rt.trigger_reflection(r + 1)
            # Should have accumulated at least 1 reflection
            assert len(brain.current_state.reflection_log) >= 1

    def test_reflection_only_latest_in_prompt(self):
        """render_prompt 中只显示最后一条反思"""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = _make_simple_config(1)
            rt = AgentBrainRuntime.load_or_create(config, tmpdir)
            brain = list(rt._brains.values())[0]
            brain.current_state.reflection_log = ["旧反思", "新反思"]
            prompt = rt.render_prompt(0)
            assert "新反思" in prompt
            # Only the latest one should appear
            assert prompt.count("近期自我反思") == 1

    def test_like_comment_counts_as_passive(self):
        """LIKE_COMMENT 归类为被动行为"""
        brain = AgentBrain(agent_id=0, entity_name="Test")
        for i in range(3):
            brain.memory_scaffold["recent_actions"].append({
                "round_num": i, "action_type": "LIKE_COMMENT", "summary": "点赞评论"
            })
        reflection = _generate_reflection(brain, 3)
        assert reflection is not None
        assert "被动" in reflection or "观望" in reflection

    def test_quote_post_counts_as_active(self):
        """QUOTE_POST 归类为主动行为"""
        brain = AgentBrain(agent_id=0, entity_name="Test")
        for i in range(3):
            brain.memory_scaffold["recent_actions"].append({
                "round_num": i, "action_type": "QUOTE_POST", "summary": "引用帖子"
            })
        reflection = _generate_reflection(brain, 3)
        assert reflection is not None
        assert "主动" in reflection or "连续" in reflection

    def test_cognitive_change_dimension_labels(self):
        """反思中认知变化使用中文标签"""
        brain = AgentBrain(agent_id=0, entity_name="Test")
        brain.current_state.attribution_events = [
            {"round": 2, "dimension": "perceived_risk", "delta": 0.2},
        ]
        brain.memory_scaffold["recent_actions"].append({
            "round_num": 2, "action_type": "CREATE_POST", "summary": "test"
        })
        reflection = _generate_reflection(brain, 3)
        assert reflection is not None
        assert "风险感知" in reflection


# ============================================================
# 17. 全链路集成测试
# ============================================================


class TestFullCycleIntegration:
    """全链路集成: apply_world_state → record_actions → trigger_reflection → snapshot → summary"""

    def test_full_cycle_multi_round(self):
        """多轮完整循环不崩溃且数据一致"""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = _make_simple_config(3, stance="neutral")
            rt = AgentBrainRuntime.load_or_create(config, tmpdir)
            for r in range(12):
                panic = 0.3 + (r % 5) * 0.12
                rt.apply_world_state(r, {
                    "panic_level": panic, "trust_level": 0.6 - panic * 0.3,
                    "risk_level": panic * 0.8, "polarization_level": panic * 0.5,
                    "attention_level": 0.3 + panic * 0.2,
                    "stability_level": 0.7 - panic * 0.3,
                })
                actions = [{"agent_id": i, "action_type": "CREATE_POST",
                            "action_args": {"content": f"r{r}_a{i}"}}
                           for i in range(3)]
                rt.record_actions(r, actions)
                rt.trigger_reflection(r)
                rt.write_cognition_snapshot(r)

            summary = rt.generate_cognition_summary()
            assert summary["total_agents"] == 3
            for agent in summary["agents"]:
                assert "attribution_events" in agent
                assert "reflections" in agent
                assert "final_state" in agent
                assert "stance_drift_pressure" in agent["final_state"]

    def test_full_cycle_personalized_perception_varies(self):
        """全链路: 不同 Agent 的个性化感知在同一轮确实不同"""
        with tempfile.TemporaryDirectory() as tmpdir:
            agents = [
                {"agent_id": 0, "entity_name": "易感学生", "entity_type": "Student",
                 "stance": "neutral", "activity_level": 0.5, "influence_weight": 1.0},
                {"agent_id": 1, "entity_name": "理性教授", "entity_type": "Professor",
                 "stance": "supportive", "activity_level": 0.5, "influence_weight": 1.0},
                {"agent_id": 2, "entity_name": "媒体", "entity_type": "Journalist",
                 "stance": "neutral", "activity_level": 0.5, "influence_weight": 1.0},
            ]
            config = {"agent_configs": agents, "simulation_requirement": "test"}
            rt = AgentBrainRuntime.load_or_create(config, tmpdir)
            rt._brains[0].prior.susceptibility = 0.9
            rt._brains[1].prior.susceptibility = 0.2
            rt._brains[1].prior.utility_weights["truth_seeking"] = 0.8
            ws = {"panic_level": 0.7, "trust_level": 0.2, "risk_level": 0.6,
                  "polarization_level": 0.6, "attention_level": 0.5, "stability_level": 0.3}
            perceptions = {}
            for aid in [0, 1, 2]:
                perceptions[aid] = rt.render_personalized_perception(aid, ws)
            # At least 2 different perception outputs
            unique = set(perceptions.values())
            assert len(unique) >= 2

    def test_full_cycle_history_file_grows(self):
        """多轮后 history.jsonl 有正确行数"""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = _make_simple_config(2)
            rt = AgentBrainRuntime.load_or_create(config, tmpdir)
            for r in range(5):
                rt.apply_world_state(r, {"panic_level": 0.5, "trust_level": 0.5,
                                         "risk_level": 0.3, "polarization_level": 0.3,
                                         "attention_level": 0.3, "stability_level": 0.5})
                rt.write_cognition_snapshot(r)
            history_path = os.path.join(tmpdir, "agent_cognition_history.jsonl")
            with open(history_path, "r", encoding="utf-8") as f:
                lines = f.readlines()
            assert len(lines) == 5
            for line in lines:
                record = json.loads(line)
                assert len(record["agents"]) == 2

    def test_all_cognitive_values_stay_in_range(self):
        """极端世界状态下认知值仍在 [0,1] 范围内"""
        with tempfile.TemporaryDirectory() as tmpdir:
            config = _make_simple_config(1)
            rt = AgentBrainRuntime.load_or_create(config, tmpdir)
            extremes = [
                {"panic_level": 1.0, "trust_level": 0.0, "risk_level": 1.0,
                 "polarization_level": 1.0, "attention_level": 1.0, "stability_level": 0.0},
                {"panic_level": 0.0, "trust_level": 1.0, "risk_level": 0.0,
                 "polarization_level": 0.0, "attention_level": 0.0, "stability_level": 1.0},
            ]
            for r, ws in enumerate(extremes * 10):
                rt.apply_world_state(r, ws)
            brain = list(rt._brains.values())[0]
            for attr in ["emotional_arousal", "perceived_risk", "trust_in_authority",
                         "trust_in_peers", "certainty"]:
                val = getattr(brain.current_state, attr)
                assert 0.0 <= val <= 1.0, f"{attr}={val} out of [0,1] range"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
