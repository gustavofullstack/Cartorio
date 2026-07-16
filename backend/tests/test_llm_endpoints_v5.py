"""Testes unitários para endpoints de listagem e teste de LLM (Wave 5 S5.T1).

Modified by Gustavo Almeida.
"""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

# API Key de teste padrão definida nas configurações do app
TEST_HEADERS = {"X-API-Key": "a" * 64}


def test_list_llm_models_without_auth_fails() -> None:
    """GET /api/v1/llm/models sem auth header deve falhar com 401."""
    resp = client.get("/api/v1/llm/models")
    assert resp.status_code == 401


def test_list_llm_models_returns_27_items() -> None:
    """GET /api/v1/llm/models com auth header deve retornar a lista com 27 modelos."""
    resp = client.get("/api/v1/llm/models", headers=TEST_HEADERS)
    assert resp.status_code == 200
    body = resp.json()
    assert isinstance(body, list)
    assert len(body) == 27
    
    # Verifica estrutura de um dos itens
    item = body[0]
    assert "name" in item
    assert "provider" in item
    assert "dpa_status" in item
    assert item["dpa_status"] in ("SIGNED", "PENDING", "NOT_APPLICABLE")


def test_test_llm_provider_without_consent_fails() -> None:
    """POST /api/v1/llm/test/local sem consentimento LGPD deve falhar com 422."""
    payload = {
        "message": "ping",
        "consent_granted": False,
    }
    resp = client.post("/api/v1/llm/test/local", json=payload, headers=TEST_HEADERS)
    assert resp.status_code == 422
    assert resp.json()["detail"]["erro"] == "LGPD_BLOCKED"


def test_test_llm_provider_local_success() -> None:
    """POST /api/v1/llm/test/local com consentimento LGPD deve retornar sucesso e resposta mockada local."""
    payload = {
        "message": "Olá, Llama!",
        "consent_granted": True,
    }
    resp = client.post("/api/v1/llm/test/local", json=payload, headers=TEST_HEADERS)
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert body["provider"] == "local"
    assert body["model"] == "llama-3.1-8b-local"
    assert "LOCAL_LLAMA_3.1_8B" in body["response"]
    assert body["latency_ms"] >= 0
    assert body["dpa_status"] == "SIGNED"
    assert body["erro"] is None


def test_test_llm_provider_unconfigured_error() -> None:
    """POST /api/v1/llm/test/google_ai_studio sem chaves configuradas em ambiente de testes deve capturar e retornar status='erro'."""
    payload = {
        "message": "ping",
        "consent_granted": True,
    }
    resp = client.post("/api/v1/llm/test/google_ai_studio", json=payload, headers=TEST_HEADERS)
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "erro"
    assert body["provider"] == "google_ai_studio"
    assert body["erro"] is not None
    assert "message" in body["erro"]
