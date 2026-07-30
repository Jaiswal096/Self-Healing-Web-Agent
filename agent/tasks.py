"""
tasks.py — Task CRUD and state management for monitoring jobs.

Each task represents a URL + selector pair that the agent monitors.
Tasks are persisted to agent/data/tasks.json.
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Optional

_TASKS_PATH = Path(__file__).resolve().parent / "data" / "tasks.json"


class TaskStatus(str, Enum):
    IDLE = "idle"
    MONITORING = "monitoring"
    HEALING = "healing"
    PENDING_APPROVAL = "pending_approval"
    ERROR = "error"


class TaskManager:
    """
    Manages the lifecycle of scraping/monitoring tasks.

    Each task dict contains:
        id, url, selector, task_label, status, interval_seconds,
        last_run, last_result, created_at, healed_count
    """

    def __init__(self, store_path: Path | str | None = None):
        self._path = Path(store_path) if store_path else _TASKS_PATH
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._tasks: dict[str, dict] = self._load()

    def _load(self) -> dict:
        if self._path.exists():
            try:
                with open(self._path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                pass
        return {}

    def _save(self) -> None:
        with open(self._path, "w", encoding="utf-8") as f:
            json.dump(self._tasks, f, indent=2, ensure_ascii=False, default=str)

    def create(
        self,
        url: str,
        selector: str,
        task_label: str,
        interval_seconds: int = 300,
    ) -> dict:
        """Create a new monitoring task and return it."""
        task_id = str(uuid.uuid4())[:8]
        task = {
            "id": task_id,
            "url": url,
            "selector": selector,
            "task_label": task_label,
            "status": TaskStatus.IDLE.value,
            "interval_seconds": interval_seconds,
            "last_run": None,
            "last_result": None,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "healed_count": 0,
            "error_message": None,
        }
        self._tasks[task_id] = task
        self._save()
        return task

    def get(self, task_id: str) -> Optional[dict]:
        return self._tasks.get(task_id)

    def list_all(self) -> list[dict]:
        return list(self._tasks.values())

    def update(self, task_id: str, **kwargs) -> Optional[dict]:
        """Update fields on an existing task."""
        task = self._tasks.get(task_id)
        if not task:
            return None
        for key, value in kwargs.items():
            if key in task:
                task[key] = value
        self._save()
        return task

    def delete(self, task_id: str) -> bool:
        if task_id in self._tasks:
            del self._tasks[task_id]
            self._save()
            return True
        return False

    def set_status(self, task_id: str, status: TaskStatus) -> None:
        task = self._tasks.get(task_id)
        if task:
            task["status"] = status.value
            self._save()

    def record_result(
        self,
        task_id: str,
        status: TaskStatus,
        result: dict | None = None,
        error: str | None = None,
    ) -> None:
        """Record the outcome of a scrape attempt."""
        task = self._tasks.get(task_id)
        if task:
            task["status"] = status.value
            task["last_run"] = datetime.now(timezone.utc).isoformat()
            task["last_result"] = result
            task["error_message"] = error
            self._save()

    def increment_healed(self, task_id: str) -> None:
        task = self._tasks.get(task_id)
        if task:
            task["healed_count"] = task.get("healed_count", 0) + 1
            self._save()
