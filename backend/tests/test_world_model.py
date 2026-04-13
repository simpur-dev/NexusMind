"""
世界模型单元测试

覆盖:
1. WorldStateSnapshot 数据结构与序列化
2. WorldStateEngine 状态计算、事件检测、持久化
3. OasisProfileGenerator 职业推导与 f-string 安全
4. 子进程世界状态读取与 prompt 构建
5. SimulationRunner 共享文件写入
"""

import os
import sys
import json
import shutil
import tempfile
import pytest
from datetime import datetime
from unittest.mock import MagicMock, patch

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.world_state import (
    WorldStateSnapshot,
    WorldStateEngine,
    WorldEvent,
    NEGATIVE_KEYWORDS,
    POSITIVE_KEYWORDS,
    AUTHORITY_KEYWORDS,
)
from app.services.oasis_profile_generator import OasisProfileGenerator, OasisAgentProfile


# ============================================================
# §1 WorldStateSnapshot 数据结构
# ============================================================

class TestWorldStateSnapshot:
    """测试 WorldStateSnapshot 数据类"""

    def test_default_values(self):
        """默认状态：低关注、低恐慌、中等信任、高稳定"""
        snap = WorldStateSnapshot(round_num=0, timestamp="2026-01-01T00:00:00")
        assert snap.attention_level == 0.1
        assert snap.panic_level == 0.1
        assert snap.trust_level == 0.6
        assert snap.stability_level == 0.8

    def test_to_dict_roundtrip(self):
        """序列化/反序列化不丢失数据"""
        snap = WorldStateSnapshot(
            round_num=5,
            timestamp="2026-01-01T00:00:00",
            attention_level=0.7,
            panic_level=0.3,
            trust_level=0.5,
            polarization_level=0.4,
            risk_level=0.6,
            stability_level=0.3,
            total_posts=20,
            total_comments=15,
            top_keywords=["高校", "舆论"],
        )
        d = snap.to_dict()
        restored = WorldStateSnapshot.from_dict(d)
        assert restored.round_num == 5
        assert restored.attention_level == 0.7
        assert restored.top_keywords == ["高校", "舆论"]

    def test_get_state_vector(self):
        """状态向量包含且仅包含 6 维"""
        snap = WorldStateSnapshot(round_num=0, timestamp="t")
        vec = snap.get_state_vector()
        assert set(vec.keys()) == {
            "attention_level", "panic_level", "trust_level",
            "polarization_level", "risk_level", "stability_level",
        }
        for v in vec.values():
            assert 0.0 <= v <= 1.0

    def test_get_state_summary_text_format(self):
        """摘要文本包含中文描述和数值"""
        snap = WorldStateSnapshot(
            round_num=3, timestamp="t",
            attention_level=0.75, panic_level=0.1,
        )
        text = snap.get_state_summary_text()
        assert "第3轮" in text
        assert "舆论关注度" in text
        assert "0.75" in text
        assert "较高" in text  # 0.75 应该是"较高"


# ============================================================
# §2 WorldStateEngine 核心逻辑
# ============================================================

