"""Agent Brain 冒烟测试 — 验证基本管线可正常运行"""
import sys, os, json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.services.agent_brain import (
    create_agent_brain_profile, AgentBrainRuntime, AgentBrain
)

def test_create_brain_profile():
    bp = create_agent_brain_profile(
        agent_id=0,
        entity_name="武汉大学",
        entity_type="University",
        entity_summary="湖北省武汉市的一所知名高校",
        simulation_requirement="模拟高校舆情事件",
        activity_config={"stance": "neutral", "activity_level": 0.2, "influence_weight": 3.0},
    )
    assert bp["agent_id"] == 0
    assert bp["prior"]["decision_style"] == "institutional"
    assert bp["prior"]["stance"] == "neutral"
    assert len(bp["prior"]["core_goals"]) >= 2
    assert len(bp["current_state"]["active_goals"]) >= 1
    print("[PASS] create_brain_profile (University)")

    bp2 = create_agent_brain_profile(
        agent_id=1,
        entity_name="张同学",
        entity_type="Student",
        entity_summary="大三学生",
        simulation_requirement="模拟高校舆情事件",
        activity_config={"stance": "opposing", "activity_level": 0.8, "influence_weight": 0.8},
    )
    assert bp2["prior"]["stance"] == "opposing"
    assert bp2["prior"]["entity_type"] == "Student"
    print("[PASS] create_brain_profile (Student opposing)")
    return bp, bp2

def test_runtime(bp, bp2):
    config = {
        "agent_configs": [
            {"agent_id": 0, "entity_name": "武汉大学", "entity_type": "University", "stance": "neutral", "brain_profile": bp},
            {"agent_id": 1, "entity_name": "张同学", "entity_type": "Student", "stance": "opposing", "brain_profile": bp2},
        ]
    }
    rt = AgentBrainRuntime.from_simulation_config(config)
    assert len(rt) == 2
    print(f"[PASS] Runtime loaded {len(rt)} brains")

    # render_prompt
    prompt0 = rt.render_prompt(0)
    assert "武汉大学" in prompt0
    assert "认知框架" in prompt0
    print(f"[PASS] render_prompt agent_0 ({len(prompt0)} chars)")

    # apply_world_state
    rt.apply_world_state(1, {
        "attention_level": 0.7,
        "panic_level": 0.4,
        "trust_level": 0.5,
        "polarization_level": 0.3,
        "risk_level": 0.35,
        "stability_level": 0.6,
    })
    prompt1 = rt.render_prompt(1)
    assert "张同学" in prompt1
    print(f"[PASS] apply_world_state + render_prompt agent_1 ({len(prompt1)} chars)")

    # record_actions
    rt.record_actions(1, [
        {"agent_id": 0, "action_type": "CREATE_POST", "action_args": {"content": "关于近期舆情的官方说明"}},
        {"agent_id": 1, "action_type": "CREATE_COMMENT", "action_args": {"content": "不同意这个说法"}},
    ])
    prompt0_after = rt.render_prompt(0)
    assert "发布帖子" in prompt0_after or "最近动作" in prompt0_after
    print("[PASS] record_actions")

    # serialization roundtrip
    brain_dict = rt._brains[0].to_dict()
    restored = AgentBrain.from_dict(brain_dict)
    assert restored.agent_id == 0
    assert restored.prior.decision_style == "institutional"
    print("[PASS] serialization roundtrip")

def test_prompt_sample():
    """打印一个完整的认知 prompt 样本"""
    bp = create_agent_brain_profile(
        agent_id=5,
        entity_name="李记者",
        entity_type="MediaOutlet",
        entity_summary="知名媒体记者",
        simulation_requirement="模拟高校舆情事件",
        activity_config={"stance": "observer", "activity_level": 0.5, "influence_weight": 2.5},
    )
    config = {"agent_configs": [{"agent_id": 5, "entity_name": "李记者", "entity_type": "MediaOutlet", "stance": "observer", "brain_profile": bp}]}
    rt = AgentBrainRuntime.from_simulation_config(config)
    rt.apply_world_state(3, {
        "attention_level": 0.8,
        "panic_level": 0.5,
        "trust_level": 0.4,
        "polarization_level": 0.45,
        "risk_level": 0.5,
        "stability_level": 0.55,
        "recent_events": [{"description": "媒体曝光新的证据材料"}],
    })
    prompt = rt.render_prompt(5)
    print("\n" + "=" * 60)
    print("Agent Brain Prompt Sample (MediaOutlet, observer, round 3)")
    print("=" * 60)
    print(prompt)
    print("=" * 60)


if __name__ == "__main__":
    bp, bp2 = test_create_brain_profile()
    test_runtime(bp, bp2)
    test_prompt_sample()
    print("\n✅ All Agent Brain smoke tests passed!")
