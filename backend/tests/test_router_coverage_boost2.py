"""Additional tests for router.py coverage boost — batch 2.

Covers: health_* endpoints, LGPD cliente CRUD, admin endpoints, agendamento,
DLQ, prometheus helpers, postman, metrics, radar, integracoes, backup, etc.
"""

from __future__ import annotations

import datetime
import json
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException


# ============================================================================
# Reuse fixtures
# ============================================================================


@pytest.fixture
def mock_request():
    req = MagicMock()
    req.state = SimpleNamespace(
        request_id="req-123",
        client_ip="192.168.1.1",
        user_agent="test-agent",
    )
    req.client = SimpleNamespace(host="192.168.1.1")
    req.headers = {
        "X-API-Key": "test-key-64-chars-aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
        "X-Canal": "api",
        "user-agent": "test-agent",
        "x-request-id": "req-123",
    }
    req.url = SimpleNamespace(path="/api/v1/test")
    req.method = "GET"
    return req


@pytest.fixture
def mock_db():
    db = MagicMock()
    db.execute.return_value = MagicMock()
    db.execute.return_value.scalar_one_or_none.return_value = None
    db.execute.return_value.scalars.return_value.all.return_value = []
    db.get.return_value = None
    db.add.return_value = None
    db.flush.return_value = None
    db.commit.return_value = None
    db.refresh.return_value = None
    return db


@pytest.fixture
def mock_settings(monkeypatch):
    monkeypatch.setenv("CARTORIO_API_KEY", "test-key-64-chars-aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa")
    monkeypatch.setenv("DATABASE_URL", "sqlite:///:memory:")
    monkeypatch.setenv("REDIS_URL", "redis://localhost:6379/0")
    monkeypatch.setenv("PII_SCRUB_ENABLED", "true")
    monkeypatch.setenv("PII_BLOCK_ON_DETECT", "true")
    monkeypatch.setenv("OPENCODE_GO_BASE_URL", "http://localhost:11434")
    monkeypatch.setenv("OPENCLAW_BASE_URL", "http://localhost:8080")
    monkeypatch.setenv("N8N_BASE_URL", "http://localhost:5678")
    monkeypatch.setenv("EVOLUTION_BASE_URL", "http://localhost:8081")
    monkeypatch.setenv("CHATWOOT_BASE_URL", "http://localhost:3000")
    monkeypatch.setenv("SUPABASE_URL", "http://localhost:54321")
    from app.config import settings

    return settings


# ============================================================================
# health_live
# ============================================================================


class TestHealthLive:
    @pytest.mark.asyncio
    async def test_returns_alive(self):
        from app.api.v1.router import health_live

        result = await health_live()
        assert result["status"] == "alive"
        assert result["service"] == "cartorio-api"
        assert "version" in result


# ============================================================================
# health_ready — engine & redis imported LOCALLY inside the function
# ============================================================================


class TestHealthReady:
    @pytest.mark.asyncio
    async def test_db_ok_redis_ok(self):
        from app.api.v1.router import health_ready

        with (
            patch("app.db.engine") as mock_eng,
            patch("redis.Redis") as mock_redis_cls,
            patch("app.api.v1.router.settings") as mock_s,
        ):
            mock_s.redis_url = "redis://localhost:6379/0"
            mock_conn = MagicMock()
            mock_eng.connect.return_value.__enter__ = MagicMock(return_value=mock_conn)
            mock_eng.connect.return_value.__exit__ = MagicMock(return_value=False)
            mock_r = MagicMock()
            mock_redis_cls.from_url.return_value = mock_r
            result = await health_ready()
            assert result.status_code == 200

    @pytest.mark.asyncio
    async def test_db_fail(self):
        from app.api.v1.router import health_ready

        with (
            patch("app.db.engine") as mock_eng,
            patch("redis.Redis") as mock_redis_cls,
            patch("app.api.v1.router.settings") as mock_s,
        ):
            mock_s.redis_url = "redis://localhost:6379/0"
            mock_eng.connect.return_value.__enter__ = MagicMock(side_effect=Exception("DB down"))
            mock_eng.connect.return_value.__exit__ = MagicMock(return_value=False)
            mock_r = MagicMock()
            mock_redis_cls.from_url.return_value = mock_r
            result = await health_ready()
            assert result.status_code == 503

    @pytest.mark.asyncio
    async def test_no_redis_url(self):
        from app.api.v1.router import health_ready

        with patch("app.db.engine") as mock_eng, patch("app.api.v1.router.settings") as mock_s:
            mock_s.redis_url = None
            mock_conn = MagicMock()
            mock_eng.connect.return_value.__enter__ = MagicMock(return_value=mock_conn)
            mock_eng.connect.return_value.__exit__ = MagicMock(return_value=False)
            result = await health_ready()
            assert result.status_code == 200