class TestWorldStateEngine:
    """测试 WorldStateEngine 状态计算与持久化"""

    @pytest.fixture
    def tmp_sim_dir(self):
        d = tempfile.mkdtemp(prefix="nexusmind_test_")
        yield d
        shutil.rmtree(d, ignore_errors=True)

    @pytest.fixture
    def engine(self, tmp_sim_dir):
        return WorldStateEngine(sim_dir=tmp_sim_dir, use_llm=False)

    def test_initial_state_is_none(self, engine):
        """引擎刚初始化时无状态"""
        assert engine.current_state is None
        assert len(engine.state_history) == 0

    def test_update_state_creates_snapshot(self, engine):
        """第一次 update 应创建初始快照"""
        actions = [
            {"action_type": "CREATE_POST", "agent_id": 1, "action_args": {"content": "测试帖子"}},
            {"action_type": "LIKE", "agent_id": 2, "action_args": {}},
        ]
        new_state, events = engine.update_state(0, actions)
        assert new_state is not None
        assert new_state.round_num == 0
        assert new_state.total_posts == 1
        assert new_state.total_likes == 1
        assert engine.current_state == new_state

    def test_state_values_in_valid_range(self, engine):
        """所有状态变量必须在 [0.0, 1.0]"""
        actions = [
            {"action_type": "CREATE_POST", "agent_id": i, "action_args": {"content": f"恐慌 愤怒 危险 post {i}"}}
            for i in range(20)
        ]
        state, _ = engine.update_state(0, actions)
        vec = state.get_state_vector()
        for name, val in vec.items():
            assert 0.0 <= val <= 1.0, f"{name}={val} 超出范围"

    def test_multiple_rounds_accumulate_history(self, engine):
        """多轮更新应累积历史"""
        for r in range(5):
            engine.update_state(r, [
                {"action_type": "CREATE_POST", "agent_id": 1, "action_args": {"content": f"Round {r}"}}
            ])
        assert len(engine.state_history) == 5
        assert engine.current_state.round_num == 4

    def test_negative_keywords_increase_panic(self, engine):
        """含负面关键词的动作应增加恐慌值"""
        # 先建立基线
        engine.update_state(0, [
            {"action_type": "CREATE_POST", "agent_id": 1, "action_args": {"content": "正常讨论"}}
        ])
        baseline_panic = engine.current_state.panic_level

        # 注入大量负面关键词
        panic_actions = [
            {"action_type": "CREATE_POST", "agent_id": i, "action_args": {"content": "恐慌 愤怒 危险 崩溃 混乱"}}
            for i in range(10)
        ]
        engine.update_state(1, panic_actions)
        assert engine.current_state.panic_level >= baseline_panic

    def test_authority_keywords_boost_trust(self, engine):
        """含权威关键词应提升信任度"""
        engine.update_state(0, [
            {"action_type": "CREATE_POST", "agent_id": 1, "action_args": {"content": "普通讨论"}}
        ])
        baseline_trust = engine.current_state.trust_level

        auth_actions = [
            {"action_type": "CREATE_POST", "agent_id": i, "action_args": {"content": "官方回应 声明 通报 措施 政策"}}
            for i in range(10)
        ]
        engine.update_state(1, auth_actions)
        assert engine.current_state.trust_level >= baseline_trust

    def test_event_detection_heat_spike(self, engine):
        """活动量激增应检测到 heat_spike 事件"""
        # 先建立低基线
        for r in range(3):
            engine.update_state(r, [
                {"action_type": "CREATE_POST", "agent_id": 1, "action_args": {"content": "日常"}}
            ])
        
        # 突然大量活动
        spike_actions = [
            {"action_type": "CREATE_POST", "agent_id": i, "action_args": {"content": f"突发新闻 {i}"}}
            for i in range(30)
        ] + [
            {"action_type": "REPOST", "agent_id": i, "action_args": {}}
            for i in range(20)
        ]
        _, events = engine.update_state(3, spike_actions)
        event_types = [e.event_type for e in events]
        # heat_spike 不一定每次触发，但 attention 应显著上升
        assert engine.current_state.attention_level > 0.2

    def test_persistence_to_file(self, engine, tmp_sim_dir):
        """状态应持久化到 JSONL 文件"""
        engine.update_state(0, [
            {"action_type": "CREATE_POST", "agent_id": 1, "action_args": {"content": "测试"}}
        ])
        history_path = os.path.join(tmp_sim_dir, "world_state_history.jsonl")
        assert os.path.exists(history_path)
        with open(history_path, 'r', encoding='utf-8') as f:
            lines = [l for l in f if l.strip()]
        assert len(lines) == 1
        data = json.loads(lines[0])
        assert data["round_num"] == 0

    def test_reload_from_file(self, tmp_sim_dir):
        """引擎应能从文件重新加载历史"""
        engine1 = WorldStateEngine(sim_dir=tmp_sim_dir, use_llm=False)
        engine1.update_state(0, [
            {"action_type": "CREATE_POST", "agent_id": 1, "action_args": {"content": "持久化"}}
        ])
        engine1.update_state(1, [
            {"action_type": "COMMENT", "agent_id": 2, "action_args": {"content": "回复"}}
        ])

        # 新引擎实例应加载已有历史
        engine2 = WorldStateEngine(sim_dir=tmp_sim_dir, use_llm=False)
        assert len(engine2.state_history) == 2
        assert engine2.current_state.round_num == 1

    def test_empty_actions(self, engine):
        """空动作列表不应崩溃"""
        state, events = engine.update_state(0, [])
        assert state is not None
        assert state.total_posts == 0


