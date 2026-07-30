"""
tests/test_server.py — Unit tests for the FastAPI server and endpoints.
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import sys
from fastapi.testclient import TestClient

# Ensure the project root is on sys.path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from agent.server import app, task_manager, approval_manager, monitor
from agent.tasks import TaskStatus
from agent.approval import ApprovalStatus


@pytest.fixture(autouse=True)
def cleanup_managers():
    """Ensure managers start fresh and store to a temp location during tests."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_tasks = Path(tmpdir) / "tasks.json"
        tmp_approvals = Path(tmpdir) / "approvals.json"
        
        with patch.object(task_manager, "_path", tmp_tasks), \
             patch.object(approval_manager, "_path", tmp_approvals):
            task_manager._tasks = {}
            approval_manager._approvals = {}
            task_manager._save()
            approval_manager._save()
            yield


def test_system_status():
    client = TestClient(app)
    response = client.get("/api/status")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "running"
    assert data["total_tasks"] == 0
    assert data["approvals"]["pending"] == 0


def test_tasks_crud():
    client = TestClient(app)

    # 1. Create task
    payload = {
        "url": "https://books.toscrape.com",
        "selector": ".price_color",
        "task_label": "book_price",
        "interval_seconds": 300
    }
    response = client.post("/api/tasks", json=payload)
    assert response.status_code == 201
    task = response.json()["task"]
    assert task["url"] == payload["url"]
    assert task["selector"] == payload["selector"]
    assert task["task_label"] == payload["task_label"]
    assert task["status"] == "idle"

    task_id = task["id"]

    # 2. Get task
    response = client.get(f"/api/tasks/{task_id}")
    assert response.status_code == 200
    assert response.json()["task"]["id"] == task_id

    # 3. Update task
    update_payload = {"interval_seconds": 600}
    response = client.patch(f"/api/tasks/{task_id}", json=update_payload)
    assert response.status_code == 200
    assert response.json()["task"]["interval_seconds"] == 600

    # 4. Delete task
    response = client.delete(f"/api/tasks/{task_id}")
    assert response.status_code == 200
    assert response.json() == {"deleted": True}

    # 5. Get missing task returns 404
    response = client.get(f"/api/tasks/{task_id}")
    assert response.status_code == 404


def test_approvals_list_and_actions():
    client = TestClient(app)

    # Mock approval creation
    from agent.server import _PROJECT_ROOT
    shot_path = str(_PROJECT_ROOT / "artifacts" / "screenshots" / "shot.png")
    app_req = approval_manager.create(
        task_id="t1",
        url="https://books.toscrape.com",
        task_label="price",
        old_selector=".old",
        new_selector=".new",
        confidence=0.88,
        reasoning="Visual match.",
        screenshot_path=shot_path
    )

    approval_id = app_req["id"]

    # List pending approvals
    response = client.get("/api/approvals?status=pending")
    assert response.status_code == 200
    approvals = response.json()["approvals"]
    assert len(approvals) == 1
    assert approvals[0]["id"] == approval_id
    assert approvals[0]["screenshot_path"] == "/artifacts/screenshots/shot.png"

    # Get single approval
    response = client.get(f"/api/approvals/{approval_id}")
    assert response.status_code == 200
    assert response.json()["approval"]["id"] == approval_id

    # Test rejection
    with patch.object(monitor, "reject_approval", return_value={"status": "rejected"}) as mock_reject:
        response = client.post(f"/api/approvals/{approval_id}/reject")
        assert response.status_code == 200
        mock_reject.assert_called_once_with(approval_id)

    # Test approval
    with patch.object(monitor, "apply_approval", return_value={"status": "approved"}) as mock_approve:
        response = client.post(f"/api/approvals/{approval_id}/approve")
        assert response.status_code == 200
        mock_approve.assert_called_once_with(approval_id)


def test_artifacts_listing():
    client = TestClient(app)

    # Write a mock JSON file in the artifacts directory
    with tempfile.TemporaryDirectory() as tmpdir:
        with patch("agent.server._PROJECT_ROOT", Path(tmpdir)):
            artifacts_dir = Path(tmpdir) / "artifacts"
            artifacts_dir.mkdir()
            
            mock_json = artifacts_dir / "adaptation_plan_test_20260730_120000.json"
            mock_data = {
                "type": "adaptation_plan",
                "timestamp": "20260730_120000",
                "url": "https://example.com",
                "task_label": "test",
                "failed_selector": ".old",
                "screenshot_path": str(artifacts_dir / "screenshots" / "shot.png")
            }
            mock_json.write_text(json.dumps(mock_data), encoding="utf-8")

            # Request artifacts listing via test server
            response = client.get("/api/artifacts")
            assert response.status_code == 200
            artifacts = response.json()["artifacts"]
            assert len(artifacts) == 1
            assert artifacts[0]["type"] == "adaptation_plan"
            assert artifacts[0]["screenshot_path"] == "/artifacts/screenshots/shot.png"
