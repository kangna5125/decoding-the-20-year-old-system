"""Language detection, capability metadata, and syntax parsers for Python, Java, JavaScript, and C++."""
import ast
import os
import re
from typing import Any, Dict, List, Optional, Tuple

from config import SUPPORTED_LANGUAGES


def detect_language(code: str, filename: Optional[str] = None) -> str:
    """Detect language from filename extension or code syntax heuristics."""
    if filename:
        ext = os.path.splitext(filename)[1].lower()
        if ext == ".py":
            return "Python"
        elif ext == ".java":
            return "Java"
        elif ext in (".js", ".jsx", ".mjs"):
            return "JavaScript"
        elif ext in (".cpp", ".cc", ".cxx", ".hpp", ".h"):
            return "C++"

    if not code or not code.strip():
        return "Python"

    # Heuristic scoring based on signature language features
    scores = {
        "Python": 0,
        "Java": 0,
        "JavaScript": 0,
        "C++": 0
    }

    # Python patterns
    if re.search(r"\bdef\s+[a-zA-Z_]\w*\s*\(", code):
        scores["Python"] += 6
    if re.search(r"\belif\s+", code):
        scores["Python"] += 5
    if re.search(r"\bimport\s+[a-zA-Z_]", code) and not re.search(r"\bimport\s+java\b", code):
        scores["Python"] += 2
    if re.search(r":\s*(#.*)?$", code, re.MULTILINE):
        scores["Python"] += 3
    if "self." in code or "__init__" in code:
        scores["Python"] += 5
    if "#" in code and not re.search(r"#include\b", code):
        scores["Python"] += 2

    # Java patterns
    if re.search(r"\bpublic\s+(class|interface|enum|static|void|int|double|String)\b", code):
        scores["Java"] += 6
    if re.search(r"\bSystem\.(out|err)\.print", code):
        scores["Java"] += 6
    if re.search(r"\bpackage\s+[a-z0-9_.]+\s*;", code):
        scores["Java"] += 6
    if "@Override" in code:
        scores["Java"] += 4
    if re.search(r"\bpublic\s+static\s+void\s+main\b", code):
        scores["Java"] += 5

    # JavaScript patterns
    if re.search(r"\bconst\s+[a-zA-Z_]\w*\s*=", code) or re.search(r"\blet\s+[a-zA-Z_]\w*\s*=", code):
        scores["JavaScript"] += 5
    if re.search(r"\bfunction\s+[a-zA-Z_]\w*\s*\(", code) or re.search(r"=>", code):
        scores["JavaScript"] += 5
    if "console.log" in code:
        scores["JavaScript"] += 6
    if re.search(r"\b(module\.exports|export\s+default)\b", code):
        scores["JavaScript"] += 5
    if re.search(r"\basync\s+function\b", code) or "await " in code:
        scores["JavaScript"] += 3

    # C++ patterns
    if re.search(r"#include\s*<[a-zA-Z0-9_.]+>", code):
        scores["C++"] += 7
    if "std::" in code or "cout <<" in code or "cin >>" in code:
        scores["C++"] += 6
    if "nullptr" in code:
        scores["C++"] += 4
    if re.search(r"\btemplate\s*<", code):
        scores["C++"] += 5
    if re.search(r"\b(namespace|typedef|struct)\b", code):
        scores["C++"] += 3

    best_lang = max(scores, key=scores.get)
    if scores[best_lang] > 0:
        return best_lang

    # Fallback attempt: if valid Python AST, return Python
    try:
        ast.parse(code)
        return "Python"
    except Exception:
        return "Python"


