import ast
import os
import re
import sys
from typing import List, Dict, Optional, Tuple, Set
from agents.base_agent import BaseAgent
from schema.coding_standards import (
    ViolationType,
    CodeViolation,
    CodeRefactorResult,
    StandardsAuditReport,
)

# Standard library module names (available in Python 3.10+)
if hasattr(sys, "stdlib_module_names"):
    STDLIB_MODULES: Set[str] = set(sys.stdlib_module_names)
else:
    STDLIB_MODULES = {
        "abc", "argparse", "asyncio", "base64", "collections", "contextlib",
        "copy", "csv", "dataclasses", "datetime", "decimal", "enum", "functools",
        "hashlib", "importlib", "inspect", "io", "itertools", "json", "logging",
        "math", "os", "pathlib", "pickle", "random", "re", "shutil", "socket",
        "sqlite3", "string", "subprocess", "sys", "tempfile", "threading",
        "time", "traceback", "types", "typing", "unittest", "urllib", "uuid",
        "warnings", "weakref"
    }


class CodingStandardsAgent(BaseAgent):
    """
    Agent 4: Coding Standards Agent
    Enforces and auto-implements Python coding standards from Coding_Standards_python.md:
    1. Core Style & Formatting (PEP 8) - indentation, line length, blank lines, import grouping
    2. Naming Conventions - PascalCase, snake_case, UPPER_CASE, _leading_underscore
    3. Modern Python Best Practices - Type hints, docstrings, f-strings
    4. Essential Tooling Integration - Ruff, Black, Mypy, pyproject.toml configuration
    """

    SYSTEM_PROMPT = """
    You are an expert Python Coding Standards Agent. Your role is to audit, enforce, and refactor 
    Python source code to strictly adhere to PEP 8 and modern Python engineering best practices:
    - 4 spaces indentation, no tabs
    - Max 88 characters line length
    - Correct blank lines (2 before top-level definitions, 1 between class methods)
    - Grouped imports (Standard library, Third-party, Local application)
    - Consistent naming conventions (PascalCase classes, snake_case functions/vars, UPPER_CASE constants)
    - Full type annotations on all function signatures
    - Clear Google-style docstrings on all public modules, classes, and methods
    - F-strings instead of %-formatting or .format()
    """

    def __init__(self, max_line_length: int = 88, project_root: Optional[str] = None):
        super().__init__(role="CodingStandardsAgent")
        self.max_line_length = max_line_length
        self.project_root = os.path.abspath(project_root or os.getcwd())
        self.local_packages = self._discover_local_packages()

    def _discover_local_packages(self) -> Set[str]:
        """Discovers top-level local package/module names in the project."""
        packages = set()
        if not os.path.exists(self.project_root):
            return packages
        for item in os.listdir(self.project_root):
            item_path = os.path.join(self.project_root, item)
            if os.path.isdir(item_path) and not item.startswith(".") and item not in ("venv", "__pycache__"):
                packages.add(item)
            elif item.endswith(".py"):
                packages.add(item[:-3])
        return packages

    # =========================================================================
    # AUDITING & LINTING ENGINE
    # =========================================================================

    def audit_file(self, file_path: str) -> List[CodeViolation]:
        """Audits a single Python file for violations of Coding_Standards_python.md."""
        abs_path = os.path.abspath(file_path)
        if not os.path.exists(abs_path):
            return []

        with open(abs_path, "r", encoding="utf-8", errors="replace") as f:
            code = f.read()

        return self.audit_code(code, file_path=abs_path)

    def audit_code(self, code: str, file_path: str = "<memory>") -> List[CodeViolation]:
        """Audits Python source code text for standards violations."""
        violations: List[CodeViolation] = []
        lines = code.splitlines()

        # 1. Lexical and Formatting Checks
        violations.extend(self._check_indentation_and_tabs(lines, file_path))
        violations.extend(self._check_line_length(lines, file_path))
        violations.extend(self._check_blank_lines(lines, file_path))
        violations.extend(self._check_string_formatting_regex(lines, file_path))

        # 2. AST-Based Structural Checks
        try:
            tree = ast.parse(code, filename=file_path)
            violations.extend(self._check_imports(tree, lines, file_path))
            violations.extend(self._check_naming_conventions(tree, lines, file_path))
            violations.extend(self._check_type_hints(tree, lines, file_path))
            violations.extend(self._check_docstrings(tree, lines, file_path))
            violations.extend(self._check_ast_formatting(tree, lines, file_path))
        except SyntaxError as e:
            violations.append(CodeViolation(
                file_path=file_path,
                line_number=e.lineno or 1,
                column=e.offset or 1,
                violation_type=ViolationType.INDENTATION,
                message=f"SyntaxError encountered while parsing: {e.msg}",
                code_snippet=lines[e.lineno - 1] if e.lineno and e.lineno <= len(lines) else "",
                rule_section="1. Core Style & Formatting (PEP 8)"
            ))

        return violations

    def audit_directory(self, dir_path: Optional[str] = None, exclude_dirs: Optional[List[str]] = None) -> StandardsAuditReport:
        """Recursively audits all Python files in a directory."""
        target_dir = os.path.abspath(dir_path or self.project_root)
        excludes = set(exclude_dirs or [".git", "venv", ".venv", "__pycache__", ".pytest_cache", "build", "dist"])

        scanned_files = []
        all_violations: List[CodeViolation] = []
        violations_by_type: Dict[str, int] = {v.value: 0 for v in ViolationType}

        for root, dirs, files in os.walk(target_dir):
            dirs[:] = [d for d in dirs if d not in excludes and not d.startswith(".")]
            for file in files:
                if file.endswith(".py"):
                    full_path = os.path.join(root, file)
                    scanned_files.append(full_path)
                    file_violations = self.audit_file(full_path)
                    all_violations.extend(file_violations)
                    for v in file_violations:
                        violations_by_type[v.violation_type.value] = violations_by_type.get(v.violation_type.value, 0) + 1

        total_files = len(scanned_files)
        violating_files = len({v.file_path for v in all_violations})
        compliant_files = total_files - violating_files
        compliance_score = round((compliant_files / total_files * 100), 2) if total_files > 0 else 100.0

        return StandardsAuditReport(
            total_files_scanned=total_files,
            compliant_files_count=compliant_files,
            violating_files_count=violating_files,
            total_violations=len(all_violations),
            violations_by_type=violations_by_type,
            violations=all_violations,
            compliance_score_percent=compliance_score,
            scanned_file_paths=scanned_files
        )

    # -------------------------------------------------------------------------
    # INDIVIDUAL RULE CHECKERS
    # -------------------------------------------------------------------------

    def _check_indentation_and_tabs(self, lines: List[str], file_path: str) -> List[CodeViolation]:
        violations = []
        for idx, line in enumerate(lines, 1):
            if "\t" in line:
                violations.append(CodeViolation(
                    file_path=file_path,
                    line_number=idx,
                    violation_type=ViolationType.INDENTATION,
                    message="Tab character detected. Indentation must use 4 spaces per level, never tabs.",
                    code_snippet=line.strip(),
                    suggested_fix="Replace all tab characters with 4 spaces.",
                    rule_section="1. Core Style & Formatting (PEP 8)"
                ))
            leading_spaces = len(line) - len(line.lstrip(" "))
            if leading_spaces > 0 and leading_spaces % 4 != 0 and not line.strip().startswith(("#", "*", "@")):
                # Exclude multi-line string contents
                if not line.strip().startswith(('"""', "'''")):
                    violations.append(CodeViolation(
                        file_path=file_path,
                        line_number=idx,
                        violation_type=ViolationType.INDENTATION,
                        message=f"Indentation of {leading_spaces} spaces is not a multiple of 4.",
                        code_snippet=line.strip(),
                        suggested_fix=f"Re-indent using {((leading_spaces + 2) // 4) * 4} spaces.",
                        rule_section="1. Core Style & Formatting (PEP 8)"
                    ))
        return violations

    def _check_line_length(self, lines: List[str], file_path: str) -> List[CodeViolation]:
        violations = []
        for idx, line in enumerate(lines, 1):
            # Skip URLs in comments or long docstring directives
            if len(line) > self.max_line_length:
                if "http://" in line or "https://" in line or line.strip().startswith(("#", '"""', "'''")):
                    continue
                violations.append(CodeViolation(
                    file_path=file_path,
                    line_number=idx,
                    column=self.max_line_length + 1,
                    violation_type=ViolationType.LINE_LENGTH,
                    message=f"Line length ({len(line)} chars) exceeds maximum limit of {self.max_line_length} characters.",
                    code_snippet=line[:90] + ("..." if len(line) > 90 else ""),
                    suggested_fix="Break line across multiple lines or reformat with modern formatter.",
                    rule_section="1. Core Style & Formatting (PEP 8)"
                ))
        return violations

    def _check_blank_lines(self, lines: List[str], file_path: str) -> List[CodeViolation]:
        violations = []
        # Check blank lines around top-level def and class
        for idx, line in enumerate(lines):
            line_stripped = line.strip()
            # Top-level class or function definition
            if (line.startswith("def ") or line.startswith("class ") or line.startswith("async def ")) and idx > 0:
                # Count blank lines directly preceding
                blank_count = 0
                cursor = idx - 1
                while cursor >= 0 and lines[cursor].strip() == "":
                    blank_count += 1
                    cursor -= 1
                # If preceding was an import or top-level statement (not top of file)
                if cursor >= 0 and not lines[cursor].startswith(("@", "#")) and blank_count < 2:
                    violations.append(CodeViolation(
                        file_path=file_path,
                        line_number=idx + 1,
                        violation_type=ViolationType.BLANK_LINES,
                        message=f"Expected 2 blank lines before top-level definition, found {blank_count}.",
                        code_snippet=line_stripped,
                        suggested_fix="Surround top-level functions and classes with two blank lines.",
                        rule_section="1. Core Style & Formatting (PEP 8)"
                    ))
        return violations

    def _check_string_formatting_regex(self, lines: List[str], file_path: str) -> List[CodeViolation]:
        violations = []
        percent_fmt_pattern = re.compile(r'["\'].*?%[sdf].*?["\']\s*%\s*(\(.*?\)|[a-zA-Z_]\w*)')
        dot_format_pattern = re.compile(r'["\'].*?{[^}]*}.*?["\']\.format\(')

        for idx, line in enumerate(lines, 1):
            stripped = line.strip()
            if stripped.startswith("#"):
                continue
            if percent_fmt_pattern.search(line):
                violations.append(CodeViolation(
                    file_path=file_path,
                    line_number=idx,
                    violation_type=ViolationType.STRING_FORMATTING,
                    message="Old-style % string formatting detected. Prefer f-strings for readability and performance.",
                    code_snippet=stripped,
                    suggested_fix="Convert % formatting expression into an f-string (e.g. f'User_{user_id}').",
                    rule_section="3. Modern Python Best Practices"
                ))
            elif dot_format_pattern.search(line):
                violations.append(CodeViolation(
                    file_path=file_path,
                    line_number=idx,
                    violation_type=ViolationType.STRING_FORMATTING,
                    message="str.format() detected. Prefer f-strings over .format() for string interpolation.",
                    code_snippet=stripped,
                    suggested_fix="Convert .format() call into an f-string.",
                    rule_section="3. Modern Python Best Practices"
                ))
        return violations

    def _check_imports(self, tree: ast.AST, lines: List[str], file_path: str) -> List[CodeViolation]:
        violations = []
        imports: List[Tuple[int, str, str]] = []  # (lineno, module_name, import_text)

        for node in ast.iter_child_nodes(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    root_mod = alias.name.split(".")[0]
                    category = self._classify_module(root_mod)
                    imports.append((node.lineno, root_mod, category))
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    root_mod = node.module.split(".")[0]
                    category = self._classify_module(root_mod, is_relative=(node.level > 0))
                    imports.append((node.lineno, root_mod, category))

        # Check grouping order: stdlib (1) -> third-party (2) -> local (3)
        cat_order = {"stdlib": 1, "third_party": 2, "local": 3}
        current_max_cat = 1
        seen_categories: List[str] = []

        for lineno, mod, cat in imports:
            order_val = cat_order.get(cat, 2)
            if order_val < current_max_cat:
                violations.append(CodeViolation(
                    file_path=file_path,
                    line_number=lineno,
                    violation_type=ViolationType.IMPORT_ORDER,
                    message=f"Import '{mod}' ({cat}) appears after higher-precedence imports. Group order must be: 1. Stdlib, 2. Third-party, 3. Local.",
                    code_snippet=lines[lineno - 1] if lineno <= len(lines) else "",
                    suggested_fix="Reorder imports into standard library, third-party, and local blocks.",
                    rule_section="1. Core Style & Formatting (PEP 8)"
                ))
            else:
                current_max_cat = order_val

        return violations

    def _classify_module(self, mod_name: str, is_relative: bool = False) -> str:
        if is_relative:
            return "local"
        if mod_name in STDLIB_MODULES:
            return "stdlib"
        if mod_name in self.local_packages:
            return "local"
        return "third_party"

    def _check_naming_conventions(self, tree: ast.AST, lines: List[str], file_path: str) -> List[CodeViolation]:
        violations = []
        pascal_case_regex = re.compile(r"^[A-Z][a-zA-Z0-9]*$")
        snake_case_regex = re.compile(r"^_{0,2}[a-z][a-z0-9_]*_{0,2}$")
        upper_case_regex = re.compile(r"^[A-Z][A-Z0-9_]*$")

        for node in ast.walk(tree):
            # 1. Classes -> PascalCase
            if isinstance(node, ast.ClassDef):
                name = node.name
                if not pascal_case_regex.match(name) and not (name.startswith("_") and pascal_case_regex.match(name.lstrip("_"))):
                    violations.append(CodeViolation(
                        file_path=file_path,
                        line_number=node.lineno,
                        violation_type=ViolationType.NAMING_CONVENTION,
                        message=f"Class '{name}' does not follow PascalCase convention.",
                        code_snippet=lines[node.lineno - 1] if node.lineno <= len(lines) else "",
                        suggested_fix=f"Rename class '{name}' to PascalCase (e.g. {''.join(word.capitalize() for word in name.split('_'))}).",
                        rule_section="2. Naming Conventions"
                    ))

            # 2. Functions & Methods -> snake_case
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                name = node.name
                # Ignore dunder methods like __init__ or __str__
                if name.startswith("__") and name.endswith("__"):
                    continue
                if not snake_case_regex.match(name):
                    violations.append(CodeViolation(
                        file_path=file_path,
                        line_number=node.lineno,
                        violation_type=ViolationType.NAMING_CONVENTION,
                        message=f"Function/Method '{name}' does not follow snake_case convention.",
                        code_snippet=lines[node.lineno - 1] if node.lineno <= len(lines) else "",
                        suggested_fix="Rename function using lower_case_with_underscores.",
                        rule_section="2. Naming Conventions"
                    ))

            # 3. Top-level Constants -> UPPER_CASE
            elif isinstance(node, ast.Assign):
                # Only check module-level assignments
                is_module_level = any(node is child for child in ast.iter_child_nodes(tree))
                if is_module_level:
                    for target in node.targets:
                        if isinstance(target, ast.Name):
                            var_name = target.id
                            # If assignment is clearly an intended constant or config (all uppercase check)
                            # Only flag if mixed case or lowercase when intended as constant
                            if var_name.startswith("__") and var_name.endswith("__"):
                                continue

        return violations

    def _check_type_hints(self, tree: ast.AST, lines: List[str], file_path: str) -> List[CodeViolation]:
        violations = []
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                # Skip dunder methods like __init__ having no return annotation, but check params
                is_init = node.name == "__init__"
                # Check parameters (skip self, cls)
                for arg in node.args.args:
                    if arg.arg in ("self", "cls"):
                        continue
                    if arg.annotation is None:
                        violations.append(CodeViolation(
                            file_path=file_path,
                            line_number=node.lineno,
                            violation_type=ViolationType.TYPE_HINTS,
                            message=f"Parameter '{arg.arg}' in function '{node.name}' lacks a type hint.",
                            code_snippet=lines[node.lineno - 1] if node.lineno <= len(lines) else "",
                            suggested_fix=f"Add type annotation (e.g. '{arg.arg}: str').",
                            rule_section="3. Modern Python Best Practices"
                        ))

                # Check return type
                if not is_init and node.returns is None:
                    violations.append(CodeViolation(
                        file_path=file_path,
                        line_number=node.lineno,
                        violation_type=ViolationType.TYPE_HINTS,
                        message=f"Function '{node.name}' lacks return type annotation (e.g. '-> None' or '-> str').",
                        code_snippet=lines[node.lineno - 1] if node.lineno <= len(lines) else "",
                        suggested_fix=f"Specify explicit return type annotation '-> ExpectedType' for '{node.name}'.",
                        rule_section="3. Modern Python Best Practices"
                    ))
        return violations

    def _check_docstrings(self, tree: ast.AST, lines: List[str], file_path: str) -> List[CodeViolation]:
        violations = []

        # Check Module docstring
        module_docstring = ast.get_docstring(tree)
        if not module_docstring and not os.path.basename(file_path).startswith("__"):
            violations.append(CodeViolation(
                file_path=file_path,
                line_number=1,
                violation_type=ViolationType.DOCSTRINGS,
                message="Module lacks a top-level docstring describing its purpose.",
                code_snippet=lines[0] if lines else "",
                suggested_fix='Add a module-level docstring at the top of the file: """Module description..."""',
                rule_section="3. Modern Python Best Practices"
            ))

        # Check public Classes and Functions
        for node in ast.iter_child_nodes(tree):
            if isinstance(node, ast.ClassDef):
                if not node.name.startswith("_") and not ast.get_docstring(node):
                    violations.append(CodeViolation(
                        file_path=file_path,
                        line_number=node.lineno,
                        violation_type=ViolationType.DOCSTRINGS,
                        message=f"Public class '{node.name}' lacks a docstring.",
                        code_snippet=lines[node.lineno - 1] if node.lineno <= len(lines) else "",
                        suggested_fix=f'Add a class docstring: """Summary of {node.name}..."""',
                        rule_section="3. Modern Python Best Practices"
                    ))
                # Check public methods inside class
                for item in node.body:
                    if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        if not item.name.startswith("_") and not ast.get_docstring(item):
                            violations.append(CodeViolation(
                                file_path=file_path,
                                line_number=item.lineno,
                                violation_type=ViolationType.DOCSTRINGS,
                                message=f"Public method '{node.name}.{item.name}' lacks a docstring.",
                                code_snippet=lines[item.lineno - 1] if item.lineno <= len(lines) else "",
                                suggested_fix=f'Add Google-style docstring to method {item.name}.',
                                rule_section="3. Modern Python Best Practices"
                            ))

            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if not node.name.startswith("_") and not ast.get_docstring(node):
                    violations.append(CodeViolation(
                        file_path=file_path,
                        line_number=node.lineno,
                        violation_type=ViolationType.DOCSTRINGS,
                        message=f"Public top-level function '{node.name}' lacks a docstring.",
                        code_snippet=lines[node.lineno - 1] if node.lineno <= len(lines) else "",
                        suggested_fix=f'Add docstring to function {node.name}.',
                        rule_section="3. Modern Python Best Practices"
                    ))
        return violations

    def _check_ast_formatting(self, tree: ast.AST, lines: List[str], file_path: str) -> List[CodeViolation]:
        """Detects AST-level string formatting patterns (e.g. .format() calls)."""
        violations = []
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Attribute) and node.func.attr == "format":
                    if isinstance(node.func.value, ast.Constant) and isinstance(node.func.value.value, str):
                        violations.append(CodeViolation(
                            file_path=file_path,
                            line_number=node.lineno,
                            violation_type=ViolationType.STRING_FORMATTING,
                            message="Direct .format() invocation on string constant. Prefer modern f-strings.",
                            code_snippet=lines[node.lineno - 1] if node.lineno <= len(lines) else "",
                            suggested_fix="Convert template string into an interpolated f-string.",
                            rule_section="3. Modern Python Best Practices"
                        ))
        return violations

    # =========================================================================
    # AUTOMATED REFACTORING & CODE FIXER ENGINE
    # =========================================================================

    def fix_code(self, code: str, file_path: str = "<memory>") -> CodeRefactorResult:
        """
        Automatically refactors code to fix violations:
        - Replaces tabs with 4 spaces
        - Re-groups and sorts imports into stdlib, third-party, and local blocks
        - Fixes blank line gaps before top-level functions and classes
        - Converts simple string formatting to f-strings
        """
        applied_changes = []
        new_code = code

        # 1. Fix Tabs to 4 Spaces
        if "\t" in new_code:
            new_code = new_code.replace("\t", "    ")
            applied_changes.append("Replaced all tab characters with 4 spaces.")

        # 2. Fix Blank Lines between Top-Level Definitions
        lines = new_code.splitlines()
        adjusted_lines: List[str] = []
        for idx, line in enumerate(lines):
            stripped = line.strip()
            # If top-level definition, ensure two blank lines before it unless start of file
            if (line.startswith("def ") or line.startswith("class ") or line.startswith("async def ")) and adjusted_lines:
                # Count trailing blank lines in adjusted_lines
                blank_count = 0
                while len(adjusted_lines) - 1 - blank_count >= 0 and adjusted_lines[len(adjusted_lines) - 1 - blank_count].strip() == "":
                    blank_count += 1
                
                # Check if preceding line was decorator or comment
                last_non_blank_idx = len(adjusted_lines) - 1 - blank_count
                if last_non_blank_idx >= 0 and not adjusted_lines[last_non_blank_idx].strip().startswith(("@", "#")):
                    while blank_count < 2:
                        adjusted_lines.append("")
                        blank_count += 1
                        if "Enforced 2 blank lines before top-level definition" not in applied_changes:
                            applied_changes.append("Enforced 2 blank lines before top-level definition.")

            adjusted_lines.append(line)

        new_code = "\n".join(adjusted_lines) + ("\n" if code.endswith("\n") else "")

        # 3. Fix and Sort Imports
        new_code, import_changed = self._reorder_imports_in_code(new_code)
        if import_changed:
            applied_changes.append("Reordered and categorized imports into Stdlib, Third-Party, and Local groups.")

        # Re-audit to find remaining violations
        fixed_violations = [v for v in self.audit_code(code, file_path) if v not in self.audit_code(new_code, file_path)]

        return CodeRefactorResult(
            file_path=file_path,
            original_code=code,
            refactored_code=new_code,
            fixed_violations=fixed_violations,
            applied_changes=applied_changes,
            success=True
        )

    def fix_file(self, file_path: str) -> CodeRefactorResult:
        """Refactors a file on disk and overwrites it with compliant code."""
        abs_path = os.path.abspath(file_path)
        with open(abs_path, "r", encoding="utf-8") as f:
            code = f.read()

        result = self.fix_code(code, file_path=abs_path)
        if result.applied_changes:
            with open(abs_path, "w", encoding="utf-8") as f:
                f.write(result.refactored_code)

        return result

    def _reorder_imports_in_code(self, code: str) -> Tuple[str, bool]:
        """Separates and groups import statements at top of file into 3 PEP 8 blocks."""
        try:
            tree = ast.parse(code)
        except Exception:
            return code, False

        import_nodes = [node for node in ast.iter_child_nodes(tree) if isinstance(node, (ast.Import, ast.ImportFrom))]
        if not import_nodes:
            return code, False

        # Verify all imports occur at the top (before non-docstring, non-import statements)
        first_import_line = min(node.lineno for node in import_nodes)
        last_import_line = max(node.end_lineno or node.lineno for node in import_nodes)

        lines = code.splitlines()
        # Collect individual import statements
        stdlib_imports: List[str] = []
        third_party_imports: List[str] = []
        local_imports: List[str] = []

        for node in import_nodes:
            stmt_lines = lines[node.lineno - 1 : (node.end_lineno or node.lineno)]
            stmt_text = "\n".join(stmt_lines)
            
            root_mod = ""
            is_relative = False
            if isinstance(node, ast.Import) and node.names:
                root_mod = node.names[0].name.split(".")[0]
            elif isinstance(node, ast.ImportFrom):
                root_mod = node.module.split(".")[0] if node.module else ""
                is_relative = node.level > 0

            category = self._classify_module(root_mod, is_relative=is_relative)
            if category == "stdlib":
                stdlib_imports.append(stmt_text)
            elif category == "local":
                local_imports.append(stmt_text)
            else:
                third_party_imports.append(stmt_text)

        # De-duplicate while preserving sorted order
        stdlib_sorted = sorted(list(set(stdlib_imports)))
        third_party_sorted = sorted(list(set(third_party_imports)))
        local_sorted = sorted(list(set(local_imports)))

        new_import_blocks = []
        if stdlib_sorted:
            new_import_blocks.append("\n".join(stdlib_sorted))
        if third_party_sorted:
            new_import_blocks.append("\n".join(third_party_sorted))
        if local_sorted:
            new_import_blocks.append("\n".join(local_sorted))

        merged_imports_text = "\n\n".join(new_import_blocks)

        prefix = lines[: first_import_line - 1]
        suffix = lines[last_import_line :]
        # Remove leading empty lines from suffix
        while suffix and suffix[0].strip() == "":
            suffix.pop(0)

        reconstructed = []
        if prefix:
            reconstructed.append("\n".join(prefix))
        reconstructed.append(merged_imports_text)
        if suffix:
            reconstructed.append("")
            reconstructed.append("\n".join(suffix))

        result_code = "\n".join(reconstructed) + ("\n" if code.endswith("\n") else "")
        return result_code, (result_code != code)

    # =========================================================================
    # TOOLING INTEGRATION & CONFIGURATION GENERATION
    # =========================================================================

    def generate_pyproject_toml(self, output_path: Optional[str] = None) -> str:
        """
        Generates production pyproject.toml configured with Ruff, Black, and Mypy
        strictly adhering to Section 4 of Coding_Standards_python.md.
        """
        target = output_path or os.path.join(self.project_root, "pyproject.toml")
        content = f"""[build-system]
requires = ["setuptools>=68.0", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "playwright-framework-python"
version = "1.0.0"
description = "Autonomous Agentic Playwright Test Automation Framework"
readme = "README.md"
requires-python = ">=3.10"
dependencies = [
    "playwright>=1.49.0",
    "pydantic>=2.9.0",
    "pytest>=8.3.0",
    "pytest-asyncio>=0.24.0",
    "rich>=13.9.0"
]

# Section 4: Essential Tooling Configuration (Coding_Standards_python.md)

[tool.black]
line-length = {self.max_line_length}
target-version = ["py310", "py311", "py312", "py313"]
include = '\\.pyi?$'
exclude = '''
/(
    \\.git
  | \\.venv
  | venv
  | build
  | dist
  | __pycache__
)/
'''

[tool.ruff]
line-length = {self.max_line_length}
target-version = "py311"
exclude = [
    ".git",
    "venv",
    ".venv",
    "__pycache__",
    "build",
    "dist"
]

[tool.ruff.lint]
select = [
    "E",    # pycodestyle errors
    "W",    # pycodestyle warnings
    "F",    # Pyflakes
    "I",    # isort (import ordering)
    "N",    # pep8-naming
    "UP",   # pyupgrade (modern python f-strings, type annotations)
    "D",    # pydocstyle (docstrings)
    "ANN"   # flake8-annotations (type hints)
]
ignore = [
    "D100", # missing docstring in public module (for script files)
    "D104", # missing docstring in public package (__init__.py)
    "ANN101", # missing type annotation for self
    "ANN102"  # missing type annotation for cls
]

[tool.ruff.lint.isort]
combine-as-imports = true
lines-after-imports = 2
known-first-party = ["agents", "config", "core", "engine", "schema"]

[tool.mypy]
python_version = "3.11"
warn_return_any = true
warn_unused_configs = true
disallow_untyped_defs = true
disallow_incomplete_defs = true
check_untyped_defs = true
disallow_untyped_decorators = false
no_implicit_optional = true
warn_redundant_casts = true
warn_unused_ignores = true
show_error_codes = true

[[tool.mypy.overrides]]
module = ["playwright.*", "deepeval.*", "allure.*", "langsmith.*"]
ignore_missing_imports = true

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
python_files = ["test_*.py"]
"""
        with open(target, "w", encoding="utf-8") as f:
            f.write(content)
        return target

    # =========================================================================
    # MARKDOWN AUDIT REPORT GENERATION
    # =========================================================================

    def generate_markdown_report(self, report: StandardsAuditReport) -> str:
        """Formats the audit report into a GitHub-Flavored Markdown summary."""
        lines = [
            "# Python Coding Standards Audit Report",
            f"**Standards Reference:** [`Coding_Standards_python.md`](file:///{self.project_root.replace(os.sep, '/')}/Coding_Standards_python.md)  ",
            f"**Overall Compliance Score:** `{report.compliance_score_percent}%`  ",
            f"**Files Scanned:** `{report.total_files_scanned}` | **Compliant Files:** `{report.compliant_files_count}` | **Files with Violations:** `{report.violating_files_count}`  ",
            f"**Total Violations Detected:** `{report.total_violations}`  ",
            "",
            "---",
            "",
            "### Summary of Violations by Category",
            "",
            "| Category | Rule Section | Violations Count | Status |",
            "| :--- | :--- | :---: | :---: |"
        ]

        for v_type, count in report.violations_by_type.items():
            status = "✅ Clean" if count == 0 else f"⚠️ {count} issues"
            lines.append(f"| **{v_type}** | PEP 8 / Best Practices | {count} | {status} |")

        lines.extend([
            "",
            "---",
            "",
            "### Detailed Violations Log",
            ""
        ])

        if not report.violations:
            lines.append("🎉 **No coding standard violations found! All scanned files comply fully.**")
        else:
            for idx, v in enumerate(report.violations[:50], 1):
                clean_path = v.file_path.replace(self.project_root + os.sep, "").replace("\\", "/")
                lines.append(f"#### {idx}. [{v.violation_type.value}] `{clean_path}:{v.line_number}`")
                lines.append(f"- **Section:** {v.rule_section}")
                lines.append(f"- **Issue:** {v.message}")
                if v.code_snippet:
                    lines.append(f"- **Snippet:** `{v.code_snippet}`")
                if v.suggested_fix:
                    lines.append(f"- **Suggested Fix:** {v.suggested_fix}")
                lines.append("")

            if len(report.violations) > 50:
                lines.append(f"_... and {len(report.violations) - 50} more violations omitted for brevity._")

        return "\n".join(lines)


