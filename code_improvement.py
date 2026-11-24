"""Code improvement engine: potential bug risk detection, modernization suggestions, and code comparison."""
import ast
import difflib
import re
from typing import Any, Dict, List, Tuple


def detect_code_risks(code: str, language: str = "Python") -> List[Dict[str, Any]]:
    """Identify potential bugs, security concerns, unhandled states, and complexity risks."""
    risks = []
    lines = code.splitlines()

    if language == "Python":
        try:
            tree = ast.parse(code)
            for node in ast.walk(tree):
                # 1. Mutable default arguments
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    for default in node.args.defaults + node.args.kw_defaults:
                        if isinstance(default, (ast.List, ast.Dict, ast.Set)):
                            risks.append({
                                "category": "Mutable Default Argument Risk",
                                "severity": "Medium",
                                "line": default.lineno,
                                "code_snippet": lines[default.lineno - 1].strip() if default.lineno <= len(lines) else "",
                                "description": (
                                    f"Function `{node.name}` defines a mutable default argument (`{ast.unparse(default)}`). "
                                    "In Python, default arguments are evaluated once at definition time and shared across calls, "
                                    "leading to unexpected state mutation bugs."
                                ),
                                "recommendation": "Use `None` as the default value and initialize the collection inside the function body."
                            })

                # 2. Division without zero check
                if isinstance(node, ast.BinOp) and isinstance(node.op, (ast.Div, ast.FloorDiv, ast.Mod)):
                    if isinstance(node.right, ast.Name):
                        risks.append({
                            "category": "Potential Division by Zero",
                            "severity": "High",
                            "line": node.lineno,
                            "code_snippet": lines[node.lineno - 1].strip() if node.lineno <= len(lines) else "",
                            "description": f"Division or modulo operation by variable `{ast.unparse(node.right)}` without an explicit zero-check.",
                            "recommendation": f"Add guard clause verifying `{ast.unparse(node.right)} != 0` before arithmetic execution."
                        })

                # 3. Bare except clauses
                if isinstance(node, ast.ExceptHandler) and node.type is None:
                    risks.append({
                        "category": "Bare Exception Handling",
                        "severity": "Medium",
                        "line": node.lineno,
                        "code_snippet": lines[node.lineno - 1].strip() if node.lineno <= len(lines) else "",
                        "description": "A bare `except:` clause catches all exceptions, including `KeyboardInterrupt` and `SystemExit`, masking critical failures.",
                        "recommendation": "Catch specific exception types such as `except Exception:` or dedicated error classes."
                    })
        except Exception:
            pass

    # Generic language checks (Python, Java, JS, C++)
    for i, line in enumerate(lines, start=1):
        line_s = line.strip()

        # Magic numbers (numeric constants > 5 without constant naming)
        num_matches = re.findall(r"(?<![a-zA-Z_0-9])(\b\d{2,}\b)(?![a-zA-Z_0-9])", line_s)
        if num_matches and not any(kw in line_s for kw in ("const", "final", "STATIC", "MAX_", "MIN_", "PORT", "VERSION")):
            if not line_s.startswith(("#", "//", "/*", "*")):
                risks.append({
                    "category": "Hardcoded Magic Number",
                    "severity": "Low",
                    "line": i,
                    "code_snippet": line_s,
                    "description": f"Contains numeric constant `{num_matches[0]}` directly in executable logic.",
                    "recommendation": "Extract magic numbers into descriptive named constants for maintainability."
                })

        # Redundant boolean comparison (e.g. if x == true)
        if re.search(r"==\s*(True|true|False|false)", line_s):
            risks.append({
                "category": "Redundant Boolean Comparison",
                "severity": "Low",
                "line": i,
                "code_snippet": line_s,
                "description": "Explicit equality comparison against a boolean literal (`== True` / `== false`).",
                "recommendation": "Simplify condition directly (e.g. `if condition:` or `if not condition:`)."
            })

    return risks


