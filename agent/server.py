"""
server.py — FastAPI REST API server for the Self-Healing Web Agent.

Exposes endpoints for the dashboard and browser extension to:
  - Manage monitoring tasks (CRUD)
  - View/approve/reject proposed selector changes
  - Trigger immediate scrapes
  - View artifacts and system status

Run with:
    cd agent && uvicorn server:app --reload --port 8000
    # or: python server.py
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

# Ensure project root is on path
_PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from dotenv import load_dotenv
load_dotenv(dotenv_path=_PROJECT_ROOT / ".env")

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from typing import Optional

from agent.tasks import TaskManager
from agent.approval import ApprovalManager
from agent.monitor import MonitorLoop

# ── Path Normalization Utility ────────────────────────────────────────────── #

def _normalize_web_path(path_str: Optional[str]) -> Optional[str]:
    if not path_str:
        return None
    try:
        p = Path(path_str).resolve()
        artifacts_dir = (_PROJECT_ROOT / "artifacts").resolve()
        # Check if the path is relative to artifacts folder
        if p.is_relative_to(artifacts_dir):
            rel = p.relative_to(artifacts_dir)
            return "/artifacts/" + rel.as_posix()
    except Exception:
        pass
    # Fallback pattern match
    normalized = path_str.replace("\\", "/")
    if "/artifacts/" in normalized:
        idx = normalized.index("/artifacts/")
        return normalized[idx:]
    return normalized

def _normalize_approval(approval: Optional[dict]) -> Optional[dict]:
    if not approval:
        return None
    normalized = dict(approval)
    if "screenshot_path" in normalized:
        normalized["screenshot_path"] = _normalize_web_path(normalized["screenshot_path"])
    return normalized

# ── App setup ─────────────────────────────────────────────────────────────── #

app = FastAPI(
    title="Self-Healing Web Agent API",
    description="REST API for managing autonomous self-healing web scrapers",
    version="0.1.0",
)

# Ensure artifacts directory exists and mount it
(_PROJECT_ROOT / "artifacts").mkdir(parents=True, exist_ok=True)
app.mount("/artifacts", StaticFiles(directory=_PROJECT_ROOT / "artifacts"), name="artifacts")
app.mount("/dashboard", StaticFiles(directory=_PROJECT_ROOT / "dashboard", html=True), name="dashboard")

# Allow dashboard and extension origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # MVP: allow all; tighten in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Shared state ──────────────────────────────────────────────────────────── #

task_manager = TaskManager()
approval_manager = ApprovalManager()
monitor = MonitorLoop(
    task_manager=task_manager,
    approval_manager=approval_manager,
    api_key=os.getenv("GOOGLE_API_KEY", ""),
    headless=True,
)

# ── Request/Response models ───────────────────────────────────────────────── #


class CreateTaskRequest(BaseModel):
    url: str
    selector: str
    task_label: str
    interval_seconds: int = Field(default=300, ge=10, le=86400)


class UpdateTaskRequest(BaseModel):
    url: Optional[str] = None
    selector: Optional[str] = None
    task_label: Optional[str] = None
    interval_seconds: Optional[int] = None


# ── Lifecycle events ──────────────────────────────────────────────────────── #


@app.on_event("startup")
async def startup():
    """Start the background monitoring loop on server boot."""
    monitor.start()


@app.on_event("shutdown")
async def shutdown():
    monitor.stop()


# ── Status endpoint ───────────────────────────────────────────────────────── #


@app.get("/api/status")
async def get_status():
    """System health and summary stats."""
    tasks = task_manager.list_all()
    approval_stats = approval_manager.stats()
    return {
        "status": "running",
        "monitor_active": monitor.is_running,
        "total_tasks": len(tasks),
        "tasks_by_status": _count_by_status(tasks),
        "approvals": approval_stats,
        "total_heals": sum(t.get("healed_count", 0) for t in tasks),
    }


def _count_by_status(tasks: list[dict]) -> dict:
    counts = {}
    for t in tasks:
        s = t.get("status", "unknown")
        counts[s] = counts.get(s, 0) + 1
    return counts


# ── Task endpoints ────────────────────────────────────────────────────────── #


@app.get("/api/tasks")
async def list_tasks():
    """List all monitoring tasks."""
    return {"tasks": task_manager.list_all()}


@app.post("/api/tasks", status_code=201)
async def create_task(req: CreateTaskRequest):
    """Create a new monitoring task."""
    task = task_manager.create(
        url=req.url,
        selector=req.selector,
        task_label=req.task_label,
        interval_seconds=req.interval_seconds,
    )
    return {"task": task}


@app.get("/api/tasks/{task_id}")
async def get_task(task_id: str):
    """Get a specific task by ID."""
    task = task_manager.get(task_id)
    if not task:
        raise HTTPException(404, "Task not found")
    return {"task": task}


@app.patch("/api/tasks/{task_id}")
async def update_task(task_id: str, req: UpdateTaskRequest):
    """Update fields on a task."""
    updates = {k: v for k, v in req.model_dump().items() if v is not None}
    task = task_manager.update(task_id, **updates)
    if not task:
        raise HTTPException(404, "Task not found")
    return {"task": task}


@app.delete("/api/tasks/{task_id}")
async def delete_task(task_id: str):
    """Delete a monitoring task."""
    if not task_manager.delete(task_id):
        raise HTTPException(404, "Task not found")
    return {"deleted": True}


@app.post("/api/tasks/{task_id}/run")
async def run_task(task_id: str):
    """Trigger an immediate scrape for a task."""
    task = monitor.run_single_task(task_id)
    if not task:
        raise HTTPException(404, "Task not found")
    return {"task": task}


# ── Approval endpoints ───────────────────────────────────────────────────── #


@app.get("/api/approvals")
async def list_approvals(status: Optional[str] = None):
    """List all approval requests, optionally filtered by status."""
    from agent.approval import ApprovalStatus
    status_filter = None
    if status:
        try:
            status_filter = ApprovalStatus(status)
        except ValueError:
            raise HTTPException(400, f"Invalid status: {status}")
    return {"approvals": [_normalize_approval(a) for a in approval_manager.list_all(status_filter=status_filter)]}


@app.get("/api/approvals/{approval_id}")
async def get_approval(approval_id: str):
    approval = approval_manager.get(approval_id)
    if not approval:
        raise HTTPException(404, "Approval not found")
    return {"approval": _normalize_approval(approval)}


@app.post("/api/approvals/{approval_id}/approve")
async def approve_change(approval_id: str):
    """
    Approve a proposed selector change.
    This updates the task's selector and persists it to the learning store.
    """
    result = monitor.apply_approval(approval_id)
    if not result:
        raise HTTPException(404, "Approval not found or already resolved")
    return {"approval": _normalize_approval(result), "message": "Change approved and applied."}


@app.post("/api/approvals/{approval_id}/reject")
async def reject_change(approval_id: str):
    """Reject a proposed selector change."""
    result = monitor.reject_approval(approval_id)
    if not result:
        raise HTTPException(404, "Approval not found or already resolved")
    return {"approval": _normalize_approval(result), "message": "Change rejected."}


# ── Artifacts endpoint ────────────────────────────────────────────────────── #


@app.get("/api/artifacts")
async def list_artifacts():
    """List generated artifact files (adaptation plans + verifications)."""
    artifact_dir = _PROJECT_ROOT / "artifacts"
    if not artifact_dir.exists():
        return {"artifacts": []}

    artifacts = []
    for f in sorted(artifact_dir.glob("*.json"), reverse=True):
        try:
            import json
            data = json.loads(f.read_text(encoding="utf-8"))
            data["filename"] = f.name
            if "screenshot_path" in data:
                data["screenshot_path"] = _normalize_web_path(data["screenshot_path"])
            artifacts.append(data)
        except Exception:
            continue

    return {"artifacts": artifacts[:50]}  # cap at 50


# ── Run directly ──────────────────────────────────────────────────────────── #


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "server:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )
