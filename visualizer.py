"""Rule-based execution flowchart generator producing Mermaid diagrams from code structure."""
import ast
import re
from typing import List, Tuple


def _sanitize(text: str) -> str:
    """Sanitize strings for Mermaid labels, quoting special characters."""
    clean = text.replace('"', "'").replace("\n", " ").strip()
    # truncate long labels to keep diagram readable
    if len(clean) > 45:
        clean = clean[:42] + "..."
    return clean


def generate_mermaid_flowchart(code: str, language: str = "Python") -> str:
    """Generate a Mermaid graph TD diagram representing code execution flow."""
    if language == "Python":
        try:
            tree = ast.parse(code)
            func = next((n for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))), None)
            if func:
                return _generate_python_mermaid(func)
        except Exception:
            pass

    # Fallback to language-agnostic line-based block flow
    return _generate_generic_mermaid(code, language)


def _generate_python_mermaid(func: ast.FunctionDef) -> str:
    """Build a detailed Mermaid flowchart from Python AST."""
    lines = ["graph TD"]
    params = ", ".join(a.arg for a in func.args.args)
    start_label = f"Start: {func.name}({params})" if params else f"Start: {func.name}()"
    lines.append(f'    start(["{_sanitize(start_label)}"])')

    current_node = "start"
    node_idx = 1
    has_explicit_return = False

    for stmt in func.body:
        # Skip leading docstring
        if (
            node_idx == 1
            and isinstance(stmt, ast.Expr)
            and isinstance(stmt.value, ast.Constant)
            and isinstance(stmt.value.value, str)
        ):
            continue

        if isinstance(stmt, (ast.Assign, ast.AugAssign)):
            nid = f"op_{node_idx}"
            node_idx += 1
            code_str = ast.unparse(stmt)
            lines.append(f'    {nid}["{_sanitize(code_str)}"]')
            lines.append(f"    {current_node} --> {nid}")
            current_node = nid

        elif isinstance(stmt, ast.If):
            cond_nid = f"cond_{node_idx}"
            node_idx += 1
            cond_str = ast.unparse(stmt.test)
            lines.append(f'    {cond_nid}{{"{_sanitize(cond_str)}?"}}')
            lines.append(f"    {current_node} --> {cond_nid}")

            # Then branch
            then_nid = f"then_{node_idx}"
            node_idx += 1
            then_desc = ast.unparse(stmt.body[0]) if stmt.body else "pass"
            lines.append(f'    {then_nid}["{_sanitize(then_desc)}"]')
            lines.append(f"    {cond_nid} -- Yes --> {then_nid}")

            join_nid = f"join_{node_idx}"
            node_idx += 1
            lines.append(f'    {join_nid}[("Merge")]')
            lines.append(f"    {then_nid} --> {join_nid}")

            if stmt.orelse:
                else_nid = f"else_{node_idx}"
                node_idx += 1
                else_desc = ast.unparse(stmt.orelse[0])
                lines.append(f'    {else_nid}["{_sanitize(else_desc)}"]')
                lines.append(f"    {cond_nid} -- No --> {else_nid}")
                lines.append(f"    {else_nid} --> {join_nid}")
            else:
                lines.append(f"    {cond_nid} -- No --> {join_nid}")

            current_node = join_nid

        elif isinstance(stmt, (ast.For, ast.AsyncFor)):
            loop_nid = f"loop_{node_idx}"
            node_idx += 1
            loop_str = f"For each {ast.unparse(stmt.target)} in {ast.unparse(stmt.iter)}"
            lines.append(f'    {loop_nid}{{"{_sanitize(loop_str)}"}}')
            lines.append(f"    {current_node} --> {loop_nid}")

            body_nid = f"lbody_{node_idx}"
            node_idx += 1
            body_desc = ast.unparse(stmt.body[0]) if stmt.body else "continue"
            lines.append(f'    {body_nid}["{_sanitize(body_desc)}"]')
            lines.append(f"    {loop_nid} -- Iterate --> {body_nid}")
            lines.append(f"    {body_nid} --> {loop_nid}")

            done_nid = f"ldone_{node_idx}"
            node_idx += 1
            lines.append(f'    {done_nid}["Loop Finished"]')
            lines.append(f"    {loop_nid} -- Done --> {done_nid}")
            current_node = done_nid

        elif isinstance(stmt, ast.While):
            loop_nid = f"loop_{node_idx}"
            node_idx += 1
            loop_str = f"While {ast.unparse(stmt.test)}"
            lines.append(f'    {loop_nid}{{"{_sanitize(loop_str)}"}}')
            lines.append(f"    {current_node} --> {loop_nid}")

            body_nid = f"lbody_{node_idx}"
            node_idx += 1
            body_desc = ast.unparse(stmt.body[0]) if stmt.body else "continue"
            lines.append(f'    {body_nid}["{_sanitize(body_desc)}"]')
            lines.append(f"    {loop_nid} -- True --> {body_nid}")
            lines.append(f"    {body_nid} --> {loop_nid}")

            done_nid = f"ldone_{node_idx}"
            node_idx += 1
            lines.append(f'    {done_nid}["Condition False"]')
            lines.append(f"    {loop_nid} -- False --> {done_nid}")
            current_node = done_nid

        elif isinstance(stmt, ast.Return):
            has_explicit_return = True
            ret_nid = f"ret_{node_idx}"
            node_idx += 1
            ret_str = f"Return {ast.unparse(stmt.value)}" if stmt.value else "Return"
            lines.append(f'    {ret_nid}(["{_sanitize(ret_str)}"])')
            lines.append(f"    {current_node} --> {ret_nid}")
            current_node = ret_nid

        elif isinstance(stmt, ast.Expr):
            call_nid = f"expr_{node_idx}"
            node_idx += 1
            lines.append(f'    {call_nid}["{_sanitize(ast.unparse(stmt.value))}"]')
            lines.append(f"    {current_node} --> {call_nid}")
            current_node = call_nid

    if not has_explicit_return:
        end_nid = f"end_{node_idx}"
        lines.append(f'    {end_nid}(["End / Exit"])')
        lines.append(f"    {current_node} --> {end_nid}")

    return "\n".join(lines)


