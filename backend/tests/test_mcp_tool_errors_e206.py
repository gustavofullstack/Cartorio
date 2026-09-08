"""E2.06 — Regressão: tools MCP de envio (Telegram/WhatsApp) e criar_protocolo
não vazam PII nem credenciais em paths de falha, e mantêm comportamento de
mutação/HITL intacto.

Cobre:
  - Falha em _react/_send_poll/_send_photo/_send_document (Telegram) retorna
    payload estruturado {sucesso: False, erro, mensagem, tipo_erro} — nunca
    str(exc) cru (bot token na URL httpx, CPF, telefone).
  - Falha em NotificationService.enviar_whatsapp_* idem.
  - Sucesso continua retornando {"sucesso": True} (comportamento preservado).
  - cartorio_criar_protocolo: gate LGPD (consent=False -> LGPD_BLOCKED sem
    tocar service), CPF malformado -> PII_INVALIDO, exceção interna ->
    INTERNAL_ERROR scrubbed, e sucesso mantém DRAFT + próxima ação HITL.

Modified by Gustavo Almeida — E2.06.
"""

from __future__ import annotations

import contextlib
import importlib.util
import sys
from pathlib import Path
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[1]
MCP_SERVER = ROOT / "mcp_server.py"

FAKE_TOKEN = "123456789:AAFakeToken_abcdefghi-1234567890"  # noqa: ALLOW_KEY_FALLBACK (motivo: FAKE_TOKEN de E2.06 — fixture sintetica estabelecida p/ scrub de erros MCP)
FAKE_CPF = "123.456.789-09"
FAKE_PHONE = "5534999998888"


@pytest.fixture(scope="module")
def mcp_module():
    """Importa mcp_server.py dinamicamente (arquivo solto, não pacote)."""
    spec = importlib.util.spec_from_file_location("mcp_server", MCP_SERVER)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    sys.modules.pop("mcp_server", None)
    spec.loader.exec_module(mod)
    return mod


def _assert_no_leak(result: Any) -> None:
    blob = str(result)
    assert FAKE_TOKEN not in blob
    assert "bot" + FAKE_TOKEN not in blob
    assert FAKE_CPF not in blob
    assert FAKE_PHONE not in blob


def _assert_structured_failure(result: Any, exc_name: str) -> None:
    assert isinstance(result, dict)
    assert result["sucesso"] is False
    assert result["erro"] == "SEND_FAILED"
    assert isinstance(result["mensagem"], str)
    assert result["tipo_erro"] == exc_name
    _assert_no_leak(result)


class TestTelegramToolsFailurePaths:
    async def test_reaction_failure_scrubs_token_and_pii(self, mcp_module, monkeypatch):
        async def _boom(chat_id, message_id, reaction="thumbsup"):
            raise RuntimeError(
                f"POST https://api.telegram.org/bot{FAKE_TOKEN}/setMessageReaction "
                f"falhou para chat {FAKE_PHONE} cpf {FAKE_CPF}"
            )

        monkeypatch.setattr("app.api.v1.telegram._react", _boom)
        result = await mcp_module.cartorio_enviar_telegram_reaction(123, 456, "👍")
        _assert_structured_failure(result, "RuntimeError")

    async def test_reaction_success_preservado(self, mcp_module, monkeypatch):
        called = {}

        async def _ok(chat_id, message_id, reaction="thumbsup"):
            called["args"] = (chat_id, message_id, reaction)

        monkeypatch.setattr("app.api.v1.telegram._react", _ok)
        result = await mcp_module.cartorio_enviar_telegram_reaction(123, 456, "❤️")
        assert result == {"sucesso": True}
        # Emoji "❤️" mapeia para a key "heart" (comportamento original intacto)
        assert called["args"] == (123, 456, "heart")

    async def test_poll_failure_scrubs_pii(self, mcp_module, monkeypatch):
        async def _boom(chat_id, question, options):
            raise ValueError(f"options invalidas para {FAKE_CPF} tel {FAKE_PHONE}")

        monkeypatch.setattr("app.api.v1.telegram._send_poll", _boom)
        result = await mcp_module.cartorio_enviar_telegram_poll(123, "P?", ["a", "b"])
        _assert_structured_failure(result, "ValueError")

    async def test_poll_success_preservado(self, mcp_module, monkeypatch):
        async def _ok(chat_id, question, options):
            return True

        monkeypatch.setattr("app.api.v1.telegram._send_poll", _ok)
        result = await mcp_module.cartorio_enviar_telegram_poll(123, "P?", ["a", "b"])
        assert result == {"sucesso": True}

    async def test_media_document_failure_scrubs_token(self, mcp_module, monkeypatch):
        async def _boom(chat_id, doc_url, filename, caption=None):
            raise RuntimeError(f"bot{FAKE_TOKEN} sendDocument 500 para {FAKE_PHONE}")

        monkeypatch.setattr("app.api.v1.telegram._send_document", _boom)
        result = await mcp_module.cartorio_enviar_telegram_media(
            123, "https://x/doc.pdf", "document", "doc.pdf"
        )
        _assert_structured_failure(result, "RuntimeError")

    async def test_media_image_success_preservado(self, mcp_module, monkeypatch):
        async def _ok(chat_id, photo_url, caption=None):
            return True

        monkeypatch.setattr("app.api.v1.telegram._send_photo", _ok)
        result = await mcp_module.cartorio_enviar_telegram_media(
            123, "https://x/img.png", "image", "img.png", caption="foto"
        )
        assert result == {"sucesso": True}