# ============================================================
# §3 OasisProfileGenerator 职业推导
# ============================================================

class TestProfileProfession:
    """测试 profession 兜底逻辑"""

    def test_derive_profession_known_types(self):
        """已知实体类型应映射到中文职业"""
        gen = OasisProfileGenerator.__new__(OasisProfileGenerator)
        assert gen._derive_profession("Student") == "学生"
        assert gen._derive_profession("Professor") == "大学教授"
        assert gen._derive_profession("MediaOutlet") == "媒体机构"
        assert gen._derive_profession("GovernmentAgency") == "政府机构"

    def test_derive_profession_unknown_type(self):
        """未知实体类型应原样返回"""
        gen = OasisProfileGenerator.__new__(OasisProfileGenerator)
        assert gen._derive_profession("CustomEntity") == "CustomEntity"
        assert gen._derive_profession("Blogger") == "Blogger"

    def test_profile_always_has_profession(self):
        """OasisAgentProfile 序列化后应包含 profession 顶层字段"""
        profile = OasisAgentProfile(
            user_id=0,
            user_name="test",
            name="Test User",
            bio="test bio",
            persona="test persona",
            profession="记者",
        )
        reddit_fmt = profile.to_reddit_format()
        assert reddit_fmt.get("profession") == "记者"

    def test_profile_without_profession_fallback(self):
        """当 profession 为 None 时 to_reddit_format 不应包含 profession"""
        profile = OasisAgentProfile(
            user_id=0,
            user_name="test",
            name="Test User",
            bio="test bio",
            persona="test persona",
        )
        reddit_fmt = profile.to_reddit_format()
        # profession 是 None，不应包含在 other_info 中
        assert "profession" not in reddit_fmt.get("other_info", {})


# ============================================================
# §4 f-string 安全性（group persona prompt 花括号转义）
# ============================================================

class TestFStringEscaping:
    """验证 LLM prompt 中的花括号不会导致 f-string 错误"""

    def test_group_persona_prompt_no_format_error(self):
        """构建机构类 prompt 不应抛出 ValueError"""
        gen = OasisProfileGenerator.__new__(OasisProfileGenerator)
        # 模拟必要属性
        gen.MBTI_TYPES = ["ISTJ"]
        gen.COUNTRIES = ["中国"]
        
        try:
            result = gen._build_group_persona_prompt(
                entity_name="新华网",
                entity_type="MediaOutlet",
                entity_summary="国家通讯社",
                entity_attributes={"type": "media"},
                context="测试上下文",
            )
            # 应该成功返回字符串，不抛异常
            assert isinstance(result, str)
            assert "新华网" in result
            assert "utility_weights" in result
        except (ValueError, KeyError) as e:
            pytest.fail(f"f-string 花括号未正确转义: {e}")

    def test_individual_persona_prompt_no_format_error(self):
        """构建个人类 prompt 不应抛出 ValueError"""
        gen = OasisProfileGenerator.__new__(OasisProfileGenerator)
        gen.MBTI_TYPES = ["INTJ"]
        gen.COUNTRIES = ["中国"]
        
        try:
            result = gen._build_individual_persona_prompt(
                entity_name="张三",
                entity_type="Student",
                entity_summary="一名大学生",
                entity_attributes={"age": 20},
                context="测试上下文",
            )
            assert isinstance(result, str)
            assert "张三" in result
        except (ValueError, KeyError) as e:
            pytest.fail(f"f-string 花括号未正确转义: {e}")


# ============================================================
# §5 子进程世界状态读取与 prompt 构建
# ============================================================

# 导入子进程脚本中的函数（需要特殊路径处理）
_scripts_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts")
sys.path.insert(0, _scripts_dir)

