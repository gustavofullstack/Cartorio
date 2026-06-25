"""Testes do service de query de Protocolos (usado pelo N8N workflow #25)."""
from __future__ import annotations

import os

os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("AUDIT_HMAC_KEY", "a" * 64)
os.environ.setdefault("CHATWOOT_ACCOUNT_ID", "0")
os.environ.setdefault("CHATWOOT_INBOX_ID", "0")
os.environ.setdefault("CARTORIO_API_KEY", "a" * 64)

from app.config import get_settings  # noqa: E402

get_settings.cache_clear()

from datetime import datetime, timedelta, timezone  # noqa: E402

import pytest  # noqa: E402
from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402

from app.models.base import Base  # noqa: E402
from app.models.cliente import Cliente  # noqa: E402
from app.models.protocolo import Protocolo  # noqa: E402
from app.services.protocolo_query import (  # noqa: E402
    listar_protocolos_recentes_concluidos,
)


@pytest.fixture
def db_session():
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


def _make_cliente(db, nome: str = "Joao da Silva") -> Cliente:
    c = Cliente(
        cpf_hash=f"hash_{nome[:5]}",
        nome=nome,
        consentimento_lgpd=True,
    )
    db.add(c)
    db.commit()
    db.refresh(c)
    return c


def _make_protocolo(
    db,
    cliente_id: int,
    numero: str,
    status: str = "concluido",
    updated_at: datetime | None = None,
) -> Protocolo:
    p = Protocolo(
        cliente_id=cliente_id,
        numero=numero,
        tipo="escritura_compra_venda",
        status=status,
        canal_origem="whatsapp",
        valor_base=350.00,
        valor_total=385.00,
        updated_at=updated_at,
    )
    db.add(p)
    db.commit()
    db.refresh(p)
    return p


# ============================================================================
# Sanidade
# ============================================================================


def test_lista_vazia_sem_concluidos(db_session) -> None:
    """Sem protocolos, retorna lista vazia."""
    result = listar_protocolos_recentes_concluidos(db_session, minutos=10)
    assert result == []


def test_lista_1_concluido_recente(db_session) -> None:
    """1 protocolo concluido agora -> retorna 1 item."""
    cliente = _make_cliente(db_session)
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    _make_protocolo(db_session, cliente.id, "2026-00001", "concluido", updated_at=now)

    result = listar_protocolos_recentes_concluidos(db_session, minutos=10)

    assert len(result) == 1
    assert result[0].numero == "2026-00001"
    assert result[0].status == "concluido"
    assert result[0].cliente_nome == "Joao da Silva"


# ============================================================================
# Filtros
# ============================================================================


def test_exclui_protocolo_nao_concluido(db_session) -> None:
    """Protocolo com status != concluido NAO aparece."""
    cliente = _make_cliente(db_session)
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    _make_protocolo(db_session, cliente.id, "2026-00001", "em_andamento", updated_at=now)
    _make_protocolo(db_session, cliente.id, "2026-00002", "aberto", updated_at=now)
    _make_protocolo(db_session, cliente.id, "2026-00003", "concluido", updated_at=now)

    result = listar_protocolos_recentes_concluidos(db_session, minutos=10)

    assert len(result) == 1
    assert result[0].numero == "2026-00003"


def test_exclui_concluido_antigo_fora_da_janela(db_session) -> None:
    """Protocolo concluido ha 2h NAO aparece em janela de 10min."""
    cliente = _make_cliente(db_session)
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    old = now - timedelta(hours=2)
    _make_protocolo(db_session, cliente.id, "2026-OLD", "concluido", updated_at=old)
    _make_protocolo(db_session, cliente.id, "2026-NEW", "concluido", updated_at=now)

    result = listar_protocolos_recentes_concluidos(db_session, minutos=10)

    assert len(result) == 1
    assert result[0].numero == "2026-NEW"


def test_exclui_cancelado_e_expirado(db_session) -> None:
    """Protocolo cancelado/expirado NAO aparece mesmo se recent."""
    cliente = _make_cliente(db_session)
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    _make_protocolo(db_session, cliente.id, "2026-CXL", "cancelado", updated_at=now)
    _make_protocolo(db_session, cliente.id, "2026-EXP", "expirado", updated_at=now)
    _make_protocolo(db_session, cliente.id, "2026-DONE", "concluido", updated_at=now)

    result = listar_protocolos_recentes_concluidos(db_session, minutos=10)

    assert len(result) == 1
    assert result[0].numero == "2026-DONE"


# ============================================================================
# Ordenacao
# ============================================================================


def test_ordenado_por_updated_at_desc(db_session) -> None:
    """Mais recente primeiro."""
    cliente = _make_cliente(db_session)
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    _make_protocolo(db_session, cliente.id, "2026-OLDEST", "concluido", updated_at=now - timedelta(minutes=8))
    _make_protocolo(db_session, cliente.id, "2026-NEWEST", "concluido", updated_at=now - timedelta(seconds=10))
    _make_protocolo(db_session, cliente.id, "2026-MID", "concluido", updated_at=now - timedelta(minutes=4))

    result = listar_protocolos_recentes_concluidos(db_session, minutos=10)

    numeros = [r.numero for r in result]
    assert numeros == ["2026-NEWEST", "2026-MID", "2026-OLDEST"]


# ============================================================================
# Paginacao
# ============================================================================


def test_limit_respeitado(db_session) -> None:
    """Limit funciona."""
    cliente = _make_cliente(db_session)
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    for i in range(10):
        _make_protocolo(db_session, cliente.id, f"2026-{i:03d}", "concluido", updated_at=now - timedelta(seconds=i))

    result = listar_protocolos_recentes_concluidos(db_session, minutos=10, limit=3)

    assert len(result) == 3


# ============================================================================
# to_dict (compatibilidade N8N)
# ============================================================================


def test_to_dict_tem_campos_esperados(db_session) -> None:
    """to_dict retorna dict compativel com JSON do N8N."""
    cliente = _make_cliente(db_session, "Maria Souza")
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    _make_protocolo(db_session, cliente.id, "2026-00001", "concluido", updated_at=now)

    result = listar_protocolos_recentes_concluidos(db_session, minutos=10)
    d = result[0].to_dict()

    assert d["id"] == 1
    assert d["numero"] == "2026-00001"
    assert d["status"] == "concluido"
    assert d["tipo"] == "escritura_compra_venda"
    assert d["valor_total"] == 385.00
    assert d["canal_origem"] == "whatsapp"
    assert d["cliente"]["nome"] == "Maria Souza"
    assert d["concluido_em"] is not None


# ============================================================================
# Edge case
# ============================================================================


def test_janela_zero_minutos_retorna_apenas_concluido_no_instante(db_session) -> None:
    """minutos=0 eh caso edge - depende do timestamp exato.

    Implementacao atual: cutoff = now - 0 = now. Protocolo com updated_at == now
    eh included, com updated_at < now nao.
    """
    cliente = _make_cliente(db_session)
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    _make_protocolo(db_session, cliente.id, "2026-00001", "concluido", updated_at=now)
    # 10s atras NAO entra
    _make_protocolo(db_session, cliente.id, "2026-00002", "concluido", updated_at=now - timedelta(seconds=10))

    result = listar_protocolos_recentes_concluidos(db_session, minutos=0, limit=10)

    # Como o now do test e o now do service sao diferentes (microsegundos),
    # pode dar 0 ou 1. Validamos apenas que nao inclui o de 10s atras.
    numeros = [r.numero for r in result]
    assert "2026-00002" not in numeros, "protocolo de 10s atras nao deveria aparecer"
