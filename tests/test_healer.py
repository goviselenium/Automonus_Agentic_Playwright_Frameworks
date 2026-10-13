import os
import tempfile
import pytest
from core.locator_registry import LocatorRegistry
from agents.healer_agent import HealerAgent
from schema.test_plan import AtomicStep, StepIntent
from schema.page_state import PageStateSnapshot, InteractiveElement


def test_locator_registry_persistence():
    with tempfile.TemporaryDirectory(dir="output") as tmp_dir:
        reg_file = os.path.join(tmp_dir, "test_locator.registry.json")
        registry = LocatorRegistry(registry_file=reg_file)

        registry.register_heal(
            target_description="Login button",
            original_locator="#old-login-id",
            healed_locator="[data-test='login-button']",
            strategy="Attribute Fallback",
            confidence=0.95,
            verified=True
        )

        # Re-instantiate to verify disk read
        registry2 = LocatorRegistry(registry_file=reg_file)
        healed = registry2.get_healed_locator("Login button", "#old-login-id")
        assert healed == "[data-test='login-button']"


@pytest.mark.asyncio
async def test_healer_agent_diagnosis():
    healer = HealerAgent()
    step = AtomicStep(
        step_id="step_3",
        intent=StepIntent.ACTION_CLICK,
        description="Click login button",
        target_description="Login button"
    )
    page_state = PageStateSnapshot(
        url="https://www.saucedemo.com",
        title="Swag Labs",
        aria_snapshot="button 'Login'",
        interactive_elements=[
            InteractiveElement(
                element_id="elem_1",
                tag_name="input",
                type_attr="submit",
                id_attr="login-button",
                test_id="login-button",
                css_selector="#login-button",
                xpath_selector="//*[@id='login-button']"
            )
        ],
        timestamp=0.0
    )

    heal_decision = await healer.heal_failure(
        step=step,
        failed_locator="#non-existent-btn",
        error_message="TimeoutError: element not found",
        page_state=page_state
    )

    assert heal_decision is not None
    assert len(heal_decision.replacement_candidates) > 0
    assert heal_decision.confidence_score > 0.5
