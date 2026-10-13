Python coding standards are primarily defined by **PEP 8** (Python Enhancement Proposal 8), which outlines the style guide for writing clean, readable, and maintainable Python code. Modern Python development also heavily relies on automated tools and type hinting.

Here is a breakdown of the essential Python coding standards and best practices:

---

### 1. Core Style & Formatting (PEP 8)

* **Indentation:** Use **4 spaces** per indentation level. Never mix tabs and spaces.
* **Line Length:** Limit all lines to a maximum of **79 characters** for code (PEP 8 standard) or **88 characters** if using modern formatters like Black.
* **Blank Lines:**
* Surround top-level functions and classes with **two blank lines**.
* Method definitions inside a class are separated by **one blank line**.


* **Imports:** Always put imports at the top of the file, grouped in this specific order:
1. Standard library imports
2. Related third-party imports
3. Local application/library specific imports
*(Separate each group with a blank line).*



---

### 2. Naming Conventions

Consistent naming makes code self-documenting. Follow these standard patterns:

| Type | Convention | Example |
| --- | --- | --- |
| **Classes** | `PascalCase` | `UserAccount`, `HttpConnection` |
| **Functions & Methods** | `snake_case` | `calculate_total`, `fetch_user_data` |
| **Variables** | `snake_case` | `user_count`, `is_active` |
| **Constants** | `UPPER_CASE` | `MAX_RETRIES`, `DEFAULT_TIMEOUT` |
| **Modules & Packages** | `snake_case` (short) | `utils.py`, `database.py` |
| **Private Attributes** | `_leading_underscore` | `_internal_cache` |

---

### 3. Modern Python Best Practices

* **Type Hints:** Use type annotations to clarify function signatures and improve IDE support:
```python
def get_user_name(user_id: int) -> str:
    return f"User_{user_id}"

```


* **Docstrings:** Use docstrings (Google or Sphinx style) for all public modules, functions, classes, and methods:
```python
def calculate_area(radius: float) -> float:
    """Calculate the area of a circle given its radius.

    Args:
        radius: The radius of the circle.

    Returns:
        The calculated area.
    """
    ...

```


* **F-strings:** Prefer f-strings over `%`-formatting or `.format()` for string interpolation because they are more readable and performant.

---

### 4. Essential Tooling (Linters & Formatters)

Instead of manually enforcing style rules, integrate automated tools into your development workflow:

* **Ruff:** The modern, lightning-fast all-in-one linter and code formatter that replaces Flake8, Black, isort, and more.
* **Black:** The uncompromising code formatter that automatically handles line wrapping and indentation.
* **Mypy:** A static type checker for catching type-related errors before runtime.

Would you like help setting up a configuration file (like `pyproject.toml`) for Ruff or Black in your project?