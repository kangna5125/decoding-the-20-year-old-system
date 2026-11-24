import pytest
from code_improvement import (
    detect_code_risks,
    generate_modernization_suggestions,
    compute_code_diff,
)


def test_detect_code_risks_mutable_defaults():
    code = """def append_item(val, target_list=[]):
    target_list.append(val)
    return target_list
"""
    risks = detect_code_risks(code, language="Python")
    assert len(risks) >= 1
    assert any(r["category"] == "Mutable Default Argument Risk" for r in risks)
    risk = next(r for r in risks if r["category"] == "Mutable Default Argument Risk")
    assert risk["severity"] == "Medium"
    assert risk["line"] == 1


def test_detect_code_risks_division_by_zero():
    code = """def compute_ratio(total, count):
    ratio = total / count
    return ratio
"""
    risks = detect_code_risks(code, language="Python")
    assert len(risks) >= 1
    assert any("Division by Zero" in r["category"] for r in risks)


def test_detect_code_risks_bare_except_and_magic_numbers():
    code = """def fetch_records():
    try:
        timeout = 9999
        connect(timeout)
    except:
        pass
"""
    risks = detect_code_risks(code, language="Python")
    assert any(r["category"] == "Bare Exception Handling" for r in risks)
    assert any(r["category"] == "Hardcoded Magic Number" for r in risks)


def test_generate_modernization_suggestions():
    code = """def format_user(name, age):
    msg = "User %s is %d years old" % (name, age)
    if age > 18 == True:
        return msg
    return msg
"""
    suggestions = generate_modernization_suggestions(code, language="Python")
    assert len(suggestions) >= 1
    titles = [s["title"] for s in suggestions]
    assert any("f-string" in t.lower() for t in titles)
    assert any("redundant boolean" in t.lower() for t in titles)


def test_compute_code_diff():
    old_code = "def calc(a, b):\n    return a + b\n"
    new_code = "def calc(a: int, b: int) -> int:\n    return a + b\n"

    res = compute_code_diff(old_code, new_code)
    assert res["added_lines"] == 1
    assert res["removed_lines"] == 1
    assert "Original Code" in res["unified_diff"]
    assert "Revised Code" in res["unified_diff"]
    assert "Behavioral equivalence" in res["behavioral_note"]