# ============================================================================
# health_db — engine, get_pool_stats imported LOCALLY
# ============================================================================


class TestHealthDb:
    @pytest.mark.asyncio
    async def test_online(self):
        from app.api.v1.router import health_db

        with patch("app.db.engine") as mock_eng, patch("app.db.get_pool_stats") as mock_pool:
            mock_conn = MagicMock()
            mock_eng.connect.return_value.__enter__ = MagicMock(return_value=mock_conn)
            mock_eng.connect.return_value.__exit__ = MagicMock(return_value=False)
            mock_pool.return_value = {"pool_size": 5}
            result = await health_db()
            assert result.status_code == 200

    @pytest.mark.asyncio
    async def test_offline(self):
        from app.api.v1.router import health_db

        with patch("app.db.engine") as mock_eng:
            mock_eng.connect.return_value.__enter__ = MagicMock(side_effect=Exception("fail"))
            mock_eng.connect.return_value.__exit__ = MagicMock(return_value=False)
            result = await health_db()
            assert result.status_code == 503


# ============================================================================
# health_redis — redis.asyncio imported LOCALLY
# ============================================================================


class TestHealthRedis:
    @pytest.mark.asyncio
    async def test_online(self):
        from app.api.v1.router import health_redis

        mock_r = AsyncMock()
        with patch("redis.asyncio.from_url", return_value=mock_r):
            result = await health_redis()
            assert result.status_code == 200

    @pytest.mark.asyncio
    async def test_offline(self):
        from app.api.v1.router import health_redis

        with patch("redis.asyncio.from_url", side_effect=Exception("fail")):
            result = await health_redis()
            assert result.status_code == 503


# ============================================================================
# health_audit — check_audit_log_alive, send_alert imported LOCALLY
# ============================================================================


class TestHealthAudit:
    @patch("app.services.dead_mans_switch.check_audit_log_alive")
    @pytest.mark.asyncio
    async def test_alive(self, mock_check):
        from app.api.v1.router import health_audit

        mock_check.return_value = {
            "alive": True,
            "cold_start": False,
            "last_seen": datetime.datetime(2026, 1, 1, tzinfo=datetime.timezone.utc),
            "seconds_since_last": 300,
        }
        db = MagicMock()
        result = await health_audit(db)
        assert result.status_code == 200

    @patch("app.services.dead_mans_switch.send_alert")
    @patch("app.services.dead_mans_switch.check_audit_log_alive")
    @pytest.mark.asyncio
    async def test_dead_sends_alert(self, mock_check, mock_alert):
        from app.api.v1.router import health_audit

        mock_check.return_value = {
            "alive": False,
            "cold_start": False,
            "last_seen": datetime.datetime(2026, 1, 1, tzinfo=datetime.timezone.utc),
            "seconds_since_last": 7200,
        }
        db = MagicMock()
        result = await health_audit(db)
        assert result.status_code == 200
        mock_alert.assert_called_once()

    @patch("app.services.dead_mans_switch.check_audit_log_alive")
    @pytest.mark.asyncio
    async def test_cold_start(self, mock_check):
        from app.api.v1.router import health_audit

        mock_check.return_value = {
            "alive": False,
            "cold_start": True,
            "last_seen": None,
            "seconds_since_last": None,
        }
        db = MagicMock()
        result = await health_audit(db)
        assert result.status_code == 503


# ============================================================================
# health_audit_freshness — check_audit_log_freshness imported LOCALLY
# ============================================================================


class TestHealthAuditFreshness:
    @patch("app.jobs.dead_mans_switch.check_audit_log_freshness")
    @pytest.mark.asyncio
    async def test_healthy(self, mock_check):
        from app.api.v1.router import health_audit_freshness
        from app.jobs.dead_mans_switch import HealthStatus

        mock_health = MagicMock()
        mock_health.status = HealthStatus.HEALTHY
        mock_health.last_entry_at = datetime.datetime(2026, 1, 1, tzinfo=datetime.timezone.utc)
        mock_health.last_entry_age_minutes = 5.0
        mock_health.threshold_minutes = 60
        mock_health.alert = None
        mock_check.return_value = mock_health
        db = MagicMock()
        result = await health_audit_freshness(db)
        assert result.status_code == 200

    @patch("app.jobs.dead_mans_switch.check_audit_log_freshness")
    @pytest.mark.asyncio
    async def test_stale(self, mock_check):
        from app.api.v1.router import health_audit_freshness
        from app.jobs.dead_mans_switch import HealthStatus

        mock_health = MagicMock()
        mock_health.status = HealthStatus.STALE
        mock_health.last_entry_at = datetime.datetime(2026, 1, 1, tzinfo=datetime.timezone.utc)
        mock_health.last_entry_age_minutes = 90.0
        mock_health.threshold_minutes = 60
        mock_health.alert = "audit stale"
        mock_check.return_value = mock_health
        db = MagicMock()
        result = await health_audit_freshness(db)
        assert result.status_code == 503


