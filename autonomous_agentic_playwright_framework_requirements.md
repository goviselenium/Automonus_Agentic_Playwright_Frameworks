# Software Requirements Specification (SRS)
## Project: Autonomous Agentic Playwright Test Automation Framework

---

## 1. Executive Summary & Vision

### 1.1 Objective
The objective of this project is to develop an autonomous, website-agnostic end-to-end test automation framework built on **Playwright** and powered by specialized **Agentic AI models** (Planner, Generator, Healer). 

Traditional automation frameworks suffer from high maintenance overhead, locator brittleness, and rigid test scripts tied to specific page structures. This framework eliminates pre-coded Page Object Models and hardcoded locators by taking unstructured requirements or use cases in plain English, analyzing target web applications dynamically at runtime, synthesizing executable Playwright interactions, and self-healing broken steps automatically when application UIs change.

### 1.2 Core Architectural Principles
* **Website Agnostic**: Operates against any arbitrary web application (React, Angular, Vue, standard HTML5, dynamic single-page applications) without domain-specific source-code preconfigurations.
* **Agentic Specialization**: Employs three distinct single-responsibility agents:
  * **Planner Agent**: Interprets business intent and breaks it into stateful, atomic test steps.
  * **Generator Agent**: Inspects active DOM and accessibility trees to synthesize executable Playwright commands.
  * **Healer Agent**: Intercepts step failures, identifies UI/DOM drift, repairs broken locators, and restores test execution.
* **Deterministic & Safe**: Employs strict JSON schemas, validation thresholds, auto-waiting mechanisms, and secure environment isolation to avoid non-deterministic hallucinations.
* **Actionable Observability**: Captures complete step-level artifacts (traces, videos, network logs, DOM diffs, and healed locator patch reports).

---

## 2. Input Specifications

The framework must accept and process the following inputs:

### 2.1 Test Requirement Ingestion
* **Formats Supported**:
  * Markdown documents containing user stories and acceptance criteria.
  * Plain-text scenarios (e.g., *"Navigate to sauce-demo, log in with standard credentials, add backpack to cart, and verify checkout total is $32.39"*).
  * Gherkin / BDD scenarios (`Given`, `When`, `Then`).
  * Structured JSON test case definitions.

### 2.2 Execution Parameters & Context
* **Target Base URL**: The starting endpoint for the test scenario.
* **Environment Credentials**: Usernames, passwords, and API tokens securely injected through `.env` files or CI/CD secret vaults (never sent raw to LLMs).
* **Browser Runtime Parameters**:
  * Browser type: Chromium, Firefox, WebKit.
  * Viewport dimensions (Desktop, Tablet, Mobile emulations).
  * Execution mode: Headed or Headless.
  * Slow motion (`slowMo`) delay for visual debugging.
  * Timeout configuration for navigation and action auto-waiting.

---

## 3. Agent Specifications & Responsibilities

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

### 3.1 Agent 1: Planner Agent
* **Primary Responsibility**: Translate high-level human requirements into an intermediate, state-aware test execution graph.
* **Key Capabilities**:
  * Analyze requirements to identify preconditions (e.g., login, cookie accept), actions (e.g., input, click, select), and postconditions/assertions (e.g., URL change, text visibility).
  * Decompose complex operations into atomic steps with designated intents (e.g., `ACTION_NAVIGATE`, `ACTION_TYPE`, `ACTION_CLICK`, `ASSERT_TEXT_EQUALS`).
  * Output strictly validated JSON adhering to the `TestPlanSchema`.
  * Support prerequisite setup sequences and cleanup teardown hooks.

### 3.2 Agent 2: Generator Agent
* **Primary Responsibility**: Inspect the target web application's live page state and translate planned atomic steps into resilient, concrete Playwright actions.
* **Key Capabilities**:
  * Extract lightweight Accessibility Trees (`aria-snapshot`), visible interactive elements, roles, names, and labels without exceeding LLM context windows.
  * Match step intent with live UI elements using semantic mapping (role-first, text-based, label-based, test-id, and robust CSS/XPath fallbacks).
  * Generate and dispatch executable Playwright actions (`page.locator().click()`, `page.fill()`, `page.selectOption()`, `expect().toBeVisible()`).
  * Handle dynamic UI behaviors: automatic waiting, hydration delays, modal dialogs, and navigation changes.

### 3.3 Agent 3: Healer Agent
* **Primary Responsibility**: Dynamically intercept execution failures, diagnose the root cause, repair broken element selectors, and resume test execution.
* **Key Capabilities**:
  * **Failure Interception**: Hook into Playwright runtime errors (`TimeoutError`, `TargetClosedError`, `ElementHandleNotFound`, `ElementClickInterceptedError`, assertion failures).
  * **Diagnostic Context Extraction**: Capture the failure state, including the failed locator, stack trace, active DOM mutation snapshot, accessibility tree diff, and failure screenshot.
  * **Element Drift Analysis**: Evaluate whether the target element underwent visual restyling, DOM hierarchy restructuring, attribute renaming (e.g., changed `id` or `class`), or semantic relocation.
  * **Locator Repair & Verification**: Generate replacement locator candidates, verify them against the live browser context (verifying uniqueness and clickability), and execute the step with the repaired locator.
  * **Persistence**: Write healed locators to a `locator.registry.json` store so subsequent executions use the repaired locator directly.
  * **Safety Thresholds**: If an element is genuinely missing due to an application bug rather than UI drift, terminate healing and report a validated defect.

