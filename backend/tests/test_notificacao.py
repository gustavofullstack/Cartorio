"""Testes A26 — NotificationService: envio de notificacoes multicanal.

Cobertura:
- NotificationMethod enum
- enviar_notificacao: cliente inexistente, sem consentimento, sem metodo contato
- enviar_notificacao: Telegram (sucesso, falha API, sem token config)
- enviar_notificacao: WhatsApp (sucesso, falha API, sem API key)
- enviar_notificacao: Email placeholder
- enviar_notificacao: SMS placeholder
- notificar_agendamento_criado/lembrete/cancelado
"""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.notificacao import NotificationMethod, NotificationService


# ─── NotificationMethod enum ──────────────────────────────────────────

def test_notification_method_values():
    """NotificationMethod enum tem valores corretos."""
    assert NotificationMethod.TELEGRAM.value == "telegram"
    assert NotificationMethod.WHATSAPP.value == "whatsapp"
    assert NotificationMethod.EMAIL.value == "email"
    assert NotificationMethod.SMS.value == "sms"


# ─── enviar_notificacao — erros ──────────────────────────────────────

async def test_enviar_cliente_inexistente():
    """enviar_notificacao levanta ValueError se cliente nao existe."""
    mock_db = MagicMock()
    mock_execute = MagicMock()
    mock_execute.scalar_one_or_none.return_value = None
    mock_db.execute.return_value = mock_execute

    with pytest.raises(ValueError, match="não encontrado"):
        await NotificationService.enviar_notificacao(
            mock_db, cliente_id=999, mensagem="teste"
        )


async def test_enviar_sem_consentimento():
    """enviar_notificacao retorna False se cliente sem consentimento LGPD."""
    mock_db = MagicMock()
    mock_cliente = MagicMock()
    mock_cliente.preferred_contact_method = NotificationMethod.TELEGRAM
    mock_cliente.consentimento_lgpd = False
    mock_execute = MagicMock()
    mock_execute.scalar_one_or_none.return_value = mock_cliente
    mock_db.execute.return_value = mock_execute

    result = await NotificationService.enviar_notificacao(
        mock_db, cliente_id=1, mensagem="teste"
    )
    assert result is False


async def test_enviar_sem_metodo_preferido_e_sem_contato():
    """enviar_notificacao levanta ValueError se sem metodo contato."""
    mock_db = MagicMock()
    mock_cliente = MagicMock()
    mock_cliente.preferred_contact_method = None
    mock_cliente.telegram_chat_id = None
    mock_cliente.whatsapp_number = None
    mock_cliente.email = None
    mock_cliente.telefone_hash = None
    mock_cliente.consentimento_lgpd = True
    mock_execute = MagicMock()
    mock_execute.scalar_one_or_none.return_value = mock_cliente
    mock_db.execute.return_value = mock_execute

    with pytest.raises(ValueError, match="não tem método de contato"):
        await NotificationService.enviar_notificacao(
            mock_db, cliente_id=1, mensagem="teste"
        )


# ─── enviar_notificacao — Telegram ───────────────────────────────────

async def test_enviar_telegram_sucesso():
    """_enviar_telegram retorna True quando API responde 200."""
    mock_response = MagicMock()
    mock_response.status_code = 200

    with (
        patch("app.services.notificacao.settings.telegram_bot_token", "bot123:token"),
        patch("httpx.AsyncClient") as mock_client_cls,
    ):
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client_cls.return_value = mock_client

        result = await NotificationService._enviar_telegram("12345", "mensagem teste")
        assert result is True


async def test_enviar_telegram_sem_token():
    """_enviar_telegram retorna False sem token configurado."""
    with patch("app.services.notificacao.settings.telegram_bot_token", ""):
        result = await NotificationService._enviar_telegram("12345", "teste")
        assert result is False


async def test_enviar_telegram_falha_api():
    """_enviar_telegram retorna False se API retorna erro."""
    with (
        patch("app.services.notificacao.settings.telegram_bot_token", "bot123:token"),
        patch("httpx.AsyncClient") as mock_client_cls,
    ):
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(side_effect=ConnectionError("timeout"))
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client_cls.return_value = mock_client

        result = await NotificationService._enviar_telegram("12345", "teste")
        assert result is False