# ============================================================================
# health_llm — httpx.AsyncClient used directly (module-level import OK)
# ============================================================================


class TestHealthLlm:
    @pytest.mark.asyncio
    async def test_online(self):
        from app.api.v1.router import health_llm

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        with patch("app.api.v1.router.httpx") as mock_httpx:
            mock_client = AsyncMock()
            mock_client.get.return_value = mock_resp
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_httpx.AsyncClient.return_value = mock_client
            result = await health_llm()
            assert result.status_code == 200

    @pytest.mark.asyncio
    async def test_no_provider(self):
        from app.api.v1.router import health_llm

        with patch("app.api.v1.router.settings") as mock_s:
            mock_s.opencode_go_base_url = None
            mock_s.openclaw_base_url = None
            result = await health_llm()
            assert result.status_code == 503

    @pytest.mark.asyncio
    async def test_connection_error(self):
        from app.api.v1.router import health_llm

        with patch("app.api.v1.router.httpx") as mock_httpx:
            mock_client = AsyncMock()
            mock_client.get.side_effect = Exception("connection refused")
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_httpx.AsyncClient.return_value = mock_client
            result = await health_llm()
            assert result.status_code == 503

    @pytest.mark.asyncio
    async def test_server_error(self):
        from app.api.v1.router import health_llm

        mock_resp = MagicMock()
        mock_resp.status_code = 500
        with patch("app.api.v1.router.httpx") as mock_httpx:
            mock_client = AsyncMock()
            mock_client.get.return_value = mock_resp
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_httpx.AsyncClient.return_value = mock_client
            result = await health_llm()
            assert result.status_code == 503


# ============================================================================
# health_radar — engine, redis, httpx, settings — all LOCALLY imported
# ============================================================================


class TestHealthRadar:
    @pytest.mark.asyncio
    async def test_all_online(self):
        from app.api.v1.router import health_radar

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        with (
            patch("app.db.engine") as mock_eng,
            patch("app.api.v1.router.redis") as mock_redis_cls,
            patch("app.api.v1.router.httpx") as mock_httpx,
            patch("app.api.v1.router.settings") as mock_s,
        ):
            mock_conn = MagicMock()
            mock_eng.connect.return_value.__enter__ = MagicMock(return_value=mock_conn)
            mock_eng.connect.return_value.__exit__ = MagicMock(return_value=False)
            mock_r = MagicMock()
            mock_redis_cls.from_url.return_value = mock_r
            mock_s.n8n_base_url = "http://n8n"
            mock_s.openclaw_base_url = "http://oc"
            mock_s.evolution_base_url = "http://evo"
            mock_s.chatwoot_base_url = "http://cw"
            mock_s.supabase_url = "http://sb"
            mock_client = AsyncMock()
            mock_client.get.return_value = mock_resp
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_httpx.AsyncClient.return_value = mock_client
            result = await health_radar()
            assert result["status"] == "green"
            assert result["services"]["database"] == "online"


# ============================================================================
# health_integracoes — engine, redis, httpx, settings, time — LOCALLY imported
# ============================================================================


class TestHealthIntegracoes:
    @pytest.mark.asyncio
    async def test_all_online(self):
        from app.api.v1.router import health_integracoes

        mock_resp = MagicMock()
        mock_resp.status_code = 200
        with (
            patch("app.db.engine") as mock_eng,
            patch("app.api.v1.router.redis") as mock_redis_cls,
            patch("app.api.v1.router.httpx") as mock_httpx,
            patch("app.api.v1.router.settings") as mock_s,
            patch("app.api.v1.router.time") as mock_time,
        ):
            mock_time.perf_counter.return_value = 0.0
            mock_conn = MagicMock()
            mock_eng.connect.return_value.__enter__ = MagicMock(return_value=mock_conn)
            mock_eng.connect.return_value.__exit__ = MagicMock(return_value=False)
            mock_r = MagicMock()
            mock_redis_cls.from_url.return_value = mock_r
            mock_s.n8n_base_url = "http://n8n"
            mock_s.openclaw_base_url = "http://oc"
            mock_s.evolution_base_url = "http://evo"
            mock_s.chatwoot_base_url = "http://cw"
            mock_s.supabase_url = "http://sb"
            mock_s.opencode_go_base_url = "http://ocg"
            mock_client = AsyncMock()
            mock_client.get.return_value = mock_resp
            mock_client.__aenter__ = AsyncMock(return_value=mock_client)
            mock_client.__aexit__ = AsyncMock(return_value=False)
            mock_httpx.AsyncClient.return_value = mock_client
            result = await health_integracoes()
            assert result["integracoes"]["database"]["status"] == "online"
            assert result["integracoes"]["redis"]["status"] == "online"


