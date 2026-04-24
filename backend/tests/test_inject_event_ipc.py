"""
动态事件注入 IPC 层单元测试（模块2）

覆盖:
1. CommandType 新增 INJECT_EVENT
2. SimulationIPCClient.send_inject_event 命令写入
3. ParallelIPCHandler.handle_inject_event 事件队列写入
4. 队列累加（多次注入不覆盖）
5. 原子写入（无 .tmp 残留）
6. process_commands 分发到 INJECT_EVENT
7. severity 范围钳制
"""

import os
import sys
import json
import shutil
import tempfile
import pytest
from datetime import datetime
from unittest.mock import patch, MagicMock

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 添加 scripts 路径
_scripts_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts")
sys.path.insert(0, _scripts_dir)

# --- Flask 端 IPC 客户端 ---
try:
    from app.services.simulation_ipc import (
        CommandType as FlaskCommandType,
        SimulationIPCClient,
        IPCResponse,
        CommandStatus,
    )
    _HAS_IPC_CLIENT = True
except ImportError:
    _HAS_IPC_CLIENT = False

# --- 子进程端 IPC 处理器 ---
try:
    from run_parallel_simulation import (
        CommandType as ScriptCommandType,
        ParallelIPCHandler,
        INJECTED_EVENTS_FILE,
    )
    _HAS_IPC_HANDLER = True
except ImportError:
    _HAS_IPC_HANDLER = False


# ============================================================
# §1 CommandType 枚举
# ============================================================

@pytest.mark.skipif(not _HAS_IPC_CLIENT, reason="Flask IPC 模块导入失败")
class TestCommandTypeEnum:
    """验证 CommandType 包含 INJECT_EVENT"""

    def test_flask_command_type_has_inject_event(self):
        assert hasattr(FlaskCommandType, "INJECT_EVENT")
        assert FlaskCommandType.INJECT_EVENT.value == "inject_event"

    def test_all_command_types_present(self):
        expected = {"interview", "batch_interview", "inject_event", "close_env"}
        actual = {ct.value for ct in FlaskCommandType}
        assert expected == actual


@pytest.mark.skipif(not _HAS_IPC_HANDLER, reason="子进程脚本导入失败")
class TestScriptCommandType:
    """验证子进程端 CommandType 也包含 INJECT_EVENT"""

    def test_script_command_type_has_inject_event(self):
        assert hasattr(ScriptCommandType, "INJECT_EVENT")
        assert ScriptCommandType.INJECT_EVENT == "inject_event"


# ============================================================
# §2 SimulationIPCClient.send_inject_event
# ============================================================

