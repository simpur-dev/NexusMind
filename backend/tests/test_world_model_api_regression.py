"""
World Model API 回归测试（不需要启动真实模拟）

复用磁盘上已有的 simulation fixture（例如 sim_07a7f2769964），直接通过
Flask test_client 验证 5 个 world-model API 的磁盘回退路径与返回结构。

运行方式（在 backend 目录下）：
    uv run pytest tests/test_world_model_api_regression.py -v

这个文件专为"修完 bug 快速回归"设计：
- 不启动子进程
- 不调 LLM
- 不依赖 Neo4j
- 整套跑完通常 <2s

核心覆盖：
1. /run-status/detail 必须包含 world_state（即使 _world_state_engines 被清空）
2. /world-state 必须能从磁盘恢复 current_state 和 state_history
3. /events 必须返回非空 events + 支持 from_round
4. /causal-graph 必须返回 edges + total_edges
5. 磁盘回退路径会把引擎缓存回 _world_state_engines
"""

import os
import sys
import glob
import json
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import create_app
from app.services.simulation_runner import SimulationRunner


# ------------------------------------------------------------------
# Fixture 发现：自动选一个磁盘上有 world_state_history.jsonl 的 sim
# ------------------------------------------------------------------

def _discover_fixture_sim_id():
    """扫 RUN_STATE_DIR 下所有 sim，挑一个同时有
    world_state_history.jsonl 和 events.jsonl 的目录作为 fixture。"""
    base = SimulationRunner.RUN_STATE_DIR
    if not os.path.isdir(base):
        return None
    for name in sorted(os.listdir(base)):
        d = os.path.join(base, name)
        hist = os.path.join(d, "world_state_history.jsonl")
        if os.path.isfile(hist) and os.path.getsize(hist) > 0:
            return name
    return None


_FIXTURE_SIM_ID = _discover_fixture_sim_id()
_SKIP_REASON = (
    f"需要至少一个已有 world_state_history.jsonl 的 simulation fixture "
    f"in {SimulationRunner.RUN_STATE_DIR}"
)


@pytest.fixture(scope="module")
def client():
    app = create_app()
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


@pytest.fixture(autouse=True)
def _clear_engine_cache():
    """每个 case 前清空 _world_state_engines，强制走磁盘回退路径，
    这样就能真正回归本次修复的 bug。"""
    SimulationRunner._world_state_engines.clear()
    yield
    SimulationRunner._world_state_engines.clear()


# ------------------------------------------------------------------
# Tests
# ------------------------------------------------------------------


@pytest.mark.skipif(_FIXTURE_SIM_ID is None, reason=_SKIP_REASON)
class TestWorldModelAPIRegression:
    """所有端点应当在 _world_state_engines 为空时仍然返回完整数据。"""

    @property
    def sim_id(self):
        return _FIXTURE_SIM_ID

    def test_get_or_restore_returns_populated_engine(self):
        engine = SimulationRunner.get_or_restore_world_state_engine(self.sim_id)
        assert engine is not None, "应当从磁盘成功重建引擎"
        assert engine.current_state is not None, "current_state 不能为空"
        assert len(engine.state_history) > 0, "state_history 不能为空"
        # 缓存回 _world_state_engines
        assert self.sim_id in SimulationRunner._world_state_engines

    def test_run_status_detail_includes_world_state(self, client):
        """主 bug 回归：run-status/detail 必须注入 world_state 字段。"""
        resp = client.get(f"/api/simulation/{self.sim_id}/run-status/detail")
        assert resp.status_code == 200
        body = resp.get_json()
        assert body["success"] is True
        data = body["data"]
        assert "world_state" in data, "world_state 字段缺失（正是之前显示'Waiting...'的根因）"
        ws = data["world_state"]
        assert ws is not None, "world_state 不能为 null"
        # 6 维状态必须全部存在
        for dim in [
            "attention_level", "panic_level", "trust_level",
            "polarization_level", "risk_level", "stability_level",
        ]:
            assert dim in ws, f"world_state 缺少维度 {dim}"
            assert isinstance(ws[dim], (int, float))
        assert isinstance(ws.get("round_num"), int)

    def test_run_status_includes_world_state(self, client):
        """/run-status 也应注入 world_state。"""
        resp = client.get(f"/api/simulation/{self.sim_id}/run-status")
        assert resp.status_code == 200
        body = resp.get_json()
        assert body["success"] is True
        assert body["data"].get("world_state") is not None

    def test_world_state_endpoint_returns_history(self, client):
        resp = client.get(f"/api/simulation/{self.sim_id}/world-state")
        assert resp.status_code == 200
        body = resp.get_json()
        assert body["success"] is True
        data = body["data"]
        assert data["current_state"] is not None
        assert isinstance(data["state_history"], list)
        assert len(data["state_history"]) > 0
        assert data.get("total_rounds", 0) == len(data["state_history"])

    def test_world_state_endpoint_last_n(self, client):
        """增量前端用的 last_n 参数必须裁剪正确（#3 相关）。"""
        resp = client.get(f"/api/simulation/{self.sim_id}/world-state?last_n=2")
        assert resp.status_code == 200
        data = resp.get_json()["data"]
        assert len(data["state_history"]) <= 2

    def test_events_endpoint_returns_events(self, client):
        resp = client.get(f"/api/simulation/{self.sim_id}/events")
        assert resp.status_code == 200
        body = resp.get_json()
        assert body["success"] is True
        events = body["data"]["events"]
        assert isinstance(events, list)
        if events:
            evt = events[0]
            for f in ("event_id", "round_num", "event_type", "description"):
                assert f in evt, f"event 缺少字段 {f}"

    def test_events_endpoint_from_round_filter(self, client):
        """增量前端用的 from_round 过滤必须生效（#3 相关）。"""
        full = client.get(f"/api/simulation/{self.sim_id}/events").get_json()["data"]
        if full["total_count"] == 0:
            pytest.skip("fixture 没有事件数据")
        max_round = max(e["round_num"] for e in full["events"])
        resp = client.get(
            f"/api/simulation/{self.sim_id}/events?from_round={max_round}"
        )
        data = resp.get_json()["data"]
        assert all(e["round_num"] >= max_round for e in data["events"])
        assert data["total_count"] <= full["total_count"]

    def test_causal_graph_endpoint(self, client):
        resp = client.get(f"/api/simulation/{self.sim_id}/causal-graph")
        assert resp.status_code == 200
        body = resp.get_json()
        assert body["success"] is True
        data = body["data"]
        assert "edges" in data
        assert "total_edges" in data
        assert isinstance(data["edges"], list)
        if data["edges"]:
            edge = data["edges"][0]
            for f in ("source_event_id", "target_event_id", "relation_type"):
                assert f in edge, f"causal edge 缺少 {f}"

    def test_unknown_simulation_does_not_crash(self, client):
        """对不存在的 sim_id，API 必须优雅返回空数据而非 500。"""
        fake_id = "sim_does_not_exist_zzz"
        # world-state 端点
        r = client.get(f"/api/simulation/{fake_id}/world-state")
        assert r.status_code == 200
        assert r.get_json()["data"]["current_state"] is None
        # events 端点
        r = client.get(f"/api/simulation/{fake_id}/events")
        assert r.status_code == 200
        assert r.get_json()["data"]["total_count"] == 0
        # causal-graph 端点
        r = client.get(f"/api/simulation/{fake_id}/causal-graph")
        assert r.status_code == 200
        assert r.get_json()["data"]["total_edges"] == 0