# ============================================================================
# health_backup — redis, os imported LOCALLY
# ============================================================================


class TestHealthBackup:
    @pytest.mark.asyncio
    async def test_redis_strategy(self):
        from app.api.v1.router import health_backup

        mock_r = MagicMock()
        mock_r.get.return_value = json.dumps(
            {
                "ok": True,
                "last_backup_age_hours": 2.0,
                "last_backup_iso": "2026-01-01T00:00:00Z",
                "backup_count_7d": 7,
                "last_backup_size_bytes": 1024,
                "last_backup_filename": "backup.tar.gz",
                "updated_at": "2026-01-01T00:00:00Z",
            }
        )
        with (
            patch("app.api.v1.router.redis") as mock_redis_cls,
            patch("app.api.v1.router.os.path") as mock_os,
        ):
            mock_redis_cls.from_url.return_value = mock_r
            mock_os.path.exists.return_value = False
            mock_os.path.isdir.return_value = False
            result = await health_backup()
            assert result["source"] == "redis"
            assert result["ok"] is True

    @pytest.mark.asyncio
    async def test_no_dir_no_json(self):
        from app.api.v1.router import health_backup

        mock_r = MagicMock()
        mock_r.get.return_value = None
        with (
            patch("app.api.v1.router.redis") as mock_redis_cls,
            patch("app.api.v1.router.os.path") as mock_path,
        ):
            mock_redis_cls.from_url.return_value = mock_r
            mock_path.exists.return_value = False
            mock_path.isdir.return_value = False
            result = await health_backup()
            assert result["source"] == "none"
            assert result["ok"] is False


# ============================================================================
# update_backup_status
# ============================================================================


class TestUpdateBackupStatus:
    @pytest.mark.asyncio
    async def test_stores_in_redis(self):
        from app.api.v1.router import update_backup_status, BackupStatusUpdate

        mock_r = MagicMock()
        with patch("app.api.v1.router.redis") as mock_redis_cls:
            mock_redis_cls.from_url.return_value = mock_r
            data = BackupStatusUpdate(ok=True, last_backup_iso="2026-01-01T00:00:00Z")
            result = await update_backup_status(data)
            assert result["ok"] is True
            mock_r.setex.assert_called_once()


# ============================================================================
# health_backup_v2 — check_backup_v2_freshness imported LOCALLY
# ============================================================================


class TestHealthBackupV2:
    @patch("app.services.backup_v2.check_backup_v2_freshness")
    @pytest.mark.asyncio
    async def test_healthy(self, mock_check):
        from app.api.v1.router import health_backup_v2
        from app.services.backup_v2 import BackupHealthStatus

        mock_h = MagicMock()
        mock_h.status = BackupHealthStatus.HEALTHY
        mock_h.last_backup_at = datetime.datetime(2026, 1, 1, tzinfo=datetime.timezone.utc)
        mock_h.last_backup_age_minutes = 30.0
        mock_h.backup_count = 4
        mock_h.threshold_minutes = 360
        mock_h.last_backup_dir = "/var/backups/pgbase/20260101_0000"
        mock_h.backup_dir = "/var/backups/pgbase"
        mock_h.alert = None
        mock_h.error = None
        mock_check.return_value = mock_h
        result = await health_backup_v2()
        assert result.status_code == 200


# ============================================================================
# postman_collection
# ============================================================================


class TestPostmanCollection:
    @pytest.mark.asyncio
    async def test_returns_valid_collection(self):
        from app.api.v1.router import postman_collection

        result = await postman_collection()
        assert result["info"]["name"] == "Cartorio API"
        assert "item" in result
        assert len(result["item"]) > 0


# ============================================================================
# get_cliente (LGPD-safe)
# ============================================================================


