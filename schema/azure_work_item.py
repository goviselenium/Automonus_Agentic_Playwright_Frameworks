from typing import List, Optional
from pydantic import BaseModel, Field


class ParsedUseCase(BaseModel):
    """Represents a parsed Use Case scenario from specs/use-case-plan.md."""
    scenario_id: str
    title: str
    actor: str = "Registered User"
    preconditions: str = ""
    main_steps: List[str] = Field(default_factory=list)
    alt_flows: List[str] = Field(default_factory=list)
    expected_outcome: str = ""


class AzureUserStoryPayload(BaseModel):
    """Formatted User Story ready for Azure DevOps Work Item API."""
    scenario_id: str
    title: str
    description_html: str
    acceptance_criteria_html: str
    tags: str = "Use-Case; Playwright-Automation; E2E"
    priority: int = 2
    story_points: int = 3


class AzureTestCasePayload(BaseModel):
    """Formatted Test Case ready for Azure DevOps Work Item API."""
    scenario_id: str
    title: str
    description_html: str
    steps_xml: str
    tags: str = "Use-Case; Playwright-Automation; TestCase"
    priority: int = 1
    linked_story_id: Optional[int] = None


class CreatedWorkItem(BaseModel):
    """Represents a work item created in Azure DevOps Boards."""
    id: int
    title: str
    scenario_id: str
    state: str = "New"
    web_url: str
    api_url: Optional[str] = None
    created_at: Optional[str] = None


class AzureCreationSummary(BaseModel):
    """Summary report of all user stories published to Azure DevOps."""
    organization: str
    project: str
    total_parsed: int = 0
    total_created: int = 0
    work_items: List[CreatedWorkItem] = Field(default_factory=list)
    markdown_report_path: Optional[str] = None
