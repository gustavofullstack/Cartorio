"""Testes do servico de query do audit log."""
from __future__ import annotations

import os

os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("AUDIT_HMAC_KEY", "a" * 64)

from app.config import get_settings  # noqa: E402

get_settings.cache_clear()

from datetime import datetime, timedelta  # noqa: E402

import pytest  # noqa: E402
from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402

from app.models.audit_log import AuditLog  # noqa: E402
from app.models.base import Base  # noqa: E402
from app.schemas.audit import AuditLogFilter  # noqa: E402
from app.services.audit import AuditService  # noqa: E402
from app.services.audit_query import get_audit_log_by_id, list_audit_logs  # noqa: E402


@pytest.fixture
def db_session():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    S = sessionmaker(bind=engine)
    session = S()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(engine)


def _log(
    db,
    *,
    actor_id: str = "escrevente-1",
    actor_type: str = "escrevente",
    action: str = "cliente.delete.soft",
    resource: str = "cliente:42",
    canal: str = "web",
) -> AuditLog:
    """Helper que cria 1 entry via AuditService (gera hash chain real)."""
    return AuditService.log(
        db,
        actor_id=actor_id,
        actor_type=actor_type,
        action=action,
        resource=resource,
        payload={"test": True},
        ip="203.0.113.7",
        user_agent="Cartorio/0.5.1",
        request_id="trace-abc",
        canal=canal,
    )


# ============================================================================
# Sanidade
# ============================================================================


def test_lista_audit_vazio(db_session) -> None:
    """Sem entries, retorna lista vazia + total=0."""
    result = list_audit_logs(db_session, AuditLogFilter())
    assert result.items == []
    assert result.total == 0
    assert result.page == 1
    assert result.page_size == 50
    assert result.has_next is False


def test_lista_1_entry(db_session) -> None:
    """Com 1 entry, retorna 1 item + total=1 + has_next=False."""
    _log(db_session)
    result = list_audit_logs(db_session, AuditLogFilter())
    assert result.total == 1
    assert len(result.items) == 1
    assert result.has_next is False
    # Verifica campos populados
    item = result.items[0]
    assert item.actor_id == "escrevente-1"
    assert item.action == "cliente.delete.soft"
    assert item.canal == "web"
    assert item.ip == "203.0.113.7"


# ============================================================================
# Filtros
# ============================================================================


def test_filtro_por_actor_id(db_session) -> None:
    """Filtro actor_id retorna apenas entries daquele ator."""
    _log(db_session, actor_id="escrevente-1")
    _log(db_session, actor_id="escrevente-2")
    _log(db_session, actor_id="bot-1")

    result = list_audit_logs(
        db_session, AuditLogFilter(actor_id="escrevente-1")
    )
    assert result.total == 1
    assert result.items[0].actor_id == "escrevente-1"


def test_filtro_por_actor_type(db_session) -> None:
    """Filtro actor_type retorna apenas aquele tipo."""
    _log(db_session, actor_id="e1", actor_type="escrevente")
    _log(db_session, actor_id="e2", actor_type="escrevente")
    _log(db_session, actor_id="b1", actor_type="bot")
    _log(db_session, actor_id="s1", actor_type="system")

    result = list_audit_logs(
        db_session, AuditLogFilter(actor_type="escrevente")
    )
    assert result.total == 2


def test_filtro_por_action_prefix(db_session) -> None:
    """Filtro action_prefix retorna todos que comecam com o prefixo."""
    _log(db_session, action="cliente.delete.soft")
    _log(db_session, action="cliente.delete.hard")
    _log(db_session, action="protocolo.create")
    _log(db_session, action="cliente.update")

    result = list_audit_logs(
        db_session, AuditLogFilter(action_prefix="cliente.delete")
    )
    assert result.total == 2
    actions = {item.action for item in result.items}
    assert actions == {"cliente.delete.soft", "cliente.delete.hard"}


def test_filtro_por_resource(db_session) -> None:
    """Filtro resource exato."""
    _log(db_session, resource="cliente:42")
    _log(db_session, resource="cliente:99")
    _log(db_session, resource="protocolo:2026-00001")

    result = list_audit_logs(
        db_session, AuditLogFilter(resource="cliente:42")
    )
    assert result.total == 1
    assert result.items[0].resource == "cliente:42"


def test_filtro_por_canal(db_session) -> None:
    """Filtro canal retorna apenas entries daquele canal."""
    _log(db_session, canal="whatsapp")
    _log(db_session, canal="whatsapp")
    _log(db_session, canal="cron")
    _log(db_session, canal="web")

    result = list_audit_logs(
        db_session, AuditLogFilter(canal="whatsapp")
    )
    assert result.total == 2