class TestGetCliente:
    @patch("app.api.v1.router.AuditService")
    @patch("app.api.v1.router.hash_pii", return_value="hash123")
    @pytest.mark.asyncio
    async def test_not_found(self, mock_hash, mock_audit):
        from app.api.v1.router import get_cliente

        db = MagicMock()
        db.get.return_value = None
        with pytest.raises(HTTPException) as exc_info:
            await get_cliente(
                request=MagicMock(client=SimpleNamespace(host="1.2.3.4"), headers={}),
                cliente_id=1,
                db=db,
                _api_key="key",
            )
        assert exc_info.value.status_code == 404

    @patch("app.api.v1.router.AuditService")
    @patch("app.api.v1.router.hash_pii", return_value="hash123")
    @pytest.mark.asyncio
    async def test_encerrado(self, mock_hash, mock_audit):
        from app.api.v1.router import get_cliente
        from app.models.cliente import MotivoEncerramento

        mock_cliente = MagicMock()
        mock_cliente.motivo_encerramento = MotivoEncerramento.REVOGACAO_CONSENTIMENTO
        db = MagicMock()
        db.get.return_value = mock_cliente
        with pytest.raises(HTTPException) as exc_info:
            await get_cliente(
                request=MagicMock(client=SimpleNamespace(host="1.2.3.4"), headers={}),
                cliente_id=1,
                db=db,
                _api_key="key",
            )
        assert exc_info.value.status_code == 410

    @patch("app.api.v1.router.AuditService")
    @patch("app.api.v1.router.hash_pii", return_value="hash123")
    @pytest.mark.asyncio
    async def test_success(self, mock_hash, mock_audit):
        from app.api.v1.router import get_cliente

        mock_cliente = MagicMock()
        mock_cliente.motivo_encerramento = None
        mock_cliente.id = 1
        mock_cliente.cpf_hash = "cpf_h"
        mock_cliente.telefone_hash = "tel_h"
        mock_cliente.email = "test@test.com"
        mock_cliente.consentimento_lgpd = True
        mock_cliente.created_at = datetime.datetime(2026, 1, 1)
        mock_cliente.updated_at = datetime.datetime(2026, 1, 1)
        db = MagicMock()
        db.get.return_value = mock_cliente
        result = await get_cliente(
            request=MagicMock(client=SimpleNamespace(host="1.2.3.4"), headers={}),
            cliente_id=1,
            db=db,
            _api_key="key",
        )
        assert result["id"] == 1


# ============================================================================
# patch_cliente (LGPD correction)
# ============================================================================


class TestPatchCliente:
    @patch("app.api.v1.router.AuditService")
    @pytest.mark.asyncio
    async def test_not_found(self, mock_audit):
        from app.api.v1.router import patch_cliente, ClienteCorrecaoRequest

        db = MagicMock()
        db.get.return_value = None
        body = ClienteCorrecaoRequest(nome="Novo Nome")
        with pytest.raises(HTTPException) as exc_info:
            await patch_cliente(
                request=MagicMock(client=SimpleNamespace(host="1.2.3.4"), headers={}),
                cliente_id=1,
                body=body,
                db=db,
                _api_key="key",
            )
        assert exc_info.value.status_code == 404

    @patch("app.api.v1.router.AuditService")
    @pytest.mark.asyncio
    async def test_encerrado(self, mock_audit):
        from app.api.v1.router import patch_cliente, ClienteCorrecaoRequest
        from app.models.cliente import MotivoEncerramento

        mock_c = MagicMock()
        mock_c.motivo_encerramento = MotivoEncerramento.REVOGACAO_CONSENTIMENTO
        db = MagicMock()
        db.get.return_value = mock_c
        body = ClienteCorrecaoRequest(nome="XX")
        with pytest.raises(HTTPException) as exc_info:
            await patch_cliente(
                request=MagicMock(client=SimpleNamespace(host="1.2.3.4"), headers={}),
                cliente_id=1,
                body=body,
                db=db,
                _api_key="key",
            )
        assert exc_info.value.status_code == 410

    @patch("app.api.v1.router.AuditService")
    @pytest.mark.asyncio
    async def test_no_valid_fields(self, mock_audit):
        from app.api.v1.router import patch_cliente, ClienteCorrecaoRequest

        mock_c = MagicMock()
        mock_c.motivo_encerramento = None
        mock_c.nome = "Old"
        mock_c.email = "old@test.com"
        db = MagicMock()
        db.get.return_value = mock_c
        body = ClienteCorrecaoRequest()  # all None
        with pytest.raises(HTTPException) as exc_info:
            await patch_cliente(
                request=MagicMock(client=SimpleNamespace(host="1.2.3.4"), headers={}),
                cliente_id=1,
                body=body,
                db=db,
                _api_key="key",
            )
        assert exc_info.value.status_code == 400

    @patch("app.api.v1.router.AuditService")
    @pytest.mark.asyncio
    async def test_success(self, mock_audit):
        from app.api.v1.router import patch_cliente, ClienteCorrecaoRequest

        mock_c = MagicMock()
        mock_c.motivo_encerramento = None
        mock_c.nome = "Old"
        mock_c.email = "old@test.com"
        db = MagicMock()
        db.get.return_value = mock_c
        body = ClienteCorrecaoRequest(nome="New")
        result = await patch_cliente(
            request=MagicMock(client=SimpleNamespace(host="1.2.3.4"), headers={}),
            cliente_id=1,
            body=body,
            db=db,
            _api_key="key",
        )
        assert result["status"] == "corrected"
        assert "nome" in result["campos_alterados"]


