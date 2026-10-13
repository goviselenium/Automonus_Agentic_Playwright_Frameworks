from enum import Enum
from typing import Optional, List
from pydantic import BaseModel, Field


class StepStatus(str, Enum):
    PENDING = "PENDING"
    PASSED = "PASSED"
    FAILED = "FAILED"
    HEALED = "HEALED"
    SKIPPED = "SKIPPED"


class SelfHealingAuditEntry(BaseModel):
    """Details of a self-healing event for audit and reporting."""
    step_id: str
    failed_locator: str
    error_message: str
    error_type: str = "ExecutionError"
    dom_diff_summary: Optional[str] = None
    healed_locator: Optional[str] = None
    strategy_used: str = "Semantic Element Matching"
    confidence_score: float = 0.0
    verified: bool = False
    timestamp: float = 0.0


class StepExecutionResult(BaseModel):
    """Result of running a single atomic step."""
    step_id: str
    intent: str
    description: str
    status: StepStatus
    used_locator: Optional[str] = None
    action_taken: str = ""
    duration_ms: float = 0.0
    error_message: Optional[str] = None
    screenshot_path: Optional[str] = None
    healing_audit: Optional[SelfHealingAuditEntry] = None


class TestExecutionReport(BaseModel):
    """Full execution report for a test scenario run."""
    test_id: str
    title: str
    target_url: str
    overall_status: StepStatus
    start_time: str
    end_time: str
    duration_seconds: float
    total_steps: int
    passed_steps: int
    failed_steps: int
    healed_steps: int
    skipped_steps: int
    trace_path: Optional[str] = None
    video_path: Optional[str] = None
    step_results: List[StepExecutionResult] = Field(default_factory=list)
    healing_audits: List[SelfHealingAuditEntry] = Field(default_factory=list)
