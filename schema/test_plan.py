import re
import json
import uuid
from enum import Enum
from typing import Optional, List, Any
from pydantic import BaseModel, Field, field_validator, AliasChoices


class StepIntent(str, Enum):
    ACTION_NAVIGATE = "ACTION_NAVIGATE"
    ACTION_CLICK = "ACTION_CLICK"
    ACTION_TYPE = "ACTION_TYPE"
    ACTION_SELECT = "ACTION_SELECT"
    ACTION_HOVER = "ACTION_HOVER"
    ACTION_CHECK = "ACTION_CHECK"
    ACTION_UNCHECK = "ACTION_UNCHECK"
    ACTION_PRESS_KEY = "ACTION_PRESS_KEY"
    ACTION_CLEAR = "ACTION_CLEAR"
    ASSERT_TEXT_EQUALS = "ASSERT_TEXT_EQUALS"
    ASSERT_TEXT_CONTAINS = "ASSERT_TEXT_CONTAINS"
    ASSERT_VISIBLE = "ASSERT_VISIBLE"
    ASSERT_URL_CONTAINS = "ASSERT_URL_CONTAINS"
    ASSERT_ELEMENT_COUNT = "ASSERT_ELEMENT_COUNT"


class AtomicStep(BaseModel):
    """Represents a single atomic step in the test plan."""
    step_id: str = Field(
        default_factory=lambda: f"step_{uuid.uuid4().hex[:6]}",
        validation_alias=AliasChoices("step_id", "id", "stepId"),
        description="Unique identifier for the step"
    )
    intent: StepIntent = Field(
        default=StepIntent.ACTION_CLICK,
        validation_alias=AliasChoices("intent", "step_intent", "action", "action_type"),
        description="The atomic intent of this step"
    )
    description: str = Field(
        default="Execute step action",
        validation_alias=AliasChoices("description", "desc", "step_description"),
        description="Human-readable description of what this step accomplishes"
    )
    target_description: str = Field(
        default="Target UI element",
        validation_alias=AliasChoices("target_description", "target", "element", "target_element"),
        description="Descriptive name of the target UI element or page"
    )
    value: Optional[str] = Field(default=None, description="Input text, URL, key code, or expected value")
    assertion_expected: Optional[str] = Field(default=None, description="Expected text/value for assertion steps")
    is_precondition: bool = Field(default=False, description="Whether this is a setup step")
    is_postcondition: bool = Field(default=False, description="Whether this is a teardown step")

    @field_validator("intent", mode="before")
    @classmethod
    def coerce_intent(cls, v: Any) -> StepIntent:
        if isinstance(v, StepIntent):
            return v
        if isinstance(v, str):
            v_clean = v.upper().strip()
            if "NAVIGATE" in v_clean or "GOTO" in v_clean:
                return StepIntent.ACTION_NAVIGATE
            elif "TYPE" in v_clean or "FILL" in v_clean or "ENTER" in v_clean or "INPUT" in v_clean:
                return StepIntent.ACTION_TYPE
            elif "CLICK" in v_clean or "PRESS" in v_clean or "SUBMIT" in v_clean:
                return StepIntent.ACTION_CLICK
            elif "SELECT" in v_clean or "CHOOSE" in v_clean:
                return StepIntent.ACTION_SELECT
            elif "ASSERT" in v_clean or "VERIFY" in v_clean or "CHECK" in v_clean:
                return StepIntent.ASSERT_VISIBLE
            try:
                return StepIntent(v_clean)
            except ValueError:
                return StepIntent.ACTION_CLICK
        return StepIntent.ACTION_CLICK

    @field_validator("value", "assertion_expected", mode="before")
    @classmethod
    def coerce_string_field(cls, v: Any) -> Optional[str]:
        if v is None:
            return None
        if isinstance(v, (dict, list)):
            return json.dumps(v)
        return str(v)


class TestPlan(BaseModel):
    """The generated test plan graph emitted by the Planner Agent."""
    __test__ = False

    plan_id: str = Field(
        default_factory=lambda: f"plan_{uuid.uuid4().hex[:8]}",
        validation_alias=AliasChoices("plan_id", "id", "test_id"),
        description="Unique execution ID for the test plan"
    )
    title: str = Field(
        default="Autonomous Test Scenario Execution",
        validation_alias=AliasChoices("title", "scenario_title", "name"),
        description="Title of the test scenario"
    )
    summary: str = Field(
        default="Decomposed execution plan",
        validation_alias=AliasChoices("summary", "description", "overview"),
        description="High-level overview of the test objective"
    )
    target_url: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices("target_url", "url", "base_url"),
        description="Base URL target for the execution"
    )
    preconditions: List[AtomicStep] = Field(default_factory=list, description="Setup steps")
    steps: List[AtomicStep] = Field(default_factory=list, description="Core execution steps")
    postconditions: List[AtomicStep] = Field(default_factory=list, description="Teardown steps")

    @field_validator("preconditions", "steps", "postconditions", mode="before")
    @classmethod
    def coerce_step_list(cls, v: Any) -> List[Any]:
        if not isinstance(v, list):
            return []
        coerced = []
        for idx, item in enumerate(v):
            if isinstance(item, str):
                item_upper = item.upper()
                intent = StepIntent.ACTION_CLICK
                val = None
                if "NAVIGATE" in item_upper or "GOTO" in item_upper or "HTTP" in item_upper:
                    intent = StepIntent.ACTION_NAVIGATE
                    url_match = re.search(r'https?://[^\s\'"`]+', item)
                    if url_match:
                        val = url_match.group(0).rstrip('.,;: `\'"')
                elif "TYPE" in item_upper or "FILL" in item_upper or "ENTER" in item_upper:
                    intent = StepIntent.ACTION_TYPE
                elif "ASSERT" in item_upper or "VERIFY" in item_upper:
                    intent = StepIntent.ASSERT_VISIBLE

                coerced.append({
                    "step_id": f"step_{idx+1}",
                    "intent": intent,
                    "description": item,
                    "target_description": item,
                    "value": val
                })
            elif isinstance(item, (dict, AtomicStep)):
                coerced.append(item)
        return coerced

    def all_steps(self) -> List[AtomicStep]:
        """Returns ordered list of all steps (preconditions + steps + postconditions)."""
        return self.preconditions + self.steps + self.postconditions
