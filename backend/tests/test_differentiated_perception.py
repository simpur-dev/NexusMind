"""
差异化感知单元测试（模块1）

覆盖:
1. _load_agent_role_map 解析
2. build_world_state_prompt 差异化行为
3. 向后兼容性
4. _STANCE_PERCEPTION_PROFILES 完整性
5. 阻尼机制在差异化场景中的保持
"""

import os
import sys
import pytest

# 添加 scripts 路径
_scripts_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts")
sys.path.insert(0, _scripts_dir)

try:
    from run_parallel_simulation import (
        build_world_state_prompt,
        _load_agent_role_map,
        _STANCE_PERCEPTION_PROFILES,
    )
    _HAS_SCRIPT = True
except ImportError:
    _HAS_SCRIPT = False


@pytest.mark.skipif(not _HAS_SCRIPT, reason="OASIS 依赖未安装")
class TestDifferentiatedPerception:
    """测试不同立场的 Agent 对同一世界状态的差异化感知"""

    # 共用的"高偏离"世界状态数据（确保通过阻尼检查）
    HIGH_DEVIATION_STATE = {
        "state_summary_text": "当前环境状态：舆论高度关注",
        "attention_level": 0.8,
        "panic_level": 0.6,
        "trust_level": 0.2,
        "polarization_level": 0.5,
        "recent_events": [
            {"event_type": "heat_spike", "description": "热度急升", "severity": 0.7},
            {"event_type": "minor_rumor", "description": "小道消息流传", "severity": 0.35},
            {"event_type": "trust_drop", "description": "信任崩塌", "severity": 0.45},
            {"event_type": "official_silence", "description": "官方沉默引发猜测", "severity": 0.55},
        ],
    }

    # =============== _load_agent_role_map ===============

    def test_load_role_map_basic(self):
        """应正确解析 agent_configs 中的 entity_type 和 stance"""
        config = {
            "agent_configs": [
                {"agent_id": 0, "entity_type": "Student", "stance": "opposing"},
                {"agent_id": 1, "entity_type": "Official", "stance": "supportive"},
                {"agent_id": 2, "entity_type": "Media", "stance": "observer"},
            ]
        }
        role_map = _load_agent_role_map(config)
        assert len(role_map) == 3
        assert role_map[0]["stance"] == "opposing"
        assert role_map[1]["entity_type"] == "Official"
        assert role_map[2]["stance"] == "observer"

    def test_load_role_map_defaults(self):
        """缺少 stance/entity_type 时应回退到默认值"""
        config = {"agent_configs": [{"agent_id": 5}]}
        role_map = _load_agent_role_map(config)
        assert role_map[5]["stance"] == "neutral"
        assert role_map[5]["entity_type"] == "Unknown"

    def test_load_role_map_empty(self):
        """空 agent_configs 应返回空字典"""
        assert _load_agent_role_map({}) == {}
        assert _load_agent_role_map({"agent_configs": []}) == {}

    # =============== 向后兼容 ===============

    def test_backward_compat_no_role(self):
        """不传 agent_role 时应与 v1 行为一致（neutral 默认）"""
        prompt_no_role = build_world_state_prompt(self.HIGH_DEVIATION_STATE)
        prompt_neutral = build_world_state_prompt(
            self.HIGH_DEVIATION_STATE,
            agent_role={"entity_type": "Unknown", "stance": "neutral"}
        )
        assert prompt_no_role == prompt_neutral

    def test_backward_compat_none_role(self):
        """agent_role=None 时应与无参调用一致"""
        prompt_none = build_world_state_prompt(self.HIGH_DEVIATION_STATE, agent_role=None)
        prompt_bare = build_world_state_prompt(self.HIGH_DEVIATION_STATE)
        assert prompt_none == prompt_bare

    # =============== 差异化事件过滤 ===============

    def test_opposing_sees_more_events(self):
        """opposing 立场（阈值 0.4）应比 neutral（阈值 0.5）看到更多事件"""
        prompt_opposing = build_world_state_prompt(
            self.HIGH_DEVIATION_STATE,
            agent_role={"entity_type": "Student", "stance": "opposing"}
        )
        prompt_neutral = build_world_state_prompt(
            self.HIGH_DEVIATION_STATE,
            agent_role={"entity_type": "Citizen", "stance": "neutral"}
        )
        # severity=0.45 的事件：opposing 看得到，neutral 看不到
        assert "信任崩塌" in prompt_opposing
        assert "信任崩塌" not in prompt_neutral

    def test_supportive_sees_fewer_events(self):
        """supportive 立场（阈值 0.6）应过滤更多事件"""
        prompt_supportive = build_world_state_prompt(
            self.HIGH_DEVIATION_STATE,
            agent_role={"entity_type": "Official", "stance": "supportive"}
        )
        # severity=0.55 的事件被过滤（阈值0.6）
        assert "官方沉默引发猜测" not in prompt_supportive
        # severity=0.7 的事件仍然可见
        assert "热度急升" in prompt_supportive

    def test_observer_sees_most_events(self):
        """observer 立场（阈值 0.35）应看到几乎所有事件"""
        prompt_observer = build_world_state_prompt(
            self.HIGH_DEVIATION_STATE,
            agent_role={"entity_type": "Media", "stance": "observer"}
        )
        assert "小道消息流传" in prompt_observer
        assert "热度急升" in prompt_observer
        assert "信任崩塌" in prompt_observer
        assert "官方沉默引发猜测" in prompt_observer

    def test_all_stances_filter_very_low_severity(self):
        """所有立场都不应看到 severity < 0.35 的事件"""
        ws = dict(self.HIGH_DEVIATION_STATE)
        ws["recent_events"] = [
            {"event_type": "noise", "description": "微弱噪声", "severity": 0.1},
        ]
        for stance in ["supportive", "opposing", "observer", "neutral"]:
            prompt = build_world_state_prompt(
                ws, agent_role={"entity_type": "Any", "stance": stance}
            )
            assert "微弱噪声" not in prompt

    # =============== 差异化感知提示 ===============

    def test_opposing_has_perspective_hint(self):
        """opposing 应包含情感侧重提示"""
        prompt = build_world_state_prompt(
            self.HIGH_DEVIATION_STATE,
            agent_role={"entity_type": "Student", "stance": "opposing"}
        )
        assert "不满" in prompt or "质疑" in prompt

    def test_supportive_has_perspective_hint(self):
        """supportive 应包含理性/建设性提示"""
        prompt = build_world_state_prompt(
            self.HIGH_DEVIATION_STATE,
            agent_role={"entity_type": "Official", "stance": "supportive"}
        )
        assert "理性" in prompt or "建设性" in prompt

    def test_observer_has_perspective_hint(self):
        """observer 应包含旁观者/发酵提示"""
        prompt = build_world_state_prompt(
            self.HIGH_DEVIATION_STATE,
            agent_role={"entity_type": "Media", "stance": "observer"}
        )
        assert "旁观者" in prompt or "发酵" in prompt

    def test_neutral_has_no_perspective_hint(self):
        """neutral 不应包含额外感知提示"""
        prompt = build_world_state_prompt(
            self.HIGH_DEVIATION_STATE,
            agent_role={"entity_type": "Citizen", "stance": "neutral"}
        )
        assert "不满" not in prompt
        assert "理性" not in prompt
        assert "旁观者" not in prompt

    # =============== 阻尼机制 ===============

    def test_calm_state_returns_empty_for_all_stances(self):
        """平静状态下所有立场都不应注入"""
        calm_state = {
            "state_summary_text": "平静",
            "attention_level": 0.1,
            "panic_level": 0.1,
            "trust_level": 0.6,
            "polarization_level": 0.1,
            "recent_events": [],
        }
        for stance in ["supportive", "opposing", "observer", "neutral"]:
            prompt = build_world_state_prompt(
                calm_state, agent_role={"entity_type": "Any", "stance": stance}
            )
            assert prompt == "", f"stance={stance} 在平静状态下不应注入"

    # =============== _STANCE_PERCEPTION_PROFILES 完整性 ===============

    def test_perception_profiles_cover_all_stances(self):
        """感知配置应覆盖所有四种立场"""
        expected = {"supportive", "opposing", "observer", "neutral"}
        assert set(_STANCE_PERCEPTION_PROFILES.keys()) == expected

    def test_perception_profiles_have_required_keys(self):
        """每个感知配置应包含必需字段"""
        required_keys = {"focus_dims", "suppress_dims", "event_severity_threshold", "perspective_hint"}
        for stance, profile in _STANCE_PERCEPTION_PROFILES.items():
            for key in required_keys:
                assert key in profile, f"stance={stance} 缺少字段: {key}"

    def test_event_threshold_ordering(self):
        """事件阈值应满足: observer < opposing < neutral ≤ supportive"""
        t = {s: _STANCE_PERCEPTION_PROFILES[s]["event_severity_threshold"]
             for s in _STANCE_PERCEPTION_PROFILES}
        assert t["observer"] < t["opposing"]
        assert t["opposing"] < t["neutral"]
        assert t["neutral"] <= t["supportive"]

    # =============== 未知立场降级 ===============

    def test_unknown_stance_falls_back_to_neutral(self):
        """未知立场应退化为 neutral 行为"""
        prompt_unknown = build_world_state_prompt(
            self.HIGH_DEVIATION_STATE,
            agent_role={"entity_type": "Alien", "stance": "unknown_stance"}
        )
        prompt_neutral = build_world_state_prompt(
            self.HIGH_DEVIATION_STATE,
            agent_role={"entity_type": "Alien", "stance": "neutral"}
        )
        assert prompt_unknown == prompt_neutral

    # =============== 各立场输出不同 ===============

    def test_different_stances_produce_different_prompts(self):
        """至少 supportive 和 opposing 的 prompt 应不同"""
        prompt_s = build_world_state_prompt(
            self.HIGH_DEVIATION_STATE,
            agent_role={"entity_type": "A", "stance": "supportive"}
        )
        prompt_o = build_world_state_prompt(
            self.HIGH_DEVIATION_STATE,
            agent_role={"entity_type": "A", "stance": "opposing"}
        )
        assert prompt_s != prompt_o, "不同立场应产生不同的 prompt"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
