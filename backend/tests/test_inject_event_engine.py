"""
WorldStateEngine 注入事件消费单元测试（模块5）

覆盖:
1. _consume_injected_events 基本消费
2. 状态变量增量正确应用
3. 增量钳制在 [0, 1]
4. 队列消费后被清空
5. 无效变量名被忽略
6. 空队列/无文件不报错
7. update_state 集成测试：注入事件出现在返回的事件列表中
8. 多事件批量消费
"""

import os
import sys
import json
import shutil
import tempfile
import pytest

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.world_state import WorldStateEngine, WorldStateSnapshot, WorldEvent


class TestConsumeInjectedEvents:
    """测试 _consume_injected_events 方法"""

    @pytest.fixture
    def engine(self):
        d = tempfile.mkdtemp(prefix="nexusmind_wse_inject_test_")
        e = WorldStateEngine(sim_dir=d, use_llm=False)
        yield e
        shutil.rmtree(d, ignore_errors=True)

    def _write_queue(self, engine, events):
        with open(engine.injected_events_path, 'w', encoding='utf-8') as f:
            json.dump(events, f, ensure_ascii=False)

    def test_no_file_returns_empty(self, engine):
        """无队列文件时返回空列表"""
        state = WorldStateSnapshot(round_num=1, timestamp="t")
        result = engine._consume_injected_events(1, state)
        assert result == []

    def test_empty_queue_returns_empty(self, engine):
        """空队列返回空列表"""
        self._write_queue(engine, [])
        state = WorldStateSnapshot(round_num=1, timestamp="t")
        result = engine._consume_injected_events(1, state)
        assert result == []

    def test_single_event_consumed(self, engine):
        """单个事件正确消费并转换为 WorldEvent"""
        self._write_queue(engine, [{
            "event_type": "breaking_news",
            "description": "突发新闻",
            "severity": 0.8,
            "affected_variables": {"panic_level": 0.2},
            "source": "god_mode",
            "timestamp": "2026-01-01T00:00:00"
        }])

        state = WorldStateSnapshot(round_num=3, timestamp="t", panic_level=0.3)
        events = engine._consume_injected_events(3, state)

        assert len(events) == 1
        evt = events[0]
        assert evt.event_type == "injected_breaking_news"
        assert "[上帝视角]" in evt.description
        assert evt.severity == 0.8
        assert evt.round_num == 3
        assert evt.affected_variables == {"panic_level": 0.2}

    def test_state_delta_applied(self, engine):
        """affected_variables 增量正确应用到状态"""
        self._write_queue(engine, [{
            "event_type": "custom",
            "description": "test",
            "severity": 0.5,
            "affected_variables": {
                "panic_level": 0.15,
                "trust_level": -0.2,
                "attention_level": 0.1
            }
        }])

        state = WorldStateSnapshot(
            round_num=1, timestamp="t",
            panic_level=0.3, trust_level=0.6, attention_level=0.2
        )
        engine._consume_injected_events(1, state)

        assert abs(state.panic_level - 0.45) < 1e-9
        assert abs(state.trust_level - 0.4) < 1e-9
        assert abs(state.attention_level - 0.3) < 1e-9

    def test_state_clamped_high(self, engine):
        """增量后值超过 1.0 应钳制"""
        self._write_queue(engine, [{
            "event_type": "custom",
            "description": "test",
            "severity": 0.5,
            "affected_variables": {"panic_level": 0.8}
        }])

        state = WorldStateSnapshot(round_num=1, timestamp="t", panic_level=0.5)
        engine._consume_injected_events(1, state)
        assert state.panic_level == 1.0

    def test_state_clamped_low(self, engine):
        """增量后值低于 0.0 应钳制"""
        self._write_queue(engine, [{
            "event_type": "custom",
            "description": "test",
            "severity": 0.5,
            "affected_variables": {"trust_level": -0.8}
        }])

        state = WorldStateSnapshot(round_num=1, timestamp="t", trust_level=0.3)
        engine._consume_injected_events(1, state)
        assert state.trust_level == 0.0

    def test_queue_cleared_after_consumption(self, engine):
        """消费后队列应被清空"""
        self._write_queue(engine, [{
            "event_type": "custom",
            "description": "test",
            "severity": 0.5,
            "affected_variables": {}
        }])

        state = WorldStateSnapshot(round_num=1, timestamp="t")
        engine._consume_injected_events(1, state)

        with open(engine.injected_events_path, 'r') as f:
            remaining = json.load(f)
        assert remaining == []

    def test_invalid_variable_names_ignored(self, engine):
        """无效的状态变量名应被忽略"""
        self._write_queue(engine, [{
            "event_type": "custom",
            "description": "test",
            "severity": 0.5,
            "affected_variables": {
                "nonexistent_var": 0.5,
                "panic_level": 0.1
            }
        }])

        state = WorldStateSnapshot(round_num=1, timestamp="t", panic_level=0.2)
        events = engine._consume_injected_events(1, state)

        # panic_level 应被应用
        assert abs(state.panic_level - 0.3) < 1e-9
        # 只有 panic_level 出现在 applied_deltas 中
        assert "nonexistent_var" not in events[0].affected_variables
        assert events[0].affected_variables == {"panic_level": 0.1}

    def test_multiple_events_batch(self, engine):
        """多个注入事件批量消费"""
        self._write_queue(engine, [
            {
                "event_type": "breaking_news",
                "description": "事件1",
                "severity": 0.6,
                "affected_variables": {"panic_level": 0.1}
            },
            {
                "event_type": "official_statement",
                "description": "事件2",
                "severity": 0.4,
                "affected_variables": {"trust_level": 0.15}
            },
            {
                "event_type": "rumor_spread",
                "description": "事件3",
                "severity": 0.9,
                "affected_variables": {"panic_level": 0.2, "trust_level": -0.1}
            }
        ])

        state = WorldStateSnapshot(
            round_num=5, timestamp="t",
            panic_level=0.2, trust_level=0.5
        )
        events = engine._consume_injected_events(5, state)

        assert len(events) == 3
        # panic: 0.2 + 0.1 + 0.2 = 0.5
        assert abs(state.panic_level - 0.5) < 1e-9
        # trust: 0.5 + 0.15 - 0.1 = 0.55
        assert abs(state.trust_level - 0.55) < 1e-9

    def test_corrupted_queue_returns_empty(self, engine):
        """损坏的队列文件返回空列表"""
        with open(engine.injected_events_path, 'w') as f:
            f.write("{corrupted")

        state = WorldStateSnapshot(round_num=1, timestamp="t")
        result = engine._consume_injected_events(1, state)
        assert result == []

    def test_no_tmp_residue(self, engine):
        """消费后无 .tmp 文件残留"""
        self._write_queue(engine, [{
            "event_type": "custom",
            "description": "test",
            "severity": 0.5,
            "affected_variables": {}
        }])

        state = WorldStateSnapshot(round_num=1, timestamp="t")
        engine._consume_injected_events(1, state)

        tmp_path = engine.injected_events_path + ".tmp"
        assert not os.path.exists(tmp_path)


