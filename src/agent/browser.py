"""
browser.py — BrowserController wrapping Playwright for synchronous browser automation.

Responsibilities:
  - Navigate to URLs
  - Extract element text/attribute via CSS or XPath selectors
  - Take screenshots
  - Return page source HTML for analysis
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import Optional

from src.utils.logger import get_logger

log = get_logger("BrowserController")


class SelectorFailedError(Exception):
    """Raised when a CSS/XPath selector finds no element or returns empty text."""

    def __init__(self, selector: str, url: str, reason: str = ""):
        self.selector = selector
        self.url = url
        self.reason = reason
        super().__init__(
            f"Selector '{selector}' failed on '{url}'. {reason}"
        )


class BrowserController:
    """
    Thin synchronous wrapper around Playwright.

    Example usage::

        with BrowserController(headless=True) as browser:
            browser.navigate("https://books.toscrape.com")
            price = browser.extract(".price_color")
            browser.screenshot("artifacts/screenshot.png")
    """

    def __init__(self, headless: bool = True, timeout_ms: int = 15_000):
        self.headless = headless
        self.timeout_ms = timeout_ms
        self._playwright = None
        self._browser = None
        self._page = None

    # ------------------------------------------------------------------ #
    # Context manager support
    # ------------------------------------------------------------------ #

    def __enter__(self) -> "BrowserController":
        self._start()
        return self

    def __exit__(self, *_) -> None:
        self._stop()

    def _start(self) -> None:
        try:
            from playwright.sync_api import sync_playwright  # lazy import
        except ImportError as exc:
            raise ImportError(
                "Playwright is not installed. Run: pip install playwright && playwright install"
            ) from exc

        log.info("Starting Playwright browser (headless=%s)", self.headless)
        self._playwright = sync_playwright().start()
        self._browser = self._playwright.chromium.launch(headless=self.headless)
        context = self._browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            )
        )
        self._page = context.new_page()
        self._page.set_default_timeout(self.timeout_ms)

    def _stop(self) -> None:
        if self._browser:
            self._browser.close()
        if self._playwright:
            self._playwright.stop()
        log.info("Browser closed.")

    # ------------------------------------------------------------------ #
    # Core API
    # ------------------------------------------------------------------ #

    def navigate(self, url: str, wait_until: str = "domcontentloaded") -> None:
        """Navigate to *url* and wait for the page to settle."""
        log.info("Navigating → %s", url)
        self._page.goto(url, wait_until=wait_until)
        # Small human-like pause
        time.sleep(0.5)

    def extract(self, selector: str, attribute: Optional[str] = None) -> str:
        """
        Extract text (or *attribute* value) of the first element matching *selector*.

        :param selector: CSS selector or XPath (prefix with ``xpath=``).
        :param attribute: Optional HTML attribute to read (e.g. ``href``).
        :raises SelectorFailedError: If selector finds no element or empty text.
        :returns: Stripped text or attribute value.
        """
        log.debug("Extracting with selector: %s", selector)

        # XPath support
        if selector.startswith("xpath="):
            xpath = selector[6:]
            locator = self._page.locator(f"xpath={xpath}")
        else:
            locator = self._page.locator(selector)

        count = locator.count()
        if count == 0:
            raise SelectorFailedError(
                selector,
                self._page.url,
                reason="No elements matched.",
            )

        first = locator.first
        if attribute:
            value = first.get_attribute(attribute) or ""
        else:
            value = first.inner_text().strip()

        if not value:
            raise SelectorFailedError(
                selector,
                self._page.url,
                reason="Element found but returned empty text.",
            )

        log.info("Extracted value: %r", value)
        return value

    def extract_all(self, selector: str) -> list[str]:
        """Return inner text for ALL elements matching *selector*."""
        locator = self._page.locator(selector)
        count = locator.count()
        results = []
        for i in range(count):
            text = locator.nth(i).inner_text().strip()
            if text:
                results.append(text)
        log.debug("extract_all('%s') → %d results", selector, len(results))
        return results

    def screenshot(self, path: str | Path) -> Path:
        """Save a full-page screenshot to *path* and return the resolved path."""
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        self._page.screenshot(path=str(path), full_page=True)
        log.info("Screenshot saved → %s", path)
        return path

    def get_page_source(self) -> str:
        """Return the current page's full HTML source."""
        return self._page.content()

    def get_current_url(self) -> str:
        return self._page.url

    def click(self, selector: str) -> None:
        """Click an element by selector."""
        log.debug("Clicking: %s", selector)
        self._page.locator(selector).first.click()

    def type_text(self, selector: str, text: str) -> None:
        """Type *text* into an input element identified by *selector*."""
        log.debug("Typing into %s", selector)
        self._page.locator(selector).first.fill(text)
