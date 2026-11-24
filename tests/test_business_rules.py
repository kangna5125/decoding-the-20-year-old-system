import pytest
from business_rules import detect_candidate_business_rules
from corrections import CorrectionStore


def test_detect_candidate_business_rules_simple_interest():
    code = """def calc_si(p, r, t):
    si = (p * r * t) / 100.0
    return si
"""
    rules = detect_candidate_business_rules(code, language="Python", filename="si.py")
    assert len(rules) >= 1
    assert any("si" in r["title"].lower() or "calculation" in r["category"].lower() for r in rules)
    rule = rules[0]
    assert rule["line_start"] == 2
    assert "Line 2" in rule["line_reference"]
    assert "100" in rule["code_snippet"] or "si" in rule["code_snippet"]


def test_detect_candidate_business_rules_penalty():
    code = """def apply_penalty(bal, minbal, fee):
    if bal < minbal:
        bal -= fee
    return bal
"""
    rules = detect_candidate_business_rules(code, language="Python", filename="account.py")
    assert len(rules) >= 1
    # Should detect balance constraint or fee calculation
    assert any("bal" in r["title"].lower() or "balance" in r["title"].lower() for r in rules)


def test_detect_candidate_business_rules_multi_language():
    java_code = """public class Billing {
    public double computeDiscount(double price) {
        if (price > 1000.0) {
            return price * 0.15;
        }
        return 0.0;
    }
}
"""
    rules = detect_candidate_business_rules(java_code, language="Java", filename="Billing.java")
    assert len(rules) >= 1
    assert any("threshold" in r["category"].lower() or "financial" in r["category"].lower() for r in rules)


def test_save_verified_rule_to_corrections_db(tmp_path):
    # Verify that approved business rules can be saved to a temporary db without touching corrections.db
    test_db = tmp_path / "test_rules.db"
    store = CorrectionStore(str(test_db))

    store.save(
        code="if bal < minbal:\n    bal -= fee",
        original="Check if balance is below threshold.",
        corrected="Business Rule: Enforce minimum balance penalty fee deduction when account funds fall below threshold.",
        reviewer="Test Reviewer"
    )

    correction = store.find("if bal < minbal:\n    bal -= fee")
    assert correction is not None
    assert "Business Rule: Enforce minimum balance" in correction["corrected"]
    assert correction["reviewer"] == "Test Reviewer"

