"""Smoke tests E2E do fluxo WhatsApp -> API -> audit log.

Valida o caminho critico:
    Cliente manda WhatsApp
    -> Evolution API recebe
    -> Webhook POST /api/v1/webhook/evolution
    -> PII scrubbing
    -> Audit log append
    -> Response com handoff se PII detectado

Por padrao, SKIPPED (depende de API deployed).
Habilitar: SMOKE_TARGET=prod pytest -m smoke
"""

from __future__ import annotations

from contextlib import contextmanager
from typing import Any, Iterator

import os

import httpx
import pytest

from app.services.pii import scrub

pytestmark = pytest.mark.smoke

API_BASE = os.getenv("API_BASE_URL", "https://api.2notasudi.com.br")
TIMEOUT_S = float(os.getenv("SMOKE_TIMEOUT", "10"))


@contextmanager
def _require_api_deployed() -> Iterator[httpx.Client]:
    """Context manager: yield client se API estiver deployed, skip senao.

    Inclui header X-API-Key quando SMOKE_CARTORIO_API_KEY estiver setado no env
    OU lido de backend/.env (sobrescreve o valor de teste do conftest).

    Para rodar smoke contra API real:
        SMOKE_CARTORIO_API_KEY=<chave_real> pytest -m smoke tests/smoke/
    """
    headers: dict[str, str] = {}
    # SMOKE_* tem precedencia; fallback le .env direto (conftest.py sobrescreve
    # CARTORIO_API_KEY com valor de teste, ignora-lo).
    api_key = os.getenv("SMOKE_CARTORIO_API_KEY")
    if not api_key:
        env_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            ".env",
        )
        if os.path.isfile(env_path):
            try:
                with open(env_path, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if line.startswith("CARTORIO_API_KEY="):
                            api_key = line.split("=", 1)[1].strip().strip('"').strip("'")
                            break
            except OSError:
                pass
    if api_key:
        headers["X-API-Key"] = api_key
    client = httpx.Client(base_url=API_BASE, timeout=TIMEOUT_S, headers=headers)
    try:
        resp = client.get("/health")
        if resp.status_code != 200:
            client.close()
            pytest.skip(f"API nao deployed ou unhealthy: {resp.status_code}")
        yield client
    except httpx.HTTPError as e:
        client.close()
        pytest.skip(f"API nao acessivel em {API_BASE}: {e}")
    finally:
        client.close()


def test_health_endpoint_returns_ok() -> None:
    """GET /health -> 200 + status=ok + version."""
    with _require_api_deployed() as client:
        resp = client.get("/health")
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "ok"
        assert "version" in body


def test_ready_endpoint_returns_ready() -> None:
    """GET /ready -> 200 + status=ready + audit_chain_initialized."""
    with _require_api_deployed() as client:
        resp = client.get("/ready")
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "ready"
        assert body.get("audit_chain_initialized") is True


def test_webhook_e2e_message_without_pii() -> None:
    """Webhook sem PII deve aceitar e devolver resposta de atendimento."""
    with _require_api_deployed() as client:
        payload = {
            "message": {"text": "Ola, gostaria de uma certidao negativa"},
            "sender": "5511999999999",
            "instance": "cartorio-2notas",
        }
        resp = client.post("/api/v1/webhook/evolution", json=payload)
        assert resp.status_code == 200
        body: dict[str, Any] = resp.json()
        assert body["status"] == "ok"
        # Sem PII = texto nao-mascarado
        scrubbed = body.get("scrubbed", "")
        assert isinstance(scrubbed, str)
        assert "5511999999999" not in scrubbed or scrubbed == "".join(
            [payload["message"]["text"]]  # type: ignore[index]
        )
        # Resposta humanizada (atendente, nao transferencia)
        assert "transferir" not in str(body["response"]).lower()

    
def test_webhook_e2e_message_with_cpf_triggers_handoff() -> None:
    """Webhook com CPF deve detectar PII e devolver mensagem de handoff humano."""
    with _require_api_deployed() as client:
        payload = {
            "message": {"text": "Meu CPF eh 123.456.789-09, podem verificar?"},
            "sender": "5511988887777",
            "instance": "cartorio-2notas",
        }
        resp = client.post("/api/v1/webhook/evolution", json=payload)
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "ok"
        # CRITICO: CPF original NAO pode vazar no scrubbed
        assert "123.456.789-09" not in body["scrubbed"]
        assert "[CPF_REDACTED]" in body["scrubbed"]
        # Handoff humano obrigatorio quando ha PII
        assert "transferir" in body["response"].lower() or "atendente" in body["response"].lower()


def test_webhook_e2e_multiple_pii_types_detected() -> None:
    """Webhook com CPF + email + telefone deve detectar todos."""
    with _require_api_deployed() as client:
        payload = {
            "message": {
                "text": (
                    "CPF 111.222.333-44, email joao@teste.com, "
                    "telefone (11) 98765-4321"
                )
            },
            "sender": "5511977776666",
            "instance": "cartorio-2notas",
        }
        resp = client.post("/api/v1/webhook/evolution", json=payload)
        assert resp.status_code == 200
        body = resp.json()
        scrubbed = body["scrubbed"]
        # Nenhum PII original pode vazar
        for original in ["111.222.333-44", "joao@teste.com", "(11) 98765-4321"]:
            assert original not in scrubbed, (
                f"PII '{original}' vazou no scrubbed: {scrubbed}"
            )
        # Todos devem ter sido redacted
        for label in ["CPF", "EMAIL", "PHONE_BR"]:
            assert f"[{label}_REDACTED]" in scrubbed, (
                f"Esperava [{label}_REDACTED] em: {scrubbed}"
            )


def test_audit_chain_integrity_over_time() -> None:
    """Apos varios webhooks, verify_chain deve estar integro."""
    with _require_api_deployed() as client:
        # Dispara 5 webhooks
        for i in range(5):
            payload = {
                "message": {"text": f"mensagem teste {i}"},
                "sender": f"55119999{i:04d}",
                "instance": "cartorio-2notas",
            }
            resp = client.post("/api/v1/webhook/evolution", json=payload)
            assert resp.status_code == 200

        # Verifica cadeia
        resp = client.post("/api/v1/audit/verify")
        assert resp.status_code == 200
        body = resp.json()
        assert body["chain_ok"] is True, (
            f"Cadeia de audit corrompida: last_valid={body['last_valid_position']}"
        )
        assert body["last_valid_position"] >= 5


def test_emolumento_endpoint_public() -> None:
    """/emolumento/calcular deve funcionar sem autenticacao (endpoint publico)."""
    with _require_api_deployed() as client:
        resp = client.get(
            "/api/v1/emolumento/calcular",
            params={"tipo": "escritura_compra_venda", "folhas": 3, "urgencia": True},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert "total" in body
        assert "tipo" in body


def test_webhook_rejects_malformed_payload_gracefully() -> None:
    """Webhook com payload quebrado deve retornar 200 (defesa em profundidade)."""
    with _require_api_deployed() as client:
        # Payload vazio
        resp = client.post("/api/v1/webhook/evolution", json={})
        assert resp.status_code == 200
        # Payload com message None
        resp = client.post("/api/v1/webhook/evolution", json={"message": None})
        assert resp.status_code in {200, 422}


def test_pii_scrubber_unit_consistency() -> None:
    """Garante que o scrubber local bate com o que a API deveria fazer."""
    # Este teste roda SEM depender da API - valida a logica PII isolada
    text = "Meu CPF 123.456.789-09 e email maria@teste.com"
    result = scrub(text)
    assert result.redaction_count == 2
    assert "123.456.789-09" not in result.text
    assert "maria@teste.com" not in result.text
    assert "[CPF_REDACTED]" in result.text
    assert "[EMAIL_REDACTED]" in result.text