# ============================================================================
# delete_cliente — direito_esquecimento imported LOCALLY
# ============================================================================


class TestDeleteCliente:
    @patch("app.api.v1.router.AuditService")
    @patch("app.services.lgpd.direito_esquecimento.direito_esquecimento")
    @pytest.mark.asyncio
    async def test_not_found(self, mock_de, mock_audit):
        from app.api.v1.router import delete_cliente
        from app.services.lgpd.direito_esquecimento import ClienteNotFoundError

        mock_de.side_effect = ClienteNotFoundError("not found")
        db = MagicMock()
        with pytest.raises(HTTPException) as exc_info:
            await delete_cliente(
                request=MagicMock(client=SimpleNamespace(host="1.2.3.4"), headers={}),
                cliente_id=1,
                db=db,
                api_key="key",
            )
        assert exc_info.value.status_code == 404

    @patch("app.api.v1.router.AuditService")
    @patch("app.services.lgpd.direito_esquecimento.direito_esquecimento")
    @pytest.mark.asyncio
    async def test_already_revoked(self, mock_de, mock_audit):
        from app.api.v1.router import delete_cliente
        from app.services.lgpd.direito_esquecimento import ClienteJaRevogadoError

        mock_de.side_effect = ClienteJaRevogadoError("already")
        db = MagicMock()
        with pytest.raises(HTTPException) as exc_info:
            await delete_cliente(
                request=MagicMock(client=SimpleNamespace(host="1.2.3.4"), headers={}),
                cliente_id=1,
                db=db,
                api_key="key",
            )
        assert exc_info.value.status_code == 409

    @patch("app.api.v1.router.AuditService")
    @patch("app.services.lgpd.direito_esquecimento.direito_esquecimento")
    @pytest.mark.asyncio
    async def test_success(self, mock_de, mock_audit):
        from app.api.v1.router import delete_cliente

        mock_result = SimpleNamespace(
            tipo="soft",
            cliente_id=1,
            protocolos_ativos=0,
            data_encerramento=datetime.datetime(2026, 1, 1, tzinfo=datetime.timezone.utc),
            motivo=SimpleNamespace(value="revogacao_consentimento"),
        )
        mock_de.return_value = mock_result
        db = MagicMock()
        result = await delete_cliente(
            request=MagicMock(client=SimpleNamespace(host="1.2.3.4"), headers={}),
            cliente_id=1,
            db=db,
            api_key="key",
        )
        assert result["status"] == "deleted"
        assert result["tipo"] == "soft"


# ============================================================================
# admin_run_retencao — run_retencao imported LOCALLY
# ============================================================================


class TestAdminRunRetencao:
    @patch("app.api.v1.router.AuditService")
    @patch("app.jobs.retencao.run_retencao")
    @pytest.mark.asyncio
    async def test_dry_run(self, mock_retencao, mock_audit):
        from app.api.v1.router import admin_run_retencao

        mock_retencao.return_value = SimpleNamespace(
            scanned=10,
            soft_deleted_5y=2,
            soft_deleted_inativo=1,
            errors=0,
            cutoff_5y=datetime.datetime(2021, 1, 1, tzinfo=datetime.timezone.utc),
            cutoff_inativo=datetime.datetime(2025, 1, 1, tzinfo=datetime.timezone.utc),
            duration_ms=50,
        )
        db = MagicMock()
        result = await admin_run_retencao(
            request=MagicMock(client=SimpleNamespace(host="1.2.3.4"), headers={}),
            db=db,
            api_key="key",
            payload={"dry_run": True},
        )
        assert result["dry_run"] is True
        assert result["scanned"] == 10


# ============================================================================
# admin_audit_dead_mans_switch_check — run_dead_mans_switch_check imported LOCALLY
# ============================================================================


class TestAdminAuditDeadMansSwitchCheck:
    @patch("app.jobs.cron_dead_mans_switch.run_dead_mans_switch_check")
    @pytest.mark.asyncio
    async def test_healthy(self, mock_run):
        from app.api.v1.router import admin_audit_dead_mans_switch_check

        from app.jobs.dead_mans_switch import HealthStatus

        mock_health = SimpleNamespace(
            status=HealthStatus.HEALTHY,
            last_entry_at=datetime.datetime(2026, 1, 1, tzinfo=datetime.timezone.utc),
            last_entry_age_minutes=5.0,
            threshold_minutes=60,
            alert=None,
        )
        mock_run.return_value = SimpleNamespace(health=mock_health, alerted=False)
        db = MagicMock()
        result = await admin_audit_dead_mans_switch_check(
            request=MagicMock(client=SimpleNamespace(host="1.2.3.4"), headers={}),
            db=db,
            api_key="key",
            payload=None,
        )
        assert result.status_code == 200


