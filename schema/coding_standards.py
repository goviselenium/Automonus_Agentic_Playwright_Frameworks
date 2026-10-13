from enum import Enum
from typing import Optional, List, Dict
from pydantic import BaseModel, Field


class ViolationType(str, Enum):
    INDENTATION = "Indentation"
    LINE_LENGTH = "Line Length"
    BLANK_LINES = "Blank Lines"
    IMPORT_ORDER = "Import Order"
    NAMING_CONVENTION = "Naming Convention"
    TYPE_HINTS = "Type Hints"
    DOCSTRINGS = "Docstrings"
    STRING_FORMATTING = "String Formatting"
    TOOLING_ISSUE = "Tooling Issue"


class CodeViolation(BaseModel):
    """Represents a single violation of Coding_Standards_python.md."""
    file_path: str
    line_number: int
    column: int = 1
    violation_type: ViolationType
    message: str
    code_snippet: str = ""
    suggested_fix: Optional[str] = None
    rule_section: str = "1. Core Style & Formatting (PEP 8)"


class CodeRefactorResult(BaseModel):
    """Result of automated code refactoring against coding standards."""
    file_path: str
    original_code: str
    refactored_code: str
    fixed_violations: List[CodeViolation] = Field(default_factory=list)
    applied_changes: List[str] = Field(default_factory=list)
    success: bool = True


class StandardsAuditReport(BaseModel):
    """Comprehensive audit report across all analyzed Python files."""
    total_files_scanned: int = 0
    compliant_files_count: int = 0
    violating_files_count: int = 0
    total_violations: int = 0
    violations_by_type: Dict[str, int] = Field(default_factory=dict)
    violations: List[CodeViolation] = Field(default_factory=list)
    compliance_score_percent: float = 100.0
    auto_fixed_violations: int = 0
    scanned_file_paths: List[str] = Field(default_factory=list)