@pytest.mark.skipif(not _HAS_IPC_CLIENT, reason="Flask IPC 模块导入失败")
class TestIPCClientInjectEvent:
    """测试 Flask 端事件注入命令写入"""

    @pytest.fixture
    def tmp_sim_dir(self):
        d = tempfile.mkdtemp(prefix="nexusmind_ipc_inject_test_")
        yield d
        shutil.rmtree(d, ignore_errors=True)

    def test_send_inject_event_calls_send_command_correctly(self, tmp_sim_dir):
        """send_inject_event 应以正确参数调用 send_command"""
        client = SimulationIPCClient(tmp_sim_dir)
        mock_response = IPCResponse(
            command_id="test", status=CommandStatus.COMPLETED, result={}
        )

        with patch.object(client, 'send_command', return_value=mock_response) as mock_send:
            client.send_inject_event(
                event_type="breaking_news",
                description="突发：校方发布紧急声明",
                severity=0.8,
                affected_variables={"panic_level": 0.2, "trust_level": -0.1},
            )

            mock_send.assert_called_once()
            call_args = mock_send.call_args
            assert call_args.kwargs["command_type"] == FlaskCommandType.INJECT_EVENT
            args = call_args.kwargs["args"]
            assert args["event_type"] == "breaking_news"
            assert args["description"] == "突发：校方发布紧急声明"
            assert args["severity"] == 0.8
            assert args["affected_variables"]["panic_level"] == 0.2
            assert args["affected_variables"]["trust_level"] == -0.1

    def test_severity_clamped_to_range(self, tmp_sim_dir):
        """severity 超出 [0, 1] 范围时应被钳制"""
        client = SimulationIPCClient(tmp_sim_dir)
        mock_response = IPCResponse(
            command_id="test", status=CommandStatus.COMPLETED, result={}
        )

        with patch.object(client, 'send_command', return_value=mock_response) as mock_send:
            client.send_inject_event("custom", "测试钳制", severity=1.5)
            args = mock_send.call_args.kwargs["args"]
            assert args["severity"] == 1.0

    def test_severity_clamped_negative(self, tmp_sim_dir):
        """负 severity 应被钳制到 0.0"""
        client = SimulationIPCClient(tmp_sim_dir)
        mock_response = IPCResponse(
            command_id="test", status=CommandStatus.COMPLETED, result={}
        )

        with patch.object(client, 'send_command', return_value=mock_response) as mock_send:
            client.send_inject_event("custom", "负值测试", severity=-0.5)
            args = mock_send.call_args.kwargs["args"]
            assert args["severity"] == 0.0

    def test_no_affected_variables_omitted(self, tmp_sim_dir):
        """不传 affected_variables 时不应在 args 中出现"""
        client = SimulationIPCClient(tmp_sim_dir)
        mock_response = IPCResponse(
            command_id="test", status=CommandStatus.COMPLETED, result={}
        )

        with patch.object(client, 'send_command', return_value=mock_response) as mock_send:
            client.send_inject_event("custom", "无变量测试", severity=0.5)
            args = mock_send.call_args.kwargs["args"]
            assert "affected_variables" not in args


# ============================================================
# §3 ParallelIPCHandler.handle_inject_event
# ============================================================

@pytest.mark.skipif(not _HAS_IPC_HANDLER, reason="子进程脚本导入失败")
class TestIPCHandlerInjectEvent:
    """测试子进程端事件注入处理"""

    @pytest.fixture
    def handler(self):
        d = tempfile.mkdtemp(prefix="nexusmind_handler_inject_test_")
        h = ParallelIPCHandler(simulation_dir=d)
        yield h
        shutil.rmtree(d, ignore_errors=True)

    def test_inject_event_creates_queue_file(self, handler):
        """注入事件应创建 injected_events.json"""
        handler.handle_inject_event(
            command_id="cmd_001",
            event_type="breaking_news",
            description="突发新闻测试",
            severity=0.8
        )

        events_path = os.path.join(handler.simulation_dir, INJECTED_EVENTS_FILE)
        assert os.path.exists(events_path)

        with open(events_path, 'r', encoding='utf-8') as f:
            events = json.load(f)

        assert len(events) == 1
        assert events[0]["event_type"] == "breaking_news"
        assert events[0]["description"] == "突发新闻测试"
        assert events[0]["severity"] == 0.8
        assert events[0]["source"] == "god_mode"
        assert "timestamp" in events[0]

    def test_inject_event_accumulates(self, handler):
        """多次注入应累加到队列，不覆盖"""
        handler.handle_inject_event("cmd_001", "breaking_news", "事件1", 0.5)
        handler.handle_inject_event("cmd_002", "official_statement", "事件2", 0.7)
        handler.handle_inject_event("cmd_003", "rumor_spread", "事件3", 0.3)

        events_path = os.path.join(handler.simulation_dir, INJECTED_EVENTS_FILE)
        with open(events_path, 'r', encoding='utf-8') as f:
            events = json.load(f)

        assert len(events) == 3
        assert events[0]["description"] == "事件1"
        assert events[1]["description"] == "事件2"
        assert events[2]["description"] == "事件3"

    def test_inject_event_no_tmp_residue(self, handler):
        """.tmp 临时文件不应残留"""
        handler.handle_inject_event("cmd_001", "custom", "原子写入测试", 0.5)

        tmp_path = os.path.join(handler.simulation_dir, INJECTED_EVENTS_FILE + ".tmp")
        assert not os.path.exists(tmp_path)

    def test_inject_event_sends_success_response(self, handler):
        """应写入成功响应"""
        handler.handle_inject_event("cmd_resp_test", "custom", "响应测试", 0.6)

        response_path = os.path.join(
            handler.simulation_dir, "ipc_responses", "cmd_resp_test.json"
        )
        assert os.path.exists(response_path)

        with open(response_path, 'r', encoding='utf-8') as f:
            resp = json.load(f)

        assert resp["status"] == "completed"
        assert resp["result"]["queue_size"] == 1
        assert resp["result"]["event"]["event_type"] == "custom"

    def test_inject_event_with_affected_variables(self, handler):
        """affected_variables 应正确持久化"""
        handler.handle_inject_event(
            "cmd_vars",
            event_type="policy_change",
            description="新政策发布",
            severity=0.9,
            affected_variables={"panic_level": -0.2, "trust_level": 0.3}
        )

        events_path = os.path.join(handler.simulation_dir, INJECTED_EVENTS_FILE)
        with open(events_path, 'r', encoding='utf-8') as f:
            events = json.load(f)

        assert events[0]["affected_variables"]["panic_level"] == -0.2
        assert events[0]["affected_variables"]["trust_level"] == 0.3

    def test_inject_event_severity_clamped(self, handler):
        """severity 超范围应被钳制"""
        handler.handle_inject_event("cmd_clamp", "custom", "钳制测试", severity=2.0)

        events_path = os.path.join(handler.simulation_dir, INJECTED_EVENTS_FILE)
        with open(events_path, 'r', encoding='utf-8') as f:
            events = json.load(f)

        assert events[0]["severity"] == 1.0

    def test_inject_event_recovers_from_corrupted_queue(self, handler):
        """队列文件损坏时应重建"""
        events_path = os.path.join(handler.simulation_dir, INJECTED_EVENTS_FILE)
        with open(events_path, 'w') as f:
            f.write("{corrupted json")

        handler.handle_inject_event("cmd_recover", "custom", "恢复测试", 0.5)

        with open(events_path, 'r', encoding='utf-8') as f:
            events = json.load(f)

        assert len(events) == 1
        assert events[0]["description"] == "恢复测试"