# ============================================================================
# admin_audit_health — check_audit_log_freshness_3lvl imported LOCALLY
# ============================================================================


class TestAdminAuditHealth:
    @patch("app.api.v1.router.AuditService")
    @patch("app.jobs.dead_mans_switch.check_audit_log_freshness_3lvl")
    @pytest.mark.asyncio
    async def test_healthy(self, mock_check, mock_audit):
        from app.api.v1.router import admin_audit_health
        from app.jobs.dead_mans_switch import HealthStatus3Lvl

        mock_h = SimpleNamespace(
            status=HealthStatus3Lvl.HEALTHY,
            last_audit_ts=datetime.datetime(2026, 1, 1, tzinfo=datetime.timezone.utc),
            stale_seconds=300,
            threshold_minutes=60,
        )
        mock_check.return_value = mock_h
        db = MagicMock()
        result = await admin_audit_health(
            request=MagicMock(client=SimpleNamespace(host="1.2.3.4"), headers={}),
            db=db,
            api_key="key",
        )
        assert result.status_code == 200


# ============================================================================
# admin_audit_check_now — run_dead_mans_switch_check_3lvl imported LOCALLY
# ============================================================================


class TestAdminAuditCheckNow:
    @patch("app.api.v1.router.AuditService")
    @patch("app.jobs.cron_dead_mans_switch.run_dead_mans_switch_check_3lvl")
    @pytest.mark.asyncio
    async def test_healthy(self, mock_run, mock_audit):
        from app.api.v1.router import admin_audit_check_now
        from app.jobs.dead_mans_switch import HealthStatus3Lvl

        mock_health = SimpleNamespace(
            status=HealthStatus3Lvl.HEALTHY,
            last_audit_ts=datetime.datetime(2026, 1, 1, tzinfo=datetime.timezone.utc),
            stale_seconds=100,
            threshold_minutes=60,
        )
        mock_run.return_value = SimpleNamespace(
            health=mock_health, alerted=False, telegram_sent=False
        )
        db = MagicMock()
        result = await admin_audit_check_now(
            request=MagicMock(client=SimpleNamespace(host="1.2.3.4"), headers={}),
            db=db,
            api_key="key",
            payload=None,
        )
        assert result.status_code == 200


# ============================================================================
# create_audit_log_endpoint — _extract_client_ip, create_audit_log_entry, detect_only
# imported LOCALLY
# ============================================================================


class TestCreateAuditLogEndpoint:
    @patch("app.services.pii.detect_only", return_value={})
    @patch("app.services.audit_create.create_audit_log_entry")
    @patch("app.api.v1.router.AuditService")
    @patch("app.middleware.request_context._extract_client_ip", return_value="1.2.3.4")
    @pytest.mark.asyncio
    async def test_create(self, mock_ip, mock_audit, mock_create, mock_pii):
        from app.api.v1.router import create_audit_log_endpoint
        from app.schemas.audit import AuditLogCreate

        mock_entry = SimpleNamespace(
            id=1, hash="h1", prev_hash="ph1", timestamp=datetime.datetime.now(datetime.timezone.utc)
        )
        mock_create.return_value = mock_entry
        entry = AuditLogCreate(
            action="test.action",
            resource="test:1",
            actor_id="test",
            actor_type="system",
            payload={"key": "value"},
        )
        db = MagicMock()
        result = await create_audit_log_endpoint(
            request=MagicMock(client=SimpleNamespace(host="1.2.3.4"), headers={}),
            entry=entry,
            db=db,
            api_key="test-key-64-chars-aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
        )
        assert result.id == 1


# ============================================================================
# list_audit_logs_endpoint
# ============================================================================


class TestListAuditLogsEndpoint:
    @patch("app.api.v1.router.list_audit_logs")
    @pytest.mark.asyncio
    async def test_list(self, mock_list):
        from app.api.v1.router import list_audit_logs_endpoint

        mock_list.return_value = SimpleNamespace(items=[], total=0, page=1, page_size=50)
        db = MagicMock()
        result = await list_audit_logs_endpoint(
            request=MagicMock(client=SimpleNamespace(host="1.2.3.4"), headers={}),
            _api_key="key",
            db=db,
        )
        assert result.total == 0


# ============================================================================
# get_audit_log_endpoint
# ============================================================================


