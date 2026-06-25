"""TDD tests E1.S4.T2 - Fix endpoint /api/v1/health/backup.

PROBLEMA: O endpoint tenta ler /var/backups/cartorio DIRETAMENTE no container
cartorio_api, mas esse path NAO esta montado (volume mount nunca foi feito).
Resultado: retorna SEMPRE ok=false.

SOLUCAO (Escolha C do MEMORY 162-165): backup.sh escreve JSON metadata em
/var/log/cartorio-backup-status.json ao terminar OK. O endpoint le esse JSON
como source-of-truth. Se JSON nao existir, fallback tenta o path local.

ESTRUTURA DO JSON (escrita por backup.sh ao terminar):
{
  "last_backup_iso": "2026-06-24T03:00:00Z",
  "last_backup_filename": "cartorio_backup_20260624_030000.tar.gz",
  "last_backup_size_bytes": 958000,
  "last_backup_age_hours": 14.2,
  "backup_count_7d": 7,
  "ok": true,
  "updated_at": "2026-06-25T16:30:00Z"
}

Cenarios:
1. JSON existe e ok=true -> retorna ok=true com dados do JSON
2. JSON existe e ok=false (backup stale > 26h) -> retorna ok=false + last_backup_age_hours
3. JSON nao existe + path local existe -> fallback para leitura local (comportamento atual)
4. JSON nao existe + path local NAO existe -> retorna ok=false + error explicativo + hint "instalar backup.sh"
5. JSON malformado -> retorna ok=false + error "JSON parse error"

TDD strict: estes testes devem FALHAR ate a implementacao.

Modified by ZCode/Mavis + Gustavo Almeida (2026-06-25)
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
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
    """TestClient FastAPI com SQLite in-memory + dependency_overrides."""
    from app.db import get_db

    with (
        patch("app.db.engine", test_engine),
        patch("app.db.SessionLocal", test_session_factory),
        patch("app.main.engine", test_engine),
    ):
        from app.main import app

        Base.metadata.create_all(test_engine)

        def _override_get_db():
            db = test_session_factory()
            try:
                yield db
            finally:
                db.close()

        app.dependency_overrides[get_db] = _override_get_db

        try:
            with TestClient(app) as c:
                yield c
        finally:
            app.dependency_overrides.clear()


# ============================================================================
# Test 1: JSON existe, backup OK
# ============================================================================


def test_health_backup_lendo_json_status_quando_existe(client, tmp_path):
    """Quando cartorio-backup-status.json existe e ok=true, retorna ok=true."""
    status_path = tmp_path / "cartorio-backup-status.json"
    last_backup_iso = (
        datetime.now(timezone.utc) - timedelta(hours=6)
    ).isoformat()
    status_data = {
        "last_backup_iso": last_backup_iso,
        "last_backup_filename": "cartorio_backup_20260625_030000.tar.gz",
        "last_backup_size_bytes": 1048576,
        "last_backup_age_hours": 6.0,
        "backup_count_7d": 7,
        "ok": True,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }
    status_path.write_text(json.dumps(status_data))

    # Endpoint le do path /var/log/cartorio-backup-status.json (default VPS)
    # Mock OS para apontar para tmp_path
    with patch("os.path.exists") as mock_exists, patch(
        "builtins.open", create=True
    ) as mock_open:
        mock_exists.return_value = True
        mock_open.return_value.__enter__.return_value.read.return_value = json.dumps(
            status_data
        )

        response = client.get("/api/v1/health/backup")
        # NOTE: este teste sera implementado para refletir o comportamento esperado
        # quando o fix for aplicado. Por enquanto, falha ate a implementacao.
        assert response.status_code == 200
        data = response.json()
        assert data["ok"] is True
        assert data["last_backup_age_hours"] == 6.0
        assert data["source"] == "status_json"  # marca que veio do JSON


# ============================================================================
# Test 2: JSON existe, backup STALE (> 26h)
# ============================================================================


def test_health_backup_json_stale_marca_ok_false(client):
    """Quando JSON existe mas backup > 26h, retorna ok=false."""
    status_data = {
        "last_backup_iso": (
            datetime.now(timezone.utc) - timedelta(hours=30)
        ).isoformat(),
        "last_backup_filename": "cartorio_backup_20260623_030000.tar.gz",
        "last_backup_size_bytes": 524288,
        "last_backup_age_hours": 30.5,
        "backup_count_7d": 2,
        "ok": False,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }

    with patch("os.path.exists") as mock_exists, patch(
        "builtins.open", create=True
    ) as mock_open:
        mock_exists.return_value = True
        mock_open.return_value.__enter__.return_value.read.return_value = json.dumps(
            status_data
        )

        response = client.get("/api/v1/health/backup")
        assert response.status_code == 200
        data = response.json()
        assert data["ok"] is False
        assert data["last_backup_age_hours"] >= 26
        assert data["source"] == "status_json"


# ============================================================================
# Test 3: JSON NAO existe + path local existe (fallback)
# ============================================================================


def test_health_backup_fallback_para_path_local_quando_json_ausente(
    client, tmp_path, monkeypatch
):
    """Quando JSON nao existe, mas /var/backups/cartorio existe no container
    (volume mount aplicado), usa o path local."""
    backup_dir = tmp_path / "backups"
    backup_dir.mkdir()
    # Cria 1 arquivo .tar.gz recente (1h atras)
    tar_file = backup_dir / "cartorio_backup_20260625_150000.tar.gz"
    tar_file.write_bytes(b"fake tarball content" * 1000)
    # set mtime para 1h atras
    import os
    import time

    one_hour_ago = time.time() - 3600
    os.utime(tar_file, (one_hour_ago, one_hour_ago))

    monkeypatch.setattr(
        "app.api.v1.router.os.path.isdir", lambda p: p == "/var/backups/cartorio"
    )
    monkeypatch.setattr(
        "app.api.v1.router.os.listdir", lambda p: ["cartorio_backup_20260625_150000.tar.gz"]
    )
    monkeypatch.setattr(
        "app.api.v1.router.os.path.getmtime", lambda p: one_hour_ago
    )
    monkeypatch.setattr(
        "app.api.v1.router.os.path.getsize", lambda p: 17000
    )
    monkeypatch.setattr(
        "app.api.v1.router.os.path.join", lambda *args: str(args[0]) + "/" + args[1]
    )

    response = client.get("/api/v1/health/backup")
    assert response.status_code == 200
    data = response.json()
    assert data["ok"] is True
    assert data["source"] == "local_path"


# ============================================================================
# Test 4: JSON NAO existe + path local NAO existe
# ============================================================================


def test_health_backup_quando_json_e_path_ausentes_retorna_instrucoes(
    client, monkeypatch
):
    """Quando NEM JSON nem path local existem, retorna ok=false + instrucoes
    para instalar backup.sh + cron."""
    monkeypatch.setattr(
        "app.api.v1.router.os.path.isdir", lambda p: False
    )

    response = client.get("/api/v1/health/backup")
    assert response.status_code == 200
    data = response.json()
    assert data["ok"] is False
    assert "error" in data
    assert "install" in data["error"].lower() or "setup" in data["error"].lower()


# ============================================================================
# Test 5: JSON malformado
# ============================================================================


def test_health_backup_json_malformado_retorna_ok_false_com_erro(client):
    """Quando JSON existe mas esta malformado, retorna ok=false sem crash."""
    with patch("os.path.exists") as mock_exists, patch(
        "builtins.open", create=True
    ) as mock_open:
        mock_exists.return_value = True
        mock_open.return_value.__enter__.return_value.read.return_value = (
            "{ invalid json content [[["
        )

        response = client.get("/api/v1/health/backup")
        assert response.status_code == 200
        data = response.json()
        assert data["ok"] is False
        assert "parse" in data.get("error", "").lower() or "json" in data.get("error", "").lower()