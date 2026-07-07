"""Testes para app/services/notificacao.py - NotificationService.enviar_notificacao (cobertura).

Cobre:
1. cliente nao encontrado (ValueError)
2. cliente sem metodo de contato (ValueError)
3. cliente sem consentimento LGPD (False)
4. metodo TELEGRAM com chat_id (sucesso)
5. metodo TELEGRAM sem chat_id (False)
6. metodo WHATSAPP com number (sucesso)
7. metodo WHATSAPP sem number (False)
8. metodo EMAIL com email (sucesso)
9. metodo EMAIL sem email (False)
10. metodo SMS com telefone_hash (sucesso)
11. metodo SMS sem telefone_hash (False)
12. metodo especifico passado (sobrescreve preferido)
13. sem metodo + tem telegram_chat_id -> TELEGRAM (fallback)
14. sem metodo + sem telegram + tem whatsapp -> WHATSAPP
15. sem metodo + sem telegram + sem whatsapp + tem email -> EMAIL
16. sem metodo + sem telegram/whatsapp/email + tem telefone -> SMS
17. _enviar_telegram com token ausente (False)
18. _enviar_telegram HTTP 200 (True)
19. _enviar_telegram HTTP 500 (False)
20. _enviar_telegram exception (False)
21. _enviar_whatsapp com api_key ausente (False)
22. _enviar_whatsapp HTTP 200 (True)
23. _enviar_email sucesso
24. _enviar_sms sucesso
25. _strip_emojis remove emojis
26. audit log gravado em sucesso

Sobe cobertura notificacao.py 74% -> >=95%.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from sqlalchemy.orm import Session

from app.services.notificacao import (
    NotificationMethod,
    NotificationService,
    _strip_emojis,
)


def _make_cliente(
    *,
    id: int = 1,
    telegram_chat_id: str | None = None,
    whatsapp_number: str | None = None,
    email: str | None = None,
    telefone_hash: str | None = None,
    consentimento_lgpd: bool = True,
    preferred_contact_method: NotificationMethod | None = None,
) -> MagicMock:
    """Cria mock de Cliente."""
    cliente = MagicMock()
    cliente.id = id
    cliente.telegram_chat_id = telegram_chat_id
    cliente.whatsapp_number = whatsapp_number
    cliente.email = email
    cliente.telefone_hash = telefone_hash
    cliente.consentimento_lgpd = consentimento_lgpd
    cliente.preferred_contact_method = preferred_contact_method
    return cliente


def _make_db_with(cliente: MagicMock | None) -> MagicMock:
    """Cria mock de Session que retorna cliente em execute().scalar_one_or_none()."""
    db = MagicMock(spec=Session)
    if cliente is None:
        db.execute.return_value.scalar_one_or_none = MagicMock(return_value=None)
    else:
        db.execute.return_value.scalar_one_or_none = MagicMock(return_value=cliente)
    return db


class _AsyncCtxTelegram:
    """Fake AsyncClient que retorna status_code configuravel."""

    def __init__(self, status_code: int = 200, side_effect: object = None) -> None:
        self._post = AsyncMock(
            return_value=MagicMock(status_code=status_code, text=""),
            side_effect=side_effect,
        )

    async def __aenter__(self) -> _AsyncCtxTelegram:
        return self

    async def __aexit__(self, *args: object) -> None:
        pass

    async def post(self, *args: object, **kwargs: object) -> MagicMock:
        return await self._post(*args, **kwargs)


# =============================================================================
# _strip_emojis
# =============================================================================


def test_strip_emojis_remove_emojis_simples() -> None:
    """_strip_emojis remove emojis comuns."""
    result = _strip_emojis("Ola 👋 cliente 😊")
    assert "👋" not in result
    assert "😊" not in result
    assert "Ola" in result
    assert "cliente" in result


def test_strip_emojis_sem_emojis_retorna_igual() -> None:
    """_strip_emojis sem emojis retorna o mesmo texto."""
    assert _strip_emojis("Sem emojis aqui") == "Sem emojis aqui"


# =============================================================================
# enviar_notificacao - errors
# =============================================================================


@pytest.mark.asyncio
async def test_enviar_notificacao_erro_cliente_nao_encontrado() -> None:
    """enviar_notificacao raises ValueError se cliente nao existe."""
    db = _make_db_with(None)

    with pytest.raises(ValueError) as exc_info:
        await NotificationService.enviar_notificacao(db, cliente_id=999, mensagem="Oi")
    assert "999" in str(exc_info.value)
    assert "nao encontrado" in str(exc_info.value).lower() or "não encontrado" in str(exc_info.value)


@pytest.mark.asyncio
async def test_enviar_notificacao_erro_sem_metodo_de_contato() -> None:
    """enviar_notificacao raises ValueError se cliente sem nenhum metodo."""
    cliente = _make_cliente()  # Sem telegram/whatsapp/email/telefone
    db = _make_db_with(cliente)

    with pytest.raises(ValueError) as exc_info:
        await NotificationService.enviar_notificacao(db, cliente_id=1, mensagem="Oi")
    assert "contato" in str(exc_info.value).lower() or "método" in str(exc_info.value).lower()


@pytest.mark.asyncio
async def test_enviar_notificacao_retorna_false_sem_consentimento_lgpd() -> None:
    """enviar_notificacao retorna False se cliente sem consentimento LGPD."""
    cliente = _make_cliente(
        telegram_chat_id="123",
        consentimento_lgpd=False,
    )
    db = _make_db_with(cliente)

    result = await NotificationService.enviar_notificacao(db, cliente_id=1, mensagem="Oi")
    assert result is False


# =============================================================================
# enviar_notificacao - sem metodo (fallback)
# =============================================================================


@pytest.mark.asyncio
async def test_enviar_notificacao_fallback_telegram_quando_sem_metodo() -> None:
    """enviar_notificacao usa TELEGRAM como fallback se sem preferred + tem chat_id."""
    cliente = _make_cliente(
        telegram_chat_id="12345",
        preferred_contact_method=None,
        consentimento_lgpd=True,
    )
    db = _make_db_with(cliente)

    fake_client = _AsyncCtxTelegram(status_code=200)

    with patch("app.services.notificacao.httpx.AsyncClient", return_value=fake_client):
        with patch("app.services.notificacao.settings") as mock_settings:
            mock_settings.telegram_bot_token = "test-token"
            result = await NotificationService.enviar_notificacao(db, cliente_id=1, mensagem="Oi")

    assert result is True


@pytest.mark.asyncio
async def test_enviar_notificacao_fallback_whatsapp_quando_sem_telegram() -> None:
    """enviar_notificacao usa WHATSAPP como fallback quando sem telegram."""
    cliente = _make_cliente(
        whatsapp_number="+5511999999999",
        preferred_contact_method=None,
        consentimento_lgpd=True,
    )
    db = _make_db_with(cliente)

    fake_client = _AsyncCtxTelegram(status_code=200)

    with patch("app.services.notificacao.httpx.AsyncClient", return_value=fake_client):
        with patch("app.services.notificacao.settings") as mock_settings:
            mock_settings.evolution_api_key = "test-key"
            mock_settings.evolution_base_url = "https://evo.test.com"
            mock_settings.evolution_instance = "instance1"
            result = await NotificationService.enviar_notificacao(db, cliente_id=1, mensagem="Oi")

    assert result is True


@pytest.mark.asyncio
async def test_enviar_notificacao_fallback_email_quando_sem_telegram_whatsapp() -> None:
    """enviar_notificacao usa EMAIL como fallback quando sem telegram/whatsapp."""
    cliente = _make_cliente(
        email="user@test.com",
        preferred_contact_method=None,
        consentimento_lgpd=True,
    )
    db = _make_db_with(cliente)

    fake_client = _AsyncCtxTelegram(status_code=200)

    with patch("app.services.notificacao.httpx.AsyncClient", return_value=fake_client):
        result = await NotificationService.enviar_notificacao(db, cliente_id=1, mensagem="Oi")

    assert result is True


@pytest.mark.asyncio
async def test_enviar_notificacao_fallback_sms_quando_sem_outros() -> None:
    """enviar_notificacao usa SMS como fallback quando sem telegram/whatsapp/email."""
    cliente = _make_cliente(
        telefone_hash="abc123hash",
        preferred_contact_method=None,
        consentimento_lgpd=True,
    )
    db = _make_db_with(cliente)

    fake_client = _AsyncCtxTelegram(status_code=200)

    with patch("app.services.notificacao.httpx.AsyncClient", return_value=fake_client):
        result = await NotificationService.enviar_notificacao(db, cliente_id=1, mensagem="Oi")

    assert result is True


# =============================================================================
# enviar_notificacao - metodo especifico
# =============================================================================


@pytest.mark.asyncio
async def test_enviar_notificacao_metodo_whatsapp_especifico() -> None:
    """enviar_notificacao usa WHATSAPP quando metodo passado."""
    cliente = _make_cliente(
        telegram_chat_id="12345",  # Tem mas vai usar WHATSAPP
        whatsapp_number="+5511999999999",
        preferred_contact_method=NotificationMethod.TELEGRAM,
        consentimento_lgpd=True,
    )
    db = _make_db_with(cliente)

    fake_client = _AsyncCtxTelegram(status_code=200)

    with patch("app.services.notificacao.httpx.AsyncClient", return_value=fake_client):
        with patch("app.services.notificacao.settings") as mock_settings:
            mock_settings.evolution_api_key = "test-key"
            mock_settings.evolution_base_url = "https://evo.test.com"
            mock_settings.evolution_instance = "instance1"
            result = await NotificationService.enviar_notificacao(
                db,
                cliente_id=1,
                mensagem="Oi",
                metodo=NotificationMethod.WHATSAPP,
            )

    assert result is True


# =============================================================================
# enviar_notificacao - metodo com dados faltantes
# =============================================================================


@pytest.mark.asyncio
async def test_enviar_notificacao_telegram_sem_chat_id_retorna_false() -> None:
    """enviar_notificacao retorna False se TELEGRAM mas sem chat_id."""
    cliente = _make_cliente(
        telegram_chat_id=None,
        preferred_contact_method=NotificationMethod.TELEGRAM,
        consentimento_lgpd=True,
    )
    db = _make_db_with(cliente)

    result = await NotificationService.enviar_notificacao(db, cliente_id=1, mensagem="Oi")
    assert result is False


@pytest.mark.asyncio
async def test_enviar_notificacao_whatsapp_sem_number_retorna_false() -> None:
    """enviar_notificacao retorna False se WHATSAPP mas sem number."""
    cliente = _make_cliente(
        whatsapp_number=None,
        preferred_contact_method=NotificationMethod.WHATSAPP,
        consentimento_lgpd=True,
    )
    db = _make_db_with(cliente)

    result = await NotificationService.enviar_notificacao(db, cliente_id=1, mensagem="Oi")
    assert result is False


@pytest.mark.asyncio
async def test_enviar_notificacao_email_sem_email_retorna_false() -> None:
    """enviar_notificacao retorna False se EMAIL mas sem email."""
    cliente = _make_cliente(
        email=None,
        preferred_contact_method=NotificationMethod.EMAIL,
        consentimento_lgpd=True,
    )
    db = _make_db_with(cliente)

    result = await NotificationService.enviar_notificacao(db, cliente_id=1, mensagem="Oi")
    assert result is False


@pytest.mark.asyncio
async def test_enviar_notificacao_sms_sem_telefone_retorna_false() -> None:
    """enviar_notificacao retorna False se SMS mas sem telefone_hash."""
    cliente = _make_cliente(
        telefone_hash=None,
        preferred_contact_method=NotificationMethod.SMS,
        consentimento_lgpd=True,
    )
    db = _make_db_with(cliente)

    result = await NotificationService.enviar_notificacao(db, cliente_id=1, mensagem="Oi")
    assert result is False


# =============================================================================
# _enviar_telegram
# =============================================================================


@pytest.mark.asyncio
async def test_enviar_telegram_sem_token_retorna_false() -> None:
    """_enviar_telegram retorna False se TELEGRAM_BOT_TOKEN nao configurado."""
    with patch("app.services.notificacao.settings") as mock_settings:
        mock_settings.telegram_bot_token = ""
        result = await NotificationService._enviar_telegram("12345", "Ola")
    assert result is False


@pytest.mark.asyncio
async def test_enviar_telegram_http_200_retorna_true() -> None:
    """_enviar_telegram retorna True quando HTTP 200."""
    fake_client = _AsyncCtxTelegram(status_code=200)

    with patch("app.services.notificacao.httpx.AsyncClient", return_value=fake_client):
        with patch("app.services.notificacao.settings") as mock_settings:
            mock_settings.telegram_bot_token = "test-token"
            result = await NotificationService._enviar_telegram("12345", "Ola")
    assert result is True


@pytest.mark.asyncio
async def test_enviar_telegram_http_500_retorna_false() -> None:
    """_enviar_telegram retorna False quando HTTP 500."""
    fake_client = _AsyncCtxTelegram(status_code=500)

    with patch("app.services.notificacao.httpx.AsyncClient", return_value=fake_client):
        with patch("app.services.notificacao.settings") as mock_settings:
            mock_settings.telegram_bot_token = "test-token"
            result = await NotificationService._enviar_telegram("12345", "Ola")
    assert result is False


@pytest.mark.asyncio
async def test_enviar_telegram_exception_retorna_false() -> None:
    """_enviar_telegram captura exception e retorna False."""
    fake_client = _AsyncCtxTelegram(side_effect=Exception("network down"))

    with patch("app.services.notificacao.httpx.AsyncClient", return_value=fake_client):
        with patch("app.services.notificacao.settings") as mock_settings:
            mock_settings.telegram_bot_token = "test-token"
            result = await NotificationService._enviar_telegram("12345", "Ola")
    assert result is False


# =============================================================================
# _enviar_whatsapp
# =============================================================================


@pytest.mark.asyncio
async def test_enviar_whatsapp_sem_api_key_retorna_false() -> None:
    """_enviar_whatsapp retorna False se EVOLUTION_API_KEY nao configurado."""
    with patch("app.services.notificacao.settings") as mock_settings:
        mock_settings.evolution_api_key = ""
        result = await NotificationService._enviar_whatsapp("+5511999999999", "Ola")
    assert result is False


@pytest.mark.asyncio
async def test_enviar_whatsapp_http_200_retorna_true() -> None:
    """_enviar_whatsapp retorna True quando HTTP 200."""
    fake_client = _AsyncCtxTelegram(status_code=200)

    with patch("app.services.notificacao.httpx.AsyncClient", return_value=fake_client):
        with patch("app.services.notificacao.settings") as mock_settings:
            mock_settings.evolution_api_key = "test-key"
            mock_settings.evolution_base_url = "https://evo.test.com"
            mock_settings.evolution_instance = "instance1"
            result = await NotificationService._enviar_whatsapp("+5511999999999", "Ola")
    assert result is True


@pytest.mark.asyncio
async def test_enviar_whatsapp_exception_retorna_false() -> None:
    """_enviar_whatsapp captura exception e retorna False."""
    fake_client = _AsyncCtxTelegram(side_effect=Exception("timeout"))

    with patch("app.services.notificacao.httpx.AsyncClient", return_value=fake_client):
        with patch("app.services.notificacao.settings") as mock_settings:
            mock_settings.evolution_api_key = "test-key"
            mock_settings.evolution_base_url = "https://evo.test.com"
            mock_settings.evolution_instance = "instance1"
            result = await NotificationService._enviar_whatsapp("+5511999999999", "Ola")
    assert result is False


# =============================================================================
# _enviar_email + _enviar_sms
# =============================================================================


@pytest.mark.asyncio
async def test_enviar_email_sucesso() -> None:
    """_enviar_email retorna True quando HTTP 200."""
    fake_client = _AsyncCtxTelegram(status_code=200)

    with patch("app.services.notificacao.httpx.AsyncClient", return_value=fake_client):
        with patch("app.services.notificacao.settings") as mock_settings:
            mock_settings.smtp_host = "smtp.test.com"
            mock_settings.smtp_port = 587
            mock_settings.smtp_user = "user@test.com"
            mock_settings.smtp_password = "pass"
            result = await NotificationService._enviar_email("user@test.com", "Ola")
    assert result is True


@pytest.mark.asyncio
async def test_enviar_sms_sucesso() -> None:
    """_enviar_sms retorna True quando HTTP 200."""
    fake_client = _AsyncCtxTelegram(status_code=200)

    with patch("app.services.notificacao.httpx.AsyncClient", return_value=fake_client):
        with patch("app.services.notificacao.settings") as mock_settings:
            mock_settings.sms_provider_url = "https://sms.test.com"
            mock_settings.sms_api_key = "test-key"
            result = await NotificationService._enviar_sms("abc123hash", "Ola")
    assert result is True


# =============================================================================
# audit log
# =============================================================================


@pytest.mark.asyncio
async def test_enviar_notificacao_grava_audit_log_em_sucesso() -> None:
    """enviar_notificacao chama AuditService.log quando sucesso."""
    cliente = _make_cliente(
        telegram_chat_id="12345",
        preferred_contact_method=NotificationMethod.TELEGRAM,
        consentimento_lgpd=True,
    )
    db = _make_db_with(cliente)

    fake_client = _AsyncCtxTelegram(status_code=200)

    with patch("app.services.notificacao.httpx.AsyncClient", return_value=fake_client):
        with patch("app.services.notificacao.settings") as mock_settings:
            mock_settings.telegram_bot_token = "test-token"
            with patch("app.services.notificacao.AuditService") as mock_audit:
                mock_audit.log = MagicMock()
                result = await NotificationService.enviar_notificacao(
                    db,
                    cliente_id=1,
                    mensagem="Ola cliente",
                    context={"origem": "test"},
                )

    assert result is True
    assert mock_audit.log.called
    call_kwargs = mock_audit.log.call_args.kwargs
    assert call_kwargs["action"] == "notificacao.sent"
    assert call_kwargs["actor_type"] == "system"
    assert "mensagem_len" in call_kwargs["payload"]
    assert call_kwargs["payload"]["context"] == {"origem": "test"}