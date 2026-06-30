"""E1.S4.T1 - Fix WF #15 Session Sync (Sprint 3 follow-up).

WF #15 (Session Sync) chamava GET /sessao/list-active + POST /sessao/sync.
Ambos endpoints NAO EXISTEM no backend (404).

Surgical fix:
- GET /atendimento/list-active?since_hours=24 -> lista sessoes ativas
  (read-only, le 'conversa' table com filtro updated_at)
- POST /sessao/sync -> REMOVIDO do WF #15 (sync pode ser job in-process)

LGPD: 0 review (read-only, sem nova PII exposta - retorna external_id que ja eh
o telefone ja conhecido e armazenado em conversa).

Cobertura:
- Sem conversa: retorna lista vazia
- Conversa recente (< 24h): retorna 1 sessao
- Conversa velha (>= 24h): NAO retorna
- Filtro since_hours customizado: aplica
- Multi-canal (whatsapp + telegram): agrupa certo
"""

from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.models.base import Base
from app.models.conversa import Conversa


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def test_engine():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    yield engine
    Base.metadata.drop_all(engine)


@pytest.fixture
def test_session_factory(test_engine):
    return sessionmaker(bind=test_engine, autoflush=False, autocommit=False)


@pytest.fixture
def client(test_engine, test_session_factory):
    @contextmanager
    def test_session_scope():
        s = test_session_factory()
        try:
            yield s
            s.commit()
        except Exception:
            s.rollback()
            raise
        finally:
            s.close()

    with (
        patch("app.db.engine", test_engine),
        patch("app.db.SessionLocal", test_session_factory),
        patch("app.db.session_scope", test_session_scope),
        patch("app.api.v1.router.session_scope", test_session_scope),
        patch("app.main.engine", test_engine),
    ):
        from app.main import app

        with TestClient(app) as c:
            yield c


def _insert_conversa(db_session_factory, external_id: str, canal: str, hours_ago: float) -> None:
    """Insere conversa com updated_at = now - hours_ago.

    ORM bypass: usa UPDATE raw no ID especifico para forcar updated_at,
    ja que TimestampMixin tem onupdate=datetime.utcnow que sobrescreve
    valores setados via ORM.
    """
    from sqlalchemy import text

    with db_session_factory() as db:
        conversa = Conversa(
            canal=canal,
            external_id=external_id,
            raw_message_hash="abc" + external_id + str(hours_ago),
            raw_message_scrubbed="Ola",
        )
        db.add(conversa)
        db.commit()
        conversa_id = conversa.id
        # Forca updated_at com raw SQL bypassando o onupdate hook do ORM
        target_ts = datetime.now(timezone.utc) - timedelta(hours=hours_ago)
        db.execute(
            text("UPDATE conversas SET updated_at = :ts WHERE id = :cid"),
            {"ts": target_ts.replace(tzinfo=None), "cid": conversa_id},
        )
        db.commit()


# ============================================================================
# Tests TDD (RED - antes do fix)
# ============================================================================


def test_list_active_sem_conversa(client):
    """Sem conversa -> retorna lista vazia."""
    resp = client.get("/api/v1/atendimento/list-active?since_hours=24")
    assert resp.status_code == 200
    data = resp.json()
    assert data["count"] == 0
    assert data["sessions"] == []


def test_list_active_com_conversa_recente(client, test_session_factory):
    """Conversa atualizada 1h atras -> retorna 1 sessao."""
    _insert_conversa(test_session_factory, "5534999999999", "whatsapp", hours_ago=1.0)

    resp = client.get("/api/v1/atendimento/list-active?since_hours=24")
    assert resp.status_code == 200
    data = resp.json()
    assert data["count"] == 1
    assert len(data["sessions"]) == 1
    s = data["sessions"][0]
    assert s["external_id"] == "5534999999999"
    assert s["canal"] == "whatsapp"
    assert "last_activity" in s


def test_list_active_exclui_conversa_velha(client, test_session_factory):
    """Conversa atualizada 30h atras com since_hours=24 -> NAO retorna."""
    _insert_conversa(test_session_factory, "5534888888888", "whatsapp", hours_ago=30.0)

    resp = client.get("/api/v1/atendimento/list-active?since_hours=24")
    assert resp.status_code == 200
    data = resp.json()
    assert data["count"] == 0
    assert data["sessions"] == []


def test_list_active_filtro_customizado(client, test_session_factory):
    """since_hours=48 inclui conversa de 30h atras."""
    _insert_conversa(test_session_factory, "5534777777777", "whatsapp", hours_ago=30.0)

    resp = client.get("/api/v1/atendimento/list-active?since_hours=48")
    assert resp.status_code == 200
    data = resp.json()
    assert data["count"] == 1
    assert data["sessions"][0]["external_id"] == "5534777777777"


def test_list_active_multi_canal_agupa_por_sender(client, test_session_factory):
    """Mesmo external_id em 2 canais -> 2 sessoes (uma por canal)."""
    _insert_conversa(test_session_factory, "5534666666666", "whatsapp", hours_ago=1.0)
    _insert_conversa(test_session_factory, "5534666666666", "telegram", hours_ago=2.0)

    resp = client.get("/api/v1/atendimento/list-active?since_hours=24")
    assert resp.status_code == 200
    data = resp.json()
    assert data["count"] == 2
    canais = {s["canal"] for s in data["sessions"]}
    assert canais == {"whatsapp", "telegram"}


def test_list_active_multi_conversa_mesma_sessao(client, test_session_factory):
    """3 conversas do mesmo sender -> 1 sessao (dedup por external_id+canal)."""
    for hours in [0.5, 1.0, 2.0]:
        _insert_conversa(test_session_factory, "5534555555555", "whatsapp", hours_ago=hours)

    # Debug removed
    resp = client.get("/api/v1/atendimento/list-active?since_hours=24")
    assert resp.status_code == 200
    data = resp.json()
    # 1 sessao (dedup), com last_activity = mais recente
    assert data["count"] == 1
    s = data["sessions"][0]
    assert s["external_id"] == "5534555555555"
    # last_activity deve ser a conversa mais recente (0.5h atras).
    # Conversa.updated_at eh naive datetime (SQLite default) — assume UTC.
    last_act_str = s["last_activity"].replace("Z", "+00:00")
    last_act = datetime.fromisoformat(last_act_str)
    if last_act.tzinfo is None:
        last_act = last_act.replace(tzinfo=timezone.utc)
    age_minutes = (datetime.now(timezone.utc) - last_act).total_seconds() / 60
    assert 20 <= age_minutes <= 40  # margem de 10min para 0.5h atras
