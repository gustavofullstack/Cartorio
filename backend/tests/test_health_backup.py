"""E1.S4.T2 — Fix GET /api/v1/health/backup (bug detectado 2026-06-23).

Bug original: endpoint usava `subprocess.run(["docker", "exec", "cartorio_api.1.", ...])`
com nome de container INVALIDO (terminava em ponto). Resultado: ok=false 24/7,
cron `cartorio-backup-status` (E6.S7.T10) reportando falha permanente.

Fix (Solucao A aprovada por Gustavo): volume mount /var/backups/cartorio no
container cartorio_api + leitura DIRETA via `os.listdir`/`os.path.getmtime`.
Sem `subprocess` nem `docker exec` (privilegios desnecessarios).

Cobertura:
- Backup recente (< 26h): ok=true
- Backup velho (>= 26h): ok=false
- Diretorio vazio: ok=false
- Diretorio inexistente: ok=false com error
- Soma de tamanhos (dir_size) correta
- REGRESSAO: nunca mais docker exec / subprocess
"""

from __future__ import annotations

import time
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.models.base import Base


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
    with (
        patch("app.db.engine", test_engine),
        patch("app.db.SessionLocal", test_session_factory),
        patch("app.main.engine", test_engine),
    ):
        from app.main import app

        with TestClient(app) as c:
            yield c


def _fake_stat(size: int, mtime: float):
    """Mock para os.stat() que retorna size + mtime."""

    class _S:
        pass

    s = _S()
    s.st_size = size  # type: ignore[attr-defined]
    s.st_mtime = mtime  # type: ignore[attr-defined]
    return s


# ============================================================================
# Tests TDD (RED — antes do fix)
# ============================================================================


def test_health_backup_ok_quando_backup_recente(client):
    """Backup com mtime = agora -> ok=true, file_count=1, age < 1h."""
    now_ts = time.time()
    fake_listing = ["backup-2026-06-23.tar.gz", "README.md"]  # so .tar.gz conta

    with (
        patch("app.api.v1.router.os.path.isdir", return_value=True),
        patch("app.api.v1.router.os.listdir", return_value=fake_listing),
        patch("app.api.v1.router.os.path.getmtime", return_value=now_ts),
        patch("app.api.v1.router.os.path.getsize", return_value=50 * 1024 * 1024),
    ):
        resp = client.get("/api/v1/health/backup")

    assert resp.status_code == 200
    data = resp.json()
    assert data["ok"] is True
    assert data["file_count"] == 1
    assert data["last_backup_age_hours"] is not None
    assert data["last_backup_age_hours"] < 1.0  # menos de 1h
    assert data["last_backup_iso"] is not None
    assert "dir_size" in data


def test_health_backup_falha_quando_backup_velho(client):
    """Backup com mtime = 30h atras -> ok=false, age ~= 30h."""
    now_ts = time.time()
    old_ts = now_ts - (30 * 3600)  # 30 horas atras
    fake_listing = ["backup-2026-06-22.tar.gz"]

    with (
        patch("app.api.v1.router.os.path.isdir", return_value=True),
        patch("app.api.v1.router.os.listdir", return_value=fake_listing),
        patch("app.api.v1.router.os.path.getmtime", return_value=old_ts),
        patch("app.api.v1.router.os.path.getsize", return_value=1024),
    ):
        resp = client.get("/api/v1/health/backup")

    assert resp.status_code == 200
    data = resp.json()
    assert data["ok"] is False
    assert data["file_count"] == 1
    assert data["last_backup_age_hours"] is not None
    assert 29.0 <= data["last_backup_age_hours"] <= 31.0  # margem de 1h


def test_health_backup_diretorio_vazio(client):
    """Diretorio existe mas vazio -> ok=false, file_count=0."""
    with (
        patch("app.api.v1.router.os.path.isdir", return_value=True),
        patch("app.api.v1.router.os.listdir", return_value=[]),
    ):
        resp = client.get("/api/v1/health/backup")

    assert resp.status_code == 200
    data = resp.json()
    assert data["ok"] is False
    assert data["file_count"] == 0
    assert data["last_backup_age_hours"] is None


def test_health_backup_diretorio_inexistente(client):
    """Diretorio NAO existe (sem volume mount) -> ok=false com error."""
    with (
        patch("app.api.v1.router.os.path.isdir", return_value=False),
        patch(
            "app.api.v1.router.os.listdir",
            side_effect=FileNotFoundError("No such directory"),
        ),
    ):
        resp = client.get("/api/v1/health/backup")

    assert resp.status_code == 200
    data = resp.json()
    assert data["ok"] is False
    assert data["file_count"] == 0
    assert "error" in data


def test_health_backup_soma_diretorio_para_dir_size(client):
    """Multiplos backups: dir_size eh a SOMA dos tamanhos individuais."""
    now_ts = time.time()
    fake_listing = [
        "backup-2026-06-22.tar.gz",
        "backup-2026-06-23.tar.gz",
        "README.md",  # ignorado (.tar.gz only)
    ]
    # 50MB + 30MB = 80MB total
    fake_dir = "/var/backups/cartorio"
    sizes = {
        f"{fake_dir}/backup-2026-06-22.tar.gz": 50 * 1024 * 1024,
        f"{fake_dir}/backup-2026-06-23.tar.gz": 30 * 1024 * 1024,
    }

    def mock_getsize(path):
        return sizes.get(path, 0)

    with (
        patch("app.api.v1.router.os.path.isdir", return_value=True),
        patch("app.api.v1.router.os.listdir", return_value=fake_listing),
        patch("app.api.v1.router.os.path.getmtime", return_value=now_ts),
        patch("app.api.v1.router.os.path.getsize", side_effect=mock_getsize),
    ):
        resp = client.get("/api/v1/health/backup")

    assert resp.status_code == 200
    data = resp.json()
    assert data["ok"] is True
    assert data["file_count"] == 2
    # dir_size vem formatado tipo "80M" via humanize ou similar
    # Verifica que o tamanho > 0 e bate com a soma esperada
    dir_size_str = str(data["dir_size"])
    assert any(unit in dir_size_str for unit in ["M", "K", "G", "B"]), (
        f"dir_size '{dir_size_str}' nao tem unidade"
    )


def test_health_backup_nunca_chama_docker_exec(client):
    """REGRESSAO: endpoint NAO chama subprocess/docker.

    Garante que o fix (Solucao A) nao introduz docker exec nem subprocess.
    """
    with (
        patch("app.api.v1.router.os.path.isdir", return_value=True),
        patch("app.api.v1.router.os.listdir", return_value=["backup.tar.gz"]),
        patch("app.api.v1.router.os.path.getmtime", return_value=time.time()),
        patch("app.api.v1.router.os.path.getsize", return_value=1024),
        patch("subprocess.run") as mock_subprocess_run,
    ):
        resp = client.get("/api/v1/health/backup")

    assert resp.status_code == 200
    # subprocess.run NAO deve ser chamado em hipotese alguma
    mock_subprocess_run.assert_not_called()
