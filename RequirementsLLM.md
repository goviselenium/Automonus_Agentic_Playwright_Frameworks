# Project Requirements: Python-Based LLM Testing Framework

This document outlines the system requirements, tool versions, dependencies, and environment configurations needed to set up and run the integrated LLM testing framework combining **Playwright**, **Pytest**, **DeepEval**, and **Promptfoo**.

---

## 1. System Prerequisites

* **Operating System**: Linux (Ubuntu 22.04+ recommended), macOS (Ventura+), or Windows 10/11 (via WSL2).
* **Python Version**: Python 3.10, 3.11, or 3.12.
* **Node.js Version**: Node.js 18.x or higher (required globally for Promptfoo CLI execution and Playwright core dependencies).
* **Git**: For version control and CI/CD repository management.

---

## 2. Core Framework Packages & Versions

### Python Dependencies (`requirements.txt`)
* `pytest >= 8.0.0`: Core test runner orchestrating unit, integration, and UI tests.
* `playwright >= 1.45.0`: Headless browser automation library for UI workflow tests and Playwright Test Agents.
* `deepeval >= 1.0.0`: LLM evaluation harness for programmatic assertions (hallucination, answer relevance, bias).
* `PyYAML >= 6.0`: Parser for reading Promptfoo YAML configuration files.
* `requests >= 2.31.0`: HTTP client for model endpoints or webhook verification.

### Node.js Global/Local Dependencies
* `promptfoo`: Evaluation CLI toolkit for prompt matrix testing and red-teaming (installed via `npm install -g promptfoo` or run via `npx promptfoo`).

---

## 3. Environment Variables & API Keys

To execute LLM evaluations via DeepEval and Promptfoo against commercial provider models (OpenAI, Anthropic, etc.), ensure the following environment variables are exported in your terminal or configured in a local `.env` file:

```bash
# Example .env configuration
OPENAI_API_KEY="sk-..."
ANTHROPIC_API_KEY="sk-ant-..."
DEEPEVAL_FIRST_NAME="..." # Optional: for telemetry tracking opt-out/in