class TestGetAuditLogEndpoint:
    @patch("app.api.v1.router.get_audit_log_by_id")
    @pytest.mark.asyncio
    async def test_not_found(self, mock_get):
        from app.api.v1.router import get_audit_log_endpoint

        mock_get.return_value = None
        db = MagicMock()
        with pytest.raises(HTTPException) as exc_info:
            await get_audit_log_endpoint(
                request=MagicMock(client=SimpleNamespace(host="1.2.3.4"), headers={}),
                log_id=1,
                db=db,
                _api_key="key",
            )
        assert exc_info.value.status_code == 404

    @patch("app.api.v1.router.get_audit_log_by_id")
    @pytest.mark.asyncio
    async def test_found(self, mock_get):
        from app.api.v1.router import get_audit_log_endpoint

        mock_get.return_value = SimpleNamespace(id=1)
        db = MagicMock()
        result = await get_audit_log_endpoint(
            request=MagicMock(client=SimpleNamespace(host="1.2.3.4"), headers={}),
            log_id=1,
            db=db,
            _api_key="key",
        )
        assert result.id == 1


# ============================================================================
# agendamento_disponibilidade
# ============================================================================


class TestAgendamentoDisponibilidade:
    @pytest.mark.asyncio
    async def test_invalid_dia(self):
        from app.api.v1.router import agendamento_disponibilidade

        result = await agendamento_disponibilidade(dia="domingo", hora=10)
        assert result["vagas"] == 0
        assert "erro" in result

    @pytest.mark.asyncio
    async def test_outside_hours(self):
        from app.api.v1.router import agendamento_disponibilidade

        result = await agendamento_disponibilidade(dia="segunda", hora=20)
        assert result["vagas"] == 0

    @pytest.mark.asyncio
    async def test_valid(self):
        from app.api.v1.router import agendamento_disponibilidade

        result = await agendamento_disponibilidade(dia="segunda", hora=10)
        assert result["vagas"] == 5
        assert len(result["slots"]) > 0


# ============================================================================
# _parse_labels_key_safe
# ============================================================================


class TestParseLabelsKeySafe:
    def test_empty(self):
        from app.api.v1.router import _parse_labels_key_safe

        assert _parse_labels_key_safe("") == {}

    def test_valid(self):
        from app.api.v1.router import _parse_labels_key_safe

        result = _parse_labels_key_safe("env=prod|region=us-east-1")
        assert result["env"] == "prod"
        assert result["region"] == "us-east-1"

    def test_long_value_truncated(self):
        from app.api.v1.router import _parse_labels_key_safe

        result = _parse_labels_key_safe(f"key={'x' * 100}")
        assert "key" not in result


# ============================================================================
# _looks_like_prometheus
# ============================================================================


class TestLooksLikePrometheus:
    def test_empty(self):
        from app.api.v1.router import _looks_like_prometheus

        assert _looks_like_prometheus("") is False

    def test_metric_with_space(self):
        from app.api.v1.router import _looks_like_prometheus

        assert _looks_like_prometheus("http_requests_total 42") is True

    def test_curly_only(self):
        from app.api.v1.router import _looks_like_prometheus

        assert _looks_like_prometheus('{foo="bar"}') is False

    def test_comment_lines_only(self):
        from app.api.v1.router import _looks_like_prometheus

        assert _looks_like_prometheus("# HELP foo bar\n# TYPE foo counter") is False


# ============================================================================
# _ingest_prometheus_text
# ============================================================================


class TestIngestPrometheusText:
    def test_gauge(self):
        from app.api.v1.router import _ingest_prometheus_text

        mock_store = MagicMock()
        counters, gauges = _ingest_prometheus_text("process_uptime_seconds 12345", mock_store)
        assert gauges == 1
        mock_store.set_gauge.assert_called_once()

    def test_counter(self):
        from app.api.v1.router import _ingest_prometheus_text

        mock_store = MagicMock()
        counters, gauges = _ingest_prometheus_text("http_requests_total 100", mock_store)
        assert counters == 1
        mock_store.inc_counter.assert_called_once()

    def test_with_labels(self):
        from app.api.v1.router import _ingest_prometheus_text

        mock_store = MagicMock()
        counters, gauges = _ingest_prometheus_text('metric{env="prod"} 42.0', mock_store)
        assert gauges == 1

    def test_skips_comments(self):
        from app.api.v1.router import _ingest_prometheus_text

        mock_store = MagicMock()
        counters, gauges = _ingest_prometheus_text("# HELP foo bar\nprocess_uptime 100", mock_store)
        assert gauges == 1


# ============================================================================
# _humanize_size (extra edge cases)
# ============================================================================


class TestHumanizeSizeExtra:
    def test_gb(self):
        from app.api.v1.router import _humanize_size

        assert _humanize_size(2 * 1024**3) == "2.0G"

    def test_mb(self):
        from app.api.v1.router import _humanize_size

        assert _humanize_size(5 * 1024**2) == "5.0M"

    def test_kb(self):
        from app.api.v1.router import _humanize_size

        assert _humanize_size(1536) == "1.5K"
