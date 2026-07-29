"""
core.py — SelfHealingWebAgent: the main orchestrator.

Ties together BrowserController, SelectorHealer, SelectorLearner and ArtifactWriter
into a unified interface.

Usage::

    agent = SelfHealingWebAgent(api_key="YOUR_GOOGLE_API_KEY")

    result = agent.scrape(
        url="https://books.toscrape.com",
        selector=".price_color",
        task_label="book_price",
    )
    print(result)  # {"status": "success", "data": "£51.77", "selector": ".price_color"}

    # Batch-scrape multiple targets
    results = agent.batch_scrape([
        {"url": "https://books.toscrape.com", "selector": ".price_color", "task_label": "book_price"},
        {"url": "https://books.toscrape.com", "selector": "h1", "task_label": "page_title"},
    ])
"""

from __future__ import annotations

import os
from typing import Optional

from src.agent.artifacts import ArtifactWriter
from src.agent.browser import BrowserController, SelectorFailedError
from src.agent.healer import SelectorHealer
from src.agent.learner import SelectorLearner
from src.utils.logger import get_logger

log = get_logger("SelfHealingWebAgent")


class SelfHealingWebAgent:
    """
    Autonomous self-healing web scraping orchestrator.

    Parameters
    ----------
    api_key : str, optional
        Google Gemini API key for vision-based healing.
        Falls back to the ``GOOGLE_API_KEY`` environment variable.
    headless : bool
        Run the browser in headless mode (default: True).
    timeout_ms : int
        Browser element-wait timeout in milliseconds (default: 15000).
    selector_store_path : str | Path, optional
        Override the path to ``selector_store.json``.
    artifact_dir : str | Path, optional
        Override the directory where artifacts are written.

    Example
    -------
    >>> agent = SelfHealingWebAgent(api_key="...")
    >>> result = agent.scrape("https://books.toscrape.com", ".price_color", "book_price")
    >>> print(result["data"])
    £51.77
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        headless: bool = True,
        timeout_ms: int = 15_000,
        selector_store_path=None,
        artifact_dir=None,
    ):
        self._api_key = api_key or os.getenv("GOOGLE_API_KEY", "")
        self._headless = headless
        self._timeout_ms = timeout_ms
        self._learner = SelectorLearner(store_path=selector_store_path)
        self._artifact_writer = ArtifactWriter(artifact_dir=artifact_dir)

        log.info("SelfHealingWebAgent initialised.")
        log.info(
            "  headless=%s | timeout=%dms | api_key=%s",
            headless,
            timeout_ms,
            "SET" if self._api_key else "NOT SET (healing uses heuristics)",
        )

    # ------------------------------------------------------------------ #
    # Primary API
    # ------------------------------------------------------------------ #

    def scrape(
        self,
        url: str,
        selector: str,
        task_label: str,
        extract_all: bool = False,
    ) -> dict:
        """
        Navigate to *url* and extract data using *selector*.

        Self-healing is triggered automatically if the selector fails.
        The healed selector is persisted so future calls skip healing.

        :param url:          Target page URL.
        :param selector:     CSS selector (or XPath prefixed with ``xpath=``).
        :param task_label:   Short label identifying the extraction task.
        :param extract_all:  If True, extract all matching elements, not just the first.
        :returns: Dict with keys:
                  - ``status``   : ``"success"`` | ``"healed"`` | ``"failed"``
                  - ``data``     : extracted string / list of strings
                  - ``selector`` : the selector used (may differ if healed)
                  - ``healed``   : bool — True if the selector was replaced
        """
        # Check for a previously-healed selector
        cached = self._learner.get_selector(url, task_label)
        effective_selector = cached["selector"] if cached else selector

        if cached and cached["selector"] != selector:
            log.info(
                "Using learned selector '%s' instead of '%s'",
                cached["selector"], selector,
            )

        with BrowserController(headless=self._headless, timeout_ms=self._timeout_ms) as browser:
            healer = SelectorHealer(browser, self._artifact_writer, api_key=self._api_key)

            # Navigate to the target URL
            browser.navigate(url)

            # ── Attempt extraction ─────────────────────────────────── #
            try:
                if extract_all:
                    data = browser.extract_all(effective_selector)
                else:
                    data = browser.extract(effective_selector)

                # Persist the working selector (could be original or cached)
                self._learner.persist(url, task_label, effective_selector, confidence=1.0)

                log.info("✅ Extraction succeeded for task '%s'.", task_label)
                return {
                    "status": "success",
                    "data": data,
                    "selector": effective_selector,
                    "healed": False,
                }

            except SelectorFailedError as exc:
                log.warning(
                    "❌ Selector '%s' failed for task '%s'. Triggering healing…",
                    effective_selector, task_label,
                )

                # ── Healing pipeline ───────────────────────────────── #
                heal_result = healer.heal(
                    url=url,
                    failed_selector=effective_selector,
                    task_label=task_label,
                )

                if heal_result:
                    new_selector, confidence = heal_result
                    # Persist the healed selector
                    self._learner.persist(url, task_label, new_selector, confidence)

                    # Re-extract with healed selector
                    try:
                        if extract_all:
                            data = browser.extract_all(new_selector)
                        else:
                            data = browser.extract(new_selector)

                        return {
                            "status": "healed",
                            "data": data,
                            "selector": new_selector,
                            "healed": True,
                            "original_selector": effective_selector,
                            "confidence": confidence,
                        }
                    except SelectorFailedError:
                        pass  # fall through to failed

                return {
                    "status": "failed",
                    "data": None,
                    "selector": effective_selector,
                    "healed": False,
                    "error": str(exc),
                }

    def batch_scrape(self, tasks: list[dict]) -> list[dict]:
        """
        Run multiple scraping tasks sequentially.

        Each task dict must have: ``url``, ``selector``, ``task_label``.
        Optional: ``extract_all`` (bool).

        :returns: List of result dicts (same format as :meth:`scrape`).
        """
        results = []
        for i, task in enumerate(tasks, 1):
            log.info(
                "Batch task %d/%d: task_label='%s'", i, len(tasks), task.get("task_label", "?")
            )
            result = self.scrape(
                url=task["url"],
                selector=task["selector"],
                task_label=task["task_label"],
                extract_all=task.get("extract_all", False),
            )
            result["task_label"] = task["task_label"]
            results.append(result)
        return results

    # ------------------------------------------------------------------ #
    # Utility helpers
    # ------------------------------------------------------------------ #

    def list_learned_selectors(self) -> list[dict]:
        """Return all selectors stored in the knowledge base."""
        entries = self._learner.list_all()
        log.info("Selector store contains %d entries.", len(entries))
        return entries

    def clear_selector_store(self) -> None:
        """Wipe the entire selector store (use with caution)."""
        removed = self._learner.clear()
        log.info("Cleared %d entries from selector store.", removed)

    def forget_selector(self, url: str, task_label: str) -> None:
        """Remove a specific learned selector."""
        self._learner.clear(url, task_label)