def get_language_capabilities(language: str) -> Dict[str, Any]:
    """Return explicit capability declarations and honest status for each language."""
    if language == "Python":
        return {
            "language": "Python",
            "model_type": "CodeT5 (fine-tuned)",
            "summary_provider": "CodeT5-small (fine-tuned checkpoint models/codet5-small-csn)",
            "detailed_provider": "Gemini (when key configured) + Python AST Walkthrough",
            "walkthrough_type": "Rule-based (ast module, verified)",
            "status": "Production (Evaluated on held-out test split)",
            "evaluation_status": "BLEU 5.05, ROUGE-L 0.3547 against official CodeSearchNet Python test set",
            "is_evaluated": True
        }
    elif language == "Java":
        return {
            "language": "Java",
            "model_type": "LLM-based (Gemini) + Java Structural Parser",
            "summary_provider": "Gemini (LLM)",
            "detailed_provider": "Gemini + Structural Parser",
            "walkthrough_type": "Rule-based structural parse + LLM",
            "status": "LLM-based, not separately evaluated",
            "evaluation_status": "Not separately evaluated against a benchmark dataset",
            "is_evaluated": False
        }
    elif language == "JavaScript":
        return {
            "language": "JavaScript",
            "model_type": "LLM-based (Gemini) + JavaScript Structural Parser",
            "summary_provider": "Gemini (LLM)",
            "detailed_provider": "Gemini + Structural Parser",
            "walkthrough_type": "Rule-based structural parse + LLM",
            "status": "LLM-based, not separately evaluated",
            "evaluation_status": "Not separately evaluated against a benchmark dataset",
            "is_evaluated": False
        }
    elif language == "C++":
        return {
            "language": "C++",
            "model_type": "LLM-based (Gemini) + C++ Structural Parser",
            "summary_provider": "Gemini (LLM)",
            "detailed_provider": "Gemini + Structural Parser",
            "walkthrough_type": "Rule-based structural parse + LLM",
            "status": "LLM-based, not separately evaluated",
            "evaluation_status": "Not separately evaluated against a benchmark dataset",
            "is_evaluated": False
        }
    return {
        "language": language,
        "model_type": "Unknown",
        "summary_provider": "None",
        "detailed_provider": "None",
        "walkthrough_type": "None",
        "status": "Unsupported",
        "evaluation_status": "None",
        "is_evaluated": False
    }


# =====================================================================
# Language-Aware Structural Parsers (Rule-Based, Non-AI)
# =====================================================================

def parse_code_structure(code: str, language: str) -> Dict[str, Any]:
    """Extract structural facts, line references, calls, branches, and metrics from code."""
    lines = code.splitlines()
    loc = len([line for line in lines if line.strip() and not line.strip().startswith(("#", "//", "/*", "*"))])

    if language == "Python":
        return _parse_python_structure(code, lines, loc)
    elif language == "Java":
        return _parse_java_structure(code, lines, loc)
    elif language == "JavaScript":
        return _parse_js_structure(code, lines, loc)
    elif language == "C++":
        return _parse_cpp_structure(code, lines, loc)
    else:
        return _parse_generic_structure(code, lines, loc, language)


def _parse_python_structure(code: str, lines: List[str], loc: int) -> Dict[str, Any]:
    """Parse Python code using native AST."""
    try:
        tree = ast.parse(code)
    except Exception as e:
        return {
            "success": False,
            "language": "Python",
            "error": f"Python parse error: {str(e)}",
            "metrics": {"inputs": 0, "decisions": 0, "loops": 0, "calls": 0, "loc": loc},
            "facts": "Could not parse AST (incomplete or Python 2 syntax).",
            "functions": [],
            "classes": [],
            "line_steps": []
        }

    funcs = []
    classes = []
    decisions = 0
    loops = 0
    calls = 0

    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            params = [a.arg for a in node.args.args]
            funcs.append({
                "name": node.name,
                "line": node.lineno,
                "end_line": getattr(node, "end_lineno", node.lineno),
                "params": params
            })
        elif isinstance(node, ast.ClassDef):
            classes.append({
                "name": node.name,
                "line": node.lineno,
                "end_line": getattr(node, "end_lineno", node.lineno)
            })
        elif isinstance(node, ast.If):
            decisions += 1
        elif isinstance(node, (ast.For, ast.AsyncFor, ast.While)):
            loops += 1
        elif isinstance(node, ast.Call):
            calls += 1

    first_func = funcs[0] if funcs else None
    inputs_count = len(first_func["params"]) if first_func else 0

    facts_lines = [
        f"Language: Python | Lines of Code: {loc}",
        f"Functions detected ({len(funcs)}): {', '.join(f['name'] for f in funcs) or 'None'}",
        f"Classes detected ({len(classes)}): {', '.join(c['name'] for c in classes) or 'None'}",
        f"Branches / Decisions: {decisions} | Loops: {loops} | Function calls: {calls}"
    ]

    return {
        "success": True,
        "language": "Python",
        "metrics": {
            "inputs": inputs_count,
            "decisions": decisions,
            "loops": loops,
            "calls": calls,
            "loc": loc
        },
        "facts": "\n".join(facts_lines),
        "functions": funcs,
        "classes": classes
    }


