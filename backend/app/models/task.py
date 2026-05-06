"""
In-memory task status model and thread-safe task registry.
"""

import threading
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, Any, Optional


class TaskStatus(str, Enum):
    """Task lifecycle status."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class Task:
    """Serializable task record."""
    task_id: str
    task_type: str
    status: TaskStatus
    created_at: datetime
    updated_at: datetime
    progress: int = 0
    message: str = ""
    result: Optional[Dict] = None
    error: Optional[str] = None
    metadata: Dict = field(default_factory=dict)
    progress_detail: Dict = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "task_id": self.task_id,
            "task_type": self.task_type,
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "progress": self.progress,
            "message": self.message,
            "progress_detail": self.progress_detail,
            "result": self.result,
            "error": self.error,
            "metadata": self.metadata,
        }


class TaskManager:
    """Thread-safe singleton task manager."""

    _instance = None
    _instance_lock = threading.Lock()

    def __new__(cls):
        with cls._instance_lock:
            if cls._instance is None:
                instance = super().__new__(cls)
                instance._tasks: Dict[str, Task] = {}
                instance._task_lock = threading.RLock()
                cls._instance = instance
        return cls._instance

    @staticmethod
    def _new_id() -> str:
        return str(uuid.uuid4())

    @staticmethod
    def _now() -> datetime:
        return datetime.now()

    def _snapshot(self, tasks):
        return [task.to_dict() for task in sorted(tasks, key=lambda item: item.created_at, reverse=True)]

    def create_task(self, task_type: str, metadata: Optional[Dict] = None) -> str:
        task_id = self._new_id()
        now = self._now()
        task = Task(
            task_id=task_id,
            task_type=task_type,
            status=TaskStatus.PENDING,
            created_at=now,
            updated_at=now,
            metadata=metadata or {},
        )
        with self._task_lock:
            self._tasks[task_id] = task
        return task_id

    def get_task(self, task_id: str) -> Optional[Task]:
        with self._task_lock:
            return self._tasks.get(task_id)

    def update_task(
        self,
        task_id: str,
        status: Optional[TaskStatus] = None,
        progress: Optional[int] = None,
        message: Optional[str] = None,
        result: Optional[Dict] = None,
        error: Optional[str] = None,
        progress_detail: Optional[Dict] = None
    ):
        updates = {
            "status": status,
            "progress": progress,
            "message": message,
            "result": result,
            "error": error,
            "progress_detail": progress_detail,
        }
        with self._task_lock:
            task = self._tasks.get(task_id)
            if task is None:
                return
            task.updated_at = self._now()
            for key, value in updates.items():
                if value is not None:
                    setattr(task, key, value)

    def complete_task(self, task_id: str, result: Dict):
        self.update_task(
            task_id,
            status=TaskStatus.COMPLETED,
            progress=100,
            message="Task completed",
            result=result,
        )

    def fail_task(self, task_id: str, error: str):
        self.update_task(
            task_id,
            status=TaskStatus.FAILED,
            message="Task failed",
            error=error,
        )

    def list_tasks(self, task_type: Optional[str] = None) -> list:
        with self._task_lock:
            tasks = self._tasks.values()
            if task_type:
                tasks = [task for task in tasks if task.task_type == task_type]
            return self._snapshot(tasks)

    def find_running_task(self, task_type: str, metadata_filter: Optional[Dict] = None) -> Optional[Dict]:
        expected = metadata_filter or {}
        active_status = {TaskStatus.PENDING, TaskStatus.PROCESSING}
        with self._task_lock:
            for task in self._tasks.values():
                if task.task_type != task_type or task.status not in active_status:
                    continue
                if all(task.metadata.get(key) == value for key, value in expected.items()):
                    return task.to_dict()
        return None

    def cleanup_old_tasks(self, max_age_hours: int = 24):
        cutoff = self._now() - timedelta(hours=max_age_hours)
        removable = {TaskStatus.COMPLETED, TaskStatus.FAILED}
        with self._task_lock:
            expired_ids = [
                task_id for task_id, task in self._tasks.items()
                if task.created_at < cutoff and task.status in removable
            ]
            for task_id in expired_ids:
                self._tasks.pop(task_id, None)
