"""
healer.py — SelectorHealer: vision-based self-healing of broken CSS/XPath selectors.

Healing pipeline:
  1. Take a screenshot of the broken page.
  2. Send the screenshot + HTML snippet to Gemini Vision (gemini-1.5-flash).
  3. Parse candidate selectors with confidence scores from the model response.
  4. Try each candidate against the live browser.
  5. Return the first selector that successfully extracts data.
  6. Emit an AdaptationPlanArtifact documenting the healing.
"""

from __future__ import annotations

import os
import re
import textwrap
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING, Optional

from src.utils.logger import get_logger

if TYPE_CHECKING:
    from src.agent.browser import BrowserController
    from src.agent.artifacts import ArtifactWriter

log = get_logger("SelectorHealer")

_SCREENSHOT_DIR = Path(__file__).resolve().parents[2] / "artifacts" / "screenshots"

# ── Gemini Vision helper ─────────────────────────────────────────────────── #

_HEALING_PROMPT = textwrap.dedent("""
You are an expert web scraping assistant. The following CSS selector has stopped working
on the web page shown in the screenshot:

FAILED SELECTOR: {failed_selector}
TASK DESCRIPTION: {task_label}
URL: {url}

Please analyse the screenshot and the HTML snippet below, then identify the best
CSS selectors that would extract the target element (described by the task label).

HTML SNIPPET (first 3000 chars):
{html_snippet}

Respond ONLY with a JSON array of objects, ordered by confidence (highest first).
Each object must have exactly these fields:
  - "selector": string (valid CSS selector or XPath prefixed with "xpath=")
  - "confidence": float between 0 and 1
  - "reasoning": string (one sentence explaining why this selector is appropriate)

Example response format:
[
  {{"selector": ".price_color", "confidence": 0.95, "reasoning": "The price is wrapped in a span with class price_color."}},
  {{"selector": "xpath=//p[@class='price_color']", "confidence": 0.80, "reasoning": "XPath fallback targeting the same element."}}
]

Return ONLY the JSON array — no markdown fences, no extra text.
""")


def _call_gemini_vision(
    screenshot_path: Path,
    failed_selector: str,
    task_label: str,
    url: str,
    html_snippet: str,
    api_key: str,
) -> list[dict]:
    """Call Gemini Vision API and parse candidate selectors."""
    try:
        import google.generativeai as genai
    except ImportError as exc:
        raise ImportError(
            "google-generativeai is not installed. Run: pip install google-generativeai"
        ) from exc

    genai.configure(api_key=api_key)
    model = genai.GenerativeModel("gemini-1.5-flash")

    prompt = _HEALING_PROMPT.format(
        failed_selector=failed_selector,
        task_label=task_label,
        url=url,
        html_snippet=html_snippet[:3000],
    )

    # Load screenshot as bytes
    image_bytes = screenshot_path.read_bytes()
    image_part = {"mime_type": "image/png", "data": image_bytes}

    log.info("Calling Gemini Vision for selector healing…")
    response = model.generate_content([prompt, image_part])
    raw = response.text.strip()

    log.debug("Gemini raw response: %s", raw[:500])

    # Strip markdown fences if the model wrapped the JSON
    raw = re.sub(r"^```[a-z]*\n?", "", raw, flags=re.MULTILINE)
    raw = re.sub(r"\n?```$", "", raw, flags=re.MULTILINE)

    import json
    candidates: list[dict] = json.loads(raw)
    log.info("Gemini returned %d candidate selector(s).", len(candidates))
    return candidates


def _fallback_candidates(html_snippet: str, task_label: str) -> list[dict]:
    """
    Heuristic-based fallback when the Gemini API call fails.
    Generates a small set of plausible candidates by scanning the HTML.
    """
    log.warning("Using heuristic fallback to generate candidate selectors.")
    candidates: list[dict] = []

    # Price-like patterns
    if "price" in task_label.lower():
        patterns = [
            (".price_color", 0.6),
            (".price", 0.55),
            ("[class*='price']", 0.50),
            ("span[class*='price']", 0.45),
            ("p.price_color", 0.40),
        ]
    else:
        # Generic: look for common data containers
        patterns = [
            ("[data-testid]", 0.40),
            ("h1", 0.35),
            ("main p", 0.30),
        ]

    for sel, conf in patterns:
        candidates.append({
            "selector": sel,
            "confidence": conf,
            "reasoning": f"Heuristic pattern for task '{task_label}'.",
        })

    return candidates


# ── Main class ───────────────────────────────────────────────────────────── #


