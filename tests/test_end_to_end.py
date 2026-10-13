import pytest
from engine.runner import AutonomousTestRunner
from schema.execution_result import StepStatus


@pytest.mark.asyncio
async def test_full_autonomous_pipeline_execution():
    runner = AutonomousTestRunner()
    requirement_file = "tests/sample_requirements/saucedemo_checkout.md"

    report = await runner.run(requirement_input=requirement_file)

    assert report is not None
    assert report.total_steps > 0
    assert report.overall_status == StepStatus.PASSED
    assert report.passed_steps + report.healed_steps == report.total_steps
