"""Smoke tests E2E para o Webhook da Evolution API (WhatsApp) e Ingestão.
Cobre:
- Formato legado (Sprint 1.2)
- Formato aninhado (Baileys/Evolution moderno)
- Idempotência (webhook_event accepted -> idempotent)
- Validação HMAC-SHA256
- Detecção e bloqueio de PII sensível (CPF)

Modified by Gustavo Almeida.
"""

from __future__ import annotations

import hmac
import hashlib
import pytest
from fastapi.testclient import TestClient

@pytest.fixture
def client() -> TestClient:
    from app.main import app
    return TestClient(app)

class FakeLLMResponse:
    def __init__(self, content: str):
        self.content = content
        self.tokens_in = 10
        self.tokens_out = 20
        self.latency_ms = 150

# =============================================================================
# Cenário 1: Formato Legado
# =============================================================================

def test_evolution_webhook_legacy_format(client: TestClient) -> None:
    # Payload com message e sender na raiz
    payload = {
        "instance": "cartorio-instance",
        "sender": "5534999999999@s.whatsapp.net",
        "message": {
            "text": "Olá, gostaria de saber os emolumentos para procuração"
        }
    }
    
    # Mockando a chamada para o fallback de LLM para evitar bater na internet
    from unittest.mock import patch, AsyncMock
    with patch("app.integrations.fallback.chat_with_fallback", new=AsyncMock(return_value=FakeLLMResponse("Resposta mockada"))):
        resp = client.post("/api/v1/webhook/evolution", json=payload)
        
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert "response" in body
    assert body["pii_blocked"] is False


# =============================================================================
# Cenário 2: Formato Aninhado Moderno
# =============================================================================

def test_evolution_webhook_nested_format(client: TestClient) -> None:
    # Payload aninhado com key, messageTimestamp e data
    payload = {
        "event": "messages.upsert",
        "instance": "cartorio-instance",
        "data": {
            "key": {
                "id": "MSG-NESTED-12345",
                "remoteJid": "5534988888888@s.whatsapp.net",
                "fromMe": False
            },
            "message": {
                "conversation": "Qual o horário de atendimento do cartório?"
            },
            "messageTimestamp": 1690000000
        }
    }
    
    from unittest.mock import patch, AsyncMock
    with patch("app.integrations.fallback.chat_with_fallback", new=AsyncMock(return_value=FakeLLMResponse("Das 9h às 17h."))):
        resp = client.post("/api/v1/webhook/evolution", json=payload)
        
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert "response" in body


# =============================================================================
# Cenário 3: Validação HMAC-SHA256 (Signature)
# =============================================================================

def test_evolution_hmac_signature() -> None:
    from app.services.evolution_ingest import validate_evolution_signature
    import os
    from unittest.mock import patch
    
    raw_body = b'{"event":"messages.upsert"}'
    
    # 1. Se secret não está configurado, valida sempre como True (dev/dev-mode)
    with patch.dict(os.environ, {"EVOLUTION_WEBHOOK_SECRET": ""}):
        assert validate_evolution_signature(raw_body, "signature_qualquer") is True
        
    # 2. Se secret está configurado
    secret = "chave-secreta-webhook"
    correct_sig = hmac.new(secret.encode(), raw_body, hashlib.sha256).hexdigest()
    
    with patch.dict(os.environ, {"EVOLUTION_WEBHOOK_SECRET": secret}):
        # Assinatura correta
        assert validate_evolution_signature(raw_body, correct_sig) is True
        # Assinatura com prefixo
        assert validate_evolution_signature(raw_body, f"sha256={correct_sig}") is True
        # Assinatura incorreta
        assert validate_evolution_signature(raw_body, "assinatura-errada") is False
        # Assinatura ausente
        assert validate_evolution_signature(raw_body, None) is False


# =============================================================================
# Cenário 4: Idempotência (webhook_event)
# =============================================================================

def test_evolution_webhook_idempotency(client: TestClient) -> None:
    # 1a chamada aceita
    msg_id = "MSG-IDEMP-99999"
    payload = {
        "event": "messages.upsert",
        "instance": "cartorio-instance",
        "data": {
            "key": {
                "id": msg_id,
                "remoteJid": "5534988888888@s.whatsapp.net",
                "fromMe": False
            },
            "message": {
                "conversation": "Testando idempotência do webhook."
            }
        }
    }
    
    from unittest.mock import patch, AsyncMock
    with patch("app.integrations.fallback.chat_with_fallback", new=AsyncMock(return_value=FakeLLMResponse("Recebido."))):
        resp1 = client.post("/api/v1/webhook/evolution", json=payload)
        
        # 2a chamada deve retornar mensagem duplicada (idempotent)
        resp2 = client.post("/api/v1/webhook/evolution", json=payload)
        
    assert resp1.status_code == 200
    assert resp2.status_code == 200
    
    body2 = resp2.json()
    assert body2["status"] == "idempotent"
    assert body2["message_id"] == msg_id


# =============================================================================
# Cenário 5: PII Scrubbing e Bloqueio (CPF no webhook)
# =============================================================================

def test_evolution_webhook_pii_blocking(client: TestClient) -> None:
    # CPF sensível inserido na conversa
    payload = {
        "instance": "cartorio-instance",
        "sender": "5534999999999@s.whatsapp.net",
        "message": {
            "text": "Meu CPF é 123.456.789-00, verifique minha certidão por favor"
        }
    }
    
    from unittest.mock import patch
    
    # Forçamos pii_block_on_detect e pii_scrub_enabled no settings
    with patch("app.config.settings.pii_scrub_enabled", True):
        with patch("app.config.settings.pii_block_on_detect", True):
            resp = client.post("/api/v1/webhook/evolution", json=payload)
            
    assert resp.status_code == 200
    body = resp.json()
    assert "sensiveis" in body["response"]
    # Garante que o CPF foi omitido/ofuscado
    assert "123.456.789-00" not in body["response"]