class SelectorHealer:
    """
    Uses Gemini Vision to recover broken selectors.

    Usage::

        healer = SelectorHealer(browser, artifact_writer, api_key="...")
        result = healer.heal(
            url="https://books.toscrape.com",
            failed_selector=".wrong-class",
            task_label="book_price",
        )
        if result:
            new_selector, confidence = result
    """

    def __init__(
        self,
        browser: "BrowserController",
        artifact_writer: "ArtifactWriter",
        api_key: Optional[str] = None,
    ):
        self._browser = browser
        self._artifact_writer = artifact_writer
        self._api_key = api_key or os.getenv("GOOGLE_API_KEY", "")
        _SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)

    def heal(
        self,
        url: str,
        failed_selector: str,
        task_label: str,
        max_candidates: int = 5,
    ) -> Optional[tuple[str, float]]:
        """
        Execute the full healing pipeline.

        :param url:              The page URL where scraping failed.
        :param failed_selector:  The selector that stopped working.
        :param task_label:       Human label for the target data (e.g. 'book_price').
        :param max_candidates:   Maximum number of candidates to try.
        :returns: ``(selector, confidence)`` tuple if healing succeeded, else ``None``.
        """
        log.info(
            "⚕️  Healing triggered — selector: '%s', task: '%s'",
            failed_selector, task_label,
        )

        # 1. Screenshot
        ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        screenshot_path = _SCREENSHOT_DIR / f"before_heal_{task_label}_{ts}.png"
        self._browser.screenshot(screenshot_path)

        # 2. Grab page HTML snippet
        html_snippet = self._browser.get_page_source()[:3000]

        # 3. Get candidates from Gemini Vision (or fallback)
        candidates: list[dict] = []
        reasoning_summary = ""

        if self._api_key:
            try:
                candidates = _call_gemini_vision(
                    screenshot_path=screenshot_path,
                    failed_selector=failed_selector,
                    task_label=task_label,
                    url=url,
                    html_snippet=html_snippet,
                    api_key=self._api_key,
                )
                reasoning_summary = "\n\n".join(
                    f"**`{c['selector']}`** (confidence {c['confidence']:.0%}): {c['reasoning']}"
                    for c in candidates[:max_candidates]
                )
            except Exception as exc:
                log.error("Gemini Vision call failed: %s — using heuristic fallback.", exc)
                candidates = _fallback_candidates(html_snippet, task_label)
                reasoning_summary = "Vision model unavailable — heuristic candidates generated."
        else:
            log.warning("No GOOGLE_API_KEY set — using heuristic fallback.")
            candidates = _fallback_candidates(html_snippet, task_label)
            reasoning_summary = "No API key provided — heuristic candidates generated."

        # 4. Write Adaptation Plan Artifact
        candidate_tuples = [
            (c["selector"], c["confidence"]) for c in candidates[:max_candidates]
        ]
        self._artifact_writer.write_adaptation_plan(
            url=url,
            task_label=task_label,
            failed_selector=failed_selector,
            candidate_selectors=candidate_tuples,
            reasoning=reasoning_summary,
            screenshot_path=screenshot_path,
            page_source_snippet=html_snippet,
        )

        # 5. Try each candidate selector against the live page
        for candidate in candidates[:max_candidates]:
            sel = candidate["selector"]
            conf = candidate["confidence"]
            log.info("Trying candidate selector: '%s' (confidence=%.2f)", sel, conf)
            try:
                value = self._browser.extract(sel)
                log.info(
                    "✅ Healing successful! New selector: '%s' → '%s'",
                    sel, value,
                )
                # 6. Screenshot after healing
                after_path = _SCREENSHOT_DIR / f"after_heal_{task_label}_{ts}.png"
                self._browser.screenshot(after_path)

                # 7. Write Verification Artifact
                self._artifact_writer.write_verification(
                    url=url,
                    task_label=task_label,
                    selector=sel,
                    extracted_data=value,
                    screenshot_path=after_path,
                    success=True,
                    notes=f"Selector confidence: {conf:.0%}. Replaced `{failed_selector}`.",
                )

                return sel, conf

            except Exception as exc:
                log.debug("Candidate '%s' failed: %s", sel, exc)
                continue

        # All candidates exhausted — healing failed
        log.error("❌ All %d candidate(s) failed. Healing unsuccessful.", len(candidates[:max_candidates]))

        self._artifact_writer.write_verification(
            url=url,
            task_label=task_label,
            selector=failed_selector,
            extracted_data="",
            screenshot_path=screenshot_path,
            success=False,
            notes="All vision-generated candidates were tried and failed.",
        )

        return None