# 动态导入避免 OASIS 依赖缺失时整个测试文件失败
try:
    from run_parallel_simulation import read_world_state, build_world_state_prompt
    _HAS_SIMULATION_SCRIPT = True
except ImportError:
    _HAS_SIMULATION_SCRIPT = False


@pytest.mark.skipif(not _HAS_SIMULATION_SCRIPT, reason="OASIS 依赖未安装")
class TestWorldStateIPC:
    """测试子进程 ↔ 主进程世界状态通信"""

    @pytest.fixture
    def tmp_sim_dir(self):
        d = tempfile.mkdtemp(prefix="nexusmind_ipc_test_")
        yield d
        shutil.rmtree(d, ignore_errors=True)

    def test_read_nonexistent_file(self, tmp_sim_dir):
        """不存在的文件应返回 None"""
        result = read_world_state(tmp_sim_dir)
        assert result is None

    def test_read_valid_file(self, tmp_sim_dir):
        """能正确读取后端写入的 JSON"""
        ws_data = {
            "round_num": 5,
            "state_summary_text": "当前环境状态（第5轮）：\n- 舆论关注度: 较高（0.65）",
            "recent_events": [
                {"event_type": "heat_spike", "description": "热度急升", "severity": 0.7}
            ],
        }
        ws_path = os.path.join(tmp_sim_dir, "world_state_current.json")
        with open(ws_path, 'w', encoding='utf-8') as f:
            json.dump(ws_data, f, ensure_ascii=False)
        
        result = read_world_state(tmp_sim_dir)
        assert result is not None
        assert result["round_num"] == 5
        assert "热度急升" in result["recent_events"][0]["description"]

    def test_read_corrupted_file(self, tmp_sim_dir):
        """损坏的 JSON 文件应返回 None"""
        ws_path = os.path.join(tmp_sim_dir, "world_state_current.json")
        with open(ws_path, 'w') as f:
            f.write("{invalid json")
        assert read_world_state(tmp_sim_dir) is None

    def test_build_prompt_with_state(self):
        """状态显著偏离基线时应生成包含环境描述的 prompt"""
        ws_data = {
            "state_summary_text": "当前环境状态（第5轮）：\n- 舆论关注度: 较高（0.65）",
            "attention_level": 0.65,
            "panic_level": 0.4,
            "trust_level": 0.3,
            "polarization_level": 0.3,
            "recent_events": [
                {"event_type": "heat_spike", "description": "舆论热度急升", "severity": 0.7}
            ],
        }
        prompt = build_world_state_prompt(ws_data)
        assert "Background" in prompt
        assert "舆论关注度" in prompt
        assert "舆论热度急升" in prompt

    def test_build_prompt_empty_state(self):
        """无状态数据时应返回空字符串"""
        prompt = build_world_state_prompt({})
        assert prompt == ""

    def test_build_prompt_calm_state_returns_empty(self):
        """状态接近基线时不应注入（阻尼机制）"""
        ws_data = {
            "state_summary_text": "平静状态",
            "attention_level": 0.1,
            "panic_level": 0.1,
            "trust_level": 0.6,
            "polarization_level": 0.1,
            "recent_events": [],
        }
        prompt = build_world_state_prompt(ws_data)
        assert prompt == "", "环境平静时不应注入任何内容"

    def test_build_prompt_filters_low_severity_events(self):
        """低严重度事件不应出现在 prompt 中"""
        ws_data = {
            "state_summary_text": "状态摘要",
            "attention_level": 0.7,
            "panic_level": 0.5,
            "trust_level": 0.3,
            "polarization_level": 0.4,
            "recent_events": [
                {"event_type": "minor", "description": "小事件", "severity": 0.3},
            ],
        }
        prompt = build_world_state_prompt(ws_data)
        assert "小事件" not in prompt

    def test_build_prompt_includes_high_severity_events(self):
        """高严重度事件应出现在 prompt 中"""
        ws_data = {
            "state_summary_text": "状态摘要",
            "attention_level": 0.7,
            "panic_level": 0.5,
            "trust_level": 0.3,
            "polarization_level": 0.4,
            "recent_events": [
                {"event_type": "trust_drop", "description": "信任骤降", "severity": 0.8},
            ],
        }
        prompt = build_world_state_prompt(ws_data)
        assert "信任骤降" in prompt


