"""
tests/test_agent.py — Unit tests for the Self-Healing Web Agent framework.

Tests are designed to run without a live browser or Gemini API key by
using mocking (unittest.mock) wherever external dependencies are required.

Run with:
    pytest tests/ -v
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import sys

# Ensure the project root is on sys.path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


# ─── SelectorLearner tests ────────────────────────────────────────────────── #


class TestSelectorLearner:
    """Tests for the persistent selector store."""

    def setup_method(self):
        """Each test gets its own temp directory."""
        self.tmp = tempfile.mkdtemp()
        self.store_path = Path(self.tmp) / "selector_store.json"

    def _make_learner(self):
        from src.agent.learner import SelectorLearner
        return SelectorLearner(store_path=self.store_path)

    def test_persist_and_retrieve(self):
        learner = self._make_learner()
        learner.persist("https://example.com", "price", ".price_color", 0.95)
        entry = learner.get_selector("https://example.com", "price")
        assert entry is not None
        assert entry["selector"] == ".price_color"
        assert entry["confidence"] == 0.95
        assert entry["task_label"] == "price"

    def test_update_selector(self):
        learner = self._make_learner()
        learner.persist("https://example.com", "price", ".old-price", 0.80)
        learner.persist("https://example.com", "price", ".new-price", 0.92)
        entry = learner.get_selector("https://example.com", "price")
        assert entry["selector"] == ".new-price"
        assert entry["healed_count"] == 1  # tracked the change

    def test_heal_count_only_increments_on_change(self):
        learner = self._make_learner()
        learner.persist("https://example.com", "price", ".price", 0.90)
        learner.persist("https://example.com", "price", ".price", 0.90)  # same selector
        entry = learner.get_selector("https://example.com", "price")
        assert entry["healed_count"] == 0  # no change = no increment

    def test_missing_entry_returns_none(self):
        learner = self._make_learner()
        result = learner.get_selector("https://not-there.com", "nothing")
        assert result is None

    def test_clear_all(self):
        learner = self._make_learner()
        learner.persist("https://a.com", "x", ".a", 0.9)
        learner.persist("https://b.com", "y", ".b", 0.8)
        removed = learner.clear()
        assert removed == 2
        assert learner.list_all() == []

    def test_clear_specific_entry(self):
        learner = self._make_learner()
        learner.persist("https://a.com", "x", ".a", 0.9)
        learner.persist("https://b.com", "y", ".b", 0.8)
        learner.clear("https://a.com", "x")
        assert learner.get_selector("https://a.com", "x") is None
        assert learner.get_selector("https://b.com", "y") is not None

    def test_persistence_across_instances(self):
        """Data should survive creating a new learner instance."""
        learner1 = self._make_learner()
        learner1.persist("https://example.com", "title", "h1", 1.0)

        learner2 = self._make_learner()
        entry = learner2.get_selector("https://example.com", "title")
        assert entry is not None
        assert entry["selector"] == "h1"

    def test_url_with_query_string_stripped(self):
        """Query strings should be stripped when forming the key."""
        learner = self._make_learner()
        learner.persist("https://example.com/shop?page=2", "price", ".price", 0.9)
        entry = learner.get_selector("https://example.com/shop?page=3", "price")
        assert entry is not None  # should match despite different query string


# ─── ArtifactWriter tests ─────────────────────────────────────────────────── #


class TestArtifactWriter:
    """Tests for markdown/JSON artifact generation."""

    def setup_method(self):
        self.tmp = tempfile.mkdtemp()
        self.artifact_dir = Path(self.tmp) / "artifacts"

    def _make_writer(self):
        from src.agent.artifacts import ArtifactWriter
        return ArtifactWriter(artifact_dir=self.artifact_dir)

    def test_adaptation_plan_creates_files(self):
        writer = self._make_writer()
        path = writer.write_adaptation_plan(
            url="https://example.com",
            task_label="price",
            failed_selector=".old-price",
            candidate_selectors=[(".new-price", 0.92), ("span.price", 0.75)],
            reasoning="Vision model identified new class.",
        )
        assert path.exists()
        assert path.suffix == ".md"
        json_path = path.with_suffix(".json")
        assert json_path.exists()

    def test_adaptation_plan_content(self):
        writer = self._make_writer()
        path = writer.write_adaptation_plan(
            url="https://example.com",
            task_label="price",
            failed_selector=".broken",
            candidate_selectors=[(".price", 0.9)],
            reasoning="Found via vision.",
        )
        content = path.read_text(encoding="utf-8")
        assert ".broken" in content
        assert ".price" in content
        assert "Adaptation Plan" in content

    def test_adaptation_plan_json_structure(self):
        writer = self._make_writer()
        path = writer.write_adaptation_plan(
            url="https://example.com",
            task_label="title",
            failed_selector="h1.old",
            candidate_selectors=[("h1", 0.95)],
            reasoning="Simple heading.",
        )
        data = json.loads(path.with_suffix(".json").read_text())
        assert data["type"] == "adaptation_plan"
        assert data["failed_selector"] == "h1.old"
        assert len(data["candidates"]) == 1
        assert data["candidates"][0]["selector"] == "h1"

    def test_verification_success_artifact(self):
        writer = self._make_writer()
        path = writer.write_verification(
            url="https://example.com",
            task_label="price",
            selector=".price_color",
            extracted_data="£19.99",
            success=True,
        )
        content = path.read_text(encoding="utf-8")
        assert "SUCCESS" in content
        assert "£19.99" in content
        assert ".price_color" in content

    def test_verification_failure_artifact(self):
        writer = self._make_writer()
        path = writer.write_verification(
            url="https://example.com",
            task_label="price",
            selector=".broken",
            extracted_data="",
            success=False,
            notes="All candidates failed.",
        )
        content = path.read_text(encoding="utf-8")
        assert "FAILURE" in content
        assert "All candidates failed." in content

    def test_verification_json_structure(self):
        writer = self._make_writer()
        path = writer.write_verification(
            url="https://x.com",
            task_label="t",
            selector=".s",
            extracted_data="val",
            success=True,
        )
        data = json.loads(path.with_suffix(".json").read_text())
        assert data["type"] == "verification"
        assert data["success"] is True
        assert data["extracted_data"] == "val"

    def test_verification_list_data(self):
        writer = self._make_writer()
        path = writer.write_verification(
            url="https://example.com",
            task_label="prices",
            selector=".price_color",
            extracted_data=["£10.00", "£15.00", "£20.00"],
            success=True,
        )
        content = path.read_text(encoding="utf-8")
        assert "£10.00" in content
        assert "£15.00" in content


# ─── BrowserController tests (mocked) ────────────────────────────────────── #


class TestBrowserController:
    """Light tests for BrowserController using mocked Playwright."""

    def _make_browser(self, headless=True):
        from src.agent.browser import BrowserController
        return BrowserController(headless=headless, timeout_ms=5000)

    def test_selector_failed_error_repr(self):
        from src.agent.browser import SelectorFailedError
        err = SelectorFailedError(".missing", "https://x.com", "No match")
        assert ".missing" in str(err)
        assert "https://x.com" in str(err)

    def test_browser_raises_on_missing_playwright(self):
        """If playwright is not installed, _start() should raise ImportError."""
        from src.agent.browser import BrowserController
        browser = BrowserController()

        with patch.dict("sys.modules", {"playwright": None, "playwright.sync_api": None}):
            # Because _start() does a lazy import, we test the import path
            # by patching the import inside the method:
            import builtins
            original_import = builtins.__import__

            def mock_import(name, *args, **kwargs):
                if "playwright" in name:
                    raise ImportError("Mocked missing playwright")
                return original_import(name, *args, **kwargs)

            with patch("builtins.__import__", side_effect=mock_import):
                with pytest.raises(ImportError, match="Playwright is not installed"):
                    browser._start()


# ─── SelfHealingWebAgent integration tests (mocked browser) ──────────────── #


class TestSelfHealingWebAgent:
    """Integration tests for the orchestrator, with browser fully mocked."""

    def setup_method(self):
        self.tmp = tempfile.mkdtemp()
        self.store_path = Path(self.tmp) / "selector_store.json"
        self.artifact_dir = Path(self.tmp) / "artifacts"

    def _make_agent(self, api_key="test-key"):
        from src.agent.core import SelfHealingWebAgent
        return SelfHealingWebAgent(
            api_key=api_key,
            headless=True,
            selector_store_path=self.store_path,
            artifact_dir=self.artifact_dir,
        )

    def _mock_browser_success(self, data="£19.99"):
        """Return a mock BrowserController context manager that always succeeds."""
        mock_browser = MagicMock()
        mock_browser.extract.return_value = data
        mock_browser.extract_all.return_value = [data]
        mock_browser.__enter__ = MagicMock(return_value=mock_browser)
        mock_browser.__exit__ = MagicMock(return_value=False)
        return mock_browser

    def _mock_browser_fail_then_succeed(self, heal_selector=".healed", heal_data="£25.00"):
        """Browser fails first, then healer finds a new selector that works."""
        from src.agent.browser import SelectorFailedError
        mock_browser = MagicMock()
        mock_browser.extract.side_effect = [
            SelectorFailedError(".old", "https://x.com"),  # first call fails
            heal_data,                                       # second call (healed) succeeds
        ]
        mock_browser.screenshot.return_value = Path(self.tmp) / "shot.png"
        mock_browser.get_page_source.return_value = "<html><body></body></html>"
        mock_browser.__enter__ = MagicMock(return_value=mock_browser)
        mock_browser.__exit__ = MagicMock(return_value=False)
        return mock_browser

    def test_successful_scrape(self):
        agent = self._make_agent()
        mock_browser = self._mock_browser_success("£19.99")

        with patch("src.agent.core.BrowserController", return_value=mock_browser):
            result = agent.scrape("https://x.com", ".price", "price")

        assert result["status"] == "success"
        assert result["data"] == "£19.99"
        assert result["healed"] is False

    def test_uses_cached_selector_on_second_call(self):
        agent = self._make_agent()
        mock_browser = self._mock_browser_success()

        with patch("src.agent.core.BrowserController", return_value=mock_browser):
            agent.scrape("https://x.com", ".price", "price")
            agent.scrape("https://x.com", ".price", "price")  # second call

        # extract was called twice total (once per scrape)
        assert mock_browser.extract.call_count == 2

    def test_list_learned_after_scrape(self):
        agent = self._make_agent()
        mock_browser = self._mock_browser_success()

        with patch("src.agent.core.BrowserController", return_value=mock_browser):
            agent.scrape("https://x.com", ".price", "price_task")

        learned = agent.list_learned_selectors()
        assert len(learned) == 1
        assert learned[0]["task_label"] == "price_task"

    def test_clear_store(self):
        agent = self._make_agent()
        mock_browser = self._mock_browser_success()

        with patch("src.agent.core.BrowserController", return_value=mock_browser):
            agent.scrape("https://x.com", ".price", "price_task")

        agent.clear_selector_store()
        assert agent.list_learned_selectors() == []

    def test_batch_scrape(self):
        agent = self._make_agent()
        mock_browser = self._mock_browser_success("val")

        tasks = [
            {"url": "https://x.com", "selector": ".a", "task_label": "task_a"},
            {"url": "https://x.com", "selector": ".b", "task_label": "task_b"},
        ]

        with patch("src.agent.core.BrowserController", return_value=mock_browser):
            results = agent.batch_scrape(tasks)

        assert len(results) == 2
        assert all(r["status"] == "success" for r in results)
        assert results[0]["task_label"] == "task_a"
        assert results[1]["task_label"] == "task_b"
