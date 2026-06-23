"""Testes do servico de direito ao esquecimento (LGPD art. 18 VI)."""
from __future__ import annotations

import os

os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("AUDIT_HMAC_KEY", "a" * 64)

from app.config import get_settings  # noqa: E402

get_settings.cache_clear()

import pytest  # noqa: E402
from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402

from app.models.base import Base  # noqa: E402
from app.models.cliente import Cliente, MotivoEncerramento  # noqa: E402
from app.models.protocolo import Protocolo  # noqa: E402
from app.services.lgpd.direito_esquecimento import (  # noqa: E402
    ClienteJaRevogadoError,
    ClienteNotFoundError,
    direito_esquecimento,
)


@pytest.fixture
def db_session():
    """SQLite in-memory para testes de direito ao esquecimento."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(engine)


def _make_cliente(db, cpf_hash: str = "hash1234567890", nome: str = "Joao da Silva") -> Cliente:
    """Cria cliente com cpf_hash e nome. CPF puro NAO persiste (ja vem como hash)."""
    c = Cliente(
        cpf_hash=cpf_hash,
        nome=nome,
        email="joao@example.com",
        telefone_hash="tel_hash_456",
        consentimento_lgpd=True,
    )
    db.add(c)
    db.commit()
    db.refresh(c)
    return c


def _make_protocolo(db, cliente_id: int, status: str = "aberto", numero: str = "2026-00001") -> Protocolo:
    """Cria protocolo vinculado ao cliente."""
    p = Protocolo(
        cliente_id=cliente_id,
        numero=numero,
        tipo="certidao_negativa",
        status=status,
        canal_origem="web",
    )
    db.add(p)
    db.commit()
    db.refresh(p)
    return p


# ============================================================================
# Hard delete: cliente SEM protocolo
# ============================================================================


def test_cliente_sem_protocolo_faz_hard_delete(db_session) -> None:
    """Cliente sem protocolo -> hard delete (remove do DB)."""
    c = _make_cliente(db_session)
    cliente_id = c.id

    result = direito_esquecimento(db_session, cliente_id)

    assert result.tipo == "hard"
    assert result.protocolos_ativos == 0
    assert result.cliente_id == cliente_id
    assert result.motivo == MotivoEncerramento.REVOGACAO_CONSENTIMENTO
    assert result.data_encerramento is not None
    # Cliente realmente removido do DB
    assert db_session.get(Cliente, cliente_id) is None


def test_cliente_com_protocolo_cancelado_faz_hard_delete(db_session) -> None:
    """Cliente com apenas protocolos cancelados/expirados -> hard delete.

    Provimento CNJ 74/2018 so obriga reter 5y para atos NAO cancelados.
    Protocolo cancelado antes do hard delete = sem retencao obrigatoria.
    """
    c = _make_cliente(db_session)
    _make_protocolo(db_session, c.id, status="cancelado")

    result = direito_esquecimento(db_session, c.id)

    assert result.tipo == "hard"
    assert result.protocolos_ativos == 0
    assert db_session.get(Cliente, c.id) is None


# ============================================================================
# Soft delete: cliente COM protocolo ativo
# ============================================================================


def test_cliente_com_protocolo_aberto_faz_soft_delete(db_session) -> None:
    """Cliente com protocolo aberto -> soft delete (anonimiza PII)."""
    c = _make_cliente(db_session, cpf_hash="abcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890")
    p = _make_protocolo(db_session, c.id)
    cliente_id = c.id

    result = direito_esquecimento(db_session, cliente_id)

    assert result.tipo == "soft"
    assert result.protocolos_ativos == 1
    assert result.motivo == MotivoEncerramento.REVOGACAO_CONSENTIMENTO
    # Cliente ainda no DB (soft)
    c2 = db_session.get(Cliente, cliente_id)
    assert c2 is not None
    assert c2.deleted_at is not None
    assert c2.motivo_encerramento == MotivoEncerramento.REVOGACAO_CONSENTIMENTO
    # PII anonimizada
    assert c2.nome.startswith("TITULAR_REVOGADO_")
    assert c2.email is None
    assert c2.telefone_hash is None
    assert c2.consentimento_lgpd is False
    # cpf_hash MANTEM (audit chain + unicidade)
    assert c2.cpf_hash == "abcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890"
    # Protocolo preservado (Provimento CNJ 74/2018)
    assert db_session.get(Protocolo, p.id) is not None


def test_soft_delete_preserva_multiplos_protocolos(db_session) -> None:
    """Soft delete conta TODOS os protocolos ativos (nao cancelados)."""
    c = _make_cliente(db_session)
    _make_protocolo(db_session, c.id, status="aberto", numero="2026-00001")
    _make_protocolo(db_session, c.id, status="em_andamento", numero="2026-00002")
    _make_protocolo(db_session, c.id, status="concluido", numero="2026-00003")
    db_session.commit()

    result = direito_esquecimento(db_session, c.id)

    assert result.tipo == "soft"
    # 3 ativos: ABERTO + EM_ANDAMENTO + CONCLUIDO (nao conta CANCELADO/EXPIRADO)
    assert result.protocolos_ativos == 3


# ============================================================================
# Idempotencia
# ============================================================================


def test_cliente_ja_revogado_retorna_409(db_session) -> None:
    """Cliente ja soft-deleted -> ClienteJaRevogadoError (idempotente)."""
    c = _make_cliente(db_session)
    _make_protocolo(db_session, c.id)
    direito_esquecimento(db_session, c.id)

    with pytest.raises(ClienteJaRevogadoError) as exc_info:
        direito_esquecimento(db_session, c.id)
    assert "ja revogado" in str(exc_info.value).lower()


def test_cliente_inexistente_retorna_404(db_session) -> None:
    """Cliente que nao existe -> ClienteNotFoundError."""
    with pytest.raises(ClienteNotFoundError) as exc_info:
        direito_esquecimento(db_session, cliente_id=99999)
    assert "99999" in str(exc_info.value)


# ============================================================================
# Motivo custom
# ============================================================================


def test_motivo_custom_exercicio_direito_titular(db_session) -> None:
    """Permite override do motivo (DPO pode encerrar por 'outros' razoes LGPD)."""
    c = _make_cliente(db_session)
    _make_protocolo(db_session, c.id)

    result = direito_esquecimento(
        db_session,
        c.id,
        motivo=MotivoEncerramento.EXERCICIO_DIREITO_TITULAR,
    )

    assert result.tipo == "soft"
    assert result.motivo == MotivoEncerramento.EXERCICIO_DIREITO_TITULAR
    c2 = db_session.get(Cliente, c.id)
    assert c2.motivo_encerramento == MotivoEncerramento.EXERCICIO_DIREITO_TITULAR


# ============================================================================
# Determinismo / sem side effects colaterais
# ============================================================================


def test_data_encerramento_aproximada_de_agora(db_session) -> None:
    """data_encerramento eh now() em UTC."""
    from datetime import datetime, timezone, timedelta

    c = _make_cliente(db_session)
    before = datetime.now(timezone.utc) - timedelta(seconds=1)

    result = direito_esquecimento(db_session, c.id)

    after = datetime.now(timezone.utc) + timedelta(seconds=1)
    assert before <= result.data_encerramento <= after
