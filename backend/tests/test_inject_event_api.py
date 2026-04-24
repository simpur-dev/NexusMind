"""
动态事件注入 API + SimulationRunner 层单元测试（模块3）

覆盖:
1. SimulationRunner.inject_event 参数传递与结果包装
2. inject-event API 端点参数验证
3. inject-event API 端点正常调用
4. inject-event API 端点错误处理
"""

import os
import sys
import json
import pytest
from unittest.mock import patch, MagicMock

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from app.services.simulation_runner import SimulationRunner
    from app.services.simulation_ipc import IPCResponse, CommandStatus
    _HAS_RUNNER = True
except ImportError:
    _HAS_RUNNER = False

try:
    from app import create_app
    _HAS_APP = True
except Exception:
    _HAS_APP = False


# ============================================================
# §1 SimulationRunner.inject_event
# ============================================================

@pytest.mark.skipif(not _HAS_RUNNER, reason="SimulationRunner 导入失败")
class TestSimulationRunnerInjectEvent:
    """测试 SimulationRunner.inject_event 方法"""

    def test_inject_event_success(self, tmp_path):
        """成功注入事件时应返回正确结果"""
        sim_id = "sim_test_inject"
        sim_dir = tmp_path / sim_id
        sim_dir.mkdir()

        mock_response = IPCResponse(
            command_id="cmd_001",
            status=CommandStatus.COMPLETED,
            result={"message": "事件已注入", "queue_size": 1}
        )

        with patch.object(SimulationRunner, 'RUN_STATE_DIR', str(tmp_path)):
            with patch('app.services.simulation_runner.SimulationIPCClient') as MockClient:
                mock_client = MockClient.return_value
                mock_client.check_env_alive.return_value = True
                mock_client.send_inject_event.return_value = mock_response

                result = SimulationRunner.inject_event(
                    simulation_id=sim_id,
                    event_type="breaking_news",
                    description="突发新闻",
                    severity=0.8,
                    affected_variables={"panic_level": 0.2}
                )

        assert result["success"] is True
        assert result["event_type"] == "breaking_news"
        assert result["description"] == "突发新闻"
        assert result["severity"] == 0.8
        assert result["result"]["queue_size"] == 1

    def test_inject_event_env_not_alive(self, tmp_path):
        """环境未运行时应抛出 ValueError"""
        sim_id = "sim_test_dead"
        sim_dir = tmp_path / sim_id
        sim_dir.mkdir()

        with patch.object(SimulationRunner, 'RUN_STATE_DIR', str(tmp_path)):
            with patch('app.services.simulation_runner.SimulationIPCClient') as MockClient:
                mock_client = MockClient.return_value
                mock_client.check_env_alive.return_value = False

                with pytest.raises(ValueError, match="未运行"):
                    SimulationRunner.inject_event(
                        simulation_id=sim_id,
                        event_type="custom",
                        description="测试"
                    )

    def test_inject_event_sim_not_exist(self, tmp_path):
        """模拟不存在时应抛出 ValueError"""
        with patch.object(SimulationRunner, 'RUN_STATE_DIR', str(tmp_path)):
            with pytest.raises(ValueError, match="不存在"):
                SimulationRunner.inject_event(
                    simulation_id="nonexistent",
                    event_type="custom",
                    description="测试"
                )

    def test_inject_event_failed_response(self, tmp_path):
        """IPC 返回失败时结果应包含 error"""
        sim_id = "sim_test_fail"
        sim_dir = tmp_path / sim_id
        sim_dir.mkdir()

        mock_response = IPCResponse(
            command_id="cmd_fail",
            status=CommandStatus.FAILED,
            error="磁盘写入失败"
        )

        with patch.object(SimulationRunner, 'RUN_STATE_DIR', str(tmp_path)):
            with patch('app.services.simulation_runner.SimulationIPCClient') as MockClient:
                mock_client = MockClient.return_value
                mock_client.check_env_alive.return_value = True
                mock_client.send_inject_event.return_value = mock_response

                result = SimulationRunner.inject_event(
                    simulation_id=sim_id,
                    event_type="custom",
                    description="失败测试"
                )

        assert result["success"] is False
        assert "磁盘写入失败" in result["error"]


# ============================================================
# §2 inject-event API 端点
# ============================================================

@pytest.mark.skipif(not _HAS_APP, reason="Flask app 导入失败")
class TestInjectEventAPI:
    """测试 /api/simulation/inject-event 端点"""

    @pytest.fixture
    def client(self):
        app = create_app()
        app.config['TESTING'] = True
        with app.test_client() as c:
            yield c

    def test_missing_simulation_id(self, client):
        """缺少 simulation_id 应返回 400"""
        resp = client.post('/api/simulation/inject-event',
                           json={"event_type": "custom", "description": "test"})
        assert resp.status_code == 400
        data = resp.get_json()
        assert "simulation_id" in data["error"]

    def test_missing_event_type(self, client):
        """缺少 event_type 应返回 400"""
        resp = client.post('/api/simulation/inject-event',
                           json={"simulation_id": "sim_001", "description": "test"})
        assert resp.status_code == 400
        data = resp.get_json()
        assert "event_type" in data["error"]

    def test_missing_description(self, client):
        """缺少 description 应返回 400"""
        resp = client.post('/api/simulation/inject-event',
                           json={"simulation_id": "sim_001", "event_type": "custom"})
        assert resp.status_code == 400
        data = resp.get_json()
        assert "description" in data["error"]

    def test_successful_inject(self, client):
        """完整参数应成功调用 SimulationRunner.inject_event"""
        mock_result = {
            "success": True,
            "event_type": "breaking_news",
            "description": "突发新闻",
            "severity": 0.8,
            "result": {"message": "事件已注入", "queue_size": 1},
            "timestamp": "2026-01-01T00:00:00"
        }

        with patch.object(SimulationRunner, 'inject_event', return_value=mock_result):
            resp = client.post('/api/simulation/inject-event', json={
                "simulation_id": "sim_001",
                "event_type": "breaking_news",
                "description": "突发新闻",
                "severity": 0.8,
                "affected_variables": {"panic_level": 0.2}
            })

        assert resp.status_code == 200
        data = resp.get_json()
        assert data["success"] is True
        assert data["data"]["event_type"] == "breaking_news"

    def test_env_not_alive_returns_400(self, client):
        """环境未运行时应返回 400"""
        with patch.object(SimulationRunner, 'inject_event',
                          side_effect=ValueError("模拟环境未运行")):
            resp = client.post('/api/simulation/inject-event', json={
                "simulation_id": "sim_001",
                "event_type": "custom",
                "description": "测试"
            })

        assert resp.status_code == 400
        data = resp.get_json()
        assert "未运行" in data["error"]

    def test_timeout_returns_504(self, client):
        """超时应返回 504"""
        with patch.object(SimulationRunner, 'inject_event',
                          side_effect=TimeoutError("等待超时")):
            resp = client.post('/api/simulation/inject-event', json={
                "simulation_id": "sim_001",
                "event_type": "custom",
                "description": "测试"
            })

        assert resp.status_code == 504


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
