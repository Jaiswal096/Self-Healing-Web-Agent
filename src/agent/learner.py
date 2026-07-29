"""
learner.py — SelectorLearner persists and retrieves healed selectors.

The selector store is a JSON file at ``data/selector_store.json``.
Each entry is keyed by ``(url_pattern, task_label)`` and stores:
  - selector     : the current best CSS/XPath selector
  - confidence   : 0.0 – 1.0 score from the vision model
  - healed_count : how many times this entry was healed
  - last_updated : ISO-8601 timestamp
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from src.utils.logger import get_logger

log = get_logger("SelectorLearner")

_STORE_PATH = Path(__file__).resolve().parents[2] / "data" / "selector_store.json"


def _make_key(url: str, task_label: str) -> str:
    """Create a stable lookup key from a URL and task label."""
    # Strip query string for a more durable key
    base_url = url.split("?")[0].rstrip("/")
    return f"{base_url}::{task_label}"


class SelectorLearner:
    """
    Persists and retrieves selectors that have been healed by the agent.

    Usage::

        learner = SelectorLearner()
        cached = learner.get_selector("https://example.com/shop", "price")
        if cached:
            selector = cached["selector"]
        learner.persist("https://example.com/shop", "price", ".new-price", 0.95)
    """

    def __init__(self, store_path: Path | str | None = None):
        self._path = Path(store_path) if store_path else _STORE_PATH
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._store: dict[str, dict] = self._load()

    # ------------------------------------------------------------------ #
    # Internal I/O
    # ------------------------------------------------------------------ #

    def _load(self) -> dict:
        if self._path.exists():
            try:
                with open(self._path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                log.debug("Loaded %d selector(s) from store.", len(data))
                return data
            except json.JSONDecodeError:
                log.warning("Selector store is corrupt — starting fresh.")
        return {}

    def _save(self) -> None:
        with open(self._path, "w", encoding="utf-8") as f:
            json.dump(self._store, f, indent=2, ensure_ascii=False)
        log.debug("Selector store saved (%d entries).", len(self._store))

    # ------------------------------------------------------------------ #
    # Public API
    # ------------------------------------------------------------------ #

    def get_selector(self, url: str, task_label: str) -> dict | None:
        """
        Look up a previously learned selector.

        :returns: Dict with ``selector``, ``confidence``, ``healed_count``,
                  ``last_updated`` — or ``None`` if not found.
        """
        key = _make_key(url, task_label)
        entry = self._store.get(key)
        if entry:
            log.info(
                "Found stored selector '%s' for task '%s' (confidence=%.2f)",
                entry["selector"],
                task_label,
                entry["confidence"],
            )
        return entry

    def persist(
        self,
        url: str,
        task_label: str,
        selector: str,
        confidence: float = 1.0,
    ) -> None:
        """
        Save (or update) a selector for a given URL + task combination.

        :param url:         Target page URL.
        :param task_label:  Human-readable label identifying the data task.
        :param selector:    CSS or XPath selector string.
        :param confidence:  0.0-1.0 — vision model's confidence score.
        """
        key = _make_key(url, task_label)
        existing = self._store.get(key, {})
        healed_count = existing.get("healed_count", 0)

        # Only increment healed_count if the selector actually changed
        if existing.get("selector") and existing["selector"] != selector:
            healed_count += 1

        self._store[key] = {
            "url": url,
            "task_label": task_label,
            "selector": selector,
            "confidence": round(confidence, 4),
            "healed_count": healed_count,
            "last_updated": datetime.now(timezone.utc).isoformat(),
        }
        self._save()
        log.info(
            "Persisted selector '%s' → task '%s' (healed %d times)",
            selector,
            task_label,
            healed_count,
        )

    def list_all(self) -> list[dict]:
        """Return all stored selector entries."""
        return list(self._store.values())

    def clear(self, url: str | None = None, task_label: str | None = None) -> int:
        """
        Clear entries. If *url* and *task_label* are given, remove only that
        entry; otherwise wipe the entire store.

        :returns: Number of entries removed.
        """
        if url and task_label:
            key = _make_key(url, task_label)
            removed = 1 if self._store.pop(key, None) else 0
        else:
            removed = len(self._store)
            self._store.clear()
        self._save()
        log.info("Cleared %d selector(s) from store.", removed)
        return removed