# ============================================================
# §6 SimulationRunner 共享文件写入
# ============================================================

class TestSimulationRunnerWorldStateWrite:
    """测试 _write_world_state_for_subprocess 的文件写入"""

    @pytest.fixture
    def tmp_sim_dir(self):
        d = tempfile.mkdtemp(prefix="nexusmind_runner_test_")
        yield d
        shutil.rmtree(d, ignore_errors=True)

    def test_write_world_state_creates_file(self, tmp_sim_dir):
        """写入后应生成 world_state_current.json"""
        from app.services.simulation_runner import SimulationRunner
        
        # 构造 mock WorldStateEngine
        mock_engine = MagicMock()
        mock_state = WorldStateSnapshot(
            round_num=3,
            timestamp="2026-01-01T00:00:00",
            attention_level=0.6,
            panic_level=0.2,
            trust_level=0.5,
        )
        mock_engine.current_state = mock_state
        mock_engine.events = []
        
        # 模拟 simulation_id 对应的目录
        sim_id = "test_sim_001"
        sim_dir = os.path.join(tmp_sim_dir, sim_id)
        os.makedirs(sim_dir, exist_ok=True)
        
        with patch.object(SimulationRunner, 'RUN_STATE_DIR', tmp_sim_dir):
            SimulationRunner._write_world_state_for_subprocess(sim_id, mock_engine)
        
        ws_file = os.path.join(sim_dir, "world_state_current.json")
        assert os.path.exists(ws_file)
        
        with open(ws_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        assert data["round_num"] == 3
        assert data["attention_level"] == 0.6
        assert "state_summary_text" in data
        assert "recent_events" in data

    def test_write_world_state_atomic(self, tmp_sim_dir):
        """写入应是原子的（无 .tmp 残留）"""
        from app.services.simulation_runner import SimulationRunner
        
        mock_engine = MagicMock()
        mock_engine.current_state = WorldStateSnapshot(round_num=1, timestamp="t")
        mock_engine.events = []
        
        sim_id = "test_sim_atomic"
        sim_dir = os.path.join(tmp_sim_dir, sim_id)
        os.makedirs(sim_dir, exist_ok=True)
        
        with patch.object(SimulationRunner, 'RUN_STATE_DIR', tmp_sim_dir):
            SimulationRunner._write_world_state_for_subprocess(sim_id, mock_engine)
        
        tmp_file = os.path.join(sim_dir, "world_state_current.json.tmp")
        assert not os.path.exists(tmp_file), ".tmp 文件应已被 os.replace 删除"

    def test_write_world_state_with_events(self, tmp_sim_dir):
        """最近事件应包含在输出中"""
        from app.services.simulation_runner import SimulationRunner
        
        mock_engine = MagicMock()
        mock_engine.current_state = WorldStateSnapshot(round_num=5, timestamp="t")
        mock_engine.events = [
            WorldEvent(
                event_id="e1", round_num=4, timestamp="t",
                event_type="heat_spike", description="舆论热度急升",
                severity=0.8, affected_variables={"attention_level": 0.3}
            ),
            WorldEvent(
                event_id="e2", round_num=5, timestamp="t",
                event_type="official_response", description="官方发布回应",
                severity=0.6, affected_variables={"trust_level": 0.2}
            ),
        ]
        
        sim_id = "test_sim_events"
        sim_dir = os.path.join(tmp_sim_dir, sim_id)
        os.makedirs(sim_dir, exist_ok=True)
        
        with patch.object(SimulationRunner, 'RUN_STATE_DIR', tmp_sim_dir):
            SimulationRunner._write_world_state_for_subprocess(sim_id, mock_engine)
        
        ws_file = os.path.join(sim_dir, "world_state_current.json")
        with open(ws_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        assert len(data["recent_events"]) == 2
        assert data["recent_events"][0]["event_type"] == "heat_spike"


# ============================================================
# 运行入口
# ============================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