---

## 4. Playwright Execution Engine Specifications

* **Browser Lifecycle Management**: Centralized management of browser instances, isolated browser contexts, and page sessions.
* **Resilient Automation Mechanics**:
  * Native Playwright auto-waiting for actionable states (visible, stable, enabled, editable).
  * Configurable retry policies per step.
  * Dynamic network idle and DOM content loaded synchronization.
* **Artifact Collection**:
  * Full-resolution execution traces (`trace.zip`) with DOM snapshots and action screencasts.
  * Step-level screenshot capture on assertion or locator failure.
  * Video recording of failed test sessions.
  * Structured JSON run logs containing timings, token usage, agent decisions, and repair diffs.

---

## 5. Non-Functional & Technical Requirements

### 5.1 Architecture & Modularity
* **Language & Runtime**: python / Node.js (v20+ LTS).
* **Automation Framework**: `@playwright/test` / `playwright` core library.
* **Validation & Schemas**: `zod` for strict structural validation of LLM outputs.
* **Decoupled Architecture**: Strict separation of concerns between Playwright browser interaction, DOM extraction, LLM communication, and orchestration logic.

### 5.2 Performance & Context Window Management
* The framework must not feed raw, multi-megabyte HTML source to LLMs.
* The system must distill pages down to filtered accessibility trees, interactive element inventories, and scoped DOM sub-trees to optimize token consumption and maintain low latency ($< 3$ seconds per agent decision).

### 5.3 Security & Masking
* Passwords, session tokens, and sensitive personal identifiable information (PII) must be masked in:
  * LLM generation prompts.
  * Framework logs and terminal output.
  * Persisted trace and report files.

### 5.4 Website Compatibility
* Must reliably inspect and interact across modern web architectures:
  * Single-Page Applications (React, Next.js, Angular, Vue).
  * Traditional Server-Side Rendered (SSR) websites.
  * Shadow DOM boundaries and nested web components.
  * Complex multi-frame (iframe) architectures.

---

## 6. Output & Deliverables

1. **Test Execution Report**:
   * HTML report displaying step-by-step progress, execution duration, and pass/fail indicators.
   * Playwright trace viewer files (`trace.zip`) downloadable for offline step-by-step debugging.
2. **Self-Healing Audit Report**:
   * Detailed breakdown of every intercepted failure.
   * Visual and structural diff: `Original Locator` vs. `Healed Locator`.
   * Healing confidence score and verification status.
3. **Persisted Locator Registry**:
   * Machine-readable JSON mapping storing verified, updated selectors for target applications across recurring test runs.

---

## 7. Phased Implementation Roadmap

* **Phase 1: Environment & Playwright Engine Foundation**: Workspace setup, TypeScript tooling, configuration, and browser context management.
* **Phase 2: Page State & Semantic DOM Extractor**: Compact accessibility tree generation (`aria-snapshot`), interactive element filtering, and token-efficient page representations.
* **Phase 3: Planner Agent Implementation**: Structured prompt schemas, requirement decomposition, and atomic step graph synthesis.
* **Phase 4: Generator Agent & Action Dispatcher**: DOM-to-action translation, Playwright locator dispatching, and dynamic wait handling.
* **Phase 5: End-to-End Dynamic Execution Pipeline**: Connecting requirements $\rightarrow$ planning $\rightarrow$ generation $\rightarrow$ live execution in a unified orchestrator.
* **Phase 6: Failure Interceptor & Context Collector**: Hooking Playwright runtime exceptions, extracting failure stacks, DOM diffs, and screenshots.
* **Phase 7: Healer Agent Implementation**: Diagnostic reasoning engine, element drift analysis, and alternative locator candidate generation.
* **Phase 8: Dynamic Healing Verification & Execution Resume**: Live page candidate validation, dynamic step re-execution, and pipeline recovery.
* **Phase 9: Persistent Locator Registry & Patching**: Locator caching, registry storage, and patch report generation.
* **Phase 10: Multi-Site Hardening & Complex UI Scenarios**: Handling shadow DOM, nested iframes, dynamic hydration, and SPAs across arbitrary domains.
* **Phase 11: Unified Reporting & Observability**: Consolidating Playwright traces, agent thought records, and self-healing logs into a comprehensive report.
* **Phase 12: Production Readiness & CI/CD**: Docker containerization, headless execution pipelines, and concurrency controls.