def _parse_java_structure(code: str, lines: List[str], loc: int) -> Dict[str, Any]:
    """Rule-based structural analysis for Java code."""
    funcs = []
    classes = []
    decisions = len(re.findall(r"\b(if|else if|case)\b", code))
    loops = len(re.findall(r"\b(for|while|do)\b", code))
    calls = len(re.findall(r"\b[a-zA-Z_]\w*\s*\(", code))

    for i, line in enumerate(lines, start=1):
        # Class definition
        cls_match = re.search(r"\b(?:public\s+|private\s+|protected\s+)?class\s+([A-Z]\w*)", line)
        if cls_match:
            classes.append({"name": cls_match.group(1), "line": i})

        # Method definition
        method_match = re.search(
            r"\b(?:public|private|protected|static|final|\s)+[\w<>\[\]]+\s+([a-zA-Z_]\w*)\s*\(([^)]*)\)\s*(?:throws\s+[\w,\s]+)?\s*\{?",
            line
        )
        if method_match and not any(kw in method_match.group(1) for kw in ("if", "for", "while", "catch", "switch")):
            params = [p.strip().split()[-1] for p in method_match.group(2).split(",") if p.strip()]
            funcs.append({"name": method_match.group(1), "line": i, "params": params})

    inputs_count = len(funcs[0]["params"]) if funcs else 0

    facts_lines = [
        f"Language: Java | Lines of Code: {loc}",
        f"Classes found ({len(classes)}): {', '.join(c['name'] for c in classes) or 'None'}",
        f"Methods found ({len(funcs)}): {', '.join(f['name'] for f in funcs) or 'None'}",
        f"Decisions (if/case): {decisions} | Loops: {loops} | Invocation calls: {calls}"
    ]

    return {
        "success": True,
        "language": "Java",
        "metrics": {
            "inputs": inputs_count,
            "decisions": decisions,
            "loops": loops,
            "calls": calls,
            "loc": loc
        },
        "facts": "\n".join(facts_lines),
        "functions": funcs,
        "classes": classes
    }


