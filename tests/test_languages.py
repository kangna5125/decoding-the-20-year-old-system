"""Unit tests for language detection, capability reporting, and structural parsing."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from languages import detect_language, get_language_capabilities, parse_code_structure
from samples import SAMPLES_BY_LANGUAGE


def test_language_detection_by_filename():
    assert detect_language("", "service.py") == "Python"
    assert detect_language("", "Account.java") == "Java"
    assert detect_language("", "cart.js") == "JavaScript"
    assert detect_language("", "cart.jsx") == "JavaScript"
    assert detect_language("", "engine.cpp") == "C++"
    assert detect_language("", "types.h") == "C++"


def test_language_detection_by_syntax():
    py_code = SAMPLES_BY_LANGUAGE["Python"]["Simple interest"]
    assert detect_language(py_code) == "Python"

    java_code = SAMPLES_BY_LANGUAGE["Java"]["Calculate account fee"]
    assert detect_language(java_code) == "Java"

    js_code = SAMPLES_BY_LANGUAGE["JavaScript"]["Cart discount validator"]
    assert detect_language(js_code) == "JavaScript"

    cpp_code = SAMPLES_BY_LANGUAGE["C++"]["Interest accrual calculator"]
    assert detect_language(cpp_code) == "C++"


def test_language_capabilities_honesty():
    py_caps = get_language_capabilities("Python")
    assert py_caps["is_evaluated"] is True
    assert "CodeT5" in py_caps["model_type"]

    for lang in ["Java", "JavaScript", "C++"]:
        caps = get_language_capabilities(lang)
        assert caps["is_evaluated"] is False
        assert "not separately evaluated" in caps["status"]
        assert "Gemini" in caps["model_type"]


def test_structural_parsing_all_languages():
    # Python
    py_res = parse_code_structure(SAMPLES_BY_LANGUAGE["Python"]["Simple interest"], "Python")
    assert py_res["success"] is True
    assert py_res["metrics"]["inputs"] == 3
    assert py_res["metrics"]["decisions"] == 1
    assert len(py_res["functions"]) == 1

    # Java
    java_res = parse_code_structure(SAMPLES_BY_LANGUAGE["Java"]["Calculate account fee"], "Java")
    assert java_res["success"] is True
    assert len(java_res["classes"]) >= 1
    assert len(java_res["functions"]) >= 1
    assert java_res["metrics"]["decisions"] >= 2

    # JavaScript
    js_res = parse_code_structure(SAMPLES_BY_LANGUAGE["JavaScript"]["Cart discount validator"], "JavaScript")
    assert js_res["success"] is True
    assert len(js_res["functions"]) >= 1
    assert js_res["metrics"]["loops"] >= 1
    assert js_res["metrics"]["decisions"] >= 1

    # C++
    cpp_res = parse_code_structure(SAMPLES_BY_LANGUAGE["C++"]["Interest accrual calculator"], "C++")
    assert cpp_res["success"] is True
    assert len(cpp_res["functions"]) >= 1
    assert cpp_res["metrics"]["loops"] >= 1
