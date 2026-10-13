import pytest
from agents.test_case_agent import TestCaseCreateAgent
from schema.azure_work_item import ParsedUseCase


def test_generate_steps_xml():
    agent = TestCaseCreateAgent()
    uc = ParsedUseCase(
        scenario_id="UC-01",
        title="Login Test",
        actor="Shopper",
        preconditions="User is on login page",
        main_steps=[
            "Open the application login portal",
            "Fill email input with demo@example.com",
            "Click login submit button",
            "Verify dashboard page loads properly"
        ],
        alt_flows=["Invalid password shows alert"],
        expected_outcome="User dashboard displays active session"
    )

    xml = agent.generate_steps_xml(uc)

    assert xml.startswith('<steps id="0" last="5">')
    assert xml.endswith('</steps>')
    assert '<step id="2" type="ActionStep">' in xml
    assert '<parameterizedString isformatted="true">Open the application login portal</parameterizedString>' in xml
    assert '<step id="5" type="ValidateStep">' in xml
    assert 'User dashboard displays active session' in xml


def test_format_test_case():
    agent = TestCaseCreateAgent()
    uc = ParsedUseCase(
        scenario_id="UC-02",
        title="Catalog Browsing",
        actor="Authenticated User",
        preconditions="User logged in",
        main_steps=["Click Mens Wear", "Verify product grid displays"],
        expected_outcome="Catalog is rendered"
    )

    tc = agent.format_test_case(uc, linked_story_id=8)

    assert tc.title == "[TC-02] Catalog Browsing"
    assert tc.linked_story_id == 8
    assert tc.priority == 1
    assert "Playwright; Automation; TestCase; UC-02" in tc.tags
    assert "<steps" in tc.steps_xml


def test_load_user_story_mappings():
    agent = TestCaseCreateAgent()
    mappings = agent.load_user_story_mappings("specs/azure-user-stories.md")

    assert len(mappings) >= 9
    assert mappings["UC-01"] == 7
    assert mappings["UC-02"] == 8
    assert mappings["UC-09"] == 15
