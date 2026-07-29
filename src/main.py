"""
main.py — CLI entry point and live demonstration of the Self-Healing Web Agent.

Usage
-----
    # Basic scrape (uses .price_color selector on books.toscrape.com)
    python src/main.py

    # Custom URL and selector
    python src/main.py --url https://books.toscrape.com --selector ".price_color" --task book_price

    # Simulate selector failure to test self-healing
    python src/main.py --simulate-failure

    # Show the selector knowledge base
    python src/main.py --list-learned

    # Batch demo
    python src/main.py --batch-demo
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

# Ensure the project root is on sys.path when running directly
_PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from dotenv import load_dotenv

load_dotenv()  # Load .env file (GOOGLE_API_KEY etc.)

from src.agent.core import SelfHealingWebAgent
from src.utils.logger import get_logger

log = get_logger("main")

# ── Demo helpers ──────────────────────────────────────────────────────────── #

DEMO_URL = "https://books.toscrape.com"
DEMO_SELECTOR = ".price_color"
DEMO_TASK = "book_price"
DEMO_BROKEN_SELECTOR = ".THIS_SELECTOR_DOES_NOT_EXIST_12345"


def _print_result(result: dict) -> None:
    """Pretty-print a scrape result dict."""
    status = result.get("status", "?")
    icons = {"success": "✅", "healed": "🩺", "failed": "❌"}
    icon = icons.get(status, "❓")

    print(f"\n{icon}  Status  : {status.upper()}")
    print(f"   Selector: {result.get('selector', '-')}")

    data = result.get("data")
    if isinstance(data, list):
        print(f"   Data    : {data[:5]} {'...' if len(data) > 5 else ''}")
    else:
        print(f"   Data    : {data}")

    if result.get("healed"):
        print(f"   Orig.   : {result.get('original_selector', '-')}")
        print(f"   Conf.   : {result.get('confidence', 0):.0%}")

    if result.get("error"):
        print(f"   Error   : {result['error']}")
    print()


# ── CLI ───────────────────────────────────────────────────────────────────── #


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="self-healing-agent",
        description=(
            "Self-Healing Web Agent — autonomously adapts CSS selectors "
            "when a website's structure changes."
        ),
        formatter_class=argparse.RawTextHelpFormatter,
    )
    p.add_argument("--url", default=DEMO_URL, help="Target page URL")
    p.add_argument("--selector", default=DEMO_SELECTOR, help="CSS selector to try")
    p.add_argument("--task", default=DEMO_TASK, help="Task label (used in artifacts)")
    p.add_argument(
        "--extract-all",
        action="store_true",
        help="Extract all matching elements (not just the first)",
    )
    p.add_argument(
        "--simulate-failure",
        action="store_true",
        help="Intentionally use a broken selector to demo self-healing",
    )
    p.add_argument(
        "--batch-demo",
        action="store_true",
        help="Run a batch of different scraping tasks as a demo",
    )
    p.add_argument(
        "--list-learned",
        action="store_true",
        help="Print the current selector knowledge base and exit",
    )
    p.add_argument(
        "--clear-store",
        action="store_true",
        help="Clear the selector store (wipes learned selectors)",
    )
    p.add_argument(
        "--no-headless",
        action="store_true",
        help="Run browser in headed (visible) mode",
    )
    p.add_argument(
        "--api-key",
        default=None,
        help="Google Gemini API key (overrides GOOGLE_API_KEY env var)",
    )
    return p


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    api_key = args.api_key or os.getenv("GOOGLE_API_KEY", "")
    headless = not args.no_headless

    agent = SelfHealingWebAgent(
        api_key=api_key,
        headless=headless,
    )

    # ── List learned selectors ────────────────────────────────────────── #
    if args.list_learned:
        entries = agent.list_learned_selectors()
        if not entries:
            print("\nSelector store is empty. Run a scrape first!\n")
        else:
            print(f"\n📚 Selector Store ({len(entries)} entries):\n")
            print(json.dumps(entries, indent=2))
        return 0

    # ── Clear store ───────────────────────────────────────────────────── #
    if args.clear_store:
        agent.clear_selector_store()
        print("✅ Selector store cleared.\n")
        return 0

    # ── Batch demo ────────────────────────────────────────────────────── #
    if args.batch_demo:
        print("\n🔄 Running batch demo on books.toscrape.com…\n")
        tasks = [
            {
                "url": DEMO_URL,
                "selector": ".price_color",
                "task_label": "book_price",
                "extract_all": True,
            },
            {
                "url": DEMO_URL,
                "selector": "h3 a",
                "task_label": "book_title",
                "extract_all": True,
            },
            {
                "url": DEMO_URL,
                "selector": ".star-rating",
                "task_label": "book_rating",
                "extract_all": True,
            },
            {
                "url": DEMO_URL,
                "selector": DEMO_BROKEN_SELECTOR,   # intentionally broken
                "task_label": "broken_demo",
            },
        ]
        results = agent.batch_scrape(tasks)
        for r in results:
            print(f"── {r.get('task_label', '?')} ──")
            _print_result(r)
        return 0

    # ── Single scrape (with optional simulated failure) ───────────────── #
    selector = DEMO_BROKEN_SELECTOR if args.simulate_failure else args.selector
    if args.simulate_failure:
        print(
            f"\n⚡ Simulating selector failure — using intentionally broken selector:\n"
            f"   {DEMO_BROKEN_SELECTOR}\n"
            f"   Healing should recover: {DEMO_SELECTOR}\n"
        )

    print(f"\n🕷️  Scraping: {args.url}")
    print(f"   Selector : {selector}")
    print(f"   Task     : {args.task}\n")

    result = agent.scrape(
        url=args.url,
        selector=selector,
        task_label=args.task,
        extract_all=args.extract_all,
    )

    _print_result(result)

    print("📁 Check the `artifacts/` directory for generated reports.")
    print("📖 Check the `data/selector_store.json` for the learning store.\n")

    return 0 if result["status"] in ("success", "healed") else 1


if __name__ == "__main__":
    sys.exit(main())