async def test_enviar_telegram_via_notificacao():
    """enviar_notificacao encaminha para Telegram quando metodo=TELEGRAM."""
    mock_db = MagicMock()
    mock_cliente = MagicMock()
    mock_cliente.preferred_contact_method = None
    mock_cliente.consentimento_lgpd = True
    mock_cliente.telegram_chat_id = "12345"
    mock_cliente.whatsapp_number = None
    mock_cliente.email = None
    mock_cliente.telefone_hash = None
    mock_execute = MagicMock()
    mock_execute.scalar_one_or_none.return_value = mock_cliente
    mock_db.execute.return_value = mock_execute

    with (
        patch.object(NotificationService, "_enviar_telegram", new=AsyncMock(return_value=True)),
        patch("app.services.notificacao.AuditService.log") as mock_audit,
    ):
        result = await NotificationService.enviar_notificacao(
            mock_db,
            cliente_id=1,
            mensagem="teste",
            metodo=NotificationMethod.TELEGRAM,
        )
        assert result is True
        mock_audit.assert_called_once()


async def test_enviar_telegram_sem_chat_id():
    """enviar_notificacao retorna False se telegram_chat_id=None e metodo=TELEGRAM."""
    mock_db = MagicMock()
    mock_cliente = MagicMock()
    mock_cliente.preferred_contact_method = None
    mock_cliente.consentimento_lgpd = True
    mock_cliente.telegram_chat_id = None
    mock_execute = MagicMock()
    mock_execute.scalar_one_or_none.return_value = mock_cliente
    mock_db.execute.return_value = mock_execute

    result = await NotificationService.enviar_notificacao(
        mock_db, cliente_id=1, mensagem="teste", metodo=NotificationMethod.TELEGRAM
    )
    assert result is False


# ─── enviar_notificacao — WhatsApp ───────────────────────────────────

async def test_enviar_whatsapp_sucesso():
    """_enviar_whatsapp retorna True quando API responde 200."""
    mock_response = MagicMock()
    mock_response.status_code = 200

    with (
        patch("app.services.notificacao.settings.evolution_api_key", "evo_key_123"),
        patch("app.services.notificacao.settings.evolution_base_url", "https://evo.test"),
        patch("app.services.notificacao.settings.evolution_instance", "cartorio-test"),
        patch("httpx.AsyncClient") as mock_client_cls,
    ):
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client_cls.return_value = mock_client

        result = await NotificationService._enviar_whatsapp("553499999999", "teste")
        assert result is True


async def test_enviar_whatsapp_sem_api_key():
    """_enviar_whatsapp retorna False sem API key configurada."""
    with patch("app.services.notificacao.settings.evolution_api_key", ""):
        result = await NotificationService._enviar_whatsapp("553499999999", "teste")
        assert result is False


async def test_enviar_whatsapp_falha_api():
    """_enviar_whatsapp retorna False se API falha."""
    with (
        patch("app.services.notificacao.settings.evolution_api_key", "evo_key_123"),
        patch("app.services.notificacao.settings.evolution_base_url", "https://evo.test"),
        patch("app.services.notificacao.settings.evolution_instance", "cartorio-test"),
        patch("httpx.AsyncClient") as mock_client_cls,
    ):
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(side_effect=ConnectionError("timeout"))
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client_cls.return_value = mock_client

        result = await NotificationService._enviar_whatsapp("553499999999", "teste")
        assert result is False


async def test_enviar_whatsapp_sem_numero():
    """enviar_notificacao retorna False se whatsapp_number=None."""
    mock_db = MagicMock()
    mock_cliente = MagicMock()
    mock_cliente.preferred_contact_method = None
    mock_cliente.consentimento_lgpd = True
    mock_cliente.whatsapp_number = None
    mock_execute = MagicMock()
    mock_execute.scalar_one_or_none.return_value = mock_cliente
    mock_db.execute.return_value = mock_execute

    result = await NotificationService.enviar_notificacao(
        mock_db, cliente_id=1, mensagem="teste", metodo=NotificationMethod.WHATSAPP
    )
    assert result is False


