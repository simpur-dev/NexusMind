"""
事实基线版本管理
每次追加材料后可生成新的基线快照，支持版本对比
"""

import os
import json
import uuid
from datetime import datetime
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from ..config import Config


@dataclass
class BaselineSnapshot:
    """一次事实基线快照"""
    baseline_id: str
    project_id: str
    created_at: str

    # 构建来源
    based_on_material_ids: List[str] = field(default_factory=list)
    previous_baseline_id: Optional[str] = None

    # 结构化事实摘要
    current_stage: Optional[str] = None             # 事件当前阶段描述
    confirmed_facts: List[str] = field(default_factory=list)
    unconfirmed_claims: List[str] = field(default_factory=list)
    key_actors: List[Dict[str, str]] = field(default_factory=list)  # [{name, role, stance}]
    key_topics: List[str] = field(default_factory=list)
    open_questions: List[str] = field(default_factory=list)
    current_risks: List[str] = field(default_factory=list)
    recommended_monitoring_signals: List[str] = field(default_factory=list)

    # 材料驱动的事件因果图
    event_causal_graph: Optional[Dict[str, Any]] = None

    # 关联的图谱
    graph_id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "baseline_id": self.baseline_id,
            "project_id": self.project_id,
            "created_at": self.created_at,
            "based_on_material_ids": self.based_on_material_ids,
            "previous_baseline_id": self.previous_baseline_id,
            "current_stage": self.current_stage,
            "confirmed_facts": self.confirmed_facts,
            "unconfirmed_claims": self.unconfirmed_claims,
            "key_actors": self.key_actors,
            "key_topics": self.key_topics,
            "open_questions": self.open_questions,
            "current_risks": self.current_risks,
            "recommended_monitoring_signals": self.recommended_monitoring_signals,
            "event_causal_graph": self.event_causal_graph,
            "graph_id": self.graph_id,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "BaselineSnapshot":
        return cls(
            baseline_id=data["baseline_id"],
            project_id=data["project_id"],
            created_at=data.get("created_at", ""),
            based_on_material_ids=data.get("based_on_material_ids", []),
            previous_baseline_id=data.get("previous_baseline_id"),
            current_stage=data.get("current_stage"),
            confirmed_facts=data.get("confirmed_facts", []),
            unconfirmed_claims=data.get("unconfirmed_claims", []),
            key_actors=data.get("key_actors", []),
            key_topics=data.get("key_topics", []),
            open_questions=data.get("open_questions", []),
            current_risks=data.get("current_risks", []),
            recommended_monitoring_signals=data.get("recommended_monitoring_signals", []),
            event_causal_graph=data.get("event_causal_graph"),
            graph_id=data.get("graph_id"),
        )


