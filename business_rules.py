"""Candidate business rule detection engine for legacy source code."""
import ast
import re
from typing import Any, Dict, List, Optional


def detect_candidate_business_rules(
    code: str,
    language: str = "Python",
    filename: str = "source"
) -> List[Dict[str, Any]]:
    """Scan source code for candidate business logic, thresholds, and financial constraints."""
    rules = []
    lines = code.splitlines()

    if language == "Python":
        try:
            tree = ast.parse(code)
            for node in ast.walk(tree):
                if isinstance(node, ast.If):
                    rule = _analyze_python_if_condition(node, lines, filename)
                    if rule:
                        rules.append(rule)
                elif isinstance(node, (ast.Assign, ast.AugAssign)):
                    calc_rule = _analyze_python_calculation(node, lines, filename)
                    if calc_rule and not any(r["line_start"] == calc_rule["line_start"] for r in rules):
                        rules.append(calc_rule)
            if rules:
                return rules
        except Exception:
            pass

    # Generic structural scanner for Java, JavaScript, C++, or unparseable Python
    for i, line in enumerate(lines, start=1):
        line_s = line.strip()
        if not line_s or line_s.startswith(("//", "#", "/*", "*")):
            continue

        # Financial or threshold conditions
        if re.search(r"\b(if|else if)\b.*\b(balance|bal|fee|rate|discount|price|minbal|total|amount|limit|credit)\b", line_s, re.I):
            cond_match = re.search(r"\((.*?)\)|if\s+(.*?):", line_s)
            cond_text = (cond_match.group(1) or cond_match.group(2) if cond_match else line_s).strip()
            num_match = re.search(r"(\d+(?:\.\d+)?)", line_s)
            num_val = num_match.group(1) if num_match else "threshold"

            rules.append({
                "rule_id": f"rule_gen_{i}",
                "title": f"Candidate Financial / Threshold Rule ({cond_text[:35]})",
                "category": "Financial / Threshold Constraint",
                "explanation": f"The code enforces a conditional check on `{cond_text}`, suggesting an operational constraint or policy threshold around value `{num_val}`.",
                "code_snippet": f"Line {i}: {line_s}",
                "line_reference": f"Line {i} of {filename or 'source'}",
                "line_start": i,
                "why_identified": f"Detected conditional branching involving business term and threshold: '{cond_text}'",
                "confidence": "Candidate Rule (High)",
                "status": "Pending Review"
            })

        # Fee or penalty calculation
        elif re.search(r"\b(fee|penalty|interest|discount|total)\s*(\+=|-=|\*=|=)\s*.*[\d*+/]", line_s, re.I):
            rules.append({
                "rule_id": f"rule_gen_calc_{i}",
                "title": f"Candidate Policy Calculation: {line_s.split('=')[0].strip()}",
                "category": "Policy Calculation",
                "explanation": f"Calculates or modifies a financial variable (`{line_s.split('=')[0].strip()}`) using mathematical formula `{line_s}`.",
                "code_snippet": f"Line {i}: {line_s}",
                "line_reference": f"Line {i} of {filename or 'source'}",
                "line_start": i,
                "why_identified": "Detected assignment modifying a financial quantity with mathematical operators.",
                "confidence": "Candidate Rule (Medium)",
                "status": "Pending Review"
            })

    return rules


def _analyze_python_if_condition(node: ast.If, lines: List[str], filename: str) -> Optional[Dict[str, Any]]:
    """Analyze a Python AST If node for candidate business rule patterns."""
    cond_str = ast.unparse(node.test)
    cond_lower = cond_str.lower()
    start_l = node.lineno
    end_l = getattr(node, "end_lineno", start_l)
    snippet = "\n".join(lines[start_l - 1:min(len(lines), end_l)])

    # Check for keywords indicating business domains
    financial_terms = ("bal", "balance", "fee", "rate", "pen", "penalty", "limit", "minbal", "discount", "tax", "si", "price")
    has_biz_term = any(t in cond_lower for t in financial_terms)

    # Check for comparison with constant
    has_const = any(isinstance(n, ast.Constant) for n in ast.walk(node.test))

    if has_biz_term or (has_const and any(isinstance(op, (ast.Lt, ast.LtE, ast.Gt, ast.GtE, ast.Eq)) for op in ast.walk(node.test))):
        if any(t in cond_lower for t in ("bal", "balance", "minbal", "limit")):
            title = f"Balance Requirement / Limit Rule (`{cond_str}`)"
            cat = "Account Constraint"
            expl = f"Evaluates whether account funds meet threshold constraint `{cond_str}` before executing state operations."
        elif any(t in cond_lower for t in ("fee", "pen", "penalty", "rate", "discount")):
            title = f"Rate / Fee Adjustment Criterion (`{cond_str}`)"
            cat = "Pricing & Penalty"
            expl = f"Applies rate or fee rules based on condition `{cond_str}`."
        else:
            title = f"Operational Boundary Condition (`{cond_str}`)"
            cat = "Validation Constraint"
            expl = f"Checks threshold condition `{cond_str}` to govern downstream logic execution."

        return {
            "rule_id": f"rule_py_{start_l}",
            "title": title,
            "category": cat,
            "explanation": expl,
            "code_snippet": snippet,
            "line_reference": f"Lines {start_l}–{end_l} of {filename or 'source'}",
            "line_start": start_l,
            "why_identified": f"AST condition evaluates `{cond_str}` comparing variables against thresholds or limits.",
            "confidence": "Candidate Rule (High)",
            "status": "Pending Review"
        }

    return None


def _analyze_python_calculation(node: ast.stmt, lines: List[str], filename: str) -> Optional[Dict[str, Any]]:
    """Analyze formula assignments (e.g. interest or fee calculation)."""
    start_l = node.lineno
    end_l = getattr(node, "end_lineno", start_l)
    snippet = "\n".join(lines[start_l - 1:end_l])
    code_str = ast.unparse(node)
    code_lower = code_str.lower()

    # Formulas involving interest, penalty, check digits, or fees
    if any(k in code_lower for k in ("* r * t", "minbal - bal", "chk_digit", "total % 10", "* rate", "round(")):
        if "* r * t" in code_lower or "interest" in code_lower:
            title = "Simple / Accrued Interest Computation Formula"
            expl = f"Computes interest on principal using formula `{code_str}`."
        elif "minbal - bal" in code_lower or "fee" in code_lower:
            title = "Balance Shortfall & Penalty Fee Calculation"
            expl = f"Computes financial penalty based on shortfall difference `{code_str}`."
        elif "total % 10" in code_lower or "10 - total" in code_lower:
            title = "Check Digit Verification Algorithm"
            expl = f"Computes verification check digit modulo checksum using formula `{code_str}`."
        else:
            title = f"Financial Rate / Fee Calculation (`{code_str[:35]}`)"
            expl = f"Applies mathematical rule `{code_str}` to calculate operational amounts."

        return {
            "rule_id": f"rule_py_calc_{start_l}",
            "title": title,
            "category": "Financial Computation",
            "explanation": expl,
            "code_snippet": snippet,
            "line_reference": f"Line {start_l} of {filename or 'source'}",
            "line_start": start_l,
            "why_identified": f"Syntactic formula pattern detected: `{code_str}`.",
            "confidence": "Candidate Rule (High)",
            "status": "Pending Review"
        }

    return None
