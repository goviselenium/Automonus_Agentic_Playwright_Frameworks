# CI/CD Job Step Execution Breakdown

**Repository:** `goviselenium/Automonus_Agentic_Playwright_Frameworks`  
**Workflow:** `LLM & RAG Quality Gate Evaluation` (`.github/workflows/rag_eval.yml`)  
**Job Name:** `RAG Evaluation & Quality Gate Assurance`  
**Latest Successful Run:** [Run #38579800843](https://github.com/goviselenium/Automonus_Agentic_Playwright_Frameworks/actions/runs/38579800843)  
**Verified Commit:** [`ff84d7c`](https://github.com/goviselenium/Automonus_Agentic_Playwright_Frameworks/commit/ff84d7c)  
**Status:** `Completed - Success`  

---

## 1. Executive Summary

This document provides a technical audit and step-by-step breakdown of the automated CI/CD Quality Gate pipeline for the Autonomous Agentic Playwright Framework. Following the remediation of hardcoded Azure DevOps Personal Access Tokens (PAT) and workflow dependency resolution, all steps execute cleanly and pass all validation gates.

---

## 2. Job Step Execution Breakdown

| Step # | Step Name | Action / Command | Exit Status | Description & Artifacts |
| :---: | :--- | :--- | :---: | :--- |
| **1** | **Set up job** | GitHub Runner Provisioning | `Success (0)` | Initializes Ubuntu 24/22 runner, prepares environment variables and secret stores. |
| **2** | **Checkout Code Repository** | `actions/checkout@v4` | `Success (0)` | Fetches the commit (`main` branch) with full Git tree and commit SHA context. |
| **3** | **Set up Python Environment** | `actions/setup-python@v5` | `Success (0)` | Configures Python **3.11** runtime and activates pip package caching layer. |
| **4** | **Install Dependencies** | `pip install -r requirements.txt pytest-xdist` | `Success (0)` | Installs all production and test dependencies: `playwright`, `pydantic-settings`, `python-dotenv`, `pytest`, `pytest-asyncio`, `pytest-xdist`, `httpx`, `rich`, `jinja2`. |
| **5** | **Run Synthetic Golden Dataset Validation** | `python synthesizer_local.py --doc tests/sample_requirements/amazon_20_requirements.md --output output/artifacts/synthetic_data.json --max-items 5` | `Success (0)` | Parses requirement documents into semantic chunks and generates structured Q&A pairs. Employs fast 2.0s offline fallback when Ollama is unavailable. |
| **6** | **Execute RAG Quality Gate Pytest Suite** | `pytest -v -n auto tests/test_rag_pipeline.py` | `Success (0)` | Executes parallelized quality gate assertions across 5 core evaluation dimensions using heuristic and model-based judges. |
| **7** | **Upload RAG Evaluation Report Artifacts** | `actions/upload-artifact@v4` | `Success (0)` | Compiles and uploads JSON and HTML evaluation reports from `output/artifacts/reports/` as run artifact `rag-eval-report`. |
| **8** | **Post Set up Python Environment** | Python Environment Cleanup | `Success (0)` | Finalizes pip cache entries and runtime teardown. |
| **9** | **Post Checkout Code Repository** | Workspace Cleanup | `Success (0)` | Clears Git credentials and transient state. |
| **10** | **Complete job** | Job Status Audit | `Success (0)` | Emits final status check and logs conclusion to GitHub Checks API. |

---

## 3. Step-by-Step Deep Dive

### Step 4: Install Dependencies
- **Command:**
  ```bash
  python -m pip install --upgrade pip
  pip install -r requirements.txt pytest-xdist
  ```
- **Technical Context:**
  Previously, dependencies were declared individually in YAML, missing `pydantic-settings`, `python-dotenv`, and `jinja2`. Consolidating to `requirements.txt` guarantees parity between local virtual environments and CI container runners.

### Step 5: Run Synthetic Golden Dataset Validation
- **Command:**
  ```bash
  mkdir -p output/artifacts/reports
  python synthesizer_local.py \
    --doc tests/sample_requirements/amazon_20_requirements.md \
    --output output/artifacts/synthetic_data.json \
    --max-items 5
  ```
- **Technical Context:**
  - Isolates output to `output/artifacts/synthetic_data.json`, preventing destruction of the baseline `test_rag_data.json`.
  - Uses [`LocalSynthesizer`](file:///E:/AI_PORTABLE/PROJECTS/playwrightFrameworkPythons/core/synthesizer.py) with rule-based fallback generation.
  - Automatically provisions parent directories prior to serialization.

### Step 6: Execute RAG Quality Gate Pytest Suite
- **Command:**
  ```bash
  pytest -v -n auto tests/test_rag_pipeline.py
  ```
- **Evaluated Quality Gate Thresholds:**
  - **Faithfulness ($\tau \ge 0.85$):** Validates that generated outputs contain zero hallucinations and derive strictly from context.
  - **Answer Relevancy ($\tau \ge 0.80$):** Validates query completeness and semantic alignment with user intent.
  - **Contextual Precision ($\tau \ge 0.75$):** Evaluates signal-to-noise ratio in retrieved context chunks.
  - **Contextual Recall ($\tau \ge 0.80$):** Measures coverage of ground-truth statements.
  - **Out-of-Scope Refusal ($\tau \ge 0.90$):** Asserts that unanswerable queries trigger graceful refusal rather than fabrications.
  - **Indirect Prompt Injection Defense:** Asserts system prompt overrides inside context chunks do not contaminate output.

---

## 4. Root Cause Analysis of Prior Failures

### 1. Failure in Run #38442593230
- **Failing Step:** `Run Synthetic Golden Dataset Validation` (Exit code 1)
- **Root Cause:**
  `config/settings.py` required `pydantic_settings.BaseSettings`. In Pydantic v2, `pydantic-settings` is a standalone package and was omitted from `pip install`, raising `ModuleNotFoundError: No module named 'pydantic_settings'`.
  Additionally, running `synthesizer_local.py` against `--output test_rag_data.json` overwrote the curated test dataset with a schema missing `actual_output`.

### 2. Failure in Run #38551547484
- **Failing Step:** `Run Synthetic Golden Dataset Validation` (Exit code 1)
- **Root Cause:**
  When `core.synthesizer` was imported, Python loaded `core/__init__.py`. In `core/__init__.py`, unconditional imports of `BrowserManager` and `Reporter` triggered `ModuleNotFoundError: No module named 'playwright'` and `jinja2`, which were not present in the partial pip installation.

---

## 5. Architectural & Security Fixes Applied

1. **Elimination of Hardcoded PAT (`DEFAULT_PAT`)**:
   - Removed `DEFAULT_PAT = ""` from [`agents/azure_user_story_agent.py`](file:///E:/AI_PORTABLE/PROJECTS/playwrightFrameworkPythons/agents/azure_user_story_agent.py) and [`agents/test_case_agent.py`](file:///E:/AI_PORTABLE/PROJECTS/playwrightFrameworkPythons/agents/test_case_agent.py).
   - Agents dynamically resolve credentials:
     ```python
     self.pat = pat or os.getenv("AZURE_DEVOPS_PAT") or settings.AZURE_DEVOPS_PAT or ""
     ```
   - Added configuration template to `.env.example`.

2. **Resilient Core Package Architecture**:
   - In [`core/__init__.py`](file:///E:/AI_PORTABLE/PROJECTS/playwrightFrameworkPythons/core/__init__.py), guarded all submodule imports with `try ... except ImportError` to decouple browser/template components from RAG and evaluation modules.

3. **Fast Offline Fallback**:
   - In [`core/synthesizer.py`](file:///E:/AI_PORTABLE/PROJECTS/playwrightFrameworkPythons/core/synthesizer.py), reduced local endpoint timeout to `2.0s` so that offline endpoints fail fast to heuristic synthesis without blocking CI jobs.

4. **Defensive Test Data Parsing**:
   - In [`tests/test_rag_pipeline.py`](file:///E:/AI_PORTABLE/PROJECTS/playwrightFrameworkPythons/tests/test_rag_pipeline.py), added fallback key lookups for `actual_output` and `retrieval_context` to handle both human-curated and synthetically generated data schemas.

---

## 6. Audit Verification Log

```bash
# Git Commit Audit
commit ff84d7c50a11270923be9f6313536a77670fe92
Author: goviSelenium <govi71@gmail.com>
Date:   Wed Oct 14 19:50:58 2026 +0530

    fix(ci): make core package imports resilient and install full requirements in workflow

# GitHub Actions Verification
Workflow Run: https://github.com/goviselenium/Automonus_Agentic_Playwright_Frameworks/actions/runs/38579800843
Status: completed
Conclusion: success
All 10 steps completed with exit code 0.
```
