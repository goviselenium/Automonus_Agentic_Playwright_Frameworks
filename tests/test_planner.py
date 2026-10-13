import pytest
from agents.planner_agent import PlannerAgent
from schema.test_plan import TestPlan


@pytest.mark.asyncio
async def test_planner_agent_decomposition():
    planner = PlannerAgent()
    requirement = "Navigate to https://www.saucedemo.com, log in as standard_user with secret_sauce, add backpack to cart, and verify cart."
    
    plan: TestPlan = await planner.plan_requirement(requirement)
    
    assert plan is not None
    assert len(plan.all_steps()) >= 3
    assert plan.preconditions[0].value == "https://www.saucedemo.com"


def test_save_use_case_plan_template():
    import os
    planner = PlannerAgent()
    out_file = os.path.join(os.path.dirname(__file__), "scratch_use_case_plan.md")
    
    try:
        saved_path = planner.save_use_case_plan(
            output_path=out_file,
            requirement_text="automationpractice e-commerce",
            base_url="https://shop.qaautomationlabs.com/index.php"
        )
        
        assert saved_path == out_file
        with open(out_file, "r", encoding="utf-8") as f:
            content = f.read()

        assert "## UC-01:" in content
        assert "- **Actor:**" in content
        assert "- **Preconditions:**" in content
        assert "- **Main Flow / Steps:**" in content
        assert "  1. " in content
        assert "- **Alternate / Exception Flows:**" in content
        assert "  - " in content
        assert "- **Expected Outcome:**" in content
    finally:
        if os.path.exists(out_file):
            os.remove(out_file)


