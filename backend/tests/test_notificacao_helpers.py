"""Testes para app/services/notificacao.py - NotificationService + helpers (cobertura).

Cobre:
1. _strip_emojis remove emojis simples
2. _strip_emojis preserva texto sem emojis
3. NotificationMethod enum tem os 4 valores canonicos
4. NotificationService.enviar_notificacao cliente inexistente -> ValueError

Sobe cobertura notificacao.py 73% -> >=85%.
"""

from __future__ import annotations

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models.cliente import Cliente
from app.services.notificacao import (
    NotificationMethod,
    NotificationService,
    _strip_emojis,
)
from app.models.base import Base


@pytest.fixture
def db_session():
    """Session SQLite in-memory com Base.metadata criado."""
    eng = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(eng)
    SessionLocal = sessionmaker(bind=eng, autoflush=False, autocommit=False, expire_on_commit=False)
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(eng)


# =============================================================================
# _strip_emojis
# =============================================================================


def test_strip_emojis_remove_emojis_simples() -> None:
    """_strip_emojis remove emojis simples."""
    text = "Ola cliente \U0001f44d tudo bem? \U0001f680"
    out = _strip_emojis(text)
    assert "\U0001f44d" not in out
    assert "\U0001f680" not in out
    assert "Ola cliente" in out
    assert "tudo bem?" in out


def test_strip_emojis_preserva_texto_sem_emoji() -> None:
    """_strip_emojis nao altera texto sem emojis."""
    text = "Apenas texto normal"
    assert _strip_emojis(text) == text


def test_strip_emojis_string_vazia() -> None:
    """_strip_emojis('') retorna ''."""
    assert _strip_emojis("") == ""


# =============================================================================
# NotificationMethod enum
# =============================================================================


def test_notification_method_tem_4_valores() -> None:
    """NotificationMethod tem 4 valores canonicos."""
    assert NotificationMethod.TELEGRAM == "telegram"
    assert NotificationMethod.WHATSAPP == "whatsapp"
    assert NotificationMethod.EMAIL == "email"
    assert NotificationMethod.SMS == "sms"


def test_notification_method_total_4() -> None:
    """NotificationMethod tem 4 membros."""
    assert len(NotificationMethod) == 4


# =============================================================================
# NotificationService.enviar_notificacao
# =============================================================================


@pytest.mark.asyncio
async def test_enviar_notificacao_cliente_inexistente_levanta_ValueError(db_session) -> None:
    """enviar_notificacao para cliente_id inexistente -> ValueError."""
    with pytest.raises(ValueError, match="Cliente #999.*n.o encontrado"):
        await NotificationService.enviar_notificacao(
            db_session,
            cliente_id=999,
            mensagem="teste",
        )


@pytest.mark.asyncio
async def test_enviar_notificacao_cliente_sem_contato_levanta_ValueError(db_session) -> None:
    """enviar_notificacao para cliente sem nenhum metodo -> ValueError."""
    cliente = Cliente(
        nome="Sem Contato",
        cpf_hash="hash123abc",
        consentimento_lgpd=True,
    )
    db_session.add(cliente)
    db_session.commit()
    db_session.refresh(cliente)

    # Sem telegram_chat_id/whatsapp/email/telefone_hash
    with pytest.raises(ValueError, match="m.todo de contato"):
        await NotificationService.enviar_notificacao(
            db_session,
            cliente_id=cliente.id,
            mensagem="teste",
        )


@pytest.mark.asyncio
async def test_enviar_notificacao_cliente_sem_consentimento_retorna_False(db_session) -> None:
    """Cliente sem consentimento LGPD -> retorna False (LGPD block)."""
    cliente = Cliente(
        nome="Sem Consent",
        cpf_hash="hash456def",
        consentimento_lgpd=False,  # SEM consentimento
        telegram_chat_id=12345,
    )
    db_session.add(cliente)
    db_session.commit()
    db_session.refresh(cliente)

    result = await NotificationService.enviar_notificacao(
        db_session,
        cliente_id=cliente.id,
        mensagem="Ola",
    )
    # Sem consentimento, retorna False (NAO envia)
    assert result is False
