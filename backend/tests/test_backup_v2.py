"""Testes A14 — Backup V2 health check (pg_basebackup 4x/dia).

Cobre 4 cenarios exigidos pelo briefing Pietra root 2026-06-25 03:00 BRT:
1. test_backup_v2_healthy_recent (1h age)              -> 200 healthy
2. test_backup_v2_stale_8h_alert                       -> 503 stale
3. test_backup_v2_stale_25h_critical                   -> 503 critical
4. test_backup_v2_never_run_critical                   -> 503 empty

Tambem cobre:
- 5. service-level classification (sem HTTP)
- 6. endpoint retorna error quando dir nao acessivel
- 7. threshold_minutes validacao
- 8. BackupHealth Pydantic frozen (imutabilidade)

LGPD: este endpoint NAO expoe dados de cliente — apenas timestamps + paths.
"""

from __future__ import annotations

import os
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.models.base import Base
from app.services.backup_v2 import (
    DEFAULT_HEALTHY_THRESHOLD_MINUTES,
    BackupHealth,
    BackupHealthStatus,
    check_backup_v2_freshness,
)


# ============================================================================
# Fixtures (padrao test_health_backup.py)
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
    with (
        patch("app.db.engine", test_engine),
        patch("app.db.SessionLocal", test_session_factory),
        patch("app.main.engine", test_engine),
    ):
        from app.main import app

        with TestClient(app) as c:
            yield c


def _make_complete_backup(dir_path: Path, dirname: str, age_minutes: int) -> None:
    """Cria um diretorio de backup completo com marker .complete.

    Args:
        dir_path: diretorio-base (ex: tmp_path).
        dirname: nome do subdiretorio (ex: "20260625_00").
        age_minutes: idade em minutos (para calcular mtime).
    """
    full = dir_path / dirname
    full.mkdir(parents=True, exist_ok=True)
    marker = full / ".complete"
    marker.touch()
    # Ajusta mtime para refletir idade
    target_mtime = time.time() - (age_minutes * 60)
    os.utime(full, (target_mtime, target_mtime))
    os.utime(marker, (target_mtime, target_mtime))


# ============================================================================
# 1-4. Tests do briefing (TDD canon — sao os 4 obrigatorios)
# ============================================================================


def test_backup_v2_healthy_recent(client, tmp_path):
    """Backup com idade 1h (60min) -> 200 healthy.

    Cron roda 4x/dia (cada 6h), entao backup de 1h atras e fresquissimo.
    Esperado: status=healthy, 200, age_minutes ~60.
    """
    _make_complete_backup(tmp_path, "20260625_00", age_minutes=60)

    with patch("app.services.backup_v2.DEFAULT_BACKUP_DIR", str(tmp_path)):
        resp = client.get("/api/v1/health/backup-v2")

    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "healthy"
    assert data["last_backup_dir"] == "20260625_00"
    assert data["backup_count"] == 1
    assert data["last_backup_age_minutes"] is not None
    assert 59 <= data["last_backup_age_minutes"] <= 61  # ~60min com margem
    assert data["threshold_minutes"] == DEFAULT_HEALTHY_THRESHOLD_MINUTES
    assert data["alert"] is None  # healthy = sem alerta


def test_backup_v2_stale_8h_alert(client, tmp_path):
    """Backup com idade 8h (480min) -> 503 stale.

    Cron deveria ter rodado novamente em 6h, mas ultimo backup foi 8h atras.
    Esperado: status=stale, 503, age ~480min, alert presente.
    """
    _make_complete_backup(tmp_path, "20260624_18", age_minutes=480)  # 8h atras

    with patch("app.services.backup_v2.DEFAULT_BACKUP_DIR", str(tmp_path)):
        resp = client.get("/api/v1/health/backup-v2")

    assert resp.status_code == 503
    data = resp.json()
    assert data["status"] == "stale"
    assert data["last_backup_dir"] == "20260624_18"
    assert data["backup_count"] == 1
    assert 479 <= data["last_backup_age_minutes"] <= 481  # ~480min com margem
    assert data["alert"] is not None
    assert "STALE" in data["alert"]


def test_backup_v2_stale_25h_critical(client, tmp_path):
    """Backup com idade 25h (1500min) -> 503 critical.

    RPO estourado (>12h sem backup). Acao imediata necessaria.
    Esperado: status=critical, 503, age ~1500min, alert com ACAO IMEDIATA.
    """
    _make_complete_backup(tmp_path, "20260624_00", age_minutes=1500)  # 25h atras

    with patch("app.services.backup_v2.DEFAULT_BACKUP_DIR", str(tmp_path)):
        resp = client.get("/api/v1/health/backup-v2")

    assert resp.status_code == 503
    data = resp.json()
    assert data["status"] == "critical"
    assert data["last_backup_dir"] == "20260624_00"
    assert 1499 <= data["last_backup_age_minutes"] <= 1501  # ~1500min
    assert data["alert"] is not None
    assert "CRITICAL" in data["alert"]
    assert "ACAO IMEDIATA" in data["alert"]