class TestWhatsappToolsFailurePaths:
    async def test_reaction_failure_scrubs_pii(self, mcp_module, monkeypatch):
        async def _boom(number, message_id, emoji):
            raise RuntimeError(f"Evolution 500 para {FAKE_PHONE} cpf {FAKE_CPF}")

        monkeypatch.setattr(
            "app.services.notificacao.NotificationService.enviar_whatsapp_reaction",
            staticmethod(_boom),
        )
        result = await mcp_module.cartorio_enviar_whatsapp_reaction(FAKE_PHONE, "mid", "👍")
        _assert_structured_failure(result, "RuntimeError")

    async def test_poll_failure_scrubs_pii(self, mcp_module, monkeypatch):
        async def _boom(number, question, options):
            raise TypeError(f"options malformed {FAKE_CPF}")

        monkeypatch.setattr(
            "app.services.notificacao.NotificationService.enviar_whatsapp_poll",
            staticmethod(_boom),
        )
        result = await mcp_module.cartorio_enviar_whatsapp_poll(FAKE_PHONE, "P?", ["a"])
        _assert_structured_failure(result, "TypeError")

    async def test_media_failure_scrubs_pii(self, mcp_module, monkeypatch):
        async def _boom(number, media_url, mediatype, filename, caption=None):
            raise RuntimeError(f"upload falhou {FAKE_PHONE}")

        monkeypatch.setattr(
            "app.services.notificacao.NotificationService.enviar_whatsapp_media",
            staticmethod(_boom),
        )
        result = await mcp_module.cartorio_enviar_whatsapp_media(
            FAKE_PHONE, "https://x/d.pdf", "document", "d.pdf"
        )
        _assert_structured_failure(result, "RuntimeError")

    async def test_reaction_success_preservado(self, mcp_module, monkeypatch):
        async def _ok(number, message_id, emoji):
            return True

        monkeypatch.setattr(
            "app.services.notificacao.NotificationService.enviar_whatsapp_reaction",
            staticmethod(_ok),
        )
        result = await mcp_module.cartorio_enviar_whatsapp_reaction("5511999", "mid", "👍")
        assert result == {"sucesso": True}


class TestCriarProtocoloGuards:
    async def test_lgpd_gate_bloqueia_sem_consentimento(self, mcp_module):
        # Não deve importar/tocar service nem DB: gate é prévio.
        result = await mcp_module.cartorio_criar_protocolo(
            tipo="certidao_negativa",
            cliente_cpf=FAKE_CPF,
            cliente_nome="Cliente X",
            consentimento_lgpd=False,
        )
        assert result["erro"] == "LGPD_BLOCKED"
        _assert_no_leak(result)

    async def test_cpf_malformado_retorna_pii_invalido(self, mcp_module):
        result = await mcp_module.cartorio_criar_protocolo(
            tipo="certidao_negativa",
            cliente_cpf="123",  # menos de 11 dígitos
            cliente_nome="Cliente X",
            consentimento_lgpd=True,
        )
        assert result["erro"] == "PII_INVALIDO"

    async def test_internal_error_scrubs_cpf(self, mcp_module, monkeypatch):
        @contextlib.contextmanager
        def _fake_scope():
            yield object()

        def _boom(*args, **kwargs):
            raise RuntimeError(f"insert falhou para cpf {FAKE_CPF} tel {FAKE_PHONE}")

        monkeypatch.setattr("app.db.session_scope", _fake_scope)
        monkeypatch.setattr("app.services.protocolo.criar_protocolo_svc", _boom)
        result = await mcp_module.cartorio_criar_protocolo(
            tipo="certidao_negativa",
            cliente_cpf=FAKE_CPF,
            cliente_nome="Cliente X",
            consentimento_lgpd=True,
        )
        assert result["erro"] == "INTERNAL_ERROR"
        assert result["tipo_erro"] == "RuntimeError"
        _assert_no_leak(result)

    async def test_hitl_draft_passthrough_preservado(self, mcp_module, monkeypatch):
        """Sucesso: dict do service passa intacto — protocolo nasce DRAFT e a
        próxima ação é validação humana (HITL não pode regredir)."""
        svc_payload = {
            "status": "criado",
            "numero": "2026-00042",
            "protocolo_id": 42,
            "estado": "DRAFT",
            "proxima_acao": (
                "Aguardando validacao humana do escrevente. "
                "O protocolo NAO sera processado ate confirmacao no painel admin."
            ),
            "cliente_id": 7,
        }

        @contextlib.contextmanager
        def _fake_scope():
            yield object()

        def _fake_svc(*args, **kwargs):
            return dict(svc_payload)

        monkeypatch.setattr("app.db.session_scope", _fake_scope)
        monkeypatch.setattr("app.services.protocolo.criar_protocolo_svc", _fake_svc)
        result = await mcp_module.cartorio_criar_protocolo(
            tipo="certidao_negativa",
            cliente_cpf=FAKE_CPF,
            cliente_nome="Cliente X",
            consentimento_lgpd=True,
        )
        assert result == svc_payload
        assert result["estado"] == "DRAFT"
        assert "validacao humana" in result["proxima_acao"]
