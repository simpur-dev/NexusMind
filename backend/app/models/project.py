"""
Persistent project context model and storage helpers.
"""

import json
import shutil
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Dict, Any, List, Optional

from ..config import Config


class ProjectStatus(str, Enum):
    """Project processing status."""
    CREATED = "created"
    ONTOLOGY_GENERATED = "ontology_generated"
    GRAPH_BUILDING = "graph_building"
    GRAPH_COMPLETED = "graph_completed"
    FAILED = "failed"


@dataclass
class Project:
    """Serializable project state."""
    project_id: str
    name: str
    status: ProjectStatus
    created_at: str
    updated_at: str
    files: List[Dict[str, str]] = field(default_factory=list)
    total_text_length: int = 0
    ontology: Optional[Dict[str, Any]] = None
    analysis_summary: Optional[str] = None
    graph_id: Optional[str] = None
    graph_build_task_id: Optional[str] = None
    simulation_requirement: Optional[str] = None
    chunk_size: int = 500
    chunk_overlap: int = 50
    simulation_id: Optional[str] = None
    report_id: Optional[str] = None
    current_baseline_id: Optional[str] = None
    active_run_id: Optional[str] = None
    materials_count: int = 0
    last_material_at: Optional[str] = None
    incident_mode: str = "demo_workflow"
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        data = self.__dict__.copy()
        data["status"] = self.status.value if isinstance(self.status, ProjectStatus) else self.status
        return data

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Project':
        payload = dict(data)
        status = payload.get('status', ProjectStatus.CREATED.value)
        payload['status'] = ProjectStatus(status) if isinstance(status, str) else status
        payload.setdefault('name', 'Unnamed Project')
        payload.setdefault('created_at', '')
        payload.setdefault('updated_at', '')
        payload.setdefault('files', [])
        payload.setdefault('total_text_length', 0)
        payload.setdefault('chunk_size', 500)
        payload.setdefault('chunk_overlap', 50)
        payload.setdefault('materials_count', 0)
        payload.setdefault('incident_mode', 'demo_workflow')
        allowed = cls.__dataclass_fields__.keys()
        return cls(**{key: payload.get(key) for key in allowed})


class ProjectManager:
    """Project persistence manager."""

    PROJECTS_DIR = str(Path(Config.UPLOAD_FOLDER) / 'projects')

    @classmethod
    def _projects_root(cls) -> Path:
        return Path(cls.PROJECTS_DIR)

    @classmethod
    def _ensure_projects_dir(cls):
        cls._projects_root().mkdir(parents=True, exist_ok=True)

    @classmethod
    def _get_project_dir(cls, project_id: str) -> str:
        return str(cls._projects_root() / project_id)

    @classmethod
    def _get_project_meta_path(cls, project_id: str) -> str:
        return str(Path(cls._get_project_dir(project_id)) / 'project.json')

    @classmethod
    def _get_project_files_dir(cls, project_id: str) -> str:
        return str(Path(cls._get_project_dir(project_id)) / 'files')

    @classmethod
    def _get_project_text_path(cls, project_id: str) -> str:
        return str(Path(cls._get_project_dir(project_id)) / 'extracted_text.txt')

    @classmethod
    def create_project(cls, name: str = "Unnamed Project") -> Project:
        cls._ensure_projects_dir()
        now = datetime.now().isoformat()
        project = Project(
            project_id=f"proj_{uuid.uuid4().hex[:12]}",
            name=name,
            status=ProjectStatus.CREATED,
            created_at=now,
            updated_at=now,
        )
        Path(cls._get_project_files_dir(project.project_id)).mkdir(parents=True, exist_ok=True)
        cls.save_project(project)
        return project

    @classmethod
    def save_project(cls, project: Project) -> None:
        project.updated_at = datetime.now().isoformat()
        meta_path = Path(cls._get_project_meta_path(project.project_id))
        meta_path.parent.mkdir(parents=True, exist_ok=True)
        meta_path.write_text(json.dumps(project.to_dict(), ensure_ascii=False, indent=2), encoding='utf-8')

    @classmethod
    def get_project(cls, project_id: str) -> Optional[Project]:
        meta_path = Path(cls._get_project_meta_path(project_id))
        if not meta_path.exists():
            return None
        data = json.loads(meta_path.read_text(encoding='utf-8'))
        return Project.from_dict(data)

    @classmethod
    def list_projects(cls, limit: int = 50) -> List[Project]:
        cls._ensure_projects_dir()
        projects = [
            project for project in (
                cls.get_project(path.name) for path in cls._projects_root().iterdir() if path.is_dir()
            )
            if project
        ]
        projects.sort(key=lambda p: p.created_at, reverse=True)
        return projects[:limit]

    @classmethod
    def delete_project(cls, project_id: str) -> bool:
        project_dir = Path(cls._get_project_dir(project_id))
        if not project_dir.exists():
            return False
        shutil.rmtree(project_dir)
        return True

    @classmethod
    def save_file_to_project(cls, project_id: str, file_storage, original_filename: str) -> Dict[str, str]:
        files_dir = Path(cls._get_project_files_dir(project_id))
        files_dir.mkdir(parents=True, exist_ok=True)
        ext = Path(original_filename).suffix.lower()
        safe_filename = f"{uuid.uuid4().hex[:8]}{ext}"
        file_path = files_dir / safe_filename
        file_storage.save(str(file_path))
        return {
            "original_filename": original_filename,
            "saved_filename": safe_filename,
            "path": str(file_path),
            "size": file_path.stat().st_size,
        }

    @classmethod
    def save_extracted_text(cls, project_id: str, text: str) -> None:
        text_path = Path(cls._get_project_text_path(project_id))
        text_path.parent.mkdir(parents=True, exist_ok=True)
        text_path.write_text(text, encoding='utf-8')

    @classmethod
    def get_extracted_text(cls, project_id: str) -> Optional[str]:
        text_path = Path(cls._get_project_text_path(project_id))
        return text_path.read_text(encoding='utf-8') if text_path.exists() else None

    @classmethod
    def get_project_files(cls, project_id: str) -> List[str]:
        files_dir = Path(cls._get_project_files_dir(project_id))
        if not files_dir.exists():
            return []
        return [str(path) for path in files_dir.iterdir() if path.is_file()]
