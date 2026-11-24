"""Drives the real Streamlit app headlessly (tiny random model, no downloads)."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.dirname(__file__))

from streamlit.testing.v1 import AppTest

from samples import SAMPLES
from tiny import build_tiny

APP = os.path.join(os.path.dirname(__file__), "..", "app.py")


def test_app_explain_correct_and_reuse(tmp_path, monkeypatch):
    model = tmp_path / "model"
    build_tiny(str(model), list(SAMPLES.values()) + ["Adds two numbers and returns the result."])
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("MODEL_DIR", str(model))

    at = AppTest.from_file(APP, default_timeout=120).run()
    assert not at.exception
    # empty input -> warning, no crash
    at.button[0].click().run()
    assert at.warning and "Paste some code" in at.warning[0].value

    # load an example, explain it
    at.selectbox(key="sample").select("Simple interest").run()
    at.button[0].click().run()
    assert not at.exception
    assert at.session_state.result["source"] == "model"
    assert at.session_state.result["level"] in ("High", "Medium", "Low")
    first_id = at.session_state.result_id

    # reviewer box shows the CURRENT explanation, then a correction is saved
    box = at.text_area(key=f"fixed_{first_id}")
    assert box.value == at.session_state.result["explanation"]
    box.input("Calculates simple interest and never returns a negative amount.")
    save = [b for b in at.button if b.label == "Save correction"][0]
    save.click().run()
    assert not at.exception
    assert at.session_state.result["source"] == "verified"
    assert at.session_state.result["explanation"].startswith("Calculates simple interest")
    assert at.sidebar.metric[0].value == "1"

    # another example gets a fresh model explanation and a fresh reviewer box
    at.selectbox(key="sample").select("Account check digit").run()
    at.button[0].click().run()
    assert at.session_state.result["source"] == "model"
    box2 = at.text_area(key=f"fixed_{at.session_state.result_id}")
    assert box2.value == at.session_state.result["explanation"]

    # going back to the corrected example shows the verified note again
    at.selectbox(key="sample").select("Simple interest").run()
    at.button[0].click().run()
    assert at.session_state.result["source"] == "verified"


def test_app_without_model_shows_error(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("MODEL_DIR", str(tmp_path / "missing"))
    at = AppTest.from_file(APP, default_timeout=60).run()
    assert at.error and "Model not found" in at.error[0].value


def test_app_all_modules_without_api_key(tmp_path, monkeypatch):
    model = tmp_path / "model"
    build_tiny(str(model), list(SAMPLES.values()) + ["Adds two numbers and returns the result."])
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("MODEL_DIR", str(model))
    monkeypatch.setenv("GEMINI_API_KEY", "")

    at = AppTest.from_file(APP, default_timeout=120).run()
    assert not at.exception

    modules = [
        "1. Dashboard",
        "2. Code Analyzer",
        "3. Explanation Studio",
        "4. AI Chatbot",
        "5. Repository Intelligence",
        "6. Business Rule Detective",
        "7. Code Improvement",
        "8. Knowledge Base & Model Report",
    ]

    for mod in modules:
        at.sidebar.radio(key="nav_module").set_value(mod).run()
        assert not at.exception, f"Module {mod} raised an exception when run without API key"

