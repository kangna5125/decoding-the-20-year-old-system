"""Rule-based, step-by-step code walkthrough generated via Python's ast module."""
import ast
import re
from typing import Any, Dict, List, Optional, Tuple


def _unp(node: ast.AST) -> str:
    """Format an AST node into clean Python code string."""
    try:
        return ast.unparse(node)
    except Exception:
        return ""


def get_numbers_used(tree: ast.AST) -> List[Any]:
    """Collect all numeric constants used in the AST."""
    nums = set()
    for n in ast.walk(tree):
        if isinstance(n, ast.Constant) and isinstance(n.value, (int, float)) and not isinstance(n.value, bool):
            nums.add(n.value)
    return sorted(nums, key=lambda x: (x, type(x).__name__))


def describe_parameters(args_node: ast.arguments) -> str:
    """Describe function parameters with defaults, e.g. 'discount_rate (default 0.1)'."""
    params = []
    n_args = len(args_node.args)
    n_defaults = len(args_node.defaults)
    offset = n_args - n_defaults

    for i, a in enumerate(args_node.args):
        if i >= offset:
            default_val = _unp(args_node.defaults[i - offset])
            params.append(f"`{a.arg}` (default `{default_val}`)")
        else:
            params.append(f"`{a.arg}`")

    for a, d in zip(args_node.kwonlyargs, args_node.kw_defaults):
        if d is not None:
            params.append(f"`{a.arg}` (default `{_unp(d)}`)")
        else:
            params.append(f"`{a.arg}`")

    if args_node.vararg:
        params.append(f"`*{args_node.vararg.arg}`")
    if args_node.kwarg:
        params.append(f"`**{args_node.kwarg.arg}`")

    if not params:
        return "Takes no arguments"
    if len(params) == 1:
        return f"Takes {params[0]}"
    if len(params) == 2:
        return f"Takes {params[0]} and {params[1]}"
    return f"Takes {', '.join(params[:-1])}, and {params[-1]}"


def _describe_expr(val: ast.AST) -> str:
    """Describe an expression statement, translating common method calls."""
    if isinstance(val, ast.Call):
        if isinstance(val.func, ast.Attribute):
            target = f"`{_unp(val.func.value)}`"
            method = val.func.attr
            args = [_unp(a) for a in val.args]
            if method == "append" and len(args) == 1:
                return f"Adds `{args[0]}` to {target}"
            elif method == "extend" and len(args) == 1:
                return f"Appends all items from `{args[0]}` to {target}"
            elif method == "remove" and len(args) == 1:
                return f"Removes `{args[0]}` from {target}"
            elif method == "pop":
                return f"Removes item from {target}"
            elif method == "insert" and len(args) == 2:
                return f"Inserts `{args[1]}` at index `{args[0]}` in {target}"
            elif method == "add" and len(args) == 1:
                return f"Adds `{args[0]}` to set {target}"
            else:
                arg_str = ", ".join(f"`{a}`" for a in args)
                return f"Calls `{_unp(val.func.value)}.{method}({arg_str})`"
        else:
            fname = _unp(val.func)
            arg_str = ", ".join(f"`{_unp(a)}`" for a in val.args)
            return f"Calls `{fname}({arg_str})`"
    return f"Runs: `{_unp(val)}`"


def _describe_augassign(stmt: ast.AugAssign) -> str:
    """Translate augmented assignment (+=, -=, *=, etc.)."""
    t = f"`{_unp(stmt.target)}`"
    v = f"`{_unp(stmt.value)}`"
    op = stmt.op
    if isinstance(op, ast.Add):
        return f"Increases {t} by {v}"
    elif isinstance(op, ast.Sub):
        return f"Reduces {t} by {v}"
    elif isinstance(op, ast.Mult):
        return f"Multiplies {t} by {v}"
    elif isinstance(op, ast.Div):
        return f"Divides {t} by {v}"
    elif isinstance(op, ast.FloorDiv):
        return f"Floor-divides {t} by {v}"
    elif isinstance(op, ast.Mod):
        return f"Sets {t} to {t} modulo {v}"
    elif isinstance(op, ast.Pow):
        return f"Raises {t} to power {v}"
    return f"Updates {t} by {v}"


def _is_docstring_expr(stmt: ast.AST) -> bool:
    return (
        isinstance(stmt, ast.Expr)
        and isinstance(stmt.value, ast.Constant)
        and isinstance(stmt.value.value, str)
    )


def _is_simple_assign(stmt: ast.AST) -> bool:
    return (
        isinstance(stmt, ast.Assign)
        and len(stmt.targets) == 1
        and isinstance(stmt.targets[0], (ast.Name, ast.Attribute, ast.Subscript))
    )


