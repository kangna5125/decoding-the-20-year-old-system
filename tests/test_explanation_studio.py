"""Unit tests for Explanation Studio modes, Mermaid visualizer, and LLM service handling."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "."))

import pytest
from explanation_engine import ExplanationStudio, generate_line_by_line_explanation
from explainer import CodeExplainer
from llm_service import is_api_key_configured
from samples import SAMPLES_BY_LANGUAGE
from tiny import build_tiny
from visualizer import generate_mermaid_flowchart


@pytest.fixture
def dummy_studio(tmp_path):
    model_dir = tmp_path / "model"
    build_tiny(str(model_dir), ["def calc_si(p, r, t): return (p * r * t) / 100", "Calculates simple interest."])
    db_file = tmp_path / "test_store.db"
    ex = CodeExplainer(str(model_dir), db_path=str(db_file))
    return ExplanationStudio(ex)


def test_visualizer_mermaid_syntax():
    code = SAMPLES_BY_LANGUAGE["Python"]["Simple interest"]
    mermaid = generate_mermaid_flowchart(code, "Python")
    assert "graph TD" in mermaid
    assert "start([" in mermaid
    assert "calc_si" in mermaid
    assert "cond_" in mermaid or "op_" in mermaid

    java_code = SAMPLES_BY_LANGUAGE["Java"]["Calculate account fee"]
    java_mermaid = generate_mermaid_flowchart(java_code, "Java")
    assert "graph TD" in java_mermaid
    assert "Entry: Java" in java_mermaid


def test_line_by_line_explanation_rule_based():
    code = SAMPLES_BY_LANGUAGE["Python"]["Simple interest"]
    lines = generate_line_by_line_explanation(code, "Python")
    assert len(lines) >= 4
    assert all("line_number" in l for l in lines)
    assert any("Defines function" in l["explanation"] for l in lines)
    assert any("Returns" in l["explanation"] for l in lines)
    assert all(l["source"].startswith("Rule-based") for l in lines)


def test_explanation_studio_all_seven_modes_without_api_key(dummy_studio, monkeypatch):
    # Ensure no API key is set
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    assert not is_api_key_configured()

    code = SAMPLES_BY_LANGUAGE["Python"]["Simple interest"]
    modes = [
        "Quick Explanation",
        "Detailed Explanation",
        "Line-by-Line Explanation",
        "Technical Explanation",
        "Business Explanation",
        "Execution Flow",
        "Documentation Generator"
    ]

    for mode in modes:
        res = dummy_studio.explain(code, "Python", mode)
        assert res["mode"] == mode
        assert "source" in res
        if mode == "Execution Flow":
            assert "mermaid" in res
        elif mode == "Line-by-Line Explanation":
            assert "lines" in res
        else:
            assert "text" in res and len(res["text"]) > 0


def test_explanation_studio_java_without_api_key(dummy_studio, monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    java_code = SAMPLES_BY_LANGUAGE["Java"]["Calculate account fee"]
    res = dummy_studio.explain(java_code, "Java", "Quick Explanation")
    assert "Rule-based" in res["source"]
    assert "API key not configured" in res["text"] or "Analyzes Java code" in res["text"]


def test_explanation_studio_with_mock_gemini(dummy_studio, monkeypatch):
    # Mock LLM client only inside automated tests as allowed by Rule 4
    monkeypatch.setenv("GEMINI_API_KEY", "mock_gemini_api_key_for_test")

    import llm_service
    monkeypatch.setattr(
        llm_service,
        "call_gemini",
        lambda prompt, code, *args, **kwargs: {
            "success": True,
            "text": "Mocked detailed explanation citing line 12: verified logic.",
            "source": "Gemini (gemini-1.5-flash)"
        }
    )

    code = SAMPLES_BY_LANGUAGE["Java"]["Calculate account fee"]
    res = dummy_studio.explain(code, "Java", "Detailed Explanation")
    assert "Gemini" in res["source"]
    assert "Mocked detailed explanation" in res["text"]