def _generate_generic_mermaid(code: str, language: str) -> str:
    """Build a flowchart for Java, JavaScript, or C++ based on syntactic blocks."""
    lines = ["graph TD"]
    lines.append(f'    start(["Entry: {language} Codeblock"])')

    current_node = "start"
    node_idx = 1
    raw_lines = [l.strip() for l in code.splitlines() if l.strip() and not l.strip().startswith(("//", "/*", "*", "#"))]

    for line in raw_lines[:15]:
        if re.search(r"\b(if|else if)\b", line):
            nid = f"cond_{node_idx}"
            node_idx += 1
            cond = re.sub(r"^(if|else if)\s*\((.*)\).*$", r"\2", line)
            lines.append(f'    {nid}{{"{_sanitize(cond)}?"}}')
            lines.append(f"    {current_node} --> {nid}")
            current_node = nid
        elif re.search(r"\b(for|while)\b", line):
            nid = f"loop_{node_idx}"
            node_idx += 1
            lines.append(f'    {nid}{{"{_sanitize(line)}"}}')
            lines.append(f"    {current_node} --> {nid}")
            current_node = nid
        elif re.search(r"\breturn\b", line):
            nid = f"ret_{node_idx}"
            node_idx += 1
            lines.append(f'    {nid}(["{_sanitize(line)}"])')
            lines.append(f"    {current_node} --> {nid}")
            current_node = nid
        elif "=" in line or "(" in line:
            nid = f"stmt_{node_idx}"
            node_idx += 1
            lines.append(f'    {nid}["{_sanitize(line.rstrip(";"))}"]')
            lines.append(f"    {current_node} --> {nid}")
            current_node = nid

    lines.append(f'    exit_node(["Exit"])')
    lines.append(f"    {current_node} --> exit_node")
    return "\n".join(lines)