def _build_raw_steps(stmts: List[ast.stmt]) -> List[Tuple[str, List[Any]]]:
    """Recursively build a list of (step_description, nested_steps)."""
    raw_steps: List[Tuple[str, List[Any]]] = []
    i = 0
    n = len(stmts)

    while i < n:
        stmt = stmts[i]

        # Skip docstring literal
        if i == 0 and _is_docstring_expr(stmt):
            i += 1
            continue

        # Merge consecutive simple assignments
        if _is_simple_assign(stmt):
            group = [stmt]
            j = i + 1
            while j < n and _is_simple_assign(stmts[j]):
                group.append(stmts[j])
                j += 1

            if len(group) == 1:
                t = f"`{_unp(stmt.targets[0])}`"
                v = f"`{_unp(stmt.value)}`"
                raw_steps.append((f"Sets {t} to {v}", []))
            else:
                parts = [f"`{_unp(s.targets[0])}` to `{_unp(s.value)}`" for s in group]
                if len(parts) == 2:
                    desc = f"Sets {parts[0]}, and {parts[1]}"
                else:
                    desc = f"Sets {', '.join(parts[:-1])}, and {parts[-1]}"
                raw_steps.append((desc, []))
            i = j
            continue

        # Augmented assignment (+=, -=, etc.)
        if isinstance(stmt, ast.AugAssign):
            raw_steps.append((_describe_augassign(stmt), []))
            i += 1
            continue

        # for loop
        if isinstance(stmt, (ast.For, ast.AsyncFor)):
            t = f"`{_unp(stmt.target)}`"
            it = f"`{_unp(stmt.iter)}`"
            body_steps = _build_raw_steps(stmt.body)
            raw_steps.append((f"For each {t} in {it}:", body_steps))
            if stmt.orelse:
                else_steps = _build_raw_steps(stmt.orelse)
                raw_steps.append(("If the loop completes without breaking:", else_steps))
            i += 1
            continue

        # while loop
        if isinstance(stmt, ast.While):
            c = f"`{_unp(stmt.test)}`"
            body_steps = _build_raw_steps(stmt.body)
            raw_steps.append((f"While {c}:", body_steps))
            if stmt.orelse:
                else_steps = _build_raw_steps(stmt.orelse)
                raw_steps.append(("If the loop completes without breaking:", else_steps))
            i += 1
            continue

        # if / elif / else
        if isinstance(stmt, ast.If):
            curr = stmt
            first = True
            while curr:
                cond = f"`{_unp(curr.test)}`"
                label = f"If {cond}:" if first else f"Otherwise, if {cond}:"
                body_steps = _build_raw_steps(curr.body)
                raw_steps.append((label, body_steps))
                first = False

                if len(curr.orelse) == 1 and isinstance(curr.orelse[0], ast.If):
                    curr = curr.orelse[0]
                else:
                    if curr.orelse:
                        else_steps = _build_raw_steps(curr.orelse)
                        raw_steps.append(("Otherwise:", else_steps))
                    curr = None
            i += 1
            continue

        # return
        if isinstance(stmt, ast.Return):
            if stmt.value:
                raw_steps.append((f"Returns `{_unp(stmt.value)}`", []))
            else:
                raw_steps.append(("Returns nothing", []))
            i += 1
            continue

        # continue
        if isinstance(stmt, ast.Continue):
            raw_steps.append(("Skips to the next item", []))
            i += 1
            continue

        # break
        if isinstance(stmt, ast.Break):
            raw_steps.append(("Stops the loop", []))
            i += 1
            continue

        # raise
        if isinstance(stmt, ast.Raise):
            if stmt.exc:
                raw_steps.append((f"Raises an error: `{_unp(stmt.exc)}`", []))
            else:
                raw_steps.append(("Re-raises the current error", []))
            i += 1
            continue

        # assert
        if isinstance(stmt, ast.Assert):
            t = f"`{_unp(stmt.test)}`"
            if stmt.msg:
                raw_steps.append((f"Asserts that {t}, otherwise `{_unp(stmt.msg)}`", []))
            else:
                raw_steps.append((f"Asserts that {t}", []))
            i += 1
            continue

        # import
        if isinstance(stmt, ast.Import):
            names = ", ".join(f"`{alias.name}`" for alias in stmt.names)
            raw_steps.append((f"Imports {names}", []))
            i += 1
            continue

        if isinstance(stmt, ast.ImportFrom):
            mod = stmt.module or ""
            names = ", ".join(f"`{alias.name}`" for alias in stmt.names)
            raw_steps.append((f"From `{mod}` imports {names}", []))
            i += 1
            continue

        # try / except
        if isinstance(stmt, ast.Try):
            raw_steps.append(("Tries:", _build_raw_steps(stmt.body)))
            for h in stmt.handlers:
                if h.type:
                    t_str = f"`{_unp(h.type)}`"
                    if h.name:
                        handler_label = f"If a {t_str} error occurs (as `{h.name}`):"
                    else:
                        handler_label = f"If a {t_str} error occurs:"
                else:
                    handler_label = "If any error occurs:"
                raw_steps.append((handler_label, _build_raw_steps(h.body)))
            if stmt.orelse:
                raw_steps.append(("If no errors occurred:", _build_raw_steps(stmt.orelse)))
            if stmt.finalbody:
                raw_steps.append(("Always (finally):", _build_raw_steps(stmt.finalbody)))
            i += 1
            continue

        # with
        if isinstance(stmt, (ast.With, ast.AsyncWith)):
            items = []
            for item in stmt.items:
                ctx = f"`{_unp(item.context_expr)}`"
                if item.optional_vars:
                    items.append(f"{ctx} as `{_unp(item.optional_vars)}`")
                else:
                    items.append(ctx)
            raw_steps.append((f"With {', '.join(items)}:", _build_raw_steps(stmt.body)))
            i += 1
            continue

        # Expression statements
        if isinstance(stmt, ast.Expr):
            raw_steps.append((_describe_expr(stmt.value), []))
            i += 1
            continue

        # Default fallback
        raw_steps.append((f"Runs: `{_unp(stmt)}`", []))
        i += 1

    return raw_steps


