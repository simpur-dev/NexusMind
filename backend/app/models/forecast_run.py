"""
预测分支管理
支持同一事件下创建多个预测分支、干预方案对比
"""

import os
import json
import uuid
from datetime import datetime
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from ..config import Config


@dataclass
class ForecastRun:
    """一次预测运行 / 分支"""
    run_id: str
    project_id: str
    baseline_id: str
    created_at: str

    # 分支信息
    parent_run_id: Optional[str] = None
    branch_type: str = "base"  # base | intervention_a | intervention_b | intervention_c
    branch_label: Optional[str] = None

    # 关联的底层模拟
    simulation_id: Optional[str] = None
    graph_id: Optional[str] = None

    # 状态
    status: str = "created"  # created | preparing | running | completed | failed
    forecast_horizon_hours: int = 168  # 默认预测 7 天
    completed_at: Optional[str] = None

    # 干预方案描述（如果是干预分支）
    intervention_plan: Optional[Dict[str, Any]] = None

    # 完成后的概述
    summary: Optional[str] = None
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "run_id": self.run_id,
            "project_id": self.project_id,
            "baseline_id": self.baseline_id,
            "created_at": self.created_at,
            "parent_run_id": self.parent_run_id,
            "branch_type": self.branch_type,
            "branch_label": self.branch_label,
            "simulation_id": self.simulation_id,
            "graph_id": self.graph_id,
            "status": self.status,
            "forecast_horizon_hours": self.forecast_horizon_hours,
            "completed_at": self.completed_at,
            "intervention_plan": self.intervention_plan,
            "summary": self.summary,
            "error": self.error,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ForecastRun":
        return cls(
            run_id=data["run_id"],
            project_id=data["project_id"],
            baseline_id=data["baseline_id"],
            created_at=data.get("created_at", ""),
            parent_run_id=data.get("parent_run_id"),
            branch_type=data.get("branch_type", "base"),
            branch_label=data.get("branch_label"),
            simulation_id=data.get("simulation_id"),
            graph_id=data.get("graph_id"),
            status=data.get("status", "created"),
            forecast_horizon_hours=data.get("forecast_horizon_hours", 168),
            completed_at=data.get("completed_at"),
            intervention_plan=data.get("intervention_plan"),
            summary=data.get("summary"),
            error=data.get("error"),
        )


class ForecastRunManager:
    """
    预测分支管理器

    目录结构：
        uploads/projects/<project_id>/
          forecast_runs/
            <run_id>.json
    """

    RUNS_SUBDIR = "forecast_runs"

    @classmethod
    def _runs_dir(cls, project_id: str) -> str:
        return os.path.join(Config.UPLOAD_FOLDER, "projects", project_id, cls.RUNS_SUBDIR)

    @classmethod
    def _run_path(cls, project_id: str, run_id: str) -> str:
        return os.path.join(cls._runs_dir(project_id), f"{run_id}.json")

    @classmethod
    def _ensure_dir(cls, project_id: str) -> None:
        os.makedirs(cls._runs_dir(project_id), exist_ok=True)

    # ── 公共 API ──

    @classmethod
    def create_run(
        cls,
        project_id: str,
        baseline_id: str,
        *,
        branch_type: str = "base",
        branch_label: Optional[str] = None,
        parent_run_id: Optional[str] = None,
        forecast_horizon_hours: int = 168,
        intervention_plan: Optional[Dict[str, Any]] = None,
    ) -> ForecastRun:
        cls._ensure_dir(project_id)

        run_id = f"run_{uuid.uuid4().hex[:12]}"
        now = datetime.now().isoformat()

        run = ForecastRun(
            run_id=run_id,
            project_id=project_id,
            baseline_id=baseline_id,
            created_at=now,
            branch_type=branch_type,
            branch_label=branch_label,
            parent_run_id=parent_run_id,
            forecast_horizon_hours=forecast_horizon_hours,
            intervention_plan=intervention_plan,
        )

        cls.save_run(run)
        return run

    @classmethod
    def save_run(cls, run: ForecastRun) -> None:
        cls._ensure_dir(run.project_id)
        path = cls._run_path(run.project_id, run.run_id)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(run.to_dict(), f, ensure_ascii=False, indent=2)

    @classmethod
    def get_run(cls, project_id: str, run_id: str) -> Optional[ForecastRun]:
        path = cls._run_path(project_id, run_id)
        if not os.path.exists(path):
            return None
        with open(path, "r", encoding="utf-8") as f:
            return ForecastRun.from_dict(json.load(f))

    @classmethod
    def list_runs(cls, project_id: str) -> List[ForecastRun]:
        """返回按创建时间正序排列的分支列表。"""
        rdir = cls._runs_dir(project_id)
        if not os.path.exists(rdir):
            return []
        result: List[ForecastRun] = []
        for fname in os.listdir(rdir):
            if not fname.endswith(".json"):
                continue
            fpath = os.path.join(rdir, fname)
            with open(fpath, "r", encoding="utf-8") as f:
                result.append(ForecastRun.from_dict(json.load(f)))
        result.sort(key=lambda r: r.created_at)
        return result

    @classmethod
    def delete_run(cls, project_id: str, run_id: str) -> bool:
        """删除指定预测分支文件，返回是否成功。"""
        path = cls._run_path(project_id, run_id)
        if os.path.exists(path):
            os.remove(path)
            return True
        return False

    @classmethod
    def list_runs_for_baseline(cls, project_id: str, baseline_id: str) -> List[ForecastRun]:
        return [r for r in cls.list_runs(project_id) if r.baseline_id == baseline_id]

    @classmethod
    def compare_runs(cls, project_id: str, run_ids: List[str]) -> Dict[str, Any]:
        """
        对比多个预测分支的元信息。
        实际趋势/状态对比需要调用 SimulationInsightService，此处仅返回分支元信息。
        """
        runs = []
        for rid in run_ids:
            run = cls.get_run(project_id, rid)
            if run:
                runs.append(run.to_dict())
        return {
            "count": len(runs),
            "runs": runs,
        }
