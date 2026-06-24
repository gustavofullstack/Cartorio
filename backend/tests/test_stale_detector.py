"""Testes do service stale_detector.

Detecta atendimentos 'abertos' sem update ha mais de N minutos e marca como 'stale'.
Usado pelo workflow N8N #23 (cron a cada 5min).

Usa db_session fixture (SQLite in-memory) em vez de MagicMock pra que o
filtro WHERE seja respeitado de verdade.
"""

from datetime import datetime, timedelta, timezone


from app.models.atendimento import Atendimento
from app.services.stale_detector import mark_stale_atendimentos


def _make_atendimento(db, **kwargs) -> Atendimento:
    """Cria atendimento com defaults sensatos."""
    defaults = {
        "canal": "whatsapp",
        "external_id": "u1",
        "tipo": "duvida",
        "status": "em_atendimento",
    }
    defaults.update(kwargs)
    a = Atendimento(**defaults)
    db.add(a)
    db.flush()
    return a


def test_marks_old_atendimento_as_stale(db_session):
    """Atendimento com updated_at > threshold vira 'stale'."""
    old = _make_atendimento(db_session, external_id="u-old", status="em_atendimento")
    old.updated_at = datetime.now(timezone.utc) - timedelta(minutes=45)
    fresh = _make_atendimento(db_session, external_id="u-fresh", status="em_atendimento")
    fresh.updated_at = datetime.now(timezone.utc) - timedelta(minutes=5)
    db_session.commit()

    result = mark_stale_atendimentos(db_session, threshold_minutes=30)

    assert result["scanned"] == 1  # so o old foi filtrado
    assert result["marked_stale"] == 1
    db_session.refresh(old)
    db_session.refresh(fresh)
    assert old.status == "stale"
    assert fresh.status == "em_atendimento"  # nao mexemos


def test_ignores_already_concluded_atendimentos(db_session):
    """Atendimentos ja concluidos nao sao marcados como stale (ja filtrados pela query)."""
    concluded = _make_atendimento(
        db_session, external_id="u-conc", status="concluido"
    )
    concluded.updated_at = datetime.now(timezone.utc) - timedelta(hours=2)
    db_session.commit()

    result = mark_stale_atendimentos(db_session, threshold_minutes=30)

    assert result["scanned"] == 0  # concluido nao entra no WHERE
    assert result["marked_stale"] == 0
    db_session.refresh(concluded)
    assert concluded.status == "concluido"


def test_returns_zero_when_no_open_atendimentos(db_session):
    """Se nao ha atendimentos abertos, retorna zeros."""
    result = mark_stale_atendimentos(db_session, threshold_minutes=30)

    assert result["scanned"] == 0
    assert result["marked_stale"] == 0


def test_marks_all_open_status_types(db_session):
    """Todos os status em STATUS_ABERTOS sao candidatos a stale."""
    for i, status in enumerate(["aberto", "em_atendimento", "aguardando_cliente"]):
        a = _make_atendimento(db_session, external_id=f"u-{status}-{i}", status=status)
        a.updated_at = datetime.now(timezone.utc) - timedelta(minutes=60)
    db_session.commit()

    result = mark_stale_atendimentos(db_session, threshold_minutes=30)

    assert result["scanned"] == 3
    assert result["marked_stale"] == 3
