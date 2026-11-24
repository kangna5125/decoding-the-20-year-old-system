"""Explanation Studio engine providing the seven distinct explanation modes."""
import ast
import re
from typing import Any, Dict, List, Optional

from explainer import CodeExplainer
from languages import get_language_capabilities, parse_code_structure
import llm_service
from visualizer import generate_mermaid_flowchart
from walkthrough import build_walkthrough


def generate_line_by_line_explanation(code: str, language: str) -> List[Dict[str, Any]]:
    """Generate a strictly rule-based, line-by-line explanation tied to line numbers."""
    lines = code.splitlines()
    explanations = []

    if language == "Python":
        try:
            tree = ast.parse(code)
            line_map: Dict[int, str] = {}
            for node in ast.walk(tree):
                if hasattr(node, "lineno"):
                    lno = node.lineno
                    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        params = ", ".join(a.arg for a in node.args.args)
                        line_map[lno] = f"Defines function `{node.name}` accepting parameters: `{params or 'none'}`."
                    elif isinstance(node, ast.ClassDef):
                        line_map[lno] = f"Defines class `{node.name}`."
                    elif isinstance(node, ast.If) and lno not in line_map:
                        line_map[lno] = f"Branch decision: Evaluates condition `{ast.unparse(node.test)}`."
                    elif isinstance(node, (ast.For, ast.AsyncFor)) and lno not in line_map:
                        line_map[lno] = f"Loop iteration: Iterates over `{ast.unparse(node.iter)}` as `{ast.unparse(node.target)}`."
                    elif isinstance(node, ast.While) and lno not in line_map:
                        line_map[lno] = f"Loop condition: Continues looping while `{ast.unparse(node.test)}` remains True."
                    elif isinstance(node, ast.Return) and lno not in line_map:
                        val = ast.unparse(node.value) if node.value else "nothing"
                        line_map[lno] = f"Function exit: Returns `{val}` to the caller."
                    elif isinstance(node, ast.AugAssign) and lno not in line_map:
                        line_map[lno] = f"State update: Modifies `{ast.unparse(node.target)}` by `{ast.unparse(node.value)}`."
                    elif isinstance(node, ast.Assign) and lno not in line_map:
                        targets = ", ".join(ast.unparse(t) for t in node.targets)
                        line_map[lno] = f"Assignment: Initializes or updates `{targets}` with `{ast.unparse(node.value)}`."

            for idx, raw_line in enumerate(lines, start=1):
                stripped = raw_line.strip()
                if not stripped:
                    continue
                if stripped.startswith("#"):
                    expl = f"Comment: {stripped.lstrip('#').strip()}"
                else:
                    expl = line_map.get(idx, f"Executes: `{stripped}`")
                explanations.append({
                    "line_number": idx,
                    "code": raw_line,
                    "explanation": expl,
                    "source": "Rule-based (Python AST)"
                })
            return explanations
        except Exception:
            pass

    # Generic rule-based line parser for other languages
    for idx, raw_line in enumerate(lines, start=1):
        stripped = raw_line.strip()
        if not stripped:
            continue
        if stripped.startswith(("//", "/*", "*")):
            expl = "Comment / documentation note."
        elif re.search(r"\b(if|else if)\b", stripped):
            expl = "Conditional branch: Evaluates decision logic."
        elif re.search(r"\b(for|while)\b", stripped):
            expl = "Loop structure: Repeats block over range or condition."
        elif re.search(r"\breturn\b", stripped):
            expl = "Return statement: Exits and yields result."
        elif "=" in stripped:
            expl = "Assignment / state modification."
        elif "(" in stripped and ")" in stripped:
            expl = "Invocation: Calls function or method."
        else:
            expl = f"Executes statement in {language}."

        explanations.append({
            "line_number": idx,
            "code": raw_line,
            "explanation": expl,
            "source": f"Rule-based ({language} Parser)"
        })

    return explanations