def test_filtro_por_periodo(db_session) -> None:
    """Filtro since/until retorna entries no periodo.

    Cria 3 entries com timestamps forçados via update para garantir
    separacao suficiente entre eles (microsegundos nao eh confiavel).
    """
    e1 = _log(db_session)
    e2 = _log(db_session)
    e3 = _log(db_session)
    db_session.commit()

    # Forca timestamps bem separados (1h entre cada)
    from datetime import timezone

    base = datetime(2026, 6, 1, 10, 0, 0, tzinfo=timezone.utc).replace(tzinfo=None)
    db_session.query(AuditLog).filter(AuditLog.id == e1.id).update(
        {"timestamp": base}
    )
    db_session.query(AuditLog).filter(AuditLog.id == e2.id).update(
        {"timestamp": base + timedelta(hours=1)}
    )
    db_session.query(AuditLog).filter(AuditLog.id == e3.id).update(
        {"timestamp": base + timedelta(hours=2)}
    )
    db_session.commit()

    # Filtra apenas o que esta entre e1+30min e e2+30min (apenas e2)
    since = base + timedelta(minutes=30)
    until = base + timedelta(minutes=90)
    result = list_audit_logs(
        db_session,
        AuditLogFilter(since=since, until=until),
    )
    assert result.total == 1
    assert result.items[0].id == e2.id


def test_filtro_since_apenas(db_session) -> None:
    """Filtro sem until retorna tudo >= since."""
    e1 = _log(db_session)
    _log(db_session)
    _log(db_session)
    db_session.commit()

    from datetime import timezone

    base = datetime(2026, 6, 1, 10, 0, 0, tzinfo=timezone.utc).replace(tzinfo=None)
    db_session.query(AuditLog).filter(AuditLog.id == e1.id).update(
        {"timestamp": base}
    )
    db_session.commit()

    result = list_audit_logs(
        db_session,
        AuditLogFilter(since=base + timedelta(hours=1)),
    )
    assert result.total == 2  # e2 e e3 (depois de e1)


# ============================================================================
# Paginacao
# ============================================================================


def test_paginacao_basica(db_session) -> None:
    """page=1, page_size=2 retorna 2 items, has_next=True quando ha mais."""
    for i in range(5):
        _log(db_session, resource=f"cliente:{i}")

    result = list_audit_logs(
        db_session, AuditLogFilter(page=1, page_size=2)
    )
    assert result.total == 5
    assert len(result.items) == 2
    assert result.page == 1
    assert result.page_size == 2
    assert result.has_next is True


def test_paginacao_ultima_pagina(db_session) -> None:
    """Ultima pagina retorna items restantes + has_next=False."""
    for i in range(5):
        _log(db_session, resource=f"cliente:{i}")

    result = list_audit_logs(
        db_session, AuditLogFilter(page=3, page_size=2)
    )
    assert result.total == 5
    assert len(result.items) == 1  # 3a pagina tem 5 - 2*2 = 1 item
    assert result.has_next is False


def test_paginacao_fora_do_range(db_session) -> None:
    """Page muito alta retorna items vazios, has_next=False."""
    for i in range(3):
        _log(db_session)

    result = list_audit_logs(
        db_session, AuditLogFilter(page=10, page_size=10)
    )
    assert result.total == 3
    assert result.items == []
    assert result.has_next is False


def test_page_size_validacao() -> None:
    """page_size > 200 deve falhar (limite do Pydantic)."""
    with pytest.raises(ValueError):
        AuditLogFilter(page_size=500)


# ============================================================================
# Get by ID
# ============================================================================


def test_get_audit_log_by_id_existente(db_session) -> None:
    e = _log(db_session, action="test.action")
    db_session.commit()

    result = get_audit_log_by_id(db_session, e.id)
    assert result is not None
    assert result.id == e.id
    assert result.action == "test.action"


def test_get_audit_log_by_id_inexistente(db_session) -> None:
    result = get_audit_log_by_id(db_session, 99999)
    assert result is None


# ============================================================================
# Ordenacao
# ============================================================================


def test_ordenacao_desc_timestamp(db_session) -> None:
    """Mais recente primeiro (DESC por timestamp)."""
    e1 = _log(db_session)
    e2 = _log(db_session)
    e3 = _log(db_session)
    db_session.commit()

    result = list_audit_logs(db_session, AuditLogFilter())
    # Ultimo criado = primeiro da lista
    assert result.items[0].id == e3.id
    assert result.items[1].id == e2.id
    assert result.items[2].id == e1.id