def _flatten_steps(
    steps: List[Tuple[str, List[Any]]],
    depth: int = 0,
    parent_index: int = 1
) -> List[Dict[str, Any]]:
    """Flatten hierarchical steps into numbered strings with indentation and depth."""
    flattened = []
    letters = "abcdefghijklmnopqrstuvwxyz"
    romans = ["i", "ii", "iii", "iv", "v", "vi", "vii", "viii", "ix", "x"]

    for idx, (text, children) in enumerate(steps):
        if depth == 0:
            prefix = f"{parent_index + idx}."
        elif depth == 1:
            prefix = f"{letters[idx % len(letters)]}."
        else:
            prefix = f"{romans[idx % len(romans)]}."

        flattened.append({
            "depth": depth,
            "prefix": prefix,
            "text": text,
            "indent_spaces": depth * 4
        })

        if children:
            child_flat = _flatten_steps(children, depth=depth + 1, parent_index=1)
            flattened.extend(child_flat)

    return flattened


def build_walkthrough(code: str) -> Dict[str, Any]:
    """Parse code and produce walkthrough steps and summary metrics.

    Returns dict with keys:
    - success: bool
    - error: Optional[str]
    - metrics: Dict with inputs, decisions, loops, calls, loc
    - numbers: List of numeric constants
    - numbers_str: formatted string of numbers
    - steps: List of step items with prefix, text, depth
    """
    if not code or not code.strip():
        return {
            "success": False,
            "error": "Paste some code to generate a walkthrough."
        }

    try:
        tree = ast.parse(code)
    except (SyntaxError, ValueError, MemoryError, RecursionError):
        return {
            "success": False,
            "error": "Could not parse this code - it may be Python 2 or incomplete"
        }

    func = next((n for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))), None)
    if func is None:
        return {
            "success": False,
            "error": "Could not parse this code - it may be Python 2 or incomplete"
        }

    # At a glance metrics
    all_nodes = list(ast.walk(func))
    inputs_count = (
        len(func.args.posonlyargs)
        + len(func.args.args)
        + len(func.args.kwonlyargs)
        + (1 if func.args.vararg else 0)
        + (1 if func.args.kwarg else 0)
    )
    decisions_count = sum(1 for n in all_nodes if isinstance(n, ast.If))
    loops_count = sum(1 for n in all_nodes if isinstance(n, (ast.For, ast.AsyncFor, ast.While)))
    calls_count = sum(1 for n in all_nodes if isinstance(n, ast.Call))
    loc_count = len([line for line in code.splitlines() if line.strip() and not line.strip().startswith("#")])

    numbers = get_numbers_used(func)
    numbers_str = ", ".join(str(n) for n in numbers) if numbers else "None"

    # Step 1: Takes <params>
    param_desc = describe_parameters(func.args)
    step1 = {
        "depth": 0,
        "prefix": "1.",
        "text": param_desc,
        "indent_spaces": 0
    }

    body_raw = _build_raw_steps(func.body)
    subsequent_steps = _flatten_steps(body_raw, depth=0, parent_index=2)

    all_steps = [step1] + subsequent_steps

    return {
        "success": True,
        "func_name": func.name,
        "metrics": {
            "inputs": inputs_count,
            "decisions": decisions_count,
            "loops": loops_count,
            "calls": calls_count,
            "loc": loc_count
        },
        "numbers": numbers,
        "numbers_str": numbers_str,
        "steps": all_steps,
        "total_steps": len(all_steps)
    }
