# User Guide: Autonomous Agentic Playwright Framework

This guide provides comprehensive instructions on how to configure, run, and customize tests using the Autonomous Agentic Playwright Framework. It covers how to override target **Base URLs**, select **LLM Providers** (including local Ollama models), run requirements in different formats, and inspect execution artifacts.

---

## 📋 Table of Contents

1. [Quick Start Overview](#1-quick-start-overview)
2. [Configuring & Overriding Base URL](#2-configuring--overriding-base-url)
   - [Method 1: CLI `--url` Parameter](#method-1-cli---url-parameter)
   - [Method 2: Environment Variable (.env)](#method-2-environment-variable-env)
   - [Method 3: Requirement Document Definition](#method-3-requirement-document-definition)
   - [Method 4: Programmatic Python API](#method-4-programmatic-python-api)
   - [Method 5: Pytest Integration](#method-5-pytest-integration)
3. [LLM Provider Configuration](#3-llm-provider-configuration)
   - [Using Local Ollama (e.g. llama3.2)](#using-local-ollama-eg-llama32)
   - [Using OpenAI or Gemini](#using-openai-or-gemini)
   - [Offline / Deterministic Fallback Mode](#offline--deterministic-fallback-mode)
4. [Supported Requirement Formats](#4-supported-requirement-formats)
5. [Running Test Suites](#5-running-test-suites)
6. [Reports & Self-Healing Audit Logs](#6-reports--self-healing-audit-logs)
7. [LLM & RAG Testing & Quality Gating Framework](#7-llm--rag-testing--quality-gating-framework)
   - [Core Evaluation Metrics & Thresholds](#core-evaluation-metrics--quality-gate-thresholds-tau)
   - [Synthetic Golden Datasets Generator](#generating-synthetic-golden-datasets-synthesizer_localpy)
   - [RAG Pytest Quality Gates](#running-rag-pytest-quality-gates-teststest_rag_pipelinepy)
   - [Edge-Case & Adversarial Verification](#edge-case--adversarial-verification)
   - [CI/CD Workflow & Artifact Exports](#cicd-automated-workflow-githubworkflowsrag_evalyml)
8. [Playwright Use Case Test Planner](#8-playwright-use-case-test-planner)
   - [Standard Use Case Template Structure](#standard-use-case-template-structure)
   - [Generating Test Plans (`--plan-only`, `--plan-output`)](#generating-test-plans---plan-only---plan-output)
9. [Python Coding Standards Agent](#9-python-coding-standards-agent)
   - [Coding Standards Overview (PEP 8 & Best Practices)](#coding-standards-overview-pep-8--best-practices)
   - [Auditing & Auto-Fixing Code (`--standards`, `--standards-fix`)](#auditing--auto-fixing-code---standards---standards-fix)
   - [Tooling Configuration (`pyproject.toml`)](#tooling-configuration-pyprojecttoml)
10. [Azure DevOps Agile Work Item Automation](#10-azure-devops-agile-work-item-automation)
    - [User Story Creation Agent (`--azure-stories`)](#user-story-creation-agent---azure-stories)
    - [Test Case Creation Agent with XML Steps (`--test-cases`)](#test-case-creation-agent-with-xml-steps---test-cases)
    - [Traceability & Linking Matrix](#traceability--linking-matrix)
11. [Azure DevOps Git Repository Synchronization](#11-azure-devops-git-repository-synchronization)

---

## 1. Quick Start Overview

The framework accepts plain English test requirements, decomposes them into atomic step graphs, dynamically inspects live DOM accessibility trees, and executes Playwright actions with dynamic self-healing.

```bash
# Basic CLI execution against default scenario
python main.py

# Run with custom requirement file
python main.py --requirement tests/sample_requirements/saucedemo_checkout.md
```

---

## 2. Configuring & Overriding Base URL

When the target application base URL changes across environments (e.g., `Staging`, `QA`, `Production`, or local `http://localhost:3000`), you can override the base URL using any of the following methods:

### Method 1: CLI & Interactive Runtime Prompting (Recommended)

#### Option A: Pass URL via `--url` CLI Flag
Pass the `-u` or `--url` argument directly when executing `main.py`:

```bash
# Run scenario against Staging environment
python main.py --requirement tests/sample_requirements/saucedemo_checkout.md --url https://staging.my-app.com
```

#### Option B: Interactive Runtime Prompt (`--interactive` or terminal prompt)
If no `--url` flag is passed in an interactive terminal session, the CLI automatically prompts you at runtime to input your Target Base URL:

```bash
# Simply execute main.py and provide URL when prompted:
python main.py

# Terminal Output:
-----------------------------------------------------------
🤖 Autonomous Agentic Playwright Framework - Runtime Setup
-----------------------------------------------------------
🌐 Enter Target Base URL (leave blank to infer from requirement): https://qa.saucedemo.com
```

### Method 2: Environment Variable (.env)

Set the default target base URL or environment parameter in your `.env` configuration file:

```env
# .env
TARGET_URL=https://qa.saucedemo.com
BROWSER_TYPE=chromium
HEADLESS=true
LLM_PROVIDER=auto
```

Or pass it dynamically in your shell session:

```bash
# Linux / macOS / Bash
TARGET_URL=https://qa.saucedemo.com python main.py

# Windows PowerShell
$env:TARGET_URL="https://qa.saucedemo.com"; python main.py
```

### Method 3: Requirement Document Definition

Specify the base URL directly inside your Markdown or Gherkin requirement file. The **Planner Agent** automatically extracts and prioritizes URLs declared within the text.

#### Markdown (`.md`) Format:
```markdown
# Scenario: Staging E-Commerce Checkout

## Target Base URL
`https://staging.saucedemo.com`

## Acceptance Criteria
1. Navigate to home page.
2. Enter standard credentials and click login.
```

#### Gherkin (`.feature`) Format:
```gherkin
Feature: User Login
  Scenario: Login to QA Portal
    Given Navigate to https://qa.saucedemo.com
    When Enter username standard_user
    And Enter password secret_sauce
    And Click Login button
```

### Method 4: Programmatic Python API

If you are invoking the runner inside custom Python code or test frameworks, pass `target_url` directly to `AutonomousTestRunner().run()`:

```python
import asyncio
from engine.runner import AutonomousTestRunner

async def run_staging_test():
    runner = AutonomousTestRunner()
    
    report = await runner.run(
        requirement_input="tests/sample_requirements/saucedemo_checkout.md",
        target_url="https://staging.saucedemo.com"
    )
    
    print(f"Execution Status: {report.overall_status.value}")
    print(f"Total Steps Passed: {report.passed_steps}/{report.total_steps}")

asyncio.run(run_staging_test())
```

### Method 5: Pytest Integration

To run tests against different base URLs via Pytest:

```bash
# Run pytest with base-url override
pytest --base-url=https://staging.saucedemo.com -v
```

---

## 3. LLM Provider Configuration

The framework supports multiple LLM providers as well as a zero-token heuristic engine.

### Using Local Ollama (e.g. llama3.2)

To run entirely locally without cloud API keys:

```bash
# Ensure local Ollama server is running (http://127.0.0.1:11434)
ollama run llama3.2:latest

# Run main runner using Ollama
python main.py --provider ollama
```

In `.env`:
```env
LLM_PROVIDER=ollama
LLM_MODEL=llama3.2:latest
LLM_BASE_URL=http://127.0.0.1:11434
```

### Using OpenAI or Gemini

Set API keys in `.env` or system environment variables:

```env
# OpenAI Configuration
LLM_PROVIDER=openai
LLM_MODEL=gpt-4o-mini
OPENAI_API_KEY=sk-...

# Google Gemini Configuration
LLM_PROVIDER=gemini
LLM_MODEL=gemini-2.5-flash
GEMINI_API_KEY=AIzaSy...
```

### Offline / Deterministic Fallback Mode

If no API keys are provided or network connection is unavailable, the framework automatically uses its rule-based heuristic engine to extract accessible elements and execute steps seamlessly:

```bash
python main.py --provider mock
```

---

## 4. Supported Requirement Formats

The framework ingests the following file formats out of the box:

| Format | Extension | Example Input |
| :--- | :--- | :--- |
| **Markdown** | `.md` | Plain text user stories with bullet points and URLs |
| **Gherkin BDD** | `.feature` | Standard `Given`, `When`, `Then` steps |
| **Plain Text** | `.txt` | Unstructured sentences or instructions |
| **Direct Text** | String | `"Navigate to https://saucedemo.com and login as standard_user"` |

---

## 5. Running Test Suites

### Execute Single Scenario via CLI

```bash
python main.py --requirement tests/sample_requirements/saucedemo_checkout.md --url https://www.saucedemo.com
```

### Run Full Pytest Suite

```bash
pytest -v
```

### Disabling Self-Healing for Strict Regression Tests

To run without self-healing enabled:

```bash
python main.py --no-heal
```

---

## 6. Reports & Self-Healing Audit Logs

After each execution, all artifacts are saved to `output/artifacts/`:

1. **HTML Dashboard**: `output/artifacts/reports/execution_report.html`
   - Interactive breakdown of step timing, pass/fail status, and embedded screenshots.
   - **Self-Healing Audit Table**: Displays original failed locator vs. healed replacement locator, confidence score, and verification status.
2. **Playwright Trace Viewer (`trace.zip`)**:
   - Inspect step-by-step DOM snapshots and video recordings using:
     ```bash
     npx playwright show-trace output/artifacts/traces/trace_<timestamp>.zip
     ```
3. **Persistent Locator Registry**:
   - Healed locators are stored in `locator.registry.json` for reuse across subsequent runs.

---

## 7. LLM & RAG Testing & Quality Gating Framework

The platform includes an end-to-end evaluation, quality gating, and synthetic dataset generation framework for Large Language Model (LLM) and Retrieval-Augmented Generation (RAG) applications.

```
                      [Unstructured Docs (PDF, TXT, MD)]
                                       │
                                       ▼
                     [Synthesizer / TestsetGenerator]
                     (Local Ollama/vLLM or OpenAI APIs)
                                       │
                                       ▼
                           [Golden Dataset (JSON)]
                                       │
                ┌──────────────────────┴──────────────────────┐
                ▼                                             ▼
        [Production RAG App]                        [Test Orchestrator]
        ├─ Retrieval Engine                         (Pytest + RAGEvaluator)
        └─ Generation Model                                   │
                │                                             │
      (actual_output, context)                                │
                │                                             │
                └──────────────────────┬──────────────────────┘
                                       │
                                       ▼
                       [Evaluation Engine (LLM Judge)]
                       ├─ FaithfulnessMetric (>= 0.85)
                       ├─ AnswerRelevancyMetric (>= 0.80)
                       ├─ ContextualPrecisionMetric (>= 0.75)
                       └─ ContextualRecallMetric (>= 0.80)
                                       │
                        ┌──────────────┴──────────────┐
                        ▼                             ▼
                 [Status: PASSED]              [Status: FAILED]
                        │                             │
                 Merge Permitted             Block PR & Export Log
```

### Core Evaluation Metrics & Quality Gate Thresholds ($\tau$)

| Target Layer | Metric | Functional Definition | Critical Failure Addressed | Default Gate ($\tau$) |
| --- | --- | --- | --- | --- |
| **Generator** | **Faithfulness** | Ratio of statements in response inferred strictly from context. | Hallucinations; unsupported claims. | $\ge 0.85$ |
| **Generator** | **Answer Relevancy** | Semantic relevance and completeness relative to user query. | Fluff, evasiveness, missing constraints. | $\ge 0.80$ |
| **Retriever** | **Contextual Precision** | Ranking accuracy of chunks ($k=1, 2$). | Low MRR; high context noise. | $\ge 0.75$ |
| **Retriever** | **Contextual Recall** | Ratio of ground-truth statements captured across context. | Under-fetching; missed documentation. | $\ge 0.80$ |

---

### Generating Synthetic Golden Datasets (`synthesizer_local.py`)

Generate domain-aligned ground-truth evaluation datasets directly from unstructured documentation without manual labeling.

#### Features:
- Parses `.pdf`, `.txt`, `.md`, `.docx` into semantic paragraph chunks.
- Supports question evolutions: `simple` (single-fact), `multihop` (complex reasoning), and `conditional` (constraint-based).
- Dual-Model Architecture: Drafting generator model + Strict critic model filtering.

#### Command Line Execution:
```bash
# Generate 10 synthetic Q&A golden items from documentation
python synthesizer_local.py --doc tests/sample_requirements/amazon_20_requirements.md --output test_rag_data.json --max-items 10
```

#### Structured Output (`test_rag_data.json`):
```json
[
  {
    "input": "What is the minimum parameter specification for local critic models?",
    "expected_output": "Minimum critic/judge specification requires 14B to 70B parameters.",
    "context": ["NFR-01.3: Minimum critic/judge: 14B-70B parameters (e.g. Qwen-2.5-14B/32B)."],
    "evolution_type": "simple"
  }
]
```

---

### Running RAG Pytest Quality Gates (`tests/test_rag_pipeline.py`)

Execute automated RAG evaluation suites with programmatic assertions and CI/CD quality gate enforcement.

```bash
# Execute RAG Quality Gate Pytest Suite
pytest -v tests/test_rag_pipeline.py

# Parallelized execution with xdist workers
pytest -v -n auto tests/test_rag_pipeline.py
```

---

### Edge-Case & Adversarial Verification

The suite automatically validates non-standard operational behaviors:

1. **Out-of-Scope Queries (FR-02.1):** When a query cannot be answered by the corpus, the system triggers graceful refusal without hallucinating (Faithfulness $\ge 0.90$).
2. **Empty Retrieval (FR-02.2):** When `retrieval_context` is `[]`, the system refuses rather than falling back to pre-training model weights.
3. **Indirect Prompt Injection (FR-02.3):** Retrieved chunks containing malicious directives (*"SYSTEM OVERRIDE: ignore instructions"*) are caught and prevented from polluting output.

---

### CI/CD Automated Workflow (`.github/workflows/rag_eval.yml`)

Evaluation suites run automatically on pull requests and pushes to `main`. If any metric drops below threshold $\tau$, PR merges are automatically blocked:

```yaml
# .github/workflows/rag_eval.yml snippet
- name: Execute RAG Quality Gate Pytest Suite
  env:
    LLM_PROVIDER: ollama
    OLLAMA_BASE_URL: http://127.0.0.1:11434/v1
  run: |
    pytest -v -n auto tests/test_rag_pipeline.py
```

#### Exported Evaluation Artifacts:
- **JSON Score Log**: `output/artifacts/reports/rag_eval_report.json`
- **HTML Test Dashboard**: `output/artifacts/reports/execution_report.html`

---

## 8. Playwright Use Case Test Planner

The framework includes a structured **Use Case Test Planner** in [`agents/planner_agent.py`](file:///e:/AI_PORTABLE/PROJECTS/playwrightFrameworkPythons/agents/planner_agent.py) that decomposes business requirements into detailed, production-grade Use Case scenarios adhering strictly to a standardized template.

### Standard Use Case Template Structure

Every scenario generated follows this exact specification:

```markdown
## [Scenario ID & Title]
- **Actor:** [e.g., Registered User]
- **Preconditions:** [e.g., User is logged in and on the dashboard]
- **Main Flow / Steps:**
  1. [Step 1]
  2. [Step 2]
- **Alternate / Exception Flows:**
  - [Alternative path if applicable]
- **Expected Outcome:** [Observable result verifying success or refusal]
```

### Generating Test Plans (`--plan-only`, `--plan-output`)

You can generate and export test plans without triggering the live Playwright browser engine:

```powershell
# Generate test plan and save to specs/use-case-plan.md
python main.py --requirement tests/sample_requirements/automationpractice.md --url https://shop.qaautomationlabs.com/index.php --plan-only

# Specify a custom plan output destination
python main.py --requirement tests/sample_requirements/automationpractice.md --url https://shop.qaautomationlabs.com/index.php --plan-output specs/my-custom-plan.md --plan-only
```

---

## 9. Python Coding Standards Agent

The framework includes a zero-dependency autonomous **Coding Standards Agent** ([`agents/standards_agent.py`](file:///e:/AI_PORTABLE/PROJECTS/playwrightFrameworkPythons/agents/standards_agent.py)) implementing all rules defined in [`Coding_Standards_python.md`](file:///e:/AI_PORTABLE/PROJECTS/playwrightFrameworkPythons/Coding_Standards_python.md).

### Coding Standards Enforced
1. **PEP 8 Formatting:**
   - 4 spaces indentation per level (tabs strictly forbidden).
   - Maximum line length of **88 characters** (Black standard).
   - Blank lines: 2 blank lines before top-level functions/classes, 1 blank line between methods.
   - Import grouping: Sorted and categorized into **1. Stdlib**, **2. Third-party**, **3. Local application**, separated by blank lines.
2. **Naming Conventions:**
   - Classes: `PascalCase`
   - Functions & Methods: `snake_case`
   - Constants: `UPPER_CASE`
   - Private attributes: `_leading_underscore`
3. **Modern Python Best Practices:**
   - Type hints on function parameters and return annotations (`-> ReturnType`).
   - Google/Sphinx style docstrings on public modules, classes, and methods.
   - Modern f-strings preferred over old-style `%` formatting and `.format()`.
4. **Tooling Integration:**
   - Automatic generation of [`pyproject.toml`](file:///e:/AI_PORTABLE/PROJECTS/playwrightFrameworkPythons/pyproject.toml) configured for **Ruff**, **Black**, and **Mypy**.

### CLI Usage: Auditing & Auto-Fixing

```powershell
# Audit codebase against Coding_Standards_python.md
python main.py --standards .

# Audit and automatically fix indentation, blank lines, and imports
python main.py --standards agents/ --standards-fix

# Generate production pyproject.toml configuration
python -m agents.standards_agent --gen-config
```

The agent outputs a detailed audit report in Markdown at [`output/artifacts/standards_report.md`](file:///e:/AI_PORTABLE/PROJECTS/playwrightFrameworkPythons/output/artifacts/standards_report.md).

---

## 10. Azure DevOps Agile Work Item Automation

The framework bridges automated testing with Agile project management by transforming test plans directly into Azure DevOps work items via the Azure DevOps REST API (v7.1).

### User Story Creation Agent (`--azure-stories`)

[`AzureUserStoryAgent`](file:///e:/AI_PORTABLE/PROJECTS/playwrightFrameworkPythons/agents/azure_user_story_agent.py) parses [`specs/use-case-plan.md`](file:///e:/AI_PORTABLE/PROJECTS/playwrightFrameworkPythons/specs/use-case-plan.md) and creates User Stories in Azure DevOps Boards following [`CreateUserStory.md`](file:///e:/AI_PORTABLE/PROJECTS/playwrightFrameworkPythons/CreateUserStory.md):

```powershell
# Create User Stories in Azure DevOps from test plan
python main.py --azure-stories

# Provide explicit Personal Access Token (PAT)
python main.py --azure-stories --pat <YOUR_AZURE_DEVOPS_PAT>
```

Each generated story features:
- **Title:** `[<Scenario ID>] <Title>`
- **Description (`System.Description`):** Structured HTML containing the User Story statement (*As an... I want to... So that...*), Preconditions, Main Execution Flow, and Exception Paths.
- **Acceptance Criteria (`Microsoft.VSTS.Common.AcceptanceCriteria`):** Concrete verification statements and test assertions.
- **Tags:** `Playwright; Automation; E2E; Use-Case; <Scenario ID>`.

Published story mappings are saved to [`specs/azure-user-stories.md`](file:///e:/AI_PORTABLE/PROJECTS/playwrightFrameworkPythons/specs/azure-user-stories.md).

---

### Test Case Creation Agent with XML Steps (`--test-cases`)

[`TestCaseCreateAgent`](file:///e:/AI_PORTABLE/PROJECTS/playwrightFrameworkPythons/agents/test_case_agent.py) creates specialized `Test Case` work items in Azure DevOps following [`CreateTestCases.md`](file:///e:/AI_PORTABLE/PROJECTS/playwrightFrameworkPythons/CreateTestCases.md):

```powershell
# Create Test Cases with XML steps and link to User Stories
python main.py --test-cases

# Run agent module directly
python -m agents.test_case_agent --plan specs/use-case-plan.md --stories specs/azure-user-stories.md
```

#### Step XML Embedding
Test steps are encoded in `/fields/Microsoft.VSTS.TCM.Steps`:
```xml
<steps id="0" last="5">
  <step id="2" type="ActionStep">
    <parameterizedString isformatted="true">Click autofill demo credentials button</parameterizedString>
    <description/>
  </step>
  <step id="3" type="ValidateStep">
    <parameterizedString isformatted="true">Click login submit button</parameterizedString>
    <parameterizedString isformatted="true">Redirects to product catalog page</parameterizedString>
  </step>
</steps>
```

#### Traceability & Linking Matrix
The agent reads [`specs/azure-user-stories.md`](file:///e:/AI_PORTABLE/PROJECTS/playwrightFrameworkPythons/specs/azure-user-stories.md) and automatically adds `Microsoft.VSTS.Common.TestedBy-Reverse` relations so every Test Case is linked to its parent User Story:

| Scenario | Parent User Story | Created Test Case | Link Status |
| :---: | :---: | :---: | :---: |
| `UC-01` | Story `#7` | Test Case `#17` | Linked |
| `UC-02` | Story `#8` | Test Case `#18` | Linked |
| `UC-03` | Story `#9` | Test Case `#19` | Linked |
| `UC-04` | Story `#10` | Test Case `#20` | Linked |
| `UC-05` | Story `#11` | Test Case `#21` | Linked |
| `UC-06` | Story `#12` | Test Case `#22` | Linked |
| `UC-07` | Story `#13` | Test Case `#23` | Linked |
| `UC-08` | Story `#14` | Test Case `#24` | Linked |
| `UC-09` | Story `#15` | Test Case `#25` | Linked |

Summary is saved to [`specs/azure-test-cases.md`](file:///e:/AI_PORTABLE/PROJECTS/playwrightFrameworkPythons/specs/azure-test-cases.md).

---

## 11. Azure DevOps Git Repository Synchronization

The codebase is version-controlled and synchronized with Azure DevOps Repos:
- **Remote URL:** `https://govidev.visualstudio.com/Frameworks/_git/Frameworks`
- **Tracked Branch:** `main`

### Routine Check-in Commands:
```powershell
# Stage changes
git add .

# Commit with semantic message
git commit -m "feat: updated test plans and agents"

# Push to Azure DevOps
git push origin main
```