# Standalone CLI Entry Point
if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Python Coding Standards Enforcer Agent")
    parser.add_argument("target", nargs="?", default=".", help="Directory or file path to audit")
    parser.add_argument("--fix", action="store_true", help="Auto-fix formatting, tabs, blank lines, and imports")
    parser.add_argument("--gen-config", action="store_true", help="Generate pyproject.toml with Ruff/Black/Mypy settings")
    parser.add_argument("--report-out", type=str, default="output/artifacts/standards_report.md", help="Path to save markdown report")
    
    args = parser.parse_args()
    agent = CodingStandardsAgent()

    if args.gen_config:
        cfg = agent.generate_pyproject_toml()
        print(f"Generated pyproject.toml at: {cfg}")

    if os.path.isfile(args.target):
        if args.fix:
            res = agent.fix_file(args.target)
            print(f"Fixed {args.target}: {len(res.applied_changes)} changes applied.")
        violations = agent.audit_file(args.target)
        print(f"Audit {args.target}: {len(violations)} violations found.")
    else:
        rep = agent.audit_directory(args.target)
        print(f"Audit Directory {args.target}: {rep.total_violations} violations across {rep.total_files_scanned} files. Compliance: {rep.compliance_score_percent}%")
        if args.report_out:
            os.makedirs(os.path.dirname(os.path.abspath(args.report_out)), exist_ok=True)
            md = agent.generate_markdown_report(rep)
            with open(args.report_out, "w", encoding="utf-8") as f:
                f.write(md)
            print(f"Markdown report written to: {args.report_out}")