# ============================================================
# §4 process_commands 分发
# ============================================================

@pytest.mark.skipif(not _HAS_IPC_HANDLER, reason="子进程脚本导入失败")
class TestProcessCommandsDispatch:
    """测试 process_commands 能正确分发 inject_event"""

    @pytest.fixture
    def handler_with_command(self):
        d = tempfile.mkdtemp(prefix="nexusmind_dispatch_test_")
        h = ParallelIPCHandler(simulation_dir=d)
        yield h
        shutil.rmtree(d, ignore_errors=True)

    @pytest.mark.asyncio
    async def test_process_inject_event_command(self, handler_with_command):
        """通过 process_commands 分发 inject_event 命令"""
        handler = handler_with_command
        commands_dir = os.path.join(handler.simulation_dir, "ipc_commands")

        # 手动写入一个 inject_event 命令
        cmd = {
            "command_id": "dispatch_test_001",
            "command_type": "inject_event",
            "args": {
                "event_type": "breaking_news",
                "description": "分发测试：突发新闻",
                "severity": 0.75,
            },
            "timestamp": datetime.now().isoformat()
        }
        with open(os.path.join(commands_dir, "dispatch_test_001.json"), 'w', encoding='utf-8') as f:
            json.dump(cmd, f, ensure_ascii=False, indent=2)

        # 调用 process_commands
        should_continue = await handler.process_commands()
        assert should_continue is True

        # 验证事件已写入队列
        events_path = os.path.join(handler.simulation_dir, INJECTED_EVENTS_FILE)
        assert os.path.exists(events_path)

        with open(events_path, 'r', encoding='utf-8') as f:
            events = json.load(f)

        assert len(events) == 1
        assert events[0]["event_type"] == "breaking_news"
        assert events[0]["description"] == "分发测试：突发新闻"

        # 验证命令文件已被清理
        remaining = [f for f in os.listdir(commands_dir) if f.endswith('.json')]
        assert len(remaining) == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
