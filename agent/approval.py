"""
approval.py — Human-in-the-loop approval queue for proposed selector changes.

When the agent heals a broken selector, it doesn't auto-apply the change.
Instead, it creates an approval request that the user must review via the
dashboard before the change is committed to the codebase.
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Optional

_APPROVALS_PATH = Path(__file__).resolve().parent / "data" / "approvals.json"


class ApprovalStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class ApprovalManager:
    """
    Manages the approval queue for proposed codebase/selector changes.

    Each approval entry:
        id, task_id, url, task_label, old_selector, new_selector,
        confidence, reasoning, screenshot_path, status, created_at,
        resolved_at, resolved_by
    """

    def __init__(self, store_path: Path | str | None = None):
        self._path = Path(store_path) if store_path else _APPROVALS_PATH
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._approvals: dict[str, dict] = self._load()

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
            json.dump(self._approvals, f, indent=2, ensure_ascii=False, default=str)

    def create(
        self,
        task_id: str,
        url: str,
        task_label: str,
        old_selector: str,
        new_selector: str,
        confidence: float = 0.0,
        reasoning: str = "",
        screenshot_path: str | None = None,
        adaptation_plan_path: str | None = None,
    ) -> dict:
        """Create a new pending approval request."""
        approval_id = str(uuid.uuid4())[:8]
        approval = {
            "id": approval_id,
            "task_id": task_id,
            "url": url,
            "task_label": task_label,
            "old_selector": old_selector,
            "new_selector": new_selector,
            "confidence": round(confidence, 4),
            "reasoning": reasoning,
            "screenshot_path": screenshot_path,
            "adaptation_plan_path": adaptation_plan_path,
            "status": ApprovalStatus.PENDING.value,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "resolved_at": None,
            "resolved_by": None,
        }
        self._approvals[approval_id] = approval
        self._save()
        return approval

    def get(self, approval_id: str) -> Optional[dict]:
        return self._approvals.get(approval_id)

    def list_all(self, status_filter: Optional[ApprovalStatus] = None) -> list[dict]:
        """Return all approvals, optionally filtered by status."""
        approvals = list(self._approvals.values())
        if status_filter:
            approvals = [a for a in approvals if a["status"] == status_filter.value]
        # Sort: pending first, then by created_at descending
        approvals.sort(
            key=lambda a: (
                0 if a["status"] == "pending" else 1,
                a.get("created_at", ""),
            ),
            reverse=False,
        )
        return approvals

    def list_pending(self) -> list[dict]:
        return self.list_all(status_filter=ApprovalStatus.PENDING)

    def approve(self, approval_id: str, resolved_by: str = "user") -> Optional[dict]:
        """
        Approve a pending change. Returns the approval dict with the
        new_selector that should be applied.
        """
        approval = self._approvals.get(approval_id)
        if not approval or approval["status"] != ApprovalStatus.PENDING.value:
            return None

        approval["status"] = ApprovalStatus.APPROVED.value
        approval["resolved_at"] = datetime.now(timezone.utc).isoformat()
        approval["resolved_by"] = resolved_by
        self._save()
        return approval

    def reject(self, approval_id: str, resolved_by: str = "user") -> Optional[dict]:
        """Reject a pending change."""
        approval = self._approvals.get(approval_id)
        if not approval or approval["status"] != ApprovalStatus.PENDING.value:
            return None

        approval["status"] = ApprovalStatus.REJECTED.value
        approval["resolved_at"] = datetime.now(timezone.utc).isoformat()
        approval["resolved_by"] = resolved_by
        self._save()
        return approval

    def pending_count(self) -> int:
        return sum(
            1 for a in self._approvals.values()
            if a["status"] == ApprovalStatus.PENDING.value
        )

    def stats(self) -> dict:
        """Return summary statistics."""
        statuses = [a["status"] for a in self._approvals.values()]
        return {
            "total": len(statuses),
            "pending": statuses.count(ApprovalStatus.PENDING.value),
            "approved": statuses.count(ApprovalStatus.APPROVED.value),
            "rejected": statuses.count(ApprovalStatus.REJECTED.value),
        }