class ExplanationStudio:
    """Coordinates the seven explanation modes across CodeT5, rule-based AST, and Gemini."""

    def __init__(self, explainer: CodeExplainer):
        self.explainer = explainer

    def explain(
        self,
        code: str,
        language: str,
        mode: str,
        gemini_model: Optional[str] = None
    ) -> Dict[str, Any]:
        """Generate analysis according to selected mode and language."""
        caps = get_language_capabilities(language)
        struct = parse_code_structure(code, language)

        # Mode 1: Quick Explanation
        if mode == "Quick Explanation":
            if language == "Python":
                # Use fine-tuned CodeT5 (or verified human correction store)
                res = self.explainer.explain(code)
                source_label = "Verified by reviewer" if res["source"] == "verified" else "CodeT5 (fine-tuned)"
                return {
                    "mode": mode,
                    "language": language,
                    "text": res["explanation"] or "(No description generated by model)",
                    "confidence": res.get("confidence"),
                    "level": res.get("level"),
                    "source": source_label,
                    "is_verified": (res["source"] == "verified"),
                    "details": res,
                    "capabilities": caps
                }
            else:
                # Java / JS / C++: use Gemini if key present, otherwise structural summary
                if llm_service.is_api_key_configured():
                    prompt = f"Provide a single clear, plain-English summary sentence explaining what this {language} function does."
                    resp = llm_service.call_gemini(prompt, code, struct["facts"], model_name=gemini_model)
                    if resp["success"]:
                        return {
                            "mode": mode,
                            "language": language,
                            "text": resp["text"],
                            "source": f"{resp['source']} [LLM-based, not separately evaluated]",
                            "capabilities": caps
                        }
                # Rule-based structural fallback
                fn_names = [f["name"] for f in struct["functions"]]
                fallback_text = f"Analyzes {language} code containing {len(struct['functions'])} function(s): {', '.join(fn_names) or 'code block'} across {struct['metrics']['loc']} lines."
                if not llm_service.is_api_key_configured():
                    fallback_text += " (API key not configured; showing rule-based structural summary)."
                return {
                    "mode": mode,
                    "language": language,
                    "text": fallback_text,
                    "source": "Rule-based structural parse",
                    "capabilities": caps
                }

        # Mode 2: Detailed Explanation
        elif mode == "Detailed Explanation":
            prompt = (
                f"Provide a thorough, comprehensive technical breakdown of this {language} code. "
                "Explain the primary objective, step-by-step logic, input parameters, transformations, "
                "and return value in clean, professional English."
            )
            resp = llm_service.call_gemini(prompt, code, struct["facts"], model_name=gemini_model)
            if resp["success"]:
                src = resp["source"]
                if language != "Python":
                    src += " [LLM-based, not separately evaluated]"
                return {
                    "mode": mode,
                    "language": language,
                    "text": resp["text"],
                    "source": src,
                    "capabilities": caps
                }
            # Fallback: Rule-based walkthrough steps
            wt = build_walkthrough(code) if language == "Python" else None
            fallback_parts = [
                f"### Detailed Breakdown ({language} - Rule-Based Analysis)",
                f"- **Lines of Code:** {struct['metrics']['loc']}",
                f"- **Decisions / Branches:** {struct['metrics']['decisions']}",
                f"- **Loops:** {struct['metrics']['loops']}",
                f"- **Function Calls:** {struct['metrics']['calls']}"
            ]
            if wt and wt["success"]:
                fallback_parts.append("\n**Execution Steps:**")
                for s in wt["steps"]:
                    indent = "  " * s["depth"]
                    fallback_parts.append(f"{indent}{s['prefix']} {s['text']}")
            if not llm_service.is_api_key_configured():
                fallback_parts.append("\n*(API key not configured. Showing complete rule-based structural breakdown.)*")
            return {
                "mode": mode,
                "language": language,
                "text": "\n".join(fallback_parts),
                "source": "Rule-based (AST/Structure)",
                "capabilities": caps
            }

        # Mode 3: Line-by-Line Explanation
        elif mode == "Line-by-Line Explanation":
            line_steps = generate_line_by_line_explanation(code, language)
            return {
                "mode": mode,
                "language": language,
                "lines": line_steps,
                "source": "Rule-based, read directly from the code",
                "capabilities": caps
            }

        # Mode 4: Technical Explanation
        elif mode == "Technical Explanation":
            prompt = (
                f"Analyze the technical implementation of this {language} code. "
                "Discuss: (1) Algorithmic complexity (time and space), (2) Data structures used, "
                "(3) Edge conditions handled or unhandled, and (4) Concurrency or type considerations. "
                "Cite specific code lines for every claim."
            )
            resp = llm_service.call_gemini(prompt, code, struct["facts"], model_name=gemini_model)
            if resp["success"]:
                src = resp["source"]
                if language != "Python":
                    src += " [LLM-based, not separately evaluated]"
                return {
                    "mode": mode,
                    "language": language,
                    "text": resp["text"],
                    "source": src,
                    "capabilities": caps
                }
            # Rule-based fallback
            m = struct["metrics"]
            time_comp = "O(n) linear" if m["loops"] == 1 else ("O(n^2) nested" if m["loops"] > 1 else "O(1) constant")
            fallback = (
                f"### Technical Implementation Profile (Rule-Based)\n"
                f"- **Language:** {language}\n"
                f"- **Estimated Time Complexity:** {time_comp} based on {m['loops']} loop construct(s)\n"
                f"- **Branching Factor:** {m['decisions']} conditional branch(es)\n"
                f"- **Subroutine Invocations:** {m['calls']} external or helper call(s)\n"
                f"- **Code Density:** {m['loc']} active lines of code\n\n"
                f"*(API key not configured. For in-depth algorithmic discussion, configure GEMINI_API_KEY in .env.)*"
            )
            return {
                "mode": mode,
                "language": language,
                "text": fallback,
                "source": "Rule-based AST profiling",
                "capabilities": caps
            }

        # Mode 5: Business Explanation
        elif mode == "Business Explanation":
            prompt = (
                f"Analyze this {language} code strictly from a business domain perspective. "
                "What real-world business process, operation, financial rule, or entity does this code support? "
                "Frame all findings as 'Candidate Business Rules' and do not assert unverified company policies."
            )
            resp = llm_service.call_gemini(prompt, code, struct["facts"], model_name=gemini_model)
            if resp["success"]:
                src = resp["source"]
                if language != "Python":
                    src += " [LLM-based, not separately evaluated]"
                return {
                    "mode": mode,
                    "language": language,
                    "text": resp["text"],
                    "source": src,
                    "capabilities": caps
                }
            # Rule-based fallback
            numbers = re.findall(r"\b\d+(?:\.\d+)?\b", code)
            num_str = ", ".join(sorted(set(numbers), key=float)) if numbers else "None"
            fallback = (
                f"### Candidate Business Logic Observations (Rule-Based)\n"
                f"- **Observed Numeric Thresholds / Constants:** `{num_str}`\n"
                f"- **Decision Points:** Code contains {struct['metrics']['decisions']} conditional checks that may enforce validation criteria or operational constraints.\n"
                f"- **Inputs Observed:** {struct['metrics']['inputs']} parameter(s) passed into the function.\n\n"
                f"*Note: These are candidate observations extracted directly from code syntax. They do not necessarily reflect official organizational policies.*"
            )
            return {
                "mode": mode,
                "language": language,
                "text": fallback,
                "source": "Rule-based structural observation",
                "capabilities": caps
            }

        # Mode 6: Execution Flow
        elif mode == "Execution Flow":
            flowchart_mermaid = generate_mermaid_flowchart(code, language)
            wt = build_walkthrough(code) if language == "Python" else None
            return {
                "mode": mode,
                "language": language,
                "mermaid": flowchart_mermaid,
                "walkthrough": wt,
                "source": "Rule-based (Mermaid & AST)",
                "capabilities": caps
            }

        # Mode 7: Documentation Generator
        elif mode == "Documentation Generator":
            prompt = (
                f"Generate clean, professional, standardized documentation for this {language} code. "
                "Use standard docstring format for Python, Javadoc for Java, JSDoc for JavaScript, or Doxygen for C++. "
                "Document all parameters, exceptions, side effects, and return values."
            )
            resp = llm_service.call_gemini(prompt, code, struct["facts"], model_name=gemini_model)
            if resp["success"]:
                src = resp["source"]
                if language != "Python":
                    src += " [LLM-based, not separately evaluated]"
                return {
                    "mode": mode,
                    "language": language,
                    "text": resp["text"],
                    "source": src,
                    "capabilities": caps
                }
            # Rule-based fallback documentation stub
            m = struct["metrics"]
            doc_stub = (
                f"/**\n"
                f" * Auto-generated structural documentation template ({language})\n"
                f" * Active Lines: {m['loc']} | Decisions: {m['decisions']}\n"
                f" * Parameters: {m['inputs']}\n"
                f" */"
            )
            if language == "Python":
                doc_stub = f'"""Auto-generated structural documentation ({language}).\n\nParameters: {m["inputs"]}\nBranches: {m["decisions"]}\n"""'
            return {
                "mode": mode,
                "language": language,
                "text": f"```\n{doc_stub}\n```\n\n*(API key not configured. Configure GEMINI_API_KEY in .env for full docstring generation.)*",
                "source": "Rule-based template",
                "capabilities": caps
            }

        return {
            "mode": mode,
            "language": language,
            "text": "Unrecognized explanation mode requested.",
            "source": "Error",
            "capabilities": caps
        }