def generate_modernization_suggestions(code: str, language: str = "Python") -> List[Dict[str, Any]]:
    """Propose maintainability and modern idiom refactorings with before/after snippets."""
    suggestions = []
    lines = code.splitlines()

    if language == "Python":
        # 1. Suggest f-strings for old % or .format formatting
        for i, line in enumerate(lines, start=1):
            if "%" in line and re.search(r'"[^"]*"\s*%\s*\(', line):
                suggestions.append({
                    "title": "Modernize to Python f-string",
                    "line": i,
                    "original": line.strip(),
                    "suggested": re.sub(r'"([^"]*)"\s*%\s*\((.*?)\)', r'f"\1"', line.strip()),
                    "explanation": "Replace legacy `%` printf-style formatting with modern f-strings (introduced in Python 3.6).",
                    "benefit": "Improved readability, type safety, and execution performance.",
                    "compatibility_concerns": "Requires Python 3.6+."
                })
            elif ".format(" in line:
                suggestions.append({
                    "title": "Replace .format() with f-strings",
                    "line": i,
                    "original": line.strip(),
                    "suggested": "# Example: f\"Value: {variable}\"",
                    "explanation": "Standardize string interpolation using clean f-strings.",
                    "benefit": "Reduces boilerplate argument mapping.",
                    "compatibility_concerns": "Requires Python 3.6+."
                })

        # 2. Redundant boolean check simplification
        for i, line in enumerate(lines, start=1):
            if "== True" in line:
                suggestions.append({
                    "title": "Simplify Redundant Boolean Expression",
                    "line": i,
                    "original": line.strip(),
                    "suggested": line.replace("== True", "").strip(),
                    "explanation": "Remove unnecessary `== True` check from conditional evaluation.",
                    "benefit": "Cleaner idiomatic syntax and prevents truthiness mismatches.",
                    "compatibility_concerns": "None."
                })

    # Generic suggestion: add documentation & type safety
    if not any("def " in l and "->" in l for l in lines) and language == "Python":
        suggestions.append({
            "title": "Add Explicit Type Annotations",
            "line": 1,
            "original": lines[0].strip() if lines else "",
            "suggested": "# Example: def calculate(x: float, rate: float = 0.05) -> float:",
            "explanation": "Add Python type annotations (`typing` / PEP 484) to function parameters and return types.",
            "benefit": "Enables static type checking (mypy), catches bugs before runtime, and enhances IDE autocomplete.",
            "compatibility_concerns": "Requires Python 3.5+."
        })

    return suggestions


def compute_code_diff(old_code: str, new_code: str) -> Dict[str, Any]:
    """Compute structured comparison and behavioral change notes between two code revisions."""
    old_lines = old_code.splitlines(keepends=True)
    new_lines = new_code.splitlines(keepends=True)

    diff = list(difflib.unified_diff(
        old_lines, new_lines,
        fromfile="Original Code", tofile="Revised Code"
    ))

    added_count = sum(1 for line in diff if line.startswith("+") and not line.startswith("+++"))
    removed_count = sum(1 for line in diff if line.startswith("-") and not line.startswith("---"))

    # Line-by-line tagged comparison for UI rendering
    tagged_lines = []
    for line in difflib.ndiff(old_code.splitlines(), new_code.splitlines()):
        tag = line[:2]
        content = line[2:]
        if tag == "+ ":
            tagged_lines.append({"status": "added", "text": content})
        elif tag == "- ":
            tagged_lines.append({"status": "removed", "text": content})
        elif tag == "  ":
            tagged_lines.append({"status": "unchanged", "text": content})

    return {
        "unified_diff": "".join(diff) or "No changes detected.",
        "added_lines": added_count,
        "removed_lines": removed_count,
        "tagged_lines": tagged_lines,
        "behavioral_note": (
            "Caution: Behavioral equivalence between legacy and refactored code has not been formally verified. "
            "Always validate modernization changes with comprehensive unit tests before deploying."
        )
    }
