# 🕷️ Self-Healing Web Agent

> **An autonomous web scraping & automation framework that detects website structure changes and heals its own CSS/XPath selectors using Gemini Vision AI.**

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue?logo=python)](https://python.org)
[![Playwright](https://img.shields.io/badge/Browser-Playwright-green?logo=playwright)](https://playwright.dev/python)
[![Gemini](https://img.shields.io/badge/AI-Gemini%201.5%20Flash-orange?logo=google)](https://ai.google.dev)
[![License](https://img.shields.io/badge/License-MIT-yellow)](LICENSE)

---

## 🚀 The Problem: Brittle Web Automation

Web scraping and automation are powerful tools, but they come with a significant headache: **brittleness**.

Websites constantly change their structure, leading to broken selectors, failed scripts, and endless maintenance. Traditional scrapers are fragile, requiring constant manual updates, which wastes developer time and leads to unreliable data pipelines.

---

## ✨ The Solution: Self-Healing Web Agent

The **Self-Healing Web Agent** leverages **Google Gemini Vision AI** to create scrapers that automatically adapt to website changes.

When a CSS selector breaks, the agent:
1. 📸 **Screenshots** the current page
2. 🤖 **Sends the screenshot** to Gemini Vision with the broken selector context
3. 🎯 **Gets candidate selectors** ranked by confidence
4. ✅ **Tests each candidate** against the live page
5. 💾 **Learns & stores** the working selector so it never heals the same change twice
6. 📋 **Writes artifacts** documenting every step of the healing

---

## 🌟 Key Features

| Feature | Description |
|---|---|
| **Self-Healing Selectors** | Vision AI automatically finds new selectors when old ones break |
| **Persistent Learning** | Healed selectors are stored in `data/selector_store.json` |
| **Adaptation Plans** | Rich Markdown reports explaining what changed and why |
| **Verification Artifacts** | Screenshots + data samples confirming successful healing |
| **Batch Scraping** | Process multiple targets in one run |
| **Heuristic Fallback** | Works even without an API key using pattern-based guesses |
| **Playwright-powered** | Full browser automation, JS rendering, anti-bot measures |

---

## 📁 Project Structure

```
Self-Healing-Web-Agent/
├── src/
│   ├── main.py                  # CLI entry point & demo runner
│   ├── agent/
│   │   ├── core.py              # SelfHealingWebAgent orchestrator
│   │   ├── browser.py           # BrowserController (Playwright)
│   │   ├── healer.py            # Vision-based SelectorHealer
│   │   ├── learner.py           # Persistent SelectorLearner
│   │   └── artifacts.py         # ArtifactWriter (Markdown + JSON)
│   └── utils/
│       └── logger.py            # Rich structured logging
├── data/
│   └── selector_store.json      # Auto-created: learning knowledge base
├── artifacts/                   # Generated reports (Adaptation Plans + Verification)
├── tests/
│   └── test_agent.py            # Full pytest suite
├── requirements.txt
├── setup.py
└── .env.example                 # Config template
```

---

## 🛠️ Getting Started

### 1. Clone the repository

```bash
git clone https://github.com/Jaiswal096/Self-Healing-Web-Agent.git
cd Self-Healing-Web-Agent
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
playwright install chromium
```

### 3. Configure API key

```bash
cp .env.example .env
# Edit .env and add your GOOGLE_API_KEY
# Get a free key at: https://aistudio.google.com/app/apikey
```

### 4. Run the demo

```bash
# Basic scrape (extracts book prices from books.toscrape.com)
python src/main.py

# Simulate a broken selector — watch the agent heal it!
python src/main.py --simulate-failure

# Batch demo: scrapes prices, titles, and ratings simultaneously
python src/main.py --batch-demo

# Inspect the learning knowledge base
python src/main.py --list-learned

# Custom target
python src/main.py --url https://books.toscrape.com --selector ".price_color" --task book_price
```

---

## 💻 Python API

```python
from src.agent.core import SelfHealingWebAgent

agent = SelfHealingWebAgent(api_key="YOUR_GOOGLE_API_KEY")

# Single scrape — auto-heals if selector breaks
result = agent.scrape(
    url="https://books.toscrape.com",
    selector=".price_color",
    task_label="book_price",
)
print(result)
# {'status': 'success', 'data': '£51.77', 'selector': '.price_color', 'healed': False}

# If the selector was broken, result would show:
# {'status': 'healed', 'data': '£51.77', 'selector': '.new-price-class',
#  'healed': True, 'original_selector': '.broken-selector', 'confidence': 0.92}

# Batch scraping
results = agent.batch_scrape([
    {"url": "https://books.toscrape.com", "selector": ".price_color", "task_label": "price"},
    {"url": "https://books.toscrape.com", "selector": "h3 a", "task_label": "title", "extract_all": True},
])

# View what the agent has learned
entries = agent.list_learned_selectors()
```

---

## 🩺 How Self-Healing Works

```
Scrape Request
      │
      ▼
┌─────────────────┐
│ Check Selector  │◄── SelectorLearner: is there a cached healed selector?
│ Knowledge Base  │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Navigate & Try  │
│ Current Selector│
└────────┬────────┘
         │
    ┌────┴────┐
    │         │
 Success   Failure
    │         │
    ▼         ▼
 Return    📸 Screenshot page
  Data         │
               ▼
         🤖 Call Gemini Vision
         with screenshot + HTML
               │
               ▼
         Get candidate
         selectors ranked
         by confidence
               │
               ▼
         Try each candidate
         against live page
               │
          ┌────┴────┐
          │         │
       Found     Not Found
          │         │
          ▼         ▼
    ✅ Persist   ❌ Write failure
    healed sel   verification
    to store     artifact
          │
          ▼
    📋 Write Adaptation
    Plan + Verification
    Artifacts
```

---

## 📋 Sample Artifacts

### Adaptation Plan (`artifacts/adaptation_plan_book_price_*.md`)
Documents what selector failed, what Gemini Vision reasoned, and what candidates were proposed.

### Verification Artifact (`artifacts/verification_book_price_*.md`)
Confirms the healed selector worked, includes the extracted data sample and a post-heal screenshot.

---

## 🧪 Running Tests

```bash
pytest tests/ -v
# Or with coverage:
pytest tests/ -v --cov=src --cov-report=term-missing
```

---

## 🤝 Contributing

We welcome contributions! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for details.

Ideas welcome:
- New heuristic patterns for common websites
- Integration with other vision models (GPT-4V, Claude)
- Dashboard UI for monitoring agent activity
- Docker container for easy deployment

---

## 📄 License

This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.

---

*Built with ❤️ using Playwright + Google Gemini Vision AI*
