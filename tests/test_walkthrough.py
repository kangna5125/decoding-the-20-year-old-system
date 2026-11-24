"""Tests for the rule-based AST step-by-step code walkthrough."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from samples import SAMPLES
from walkthrough import build_walkthrough

ORDER_PROCESSING_CODE = '''def process_order(items, discount_rate=0.1, tax_rate=0.05):
    total = 0
    for item in items:
        price = item["price"]
        qty = item["quantity"]
        total += price * qty
    if discount_rate > 0:
        total -= total * discount_rate
    total += total * tax_rate
    return round(total, 2)
'''

PYTHON_2_CODE = "print 'old python 2 code'"


def test_walkthrough_simple_interest():
    res = build_walkthrough(SAMPLES["Simple interest"])
    assert res["success"] is True
    assert res["metrics"]["inputs"] == 3
    assert res["metrics"]["decisions"] == 1
    assert res["metrics"]["loops"] == 0
    assert res["numbers"] == [0, 2, 100]
    assert "0, 2, 100" in res["numbers_str"]
    step_texts = [s["text"] for s in res["steps"]]
    assert any("Takes" in t and "`p`" in t and "`r`" in t and "`t`" in t for t in step_texts)
    assert any("Sets `si`" in t for t in step_texts)
    assert any("If `si < 0`" in t for t in step_texts)
    assert any("Returns `round(si, 2)`" in t for t in step_texts)


def test_walkthrough_account_check_digit():
    res = build_walkthrough(SAMPLES["Account check digit"])
    assert res["success"] is True
    assert res["metrics"]["inputs"] == 1
    assert res["metrics"]["loops"] == 1
    assert res["metrics"]["decisions"] >= 2
    assert 0 in res["numbers"] and 9 in res["numbers"] and 10 in res["numbers"]
    step_texts = [s["text"] for s in res["steps"]]
    assert any("Takes `acc`" in t for t in step_texts)
    assert any("Sets `total` to `0`" in t for t in step_texts)
    assert any("For each" in t for t in step_texts)
    assert any("Returns `(10 - total % 10) % 10`" in t for t in step_texts)


def test_walkthrough_minimum_balance_penalty():
    res = build_walkthrough(SAMPLES["Minimum balance penalty"])
    assert res["success"] is True
    assert res["metrics"]["inputs"] == 3
    assert res["metrics"]["decisions"] == 2
    assert 0 in res["numbers"] and 10 in res["numbers"]
    step_texts = [s["text"] for s in res["steps"]]
    assert any("Takes `bal`, `minbal`, and `rate`" in t for t in step_texts)
    assert any("If `bal >= minbal`" in t for t in step_texts)
    # Check that consecutive simple assigns were merged
    assert any("Sets `short`" in t and "`fee`" in t for t in step_texts)
    assert any("Returns `fee`" in t for t in step_texts)


def test_walkthrough_order_processing():
    res = build_walkthrough(ORDER_PROCESSING_CODE)
    assert res["success"] is True
    assert res["func_name"] == "process_order"
    assert res["metrics"]["inputs"] == 3
    assert res["metrics"]["loops"] == 1
    assert res["metrics"]["decisions"] == 1
    assert 0 in res["numbers"] and 0.1 in res["numbers"] and 0.05 in res["numbers"] and 2 in res["numbers"]
    step_texts = [s["text"] for s in res["steps"]]
    # Parameters with defaults
    assert any("Takes `items`" in t and "discount_rate" in t and "default `0.1`" in t for t in step_texts)
    # Merged assignments inside loop
    assert any("Sets `price`" in t and "`qty`" in t for t in step_texts)
    # Augmented assignments
    assert any("Increases `total` by `price * qty`" in t for t in step_texts)
    assert any("Reduces `total` by `total * discount_rate`" in t for t in step_texts)
    assert any("Increases `total` by `total * tax_rate`" in t for t in step_texts)
    assert any("Returns `round(total, 2)`" in t for t in step_texts)


def test_walkthrough_python_2_snippet():
    res = build_walkthrough(PYTHON_2_CODE)
    assert res["success"] is False
    assert "Could not parse this code - it may be Python 2 or incomplete" in res["error"]


def test_walkthrough_empty_and_no_function():
    res_empty = build_walkthrough("")
    assert res_empty["success"] is False
    res_no_func = build_walkthrough("x = 10\ny = 20\n")
    assert res_no_func["success"] is False
    assert "Could not parse this code - it may be Python 2 or incomplete" in res_no_func["error"]
