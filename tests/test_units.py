import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest

from common import first_sentence, strip_docstring, valid_description
from corrections import CorrectionStore

CODE = '''def add_tax(price, rate):
    """Add tax to a price.

    More detail here.
    """
    total = price * (1 + rate)
    return round(total, 2)
'''


def test_strip_docstring_removes_only_docstring():
    out = strip_docstring(CODE)
    assert "Add tax" not in out and "More detail" not in out
    assert out.startswith("def add_tax(price, rate):")
    assert "total = price * (1 + rate)" in out
    compile(out, "x", "exec")  # still valid Python


def test_strip_docstring_edge_cases():
    assert strip_docstring("def f(x):\n    return x + 1\n").count("return") == 1
    assert strip_docstring("print 'old python 2 code'") is None
    assert strip_docstring('def f(): """one liner"""') is None
    method = "    def m(self):\n        '''Doc.'''\n        return 1\n"
    assert "Doc" not in strip_docstring(method)


def test_first_sentence_and_validation():
    assert first_sentence("Add tax to a price. More text.\n\nNext paragraph.") == "Add tax to a price."
    assert first_sentence("Return the total e.g. 5 items in the cart") .startswith("Return the total")
    assert valid_description("Add tax to a price.")
    assert not valid_description("Too short")
    assert not valid_description(":param x: the value")
    assert not valid_description("See http://example.com for the details here")
    assert not valid_description("Ésto ño está én inglés porque tiene muchos acentos aquí")


def test_corrections_exact_similar_and_update(tmp_path):
    store = CorrectionStore(str(tmp_path / "c.db"))
    assert store.count() == 0 and store.find(CODE) is None
    store.save(CODE, "wrong text", "Adds tax to a price.", "Kangna")
    assert store.count() == 1
    # same code with different spacing still matches exactly
    hit = store.find(CODE.replace("    ", "\t"))
    assert hit["corrected"] == "Adds tax to a price." and hit["similarity"] == 1.0
    # slightly changed code matches by similarity
    near = store.find(CODE.replace("round(total, 2)", "round(total, 3)"))
    assert near and 0.9 <= near["similarity"] < 1.0
    # very different code does not match
    assert store.find("def other(a):\n    return a * a * a * a\n") is None
    # saving again updates, not duplicates
    store.save(CODE, "wrong text", "Adds tax.", "Kangna")
    assert store.count() == 1 and store.find(CODE)["corrected"] == "Adds tax."
    with pytest.raises(ValueError):
        store.save(CODE, "x", "   ")


def test_corrections_advanced_operations(tmp_path):
    store = CorrectionStore(str(tmp_path / "adv.db"))
    code_a = "def calc_discount(price):\n    return price * 0.9\n"
    code_b = "def compute_tax(total):\n    return total * 0.05\n"

    # Save explanation and business rule
    store.save(code_a, "Model text", "Calculates discounted price.", reviewer="Analyst",
               status="Approved", source="Human Reviewer", rule_type="Explanation Correction")
    store.save(code_b, "Tax calculation", "Computes standard tax.", reviewer="TaxOfficer",
               status="Pending Review", source="Business Rule Detective", rule_type="Business Rule")

    assert store.count() == 2

    # Approved is found, Pending is not returned by find()
    assert store.find(code_a) is not None
    assert store.find(code_b) is None

    # Search operations
    results_all = store.search()
    assert len(results_all) == 2

    results_tax = store.search(query="tax")
    assert len(results_tax) == 1
    assert results_tax[0]["rule_type"] == "Business Rule"

    results_approved = store.search(status_filter="Approved")
    assert len(results_approved) == 1

    results_rules = store.search(rule_type_filter="Business Rule")
    assert len(results_rules) == 1

    # Status update: approve code_b
    rows = store.all()
    code_b_hash = next(r["code_hash"] for r in rows if "compute_tax" in r["code"])
    store.update_status(code_b_hash, "Approved", reviewer="LeadReviewer")
    assert store.find(code_b) is not None

    # Edit correction
    store.edit_correction(code_b_hash, "Computes 5% VAT rate.", new_status="Approved", reviewer="LeadReviewer")
    hit = store.find(code_b)
    assert hit["corrected"] == "Computes 5% VAT rate."

    # Delete
    store.delete(code_b_hash)
    assert store.count() == 1
    assert store.find(code_b) is None
