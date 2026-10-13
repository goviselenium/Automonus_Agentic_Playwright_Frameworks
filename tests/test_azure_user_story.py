import pytest
from agents.azure_user_story_agent import AzureUserStoryAgent
from schema.azure_work_item import ParsedUseCase, AzureUserStoryPayload


SAMPLE_MD = """# Playwright Test Plan: Sample Plan
**Target Base URL:** `https://shop.example.com`

---

## UC-01: User Login Verification
- **Actor:** E-Commerce Shopper
- **Preconditions:** Browser is on login page.
- **Main Flow / Steps:**
  1. Fill email input with demo@example.com
  2. Fill password input with secret
  3. Click submit button
- **Alternate / Exception Flows:**
  - Invalid password displays alert
- **Expected Outcome:** User is redirected to dashboard.

## UC-02: Search Product
- **Actor:** Shopper
- **Preconditions:** User is on dashboard.
- **Main Flow / Steps:**
  1. Type product in search bar
  2. Press enter
- **Alternate / Exception Flows:**
  - No matching products displays empty message
- **Expected Outcome:** Search results table renders matching items.
"""


def test_parse_use_case_markdown():
    agent = AzureUserStoryAgent()
    scenarios = agent.parse_use_case_markdown(SAMPLE_MD)
    
    assert len(scenarios) == 2
    assert scenarios[0].scenario_id == "UC-01"
    assert scenarios[0].title == "User Login Verification"
    assert scenarios[0].actor == "E-Commerce Shopper"
    assert len(scenarios[0].main_steps) == 3
    assert len(scenarios[0].alt_flows) == 1
    assert "dashboard" in scenarios[0].expected_outcome

    assert scenarios[1].scenario_id == "UC-02"
    assert scenarios[1].title == "Search Product"
    assert len(scenarios[1].main_steps) == 2


def test_format_user_story():
    agent = AzureUserStoryAgent()
    scenarios = agent.parse_use_case_markdown(SAMPLE_MD)
    payload = agent.format_user_story(scenarios[0])

    assert payload.scenario_id == "UC-01"
    assert payload.title == "[UC-01] User Login Verification"
    assert "<h3>User Story Statement</h3>" in payload.description_html
    assert "<strong>As an</strong> E-Commerce Shopper" in payload.description_html
    assert "<h4>Acceptance Criteria & Verification</h4>" in payload.acceptance_criteria_html
    assert "UC-01" in payload.tags
    assert payload.priority == 2
    assert payload.story_points == 3
