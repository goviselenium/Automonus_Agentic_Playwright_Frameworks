# Autonomous Agentic Playwright Test Automation Framework (Python)

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/)
[![Playwright](https://img.shields.io/badge/playwright-v1.49+-green.svg)](https://playwright.dev/python/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

An autonomous, website-agnostic end-to-end test automation framework built on **Playwright** and powered by specialized **Agentic AI models** (Planner, Generator, Healer).

---

## 🌟 Key Capabilities & Features

- **Website Agnostic**: Operates against any web application (React, Angular, Vue, SSR, SPAs) without domain-specific source code or pre-coded Page Object Models.
- **Three Specialized AI Agents**:
  1. **Planner Agent**: Interprets business requirements (Markdown, Plain Text, Gherkin BDD, JSON) and decomposes them into a state-aware Atomic Step Graph.
  2. **Generator Agent**: Inspects active live DOM accessibility trees (`aria-snapshot`) and interactive element inventories to synthesize dynamic, resilient Playwright actions.
  3. **Healer Agent**: Intercepts step failures (`TimeoutError`, `ElementHandleNotFound`, assertion errors), analyzes element drift, generates replacement locators, verifies them against live browser state, and resumes execution seamlessly.
- **Persistent Locator Registry**: Stores verified healed locators in `locator.registry.json` so subsequent executions use repaired selectors directly.
- **Resilient Automation & Observability**: Native auto-waiting, screenshot capture, video recording, Playwright trace viewer (`trace.zip`), and rich HTML execution & self-healing audit dashboards.
- **Zero Mandatory External API Dependencies**: Built-in deterministic heuristic fallback engine allows out-of-the-box execution in CI/CD without mandatory LLM API keys.

---

## 🏗 System Architecture

```text
               +-------------------------------------------+
               | User Requirement / Test Use Case Document |
               +-------------------------------------------+
                                     │
                                     ▼
                      +-----------------------------+
                      |       Planner Agent         |
                      | - Decomposes user journeys  |
                      | - Emits Atomic Step Graph   |
                      +-----------------------------+
                                     │
                                     ▼
                      +-----------------------------+
                      |      Generator Agent        |
                      | - Inspects Live Page State  |
                      | - Resolves Active Locators  |
                      | - Dispatches Actions        |
                      +-----------------------------+
                                     │
                                     ▼
                      +-----------------------------+
                      | Playwright Execution Engine |
                      +-----------------------------+
                                     │
                      +──────────────┴──────────────+
                      │                             │
                   [PASS]                        [FAIL]
                      │                             │
                      ▼                             ▼
             Step Logged as OK             +------------------+
                      │                    |   Healer Agent   |
                      │                    | - Intercepts Err |
                      │                    | - Inspects Diff  |
                      │                    | - Patches Target |
                      │                    +------------------+
                      │                             │
                      │                       [Heal Status]
                      │                       ┌─────┴─────┐
                      │                    Success     Failure
                      │                       │           │
                      │                       ▼           ▼
                      │                  Resume Test   Log Bug
                      │                       │           │
                      └───────────────────────┴───────────┘
                                     │
                                     ▼
                     +-------------------------------+
                     | Unified Report & Patch Output |
                     +-------------------------------+
```

---

## 📂 Project Structure

```
playwrightFrameworkPython/
├── config/
│   ├── __init__.py
│   └── settings.py              # Pydantic settings & environment configuration
├── schema/
│   ├── __init__.py
│   ├── test_plan.py             # Atomic Step, Intent, Action, Assertion, TestPlan schemas
│   ├── page_state.py           # Element node, Accessibility snapshot schemas
│   └── execution_result.py     # Execution step log, Self-healing audit entry schema
├── core/
│   ├── __init__.py
│   ├── browser_manager.py       # Playwright browser context, tracing, video, screenshots
│   ├── dom_extractor.py         # Page inspector & compact aria-snapshot generator
│   ├── locator_registry.py      # Persistent locator registry (locator.registry.json)
│   ├── security_masker.py       # PII & credential masker in prompts and reports
│   └── reporter.py              # HTML execution report & Self-Healing Audit reporter
├── agents/
│   ├── __init__.py
│   ├── base_agent.py            # Multi-provider LLM interface (OpenAI, Gemini, Anthropic, Mock)
│   ├── planner_agent.py         # Requirements decomposition & Atomic Step Graph builder
│   ├── generator_agent.py       # Live page DOM-to-Playwright locator generator
│   └── healer_agent.py          # Failure interceptor context analyzer & locator repair engine
├── engine/
│   ├── __init__.py
│   ├── failure_interceptor.py  # Runtime exception hook & context collector
│   ├── executor.py              # Playwright action dispatcher with auto-waiting
│   └── runner.py                # Main orchestrator pipeline
├── tests/
│   ├── test_planner.py          # Planner agent unit tests
│   ├── test_healer.py           # Self-healing & registry unit tests
│   ├── test_end_to_end.py       # End-to-end autonomous integration test
│   └── sample_requirements/     # Sample requirements (Markdown, Plain Text, Gherkin)
├── main.py                      # CLI entrypoint
├── pytest.ini
├── requirements.txt
└── README.md
```

---

## 🚀 Quick Start Guide

### 1. Installation & Environment Setup

```bash
# Clone or navigate to the project workspace
cd playwrightFrameworkPython

# Install dependencies
pip install -r requirements.txt

# Install Playwright browser binaries
playwright install chromium
```

### 2. Configuration (.env)

Copy `.env.example` to `.env` and set optional LLM API keys:

```env
# Supported LLM Providers: auto, openai, gemini, anthropic, mock
LLM_PROVIDER=auto
OPENAI_API_KEY=your_openai_api_key_here
GEMINI_API_KEY=your_gemini_api_key_here

# Browser Parameters
BROWSER_TYPE=chromium
HEADLESS=true
```

---

## 💻 Usage

### Run via CLI

```bash
# Run using default sample requirement file (SauceDemo E-Commerce Checkout)
python main.py

# Run custom requirement file in headed mode
python main.py --requirement tests/sample_requirements/saucedemo_checkout.md --headed

# Run with Gherkin BDD scenario file
python main.py --requirement tests/sample_requirements/saucedemo_login.feature

# Run with target URL override
python main.py --requirement "Navigate to sauce-demo, log in as standard_user with secret_sauce" --url https://www.saucedemo.com
```

### Run via Pytest

```bash
# Run full test suite
pytest
```

---

## 📊 Reports & Observability Output

After execution, all artifacts are saved under `output/artifacts/`:

1. **HTML Execution Dashboard**: `output/artifacts/reports/execution_report.html`
2. **Self-Healing Audit Report**: Embedded in HTML report detailing Intercepted Errors, Failed Locators vs. Healed Locators, Confidence Scores, and Verification Status.
3. **Playwright Traces**: `output/artifacts/traces/trace_<timestamp>.zip` (Inspect with `npx playwright show-trace <trace.zip>`)
4. **Failure Screenshots & Session Videos**: `output/artifacts/screenshots/` and `output/artifacts/videos/`
5. **Persisted Locator Registry**: `locator.registry.json`
