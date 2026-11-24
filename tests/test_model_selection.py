import json
from unittest.mock import patch, MagicMock
import urllib.error
import pytest

import llm_service


def test_parse_model_score():
    # 1. Version extraction
    s_25 = llm_service.parse_model_score("gemini-2.5-pro")
    s_20 = llm_service.parse_model_score("gemini-2.0-flash")
    s_15 = llm_service.parse_model_score("gemini-1.5-pro")
    assert s_25[0] > s_20[0] > s_15[0]

    # 2. Tier comparison (pro > flash > lite/8b)
    s_pro = llm_service.parse_model_score("gemini-2.0-pro")
    s_flash = llm_service.parse_model_score("gemini-2.0-flash")
    s_8b = llm_service.parse_model_score("gemini-2.0-flash-8b")
    assert s_pro[1] > s_flash[1] > s_8b[1]

    # 3. Stability comparison (stable > preview/exp)
    s_stable = llm_service.parse_model_score("gemini-2.0-flash")
    s_exp = llm_service.parse_model_score("gemini-2.0-flash-exp")
    assert s_stable[2] > s_exp[2]


def test_filter_and_rank_models():
    mock_models = [
        {"name": "models/text-embedding-004", "supportedGenerationMethods": ["embedContent"]},
        {"name": "models/imagen-3.0-generate-002", "supportedGenerationMethods": ["generateContent"]},
        {"name": "models/gemini-1.5-flash", "supportedGenerationMethods": ["generateContent"]},
        {"name": "models/gemini-2.0-flash", "supportedGenerationMethods": ["generateContent"]},
        {"name": "models/gemini-2.5-pro", "supportedGenerationMethods": ["generateContent"]},
        {"name": "models/gemini-2.0-pro-exp-02-05", "supportedGenerationMethods": ["generateContent"]},
        {"name": "models/gemini-1.5-flash-8b", "supportedGenerationMethods": ["generateContent"]},
        {"name": "models/gemini-live-audio", "supportedGenerationMethods": ["generateContent"]},
    ]

    ranked = llm_service.filter_and_rank_models(mock_models)

    # Exclusions
    assert "text-embedding-004" not in ranked
    assert "imagen-3.0-generate-002" not in ranked
    assert "gemini-live-audio" not in ranked

    # Ranking: 2.5-pro should be top
    assert ranked[0] == "gemini-2.5-pro"
    # 2.0 models should come before 1.5 models
    idx_20 = [i for i, m in enumerate(ranked) if "2.0" in m]
    idx_15 = [i for i, m in enumerate(ranked) if "1.5" in m]
    assert max(idx_20) < min(idx_15)


def test_auto_select_best_model_fallback():
    mock_ranked_models = ["gemini-2.5-pro", "gemini-2.0-flash"]

    # Simulate top candidate failing connection test, second succeeding
    def mock_test_connection(model):
        if "2.5-pro" in model:
            return False, "403 Forbidden"
        return True, "Success"

    with patch.object(llm_service, "is_api_key_configured", return_value=True):
        with patch.object(llm_service, "fetch_available_gemini_models", return_value=mock_ranked_models):
            with patch.object(llm_service, "test_gemini_connection", side_effect=mock_test_connection):
                selection = llm_service.auto_select_best_model(force_refresh=True)
                assert selection["success"] is True
                assert selection["model"] == "gemini-2.0-flash"


def test_call_gemini_rate_limit_fallback():
    # Test that HTTP 429 on primary triggers fallback to next candidate
    llm_service._RANKED_MODELS_CACHE = ["gemini-2.5-pro", "gemini-2.0-flash"]
    llm_service.set_active_model("gemini-2.5-pro")

    def mock_urlopen(req, timeout=30):
        url = req.full_url if hasattr(req, "full_url") else str(req)
        if "gemini-2.5-pro" in url:
            raise urllib.error.HTTPError(url, 429, "Too Many Requests", {}, None)

        mock_resp = MagicMock()
        payload = {
            "candidates": [
                {"content": {"parts": [{"text": "Answer from fallback model"}]}}
            ]
        }
        mock_resp.read.return_value = json.dumps(payload).encode("utf-8")
        mock_resp.__enter__.return_value = mock_resp
        return mock_resp

    with patch.object(llm_service, "is_api_key_configured", return_value=True):
        with patch.object(llm_service, "get_api_key", return_value="dummy_valid_api_key"):
            with patch("urllib.request.urlopen", side_effect=mock_urlopen):
                res = llm_service.call_gemini("Explain this code", code="def foo(): pass", model_name="gemini-2.5-pro")
                assert res["success"] is True
                assert "Answer from fallback model" in res["text"]
                assert res["model"] == "gemini-2.0-flash"
                assert "Rate limit fallback" in res["source"]