# ─── enviar_notificacao — Email / SMS (placeholders) ────────────────

async def test_enviar_email_placeholder():
    """_enviar_email retorna True (placeholder)."""
    result = await NotificationService._enviar_email("teste@test.com", "msg")
    assert result is True


async def test_enviar_email_sem_email():
    """enviar_notificacao retorna False se email=None."""
    mock_db = MagicMock()
    mock_cliente = MagicMock()
    mock_cliente.preferred_contact_method = None
    mock_cliente.consentimento_lgpd = True
    mock_cliente.email = None
    mock_execute = MagicMock()
    mock_execute.scalar_one_or_none.return_value = mock_cliente
    mock_db.execute.return_value = mock_execute

    result = await NotificationService.enviar_notificacao(
        mock_db, cliente_id=1, mensagem="teste", metodo=NotificationMethod.EMAIL
    )
    assert result is False


async def test_enviar_sms_placeholder():
    """_enviar_sms retorna True (placeholder)."""
    result = await NotificationService._enviar_sms("hash123", "msg")
    assert result is True


async def test_enviar_sms_sem_telefone():
    """enviar_notificacao retorna False se telefone_hash=None."""
    mock_db = MagicMock()
    mock_cliente = MagicMock()
    mock_cliente.preferred_contact_method = None
    mock_cliente.consentimento_lgpd = True
    mock_cliente.telefone_hash = None
    mock_execute = MagicMock()
    mock_execute.scalar_one_or_none.return_value = mock_cliente
    mock_db.execute.return_value = mock_execute

    result = await NotificationService.enviar_notificacao(
        mock_db, cliente_id=1, mensagem="teste", metodo=NotificationMethod.SMS
    )
    assert result is False


# ─── Métodos de conveniência ─────────────────────────────────────────

async def test_notificar_agendamento_criado():
    """notificar_agendamento_criado constroi mensagem e chama enviar_notificacao."""
    mock_db = MagicMock()
    mock_cliente = MagicMock()
    mock_cliente.preferred_contact_method = NotificationMethod.EMAIL
    mock_cliente.consentimento_lgpd = True
    mock_cliente.email = "teste@test.com"
    mock_execute = MagicMock()
    mock_execute.scalar_one_or_none.return_value = mock_cliente
    mock_db.execute.return_value = mock_execute

    with patch("app.services.notificacao.AuditService.log"):
        result = await NotificationService.notificar_agendamento_criado(
            mock_db, cliente_id=1, agendamento_id=42,
            titulo="Teste", data_hora="2026-07-01 10:00", local="Sala 1"
        )
        assert result is True


async def test_notificar_agendamento_lembrete():
    """notificar_agendamento_lembrete constroi mensagem e chama enviar_notificacao."""
    mock_db = MagicMock()
    mock_cliente = MagicMock()
    mock_cliente.preferred_contact_method = NotificationMethod.EMAIL
    mock_cliente.consentimento_lgpd = True
    mock_cliente.email = "teste@test.com"
    mock_execute = MagicMock()
    mock_execute.scalar_one_or_none.return_value = mock_cliente
    mock_db.execute.return_value = mock_execute

    with patch("app.services.notificacao.AuditService.log"):
        result = await NotificationService.notificar_agendamento_lembrete(
            mock_db, cliente_id=1, agendamento_id=42,
            titulo="Teste", data_hora="2026-07-01 10:00", local="Sala 1"
        )
        assert result is True


async def test_notificar_agendamento_cancelado():
    """notificar_agendamento_cancelado constroi mensagem e chama enviar_notificacao."""
    mock_db = MagicMock()
    mock_cliente = MagicMock()
    mock_cliente.preferred_contact_method = NotificationMethod.EMAIL
    mock_cliente.consentimento_lgpd = True
    mock_cliente.email = "teste@test.com"
    mock_execute = MagicMock()
    mock_execute.scalar_one_or_none.return_value = mock_cliente
    mock_db.execute.return_value = mock_execute

    with patch("app.services.notificacao.AuditService.log"):
        result = await NotificationService.notificar_agendamento_cancelado(
            mock_db, cliente_id=1, agendamento_id=42, titulo="Teste"
        )
        assert result is True
