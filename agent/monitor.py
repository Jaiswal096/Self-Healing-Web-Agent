"""
monitor.py — 24/7 background monitoring loop.

Runs scraping tasks on configurable intervals, detects failures,
triggers healing, and creates approval requests for proposed changes.
"""

from __future__ import annotations

import asyncio
import os
import sys
import time
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

# Ensure project root is on path for imports from src/
_PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from agent.tasks import TaskManager, TaskStatus
from agent.approval import ApprovalManager, ApprovalStatus

# Conditional import of the core agent (from existing src/)
try:
    from src.agent.core import SelfHealingWebAgent
    from src.agent.browser import BrowserController, SelectorFailedError
    from src.agent.healer import SelectorHealer
    from src.agent.artifacts import ArtifactWriter
    from src.agent.learner import SelectorLearner
    _AGENT_AVAILABLE = True
except ImportError:
    _AGENT_AVAILABLE = False


class MonitorLoop:
    """
    Background monitoring loop that:
    1. Iterates over all active tasks
    2. Runs the scrape for each task at its interval
    3. On selector failure → triggers healing
    4. On healing success → creates an approval request (human-in-the-loop)
    5. On approval → persists the new selector

    Usage::

        monitor = MonitorLoop(task_manager, approval_manager, api_key="...")
        monitor.start()  # runs in background thread
        monitor.stop()
    """

    def __init__(
        self,
        task_manager: TaskManager,
        approval_manager: ApprovalManager,
        api_key: Optional[str] = None,
        headless: bool = True,
        check_interval: int = 10,
    ):
        self._task_mgr = task_manager
        self._approval_mgr = approval_manager
        self._api_key = api_key or os.getenv("GOOGLE_API_KEY", "")
        self._headless = headless
        self._check_interval = check_interval  # seconds between checking if tasks need to run
        self._running = False
        self._thread: Optional[threading.Thread] = None

    @property
    def is_running(self) -> bool:
        return self._running

    def start(self) -> None:
        """Start the monitoring loop in a background thread."""
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True, name="monitor-loop")
        self._thread.start()

    def stop(self) -> None:
        """Stop the monitoring loop."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)

    def _loop(self) -> None:
        """Main monitoring loop — runs continuously until stopped."""
        while self._running:
            try:
                tasks = self._task_mgr.list_all()
                now = datetime.now(timezone.utc)

                for task in tasks:
                    if not self._running:
                        break

                    # Skip tasks that are pending approval or in error
                    if task["status"] in (TaskStatus.PENDING_APPROVAL.value, TaskStatus.ERROR.value):
                        continue

                    # Check if task needs to run based on interval
                    if self._should_run(task, now):
                        self._run_task(task)

            except Exception as exc:
                # Log but don't crash the loop
                print(f"[MonitorLoop] Error in loop iteration: {exc}")

            # Wait before next check
            for _ in range(self._check_interval):
                if not self._running:
                    break
                time.sleep(1)

    def _should_run(self, task: dict, now: datetime) -> bool:
        """Check if a task should be executed based on its interval."""
        last_run = task.get("last_run")
        if not last_run:
            return True  # Never run before
        try:
            last_dt = datetime.fromisoformat(last_run)
            elapsed = (now - last_dt).total_seconds()
            return elapsed >= task.get("interval_seconds", 300)
        except (ValueError, TypeError):
            return True

    def _run_task(self, task: dict) -> None:
        """Execute a single scraping task with healing support."""
        task_id = task["id"]
        url = task["url"]
        selector = task["selector"]
        task_label = task["task_label"]

        self._task_mgr.set_status(task_id, TaskStatus.MONITORING)

        if not _AGENT_AVAILABLE:
            self._task_mgr.record_result(
                task_id,
                TaskStatus.ERROR,
                error="Core agent (src/agent) not available. Check imports.",
            )
            return

        try:
            # Use existing SelfHealingWebAgent but intercept the healing
            learner = SelectorLearner()
            artifact_writer = ArtifactWriter()

            with BrowserController(headless=self._headless) as browser:
                browser.navigate(url)

                # Try extraction with current selector
                try:
                    data = browser.extract(selector)

                    # Success — record result
                    self._task_mgr.record_result(
                        task_id,
                        TaskStatus.MONITORING,
                        result={"data": data, "selector": selector, "status": "success"},
                    )
                    learner.persist(url, task_label, selector, confidence=1.0)

                except SelectorFailedError:
                    # Selector failed — trigger healing
                    self._task_mgr.set_status(task_id, TaskStatus.HEALING)

                    healer = SelectorHealer(browser, artifact_writer, api_key=self._api_key)
                    heal_result = healer.heal(
                        url=url,
                        failed_selector=selector,
                        task_label=task_label,
                    )

                    if heal_result:
                        new_selector, confidence = heal_result

                        # DON'T auto-apply — create an approval request instead
                        shot_path = str(healer.last_screenshot_path) if getattr(healer, "last_screenshot_path", None) else None
                        approval = self._approval_mgr.create(
                            task_id=task_id,
                            url=url,
                            task_label=task_label,
                            old_selector=selector,
                            new_selector=new_selector,
                            confidence=confidence,
                            reasoning=f"Vision model found replacement with {confidence:.0%} confidence.",
                            screenshot_path=shot_path,
                        )

                        self._task_mgr.record_result(
                            task_id,
                            TaskStatus.PENDING_APPROVAL,
                            result={
                                "status": "pending_approval",
                                "approval_id": approval["id"],
                                "old_selector": selector,
                                "new_selector": new_selector,
                                "confidence": confidence,
                            },
                        )
                    else:
                        # Healing failed entirely
                        self._task_mgr.record_result(
                            task_id,
                            TaskStatus.ERROR,
                            error=f"Selector '{selector}' failed and healing could not find a replacement.",
                        )

        except Exception as exc:
            self._task_mgr.record_result(
                task_id,
                TaskStatus.ERROR,
                error=str(exc),
            )

    def run_single_task(self, task_id: str) -> Optional[dict]:
        """Run a single task immediately (called from API). Returns the task."""
        task = self._task_mgr.get(task_id)
        if not task:
            return None
        self._run_task(task)
        return self._task_mgr.get(task_id)

    def apply_approval(self, approval_id: str) -> Optional[dict]:
        """
        Apply an approved change — updates the task's selector and persists
        to the learning store.
        """
        approval = self._approval_mgr.approve(approval_id)
        if not approval:
            return None

        task_id = approval["task_id"]
        task = self._task_mgr.get(task_id)
        if task:
            # Update the task's selector to the approved new one
            self._task_mgr.update(
                task_id,
                selector=approval["new_selector"],
                status=TaskStatus.MONITORING.value,
            )
            self._task_mgr.increment_healed(task_id)

            # Persist to the learning store
            if _AGENT_AVAILABLE:
                learner = SelectorLearner()
                learner.persist(
                    approval["url"],
                    approval["task_label"],
                    approval["new_selector"],
                    approval["confidence"],
                )

        return approval

    def reject_approval(self, approval_id: str) -> Optional[dict]:
        """Reject a proposed change and reset the task to monitoring."""
        approval = self._approval_mgr.reject(approval_id)
        if not approval:
            return None

        task = self._task_mgr.get(approval["task_id"])
        if task:
            self._task_mgr.set_status(approval["task_id"], TaskStatus.MONITORING)

        return approval