class BaselineManager:
    """
    基线管理器

    目录结构：
        uploads/projects/<project_id>/
          baselines/
            <baseline_id>.json
    """

    BASELINES_SUBDIR = "baselines"

    @classmethod
    def _baselines_dir(cls, project_id: str) -> str:
        return os.path.join(Config.UPLOAD_FOLDER, "projects", project_id, cls.BASELINES_SUBDIR)

    @classmethod
    def _baseline_path(cls, project_id: str, baseline_id: str) -> str:
        return os.path.join(cls._baselines_dir(project_id), f"{baseline_id}.json")

    @classmethod
    def _ensure_dir(cls, project_id: str) -> None:
        os.makedirs(cls._baselines_dir(project_id), exist_ok=True)

    # ── 公共 API ──

    @classmethod
    def create_baseline(
        cls,
        project_id: str,
        *,
        based_on_material_ids: List[str],
        previous_baseline_id: Optional[str] = None,
        current_stage: Optional[str] = None,
        confirmed_facts: Optional[List[str]] = None,
        unconfirmed_claims: Optional[List[str]] = None,
        key_actors: Optional[List[Dict[str, str]]] = None,
        key_topics: Optional[List[str]] = None,
        open_questions: Optional[List[str]] = None,
        current_risks: Optional[List[str]] = None,
        recommended_monitoring_signals: Optional[List[str]] = None,
        event_causal_graph: Optional[Dict[str, Any]] = None,
        graph_id: Optional[str] = None,
    ) -> BaselineSnapshot:
        cls._ensure_dir(project_id)

        baseline_id = f"bl_{uuid.uuid4().hex[:12]}"
        now = datetime.now().isoformat()

        snapshot = BaselineSnapshot(
            baseline_id=baseline_id,
            project_id=project_id,
            created_at=now,
            based_on_material_ids=based_on_material_ids,
            previous_baseline_id=previous_baseline_id,
            current_stage=current_stage,
            confirmed_facts=confirmed_facts or [],
            unconfirmed_claims=unconfirmed_claims or [],
            key_actors=key_actors or [],
            key_topics=key_topics or [],
            open_questions=open_questions or [],
            current_risks=current_risks or [],
            recommended_monitoring_signals=recommended_monitoring_signals or [],
            event_causal_graph=event_causal_graph,
            graph_id=graph_id,
        )

        path = cls._baseline_path(project_id, baseline_id)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(snapshot.to_dict(), f, ensure_ascii=False, indent=2)

        return snapshot

    @classmethod
    def get_baseline(cls, project_id: str, baseline_id: str) -> Optional[BaselineSnapshot]:
        path = cls._baseline_path(project_id, baseline_id)
        if not os.path.exists(path):
            return None
        with open(path, "r", encoding="utf-8") as f:
            return BaselineSnapshot.from_dict(json.load(f))

    @classmethod
    def list_baselines(cls, project_id: str) -> List[BaselineSnapshot]:
        """返回按创建时间正序排列的基线列表。"""
        bdir = cls._baselines_dir(project_id)
        if not os.path.exists(bdir):
            return []
        result: List[BaselineSnapshot] = []
        for fname in os.listdir(bdir):
            if not fname.endswith(".json"):
                continue
            fpath = os.path.join(bdir, fname)
            with open(fpath, "r", encoding="utf-8") as f:
                result.append(BaselineSnapshot.from_dict(json.load(f)))
        result.sort(key=lambda b: b.created_at)
        return result

    @classmethod
    def get_latest_baseline(cls, project_id: str) -> Optional[BaselineSnapshot]:
        baselines = cls.list_baselines(project_id)
        return baselines[-1] if baselines else None

    @classmethod
    def save_baseline(cls, snapshot: BaselineSnapshot) -> None:
        """保存/覆盖一个已存在的基线快照。"""
        cls._ensure_dir(snapshot.project_id)
        path = cls._baseline_path(snapshot.project_id, snapshot.baseline_id)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(snapshot.to_dict(), f, ensure_ascii=False, indent=2)

    @classmethod
    def delete_baseline(cls, project_id: str, baseline_id: str) -> bool:
        """删除指定基线文件，返回是否成功。"""
        path = cls._baseline_path(project_id, baseline_id)
        if os.path.exists(path):
            os.remove(path)
            return True
        return False

    @classmethod
    def diff_baselines(
        cls,
        project_id: str,
        baseline_a_id: str,
        baseline_b_id: str,
    ) -> Dict[str, Any]:
        """
        对比两个基线版本，返回差异摘要。
        """
        a = cls.get_baseline(project_id, baseline_a_id)
        b = cls.get_baseline(project_id, baseline_b_id)
        if not a or not b:
            return {"error": "基线不存在"}

        def _set_diff(old_list, new_list):
            old_set = set(old_list)
            new_set = set(new_list)
            return {
                "added": sorted(new_set - old_set),
                "removed": sorted(old_set - new_set),
                "unchanged": sorted(old_set & new_set),
            }

        return {
            "baseline_a": baseline_a_id,
            "baseline_b": baseline_b_id,
            "materials_diff": {
                "added": sorted(set(b.based_on_material_ids) - set(a.based_on_material_ids)),
                "removed": sorted(set(a.based_on_material_ids) - set(b.based_on_material_ids)),
            },
            "stage_change": {
                "before": a.current_stage,
                "after": b.current_stage,
            },
            "confirmed_facts_diff": _set_diff(a.confirmed_facts, b.confirmed_facts),
            "unconfirmed_claims_diff": _set_diff(a.unconfirmed_claims, b.unconfirmed_claims),
            "key_topics_diff": _set_diff(a.key_topics, b.key_topics),
            "open_questions_diff": _set_diff(a.open_questions, b.open_questions),
            "current_risks_diff": _set_diff(a.current_risks, b.current_risks),
        }