def test_backup_v2_never_run_critical(client, tmp_path):
    """Diretorio vazio (sem nenhum marker .complete) -> 503 empty.

    Cron nunca rodou com sucesso, ou script nao instalado.
    Esperado: status=empty, 503, last_backup=None, count=0, alert presente.
    """
    # tmp_path existe mas vazio (nenhum subdiretorio)
    with patch("app.services.backup_v2.DEFAULT_BACKUP_DIR", str(tmp_path)):
        resp = client.get("/api/v1/health/backup-v2")

    assert resp.status_code == 503
    data = resp.json()
    assert data["status"] == "empty"
    assert data["last_backup_at"] is None
    assert data["last_backup_age_minutes"] is None
    assert data["last_backup_dir"] is None
    assert data["backup_count"] == 0
    assert data["alert"] is not None
    assert "VAZIO" in data["alert"] or "vazio" in data["alert"].lower()


# ============================================================================
# 5. Service-level tests (sem HTTP, logica pura)
# ============================================================================


def test_check_backup_v2_healthy_when_recent(tmp_path):
    """Service retorna BackupHealth com status=healthy para backup 1h atras."""
    _make_complete_backup(tmp_path, "20260625_00", age_minutes=60)

    health = check_backup_v2_freshness(backup_dir=str(tmp_path))

    assert health.status == BackupHealthStatus.HEALTHY
    assert health.last_backup_dir == "20260625_00"
    assert health.backup_count == 1
    assert health.last_backup_age_minutes is not None
    assert 59 <= health.last_backup_age_minutes <= 61
    assert health.alert is None
    assert health.error is None


def test_check_backup_v2_picks_most_recent_when_multiple(tmp_path):
    """Com multiplos backups, pega o MAIS RECENTE (nao o mais antigo)."""
    _make_complete_backup(tmp_path, "20260625_00", age_minutes=30)  # mais recente
    _make_complete_backup(tmp_path, "20260624_18", age_minutes=720)  # 12h atras
    _make_complete_backup(tmp_path, "20260624_12", age_minutes=1080)  # 18h atras

    health = check_backup_v2_freshness(backup_dir=str(tmp_path))

    assert health.status == BackupHealthStatus.HEALTHY
    assert health.last_backup_dir == "20260625_00"
    assert health.backup_count == 3  # todos contados


def test_check_backup_v2_ignores_incomplete_backups(tmp_path):
    """Diretorio sem marker .complete eh ignorado (backup em andamento)."""
    # Backup completo
    _make_complete_backup(tmp_path, "20260625_00", age_minutes=30)

    # Backup em andamento (sem marker .complete)
    incomplete = tmp_path / "20260625_06"
    incomplete.mkdir(parents=True, exist_ok=True)
    # NAO cria marker

    health = check_backup_v2_freshness(backup_dir=str(tmp_path))

    # So conta o completo; status continua healthy
    assert health.status == BackupHealthStatus.HEALTHY
    assert health.last_backup_dir == "20260625_00"
    assert health.backup_count == 1


def test_check_backup_v2_threshold_validation():
    """threshold_minutes < 1 levanta ValueError."""
    with pytest.raises(ValueError, match="threshold_minutes deve ser >= 1"):
        check_backup_v2_freshness(backup_dir="/tmp/nonexistent", threshold_minutes=0)


def test_check_backup_v2_uses_now_override_for_deterministic(tmp_path):
    """Parametro `now` permite testes deterministicos sem time.time()."""
    _make_complete_backup(tmp_path, "20260625_00", age_minutes=0)  # agora

    # Override now para 2h depois do mtime
    future = datetime.now(tz=timezone.utc) + timedelta(hours=2)
    health = check_backup_v2_freshness(backup_dir=str(tmp_path), now=future)

    # 2h = 120min, ainda < 360 (threshold healthy), entao healthy
    assert health.status == BackupHealthStatus.HEALTHY
    assert health.last_backup_age_minutes is not None
    assert 119 <= health.last_backup_age_minutes <= 121


def test_check_backup_v2_directory_not_accessible(tmp_path):
    """Quando diretorio nao existe (sem volume mount) -> empty com error."""
    nonexistent = tmp_path / "does_not_exist"

    health = check_backup_v2_freshness(backup_dir=str(nonexistent))

    assert health.status == BackupHealthStatus.EMPTY
    assert health.backup_count == 0
    assert health.alert is not None
    assert "VAZIO" in health.alert


# ============================================================================
# 6. Pydantic model tests
# ============================================================================