class TestUpdateStateWithInjection:
    """测试 update_state 集成注入事件"""

    @pytest.fixture
    def engine(self):
        d = tempfile.mkdtemp(prefix="nexusmind_wse_update_inject_test_")
        e = WorldStateEngine(sim_dir=d, use_llm=False)
        yield e
        shutil.rmtree(d, ignore_errors=True)

    def _write_queue(self, engine, events):
        with open(engine.injected_events_path, 'w', encoding='utf-8') as f:
            json.dump(events, f, ensure_ascii=False)

    def test_injected_events_in_update_result(self, engine):
        """update_state 返回的事件列表应包含注入事件"""
        self._write_queue(engine, [{
            "event_type": "breaking_news",
            "description": "集成测试事件",
            "severity": 0.8,
            "affected_variables": {"panic_level": 0.3}
        }])

        # 提供一些 agent 动作
        actions = [
            {"agent_id": 0, "action_type": "CREATE_POST",
             "action_args": {"content": "Hello world"}},
        ]

        new_state, new_events = engine.update_state(round_num=1, actions=actions)

        # 至少有注入事件
        injected = [e for e in new_events if e.event_type.startswith("injected_")]
        assert len(injected) >= 1
        assert injected[0].event_type == "injected_breaking_news"
        assert "[上帝视角]" in injected[0].description

    def test_injected_deltas_reflected_in_state(self, engine):
        """注入事件的增量应反映在 update_state 返回的状态中"""
        # 先做一轮建立基线
        engine.update_state(round_num=0, actions=[])

        self._write_queue(engine, [{
            "event_type": "policy_change",
            "description": "新政策",
            "severity": 0.6,
            "affected_variables": {"trust_level": 0.25}
        }])

        state_before_trust = engine.current_state.trust_level if engine.current_state else 0.6
        new_state, _ = engine.update_state(round_num=1, actions=[])

        # trust_level 应比基线高约 0.25（可能有规则引擎的小调整）
        # 但至少比之前的基线高
        assert new_state.trust_level > state_before_trust

    def test_queue_empty_after_update(self, engine):
        """update_state 后队列应为空"""
        self._write_queue(engine, [{
            "event_type": "custom",
            "description": "测试",
            "severity": 0.5,
            "affected_variables": {}
        }])

        engine.update_state(round_num=1, actions=[])

        with open(engine.injected_events_path, 'r') as f:
            remaining = json.load(f)
        assert remaining == []


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