def _parse_js_structure(code: str, lines: List[str], loc: int) -> Dict[str, Any]:
    """Rule-based structural analysis for JavaScript code."""
    funcs = []
    classes = []
    decisions = len(re.findall(r"\b(if|else if|case)\b", code))
    loops = len(re.findall(r"\b(for|while|do)\b", code))
    calls = len(re.findall(r"\b[a-zA-Z_]\w*\s*\(", code))

    for i, line in enumerate(lines, start=1):
        # Class
        cls_match = re.search(r"\bclass\s+([A-Z]\w*)", line)
        if cls_match:
            classes.append({"name": cls_match.group(1), "line": i})

        # function name(...)
        fn_match = re.search(r"\bfunction(?:\s+([a-zA-Z_]\w*))?\s*\(([^)]*)\)", line)
        if fn_match:
            name = fn_match.group(1) or f"anonymous_fn_L{i}"
            params = [p.strip().split("=")[0].strip() for p in fn_match.group(2).split(",") if p.strip()]
            funcs.append({"name": name, "line": i, "params": params})
            continue

        # const/let name = (...) => or function(...)
        arrow_match = re.search(r"\b(?:const|let|var)\s+([a-zA-Z_]\w*)\s*=\s*(?:async\s*)?\(([^)]*)\)\s*=>", line)
        if arrow_match:
            name = arrow_match.group(1)
            params = [p.strip().split("=")[0].strip() for p in arrow_match.group(2).split(",") if p.strip()]
            funcs.append({"name": name, "line": i, "params": params})

    inputs_count = len(funcs[0]["params"]) if funcs else 0

    facts_lines = [
        f"Language: JavaScript | Lines of Code: {loc}",
        f"Classes found ({len(classes)}): {', '.join(c['name'] for c in classes) or 'None'}",
        f"Functions found ({len(funcs)}): {', '.join(f['name'] for f in funcs) or 'None'}",
        f"Decisions (if/case): {decisions} | Loops: {loops} | Function calls: {calls}"
    ]

    return {
        "success": True,
        "language": "JavaScript",
        "metrics": {
            "inputs": inputs_count,
            "decisions": decisions,
            "loops": loops,
            "calls": calls,
            "loc": loc
        },
        "facts": "\n".join(facts_lines),
        "functions": funcs,
        "classes": classes
    }


def _parse_cpp_structure(code: str, lines: List[str], loc: int) -> Dict[str, Any]:
    """Rule-based structural analysis for C++ code."""
    funcs = []
    classes = []
    decisions = len(re.findall(r"\b(if|else if|case)\b", code))
    loops = len(re.findall(r"\b(for|while|do)\b", code))
    calls = len(re.findall(r"\b[a-zA-Z_]\w*\s*\(", code))

    for i, line in enumerate(lines, start=1):
        # Class or Struct
        cls_match = re.search(r"\b(class|struct)\s+([A-Za-z_]\w*)\s*(?::|\{|$)", line)
        if cls_match and not line.strip().startswith("//"):
            classes.append({"name": cls_match.group(2), "line": i})

        # Function definition (excluding control keywords)
        fn_match = re.search(r"\b([\w:<>&*~]+)\s+([a-zA-Z_]\w*)\s*\(([^)]*)\)\s*(?:const)?\s*\{?", line)
        if fn_match and not any(kw in fn_match.group(2) for kw in ("if", "for", "while", "catch", "switch")):
            ret_type = fn_match.group(1)
            name = fn_match.group(2)
            if ret_type not in ("return", "throw", "case", "new", "delete", "goto"):
                raw_params = fn_match.group(3)
                params = [p.strip().split()[-1].lstrip("*&") for p in raw_params.split(",") if p.strip()]
                funcs.append({"name": name, "line": i, "params": params, "return_type": ret_type})

    inputs_count = len(funcs[0]["params"]) if funcs else 0

    facts_lines = [
        f"Language: C++ | Lines of Code: {loc}",
        f"Classes/Structs found ({len(classes)}): {', '.join(c['name'] for c in classes) or 'None'}",
        f"Functions found ({len(funcs)}): {', '.join(f['name'] for f in funcs) or 'None'}",
        f"Decisions (if/case): {decisions} | Loops: {loops} | Function calls: {calls}"
    ]

    return {
        "success": True,
        "language": "C++",
        "metrics": {
            "inputs": inputs_count,
            "decisions": decisions,
            "loops": loops,
            "calls": calls,
            "loc": loc
        },
        "facts": "\n".join(facts_lines),
        "functions": funcs,
        "classes": classes
    }


def _parse_generic_structure(code: str, lines: List[str], loc: int, language: str) -> Dict[str, Any]:
    return {
        "success": True,
        "language": language,
        "metrics": {"inputs": 0, "decisions": 0, "loops": 0, "calls": 0, "loc": loc},
        "facts": f"Language: {language} | Lines of Code: {loc}",
        "functions": [],
        "classes": []
    }