def test_backup_health_frozen():
    """BackupHealth eh frozen (imutavel) — protege contra mutacao acidental."""
    health = BackupHealth(
        status=BackupHealthStatus.HEALTHY,
        threshold_minutes=360,
        backup_dir="/tmp",
    )

    with pytest.raises(Exception):  # ValidationError do Pydantic
        health.status = BackupHealthStatus.CRITICAL  # type: ignore[misc]


def test_backup_health_serialization_roundtrip():
    """BackupHealth -> dict -> JSON -> BackupHealth preserva dados."""
    original = BackupHealth(
        status=BackupHealthStatus.STALE,
        last_backup_at=datetime(2026, 6, 25, 12, 0, tzinfo=timezone.utc),
        last_backup_age_minutes=400,
        last_backup_dir="20260625_06",
        backup_count=2,
        threshold_minutes=360,
        backup_dir="/var/backups/cartorio/pgbase",
        error=None,
        alert="STALE test",
    )

    dumped = original.model_dump()
    restored = BackupHealth(**dumped)

    assert restored.status == original.status
    assert restored.last_backup_dir == original.last_backup_dir
    assert restored.backup_count == original.backup_count
    assert restored.alert == original.alert


# ============================================================================
# 9. Test briefing A14 verify-and-close — backup recente (<26h) = ok=true
# ============================================================================


def test_backup_recent_under_26h_returns_ok_true(client, tmp_path):
    """Backup com idade 20h (1200min) ainda eh saudavel via v1 endpoint.

    Briefing A14 verify-and-close 2026-06-25: adicionar 1 teste para garantir
    que backup RECENTE (sub-26h, mesmo acima do threshold v2 de 360min)
    ainda eh considerado ok=true pelo endpoint legado /health/backup (v1).
    Isso protege contra regressao no endpoint legado apos mudancas em v2.
    """
    # v1 (legacy) endpoint checa .tar.gz no /var/backups/cartorio (raiz)
    # enquanto v2 checa /var/backups/cartorio/pgbase/<DIR>/.complete.
    # Para este teste, mockamos os.path.isdir / os.listdir do router v1.
    import time as time_mod

    now_ts = time_mod.time()
    backup_age_s = 20 * 3600  # 20h atras (sub-26h)
    backup_ts = now_ts - backup_age_s

    fake_listing = ["backup-2026-06-25.tar.gz"]

    with (
        patch("app.api.v1.router.os.path.isdir", return_value=True),
        patch("app.api.v1.router.os.listdir", return_value=fake_listing),
        patch("app.api.v1.router.os.path.getmtime", return_value=backup_ts),
        patch("app.api.v1.router.os.path.getsize", return_value=100 * 1024 * 1024),
    ):
        resp = client.get("/api/v1/health/backup")

    assert resp.status_code == 200
    data = resp.json()
    assert data["ok"] is True
    assert data["last_backup_age_hours"] is not None
    # 20h < 26h => ok=true
    assert data["last_backup_age_hours"] < 26.0
    assert 19.0 <= data["last_backup_age_hours"] <= 21.0


def test_backup_v2_updates_prometheus_metric(client, tmp_path):
    """A14 verify-and-close: endpoint /health/backup-v2 atualiza metrica Prometheus.

    Verifica que `backup_last_success_timestamp_seconds` eh setado com
    Unix epoch do ultimo backup (ou 0 para cold-start).
    """
    from app.services.metrics import store as metrics_store

    # Backup recente (1h atras) — metrica deve refletir mtime do diretorio
    _make_complete_backup(tmp_path, "20260625_00", age_minutes=60)
    expected_ts = time.time() - (60 * 60)

    with patch("app.services.backup_v2.DEFAULT_BACKUP_DIR", str(tmp_path)):
        resp = client.get("/api/v1/health/backup-v2")

    assert resp.status_code == 200
    # Metrica deve estar setada (valor aproximado, margem 5s)
    gauge = metrics_store.gauges.get("backup_last_success_timestamp_seconds")
    assert gauge is not None, "Gauge backup_last_success_timestamp_seconds nao foi setada"
    assert isinstance(gauge, float)
    # Margem de 5s para cobrir latencia entre mtime set e leitura
    assert abs(gauge - expected_ts) < 5.0, f"Gauge {gauge} != expected ~{expected_ts} (margem 5s)"

    # Cold-start: sem nenhum backup -> metrica = 0
    empty_dir = tmp_path / "empty"
    empty_dir.mkdir()
    with patch("app.services.backup_v2.DEFAULT_BACKUP_DIR", str(empty_dir)):
        resp = client.get("/api/v1/health/backup-v2")
    assert resp.status_code == 503
    gauge_empty = metrics_store.gauges.get("backup_last_success_timestamp_seconds")
    assert gauge_empty == 0.0, f"Cold-start gauge deveria ser 0.0, recebeu {gauge_empty}"
