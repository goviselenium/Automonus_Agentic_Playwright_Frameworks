import pytest
from agents.standards_agent import CodingStandardsAgent
from schema.coding_standards import ViolationType


def test_audit_indentation_and_tabs():
    agent = CodingStandardsAgent()
    sample_code = "def sample():\n\tprint('tab used')\n"
    violations = agent.audit_code(sample_code)
    
    assert any(v.violation_type == ViolationType.INDENTATION for v in violations)
    tab_violation = next(v for v in violations if v.violation_type == ViolationType.INDENTATION)
    assert "Tab character detected" in tab_violation.message


def test_audit_line_length():
    agent = CodingStandardsAgent(max_line_length=50)
    sample_code = "def sample():\n    x = 'this is an extremely long string that exceeds fifty characters'\n"
    violations = agent.audit_code(sample_code)
    
    assert any(v.violation_type == ViolationType.LINE_LENGTH for v in violations)


def test_audit_naming_conventions():
    agent = CodingStandardsAgent()
    sample_code = (
        "class invalid_class_name:\n"
        "    def BadMethodName(self):\n"
        "        pass\n"
    )
    violations = agent.audit_code(sample_code)
    
    naming_violations = [v for v in violations if v.violation_type == ViolationType.NAMING_CONVENTION]
    assert len(naming_violations) >= 2
    assert any("PascalCase" in v.message for v in naming_violations)
    assert any("snake_case" in v.message for v in naming_violations)


def test_audit_type_hints():
    agent = CodingStandardsAgent()
    sample_code = (
        "def calculate_total(quantity, price):\n"
        "    return quantity * price\n"
    )
    violations = agent.audit_code(sample_code)
    
    hint_violations = [v for v in violations if v.violation_type == ViolationType.TYPE_HINTS]
    assert len(hint_violations) >= 3  # quantity, price, and return type
    assert any("quantity" in v.message for v in hint_violations)
    assert any("price" in v.message for v in hint_violations)
    assert any("return type" in v.message for v in hint_violations)


def test_audit_docstrings():
    agent = CodingStandardsAgent()
    sample_code = (
        "class PublicClass:\n"
        "    def public_method(self) -> None:\n"
        "        pass\n"
    )
    violations = agent.audit_code(sample_code)
    
    doc_violations = [v for v in violations if v.violation_type == ViolationType.DOCSTRINGS]
    assert any("PublicClass" in v.message for v in doc_violations)
    assert any("public_method" in v.message for v in doc_violations)


def test_audit_string_formatting():
    agent = CodingStandardsAgent()
    sample_code = (
        "def greet(name: str) -> str:\n"
        "    msg1 = 'Hello %s' % name\n"
        "    msg2 = 'Welcome {}'.format(name)\n"
        "    return msg1 + msg2\n"
    )
    violations = agent.audit_code(sample_code)
    
    fmt_violations = [v for v in violations if v.violation_type == ViolationType.STRING_FORMATTING]
    assert len(fmt_violations) >= 2
    assert any("%" in v.message for v in fmt_violations)
    assert any(".format()" in v.message for v in fmt_violations)


def test_fix_code_tabs_and_blank_lines():
    agent = CodingStandardsAgent()
    sample_code = (
        "import os\n"
        "def first_func():\n"
        "\treturn 1\n"
        "def second_func():\n"
        "\treturn 2\n"
    )
    result = agent.fix_code(sample_code)
    
    assert "\t" not in result.refactored_code
    assert "    return 1" in result.refactored_code
    assert "\n\ndef second_func" in result.refactored_code
    assert result.success is True


def test_fix_code_import_grouping():
    agent = CodingStandardsAgent()
    sample_code = (
        "import pytest\n"
        "import os\n"
        "import sys\n"
        "from agents.base_agent import BaseAgent\n"
    )
    result = agent.fix_code(sample_code)
    lines = result.refactored_code.splitlines()
    
    # os and sys (stdlib) should come before pytest (third-party) and BaseAgent (local)
    assert "import os" in lines
    assert "import sys" in lines
    os_idx = lines.index("import os")
    pytest_idx = lines.index("import pytest")
    agent_idx = lines.index("from agents.base_agent import BaseAgent")
    assert os_idx < pytest_idx < agent_idx


def test_generate_pyproject_toml():
    import os
    agent = CodingStandardsAgent()
    out_file = os.path.join(os.path.dirname(__file__), "scratch_pyproject.toml")
    try:
        result_path = agent.generate_pyproject_toml(out_file)
        assert result_path == out_file
        with open(out_file, "r", encoding="utf-8") as f:
            content = f.read()
        
        assert "[tool.black]" in content
        assert "[tool.ruff]" in content
        assert "[tool.mypy]" in content
        assert "line-length = 88" in content
    finally:
        if os.path.exists(out_file):
            os.remove(out_file)

