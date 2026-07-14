"""Sprint 8 coverage push — focado nos bottom 5 modulos backend.

Cobertura inicial: 94.09% TOTAL.
Target: >= 95% TOTAL.

Bottom 5 modulos (statements missing):
1. app/main.py                          (25 miss, 83.2%)
2. app/api/v1/lgpd_direitos_v2.py       (20 miss, 90.1%)
3. app/services/notificacao.py          (15 miss, 90.7%)
4. app/api/v1/integrations.py           (10 miss, 95.4%)
5. app/api/v1/ws/atendimentos.py        ( 7 miss, 87.0%)

Bonus (baixa cobertura):
- app/services/protocolo.py             ( 5 miss, 89.6%) — LGPDBlock + TipoInvalido
- app/api/deps.py                       ( 7 miss, 91.2%) — include_deleted gate
- app/services/backup_v2.py             ( 6 miss, 92.1%) — OSError + scan fail

Cada target recebe happy + 2-3 edge cases conforme briefing.
"""

from __future__ import annotations

import asyncio
import contextlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

# =============================================================================
# 1. app/main.py — Lifespan / health probes / swagger / mcp-servers
# =============================================================================


class TestMainEndpoints:
    """Testes para endpoints canonicos e rotas auxiliares em main.py."""

    def test_health_endpoint(self) -> None:
        """GET /health retorna 200 com service/version (cobre main.py:417-419)."""
        from app.main import app

        client = TestClient(app)
        resp = client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert "service" in data
        assert "version" in data

    def test_ready_endpoint(self) -> None:
        """GET /ready retorna 200 (cobre main.py:422-425)."""
        from app.main import app

        client = TestClient(app)
        resp = client.get("/ready")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ready"
        assert data["audit_chain_initialized"] is True

    def test_healthz_canonical_alias(self) -> None:
        """GET /healthz (canonico k8s) — alias de /health (cobre main.py:433-436)."""
        from app.main import app

        client = TestClient(app)
        resp = client.get("/healthz")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"

    def test_readyz_canonical_alias(self) -> None:
        """GET /readyz (canonico k8s) — alias de /ready (cobre main.py:439-442)."""
        from app.main import app

        client = TestClient(app)
        resp = client.get("/readyz")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ready"

    def test_metrics_root_returns_410(self) -> None:
        """GET /metrics na raiz retorna 410 Gone (cobre main.py:445-461).

        Sprint 5: redirecionado para /api/v1/metrics/prometheus.
        """
        from app.main import app

        client = TestClient(app)
        resp = client.get("/metrics")
        assert resp.status_code == 410
        # Body deve indicar o endpoint correto
        assert "/api/v1/metrics/prometheus" in resp.text

    def test_root_endpoint_metadata(self) -> None:
        """GET / retorna metadata do servico (cobre main.py:464-475)."""
        from app.main import app

        client = TestClient(app)
        resp = client.get("/")
        assert resp.status_code == 200
        data = resp.json()
        assert "service" in data
        assert data["docs"] == "/docs"
        assert data["redoc"] == "/redoc"
        assert data["openapi"] == "/openapi.json"
        assert data["mcp"] == "/mcp"

    def test_mcp_servers_endpoint_lists_servers(self) -> None:
        """GET /mcp-servers lista 5 servers MCP (cobre main.py:478-540)."""
        from app.main import app

        client = TestClient(app)
        resp = client.get("/mcp-servers")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"
        assert len(data["servers"]) == 5
        names = {s["name"] for s in data["servers"]}
        assert "cartorio-api" in names
        assert "n8n-mcp" in names
        assert "supabase-mcp" in names
        assert "easypanel-mcp" in names
        assert "openclaw-mcp" in names

    def test_custom_swagger_ui_html(self) -> None:
        """GET /docs retorna Swagger UI customizado (cobre main.py:637-640)."""
        from app.main import app

        client = TestClient(app)
        resp = client.get("/docs")
        assert resp.status_code == 200
        assert "text/html" in resp.headers.get("content-type", "")
        assert "swagger-ui-bundle.js" in resp.text
        assert "Cartorio" in resp.text

    def test_redoc_html_endpoint(self) -> None:
        """GET /redoc retorna ReDoc HTML (cobre main.py:643-650)."""
        from app.main import app

        client = TestClient(app)
        resp = client.get("/redoc")
        assert resp.status_code == 200
        assert "text/html" in resp.headers.get("content-type", "")


# =============================================================================
# 2. app/services/protocolo.py — LGPDBlockedError + TipoInvalidoError + protocolo sequencial
# =============================================================================


class TestProtocoloService:
    """Cobre app/services/protocolo.py LGPDBlocked + TipoInvalido + _gerar_numero_protocolo edge."""

    def test_criar_protocolo_svc_lgpd_blocked_raises_and_audit(self) -> None:
        """criar_protocolo_svc com consentimento_lgpd=False raises LGPDBlockedError + audit log."""
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker
        from sqlalchemy.pool import StaticPool

        from app.models.base import Base
        from app.services.protocolo import LGPDBlockedError, criar_protocolo_svc

        eng = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(eng)
        SessionLocal = sessionmaker(
            bind=eng, autoflush=False, autocommit=False, expire_on_commit=False
        )
        db = SessionLocal()
        try:
            with pytest.raises(LGPDBlockedError, match="Consentimento LGPD obrigatorio"):
                criar_protocolo_svc(
                    db,
                    tipo="certidao_negativa",
                    cliente_cpf="12345678901",
                    cliente_nome="Joao Teste",
                    consentimento_lgpd=False,  # GATE LGPD
                    canal_origem="web",
                )
            # Audit log deve ter sido gravado (action=protocolo.create.lgpd_blocked)
            from app.models.audit_log import AuditLog

            entries = (
                db.query(AuditLog).filter(AuditLog.action == "protocolo.create.lgpd_blocked").all()
            )
            assert len(entries) >= 1
            assert entries[0].payload["motivo"] == "consentimento_lgpd=false"
        finally:
            db.close()
            Base.metadata.drop_all(eng)

    def test_criar_protocolo_svc_tipo_invalido_raises(self) -> None:
        """criar_protocolo_svc com tipo fora de TIPOS_VALIDOS raises TipoInvalidoError."""
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker
        from sqlalchemy.pool import StaticPool

        from app.models.base import Base
        from app.services.protocolo import TipoInvalidoError, criar_protocolo_svc

        eng = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(eng)
        SessionLocal = sessionmaker(
            bind=eng, autoflush=False, autocommit=False, expire_on_commit=False
        )
        db = SessionLocal()
        try:
            with pytest.raises(TipoInvalidoError, match="nao esta na tabela de emolumentos"):
                criar_protocolo_svc(
                    db,
                    tipo="tipo_invalido_xyz",
                    cliente_cpf="12345678901",
                    cliente_nome="Maria",
                    consentimento_lgpd=True,
                    canal_origem="whatsapp",
                )
        finally:
            db.close()
            Base.metadata.drop_all(eng)

    def test_criar_protocolo_svc_happy_path(self) -> None:
        """criar_protocolo_svc happy path: protocolo DRAFT criado com audit log."""
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker
        from sqlalchemy.pool import StaticPool

        from app.models.base import Base
        from app.services.protocolo import criar_protocolo_svc

        eng = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(eng)
        SessionLocal = sessionmaker(
            bind=eng, autoflush=False, autocommit=False, expire_on_commit=False
        )
        db = SessionLocal()
        try:
            result = criar_protocolo_svc(
                db,
                tipo="certidao_negativa",
                cliente_cpf="12345678901",
                cliente_nome="Joao Teste",
                consentimento_lgpd=True,
                canal_origem="web",
            )
            assert result["status"] == "criado"
            assert result["estado"] == "DRAFT"
            assert result["numero"].startswith(str(datetime.now(tz=timezone.utc).year))
            assert result["cliente_id"] >= 1
            # HITL message presente
            assert (
                "escrevente" in result["proxima_acao"].lower()
                or "validacao" in result["proxima_acao"].lower()
            )
        finally:
            db.close()
            Base.metadata.drop_all(eng)

    def test_gerar_numero_protocolo_handles_malformed_existing(self) -> None:
        """_gerar_numero_protocolo ignora numero mal formado (sem '-') e comeca do 00001.

        Edge case: se o ultimo protocolo tiver numero malformado (sem '-'),
        o split levanta ValueError -> retorna prefix-00001.
        """
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker
        from sqlalchemy.pool import StaticPool

        from app.models.base import Base
        from app.models.protocolo import Protocolo
        from app.services.protocolo import _gerar_numero_protocolo

        eng = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(eng)
        SessionLocal = sessionmaker(
            bind=eng, autoflush=False, autocommit=False, expire_on_commit=False
        )
        db = SessionLocal()
        try:
            # Insere protocolo com numero malformado (sem '-')
            db.add(
                Protocolo(
                    numero="2026-malformed",
                    cliente_id=1,
                    tipo="certidao",
                    status="DRAFT",
                    canal_origem="presencial",
                )
            )
            db.commit()

            # Deve cair no except e retornar 00001
            numero = _gerar_numero_protocolo(db, ano=2026)
            assert numero == "2026-00001"
        finally:
            db.close()
            Base.metadata.drop_all(eng)


# =============================================================================
# 3. app/api/deps.py — assert_dpo_for_include_deleted (lines 296, 311, 319, 323)
# =============================================================================


class TestDepsIncludeDeleted:
    """Cobre app/api/deps.py::assert_dpo_for_include_deleted (gate admin LGPD)."""

    def test_noop_when_include_deleted_false(self) -> None:
        """assert_dpo_for_include_deleted retorna None sem checagem se include_deleted=False."""
        from fastapi import Request

        from app.api.deps import assert_dpo_for_include_deleted

        mock_req = MagicMock(spec=Request)
        mock_req.headers = {}
        # NAO deve levantar
        result = assert_dpo_for_include_deleted(mock_req, include_deleted=False)
        assert result is None

    def test_raises_401_when_include_deleted_true_without_auth(self) -> None:
        """?include_deleted=true sem Authorization header -> 401."""
        from fastapi import HTTPException, Request

        from app.api.deps import assert_dpo_for_include_deleted

        mock_req = MagicMock(spec=Request)
        mock_req.headers = {}  # sem Authorization
        with pytest.raises(HTTPException) as exc_info:
            assert_dpo_for_include_deleted(mock_req, include_deleted=True)
        assert exc_info.value.status_code == 401
        assert exc_info.value.headers.get("WWW-Authenticate") == "Bearer"

    def test_raises_401_when_jwt_invalid(self) -> None:
        """?include_deleted=true com JWT invalido -> 401."""
        from fastapi import HTTPException, Request

        from app.api.deps import assert_dpo_for_include_deleted

        mock_req = MagicMock(spec=Request)
        mock_req.headers = {"authorization": "Bearer token-invalido"}
        with pytest.raises(HTTPException) as exc_info:
            assert_dpo_for_include_deleted(mock_req, include_deleted=True)
        assert exc_info.value.status_code == 401

    def test_raises_403_when_jwt_valid_but_no_dpo_claim(self) -> None:
        """?include_deleted=true com JWT sem claim dpo -> 403."""
        from fastapi import HTTPException, Request

        from app.api.deps import assert_dpo_for_include_deleted
        from app.services.auth_jwt import issue_access_token

        # Cria JWT sem dpo=True (dpo=False explicito)
        token = issue_access_token("cliente-1", dpo=False)

        mock_req = MagicMock(spec=Request)
        mock_req.headers = {"authorization": f"Bearer {token}"}

        with pytest.raises(HTTPException) as exc_info:
            assert_dpo_for_include_deleted(mock_req, include_deleted=True)
        assert exc_info.value.status_code == 403
        assert "DPO" in str(exc_info.value.detail)

    def test_passes_when_jwt_has_dpo_claim(self) -> None:
        """?include_deleted=true com JWT + dpo=True -> OK (sem excecao)."""
        from fastapi import Request

        from app.api.deps import assert_dpo_for_include_deleted
        from app.services.auth_jwt import issue_access_token

        token = issue_access_token("dpo-1", dpo=True)

        mock_req = MagicMock(spec=Request)
        mock_req.headers = {"authorization": f"Bearer {token}"}

        # NAO deve levantar
        result = assert_dpo_for_include_deleted(mock_req, include_deleted=True)
        assert result is None


# =============================================================================
# 4. app/services/backup_v2.py — OSError + scan exception branches
# =============================================================================


class TestBackupV2EdgeCases:
    """Cobre branches nao testadas em test_backup_v2.py: OSError em getmtime + scan fail."""

    def test_list_complete_backups_handles_oserror_on_getmtime(self, tmp_path: Path) -> None:
        """_list_complete_backups pula diretorios com OSError no getmtime."""
        from app.services.backup_v2 import _list_complete_backups

        # Cria backup completo valido
        valid_dir = tmp_path / "20260713_00"
        valid_dir.mkdir()
        (valid_dir / ".complete").touch()

        # Cria backup com marker mas getmtime vai explodir (mock)
        broken_dir = tmp_path / "20260713_06"
        broken_dir.mkdir()
        (broken_dir / ".complete").touch()

        # Mock os.path.getmtime para explodir quando chamado no broken_dir
        original_getmtime = os.path.getmtime

        def selective_getmtime(path: str) -> float:
            if "20260713_06" in path:
                raise OSError("permission denied")
            return original_getmtime(path)

        with patch("app.services.backup_v2.os.path.getmtime", side_effect=selective_getmtime):
            results = _list_complete_backups(str(tmp_path))

        # Apenas o backup valido deve aparecer
        assert len(results) == 1
        assert results[0][0] == "20260713_00"

    def test_list_complete_backups_skips_files_not_dirs(self, tmp_path: Path) -> None:
        """_list_complete_backups ignora arquivos regulares (so conta diretorios)."""
        from app.services.backup_v2 import _list_complete_backups

        # Cria arquivo (NAO diretorio) — deve ser ignorado
        (tmp_path / "stray_file.txt").write_text("not a backup")

        # Cria diretorio valido
        valid_dir = tmp_path / "20260713_00"
        valid_dir.mkdir()
        (valid_dir / ".complete").touch()

        results = _list_complete_backups(str(tmp_path))
        assert len(results) == 1
        assert results[0][0] == "20260713_00"

    def test_check_backup_v2_scan_exception_returns_empty_with_error(self, tmp_path: Path) -> None:
        """check_backup_v2_freshness: exception durante scan -> empty + error field."""
        from app.services.backup_v2 import (
            BackupHealthStatus,
            check_backup_v2_freshness,
        )

        # Mock _list_complete_backups para explodir (simula permissao negada no mount)
        with patch(
            "app.services.backup_v2._list_complete_backups",
            side_effect=PermissionError("permission denied on /var/backups"),
        ):
            health = check_backup_v2_freshness(backup_dir=str(tmp_path))

        assert health.status == BackupHealthStatus.EMPTY
        assert health.backup_count == 0
        assert health.error is not None
        assert "PermissionError" in health.error
        assert "permission denied" in health.error
        # Alert formatado menciona erro de leitura
        assert health.alert is not None
        assert "erro de leitura" in health.alert


# =============================================================================
# 5. app/api/v1/ws/atendimentos.py — _redis_listener_loop edges
# =============================================================================


class TestRedisListenerLoop:
    """Cobre _redis_listener_loop data validation + exception handlers."""

    async def test_listener_skips_non_dict_messages(self) -> None:
        """_redis_listener_loop ignora mensagens que nao sao dict (cobre ws/atendimentos.py:51-55)."""
        from app.api.v1.ws.atendimentos import _redis_listener_loop
        from app.services.redis_bus import RedisBus

        # Mock manager que NAO espera ser chamado para mensagens nao-dict
        mock_manager = MagicMock()
        mock_manager.broadcast = AsyncMock(return_value=0)
        mock_manager.total_connections = MagicMock(return_value=0)

        # Mock bus que retorna mensagens nao-dict + dict
        mock_bus = MagicMock(spec=RedisBus)

        async def fake_subscribe(channel: str) -> Any:
            yield {"data": "string-nao-dict"}  # deve ser pulado
            yield {"data": 12345}  # deve ser pulado
            yield {"data": None}  # deve ser pulado
            yield {"data": {"evento": "valido"}}  # DEVE ser entregue
            return

        mock_bus.subscribe = fake_subscribe

        # Roda o listener com timeout curto
        async def run_with_timeout() -> None:
            await asyncio.wait_for(
                _redis_listener_loop(mock_manager, mock_bus, "cartorio:atendimentos"),
                timeout=2.0,
            )

        # O listener vai processar tudo e retornar (loop encerra apos yield)
        try:
            await run_with_timeout()
        except asyncio.TimeoutError:
            pass

        # broadcast foi chamado APENAS para o dict valido
        assert mock_manager.broadcast.call_count == 1
        call_args = mock_manager.broadcast.call_args
        assert call_args[0][0] == "cartorio:atendimentos"
        assert call_args[0][1] == {"evento": "valido"}

    async def test_listener_logs_and_swallows_broadcast_exception(self) -> None:
        """_redis_listener_loop captura exception e loga (cobre ws/atendimentos.py:107-108).

        Simula um manager que exploda — o listener NAO deve crashar.
        """
        from app.api.v1.ws.atendimentos import _redis_listener_loop
        from app.services.redis_bus import RedisBus

        # Mock manager que SEMPRE explode
        mock_manager = MagicMock()
        mock_manager.broadcast = AsyncMock(side_effect=RuntimeError("redis disconnected"))
        mock_manager.total_connections = MagicMock(return_value=0)

        mock_bus = MagicMock(spec=RedisBus)

        async def fake_subscribe(channel: str) -> Any:
            yield {"data": {"evento": "trigger"}}
            return

        mock_bus.subscribe = fake_subscribe

        # Listener NAO deve crashar — exception eh engolida + logada
        try:
            await asyncio.wait_for(
                _redis_listener_loop(mock_manager, mock_bus, "cartorio:atendimentos"),
                timeout=2.0,
            )
        except asyncio.TimeoutError:
            pass

        # broadcast foi chamado pelo menos 1x antes de explodir
        assert mock_manager.broadcast.call_count >= 1


# =============================================================================
# 6. app/services/notificacao.py — Exception branches em whatsapp reaction/poll/media
# =============================================================================


class _AsyncCtxExplode:
    """Fake httpx.AsyncClient que explode no __aenter__ para simular network down."""

    def __init__(self, error: Exception | None = None) -> None:
        self._error = error or Exception("network down")

    async def __aenter__(self) -> _AsyncCtxExplode:
        raise self._error

    async def __aexit__(self, *args: object) -> None:
        pass

    async def post(self, *args: object, **kwargs: object) -> MagicMock:
        return MagicMock(status_code=200)


class TestNotificacaoExceptionBranches:
    """Cobre exception handlers nas funcoes Evolution (lines 210-211, 229-231, 237-238, 253-255, 263-264, 283-285)."""

    def setup_method(self) -> None:
        """Configura settings.evolution_api_key antes de cada teste."""
        from app.services import notificacao

        # Garante evolution_api_key setado (early-return sem isso)
        self._patch = patch.object(
            notificacao.settings,
            "evolution_api_key",
            "test-evolution-key",
            create=True,
        )
        self._patch.start()
        patch.object(
            notificacao.settings,
            "evolution_base_url",
            "https://evo.test.com",
            create=True,
        ).start()
        patch.object(
            notificacao.settings,
            "evolution_instance",
            "instance-1",
            create=True,
        ).start()

    def teardown_method(self) -> None:
        self._patch.stop()

    @pytest.mark.asyncio
    async def test_enviar_whatsapp_reaction_exception_returns_false(self) -> None:
        """enviar_whatsapp_reaction captura exception e retorna False (cobre lines 210-211, 229-231)."""
        from app.services.notificacao import NotificationService

        # Configura mock que explode no post
        fake_client = _AsyncCtxExplode(RuntimeError("redis disconnected mid-request"))

        with patch("app.services.notificacao.httpx.AsyncClient", return_value=fake_client):
            result = await NotificationService.enviar_whatsapp_reaction(
                "5511999999999", "msg-id-1", "👍"
            )

        assert result is False

    @pytest.mark.asyncio
    async def test_enviar_whatsapp_reaction_without_api_key_returns_false(self) -> None:
        """enviar_whatsapp_reaction com EVOLUTION_API_KEY vazio retorna False (cobre lines 210-211)."""
        from app.services import notificacao
        from app.services.notificacao import NotificationService

        with patch.object(notificacao.settings, "evolution_api_key", "", create=True):
            result = await NotificationService.enviar_whatsapp_reaction(
                "5511999999999", "msg-id-1", "👍"
            )

        assert result is False

    @pytest.mark.asyncio
    async def test_enviar_whatsapp_poll_exception_returns_false(self) -> None:
        """enviar_whatsapp_poll captura exception e retorna False (cobre lines 237-238, 253-255)."""
        from app.services.notificacao import NotificationService

        fake_client = _AsyncCtxExplode(TimeoutError("evolution timeout"))

        with patch("app.services.notificacao.httpx.AsyncClient", return_value=fake_client):
            result = await NotificationService.enviar_whatsapp_poll(
                "5511999999999",
                "Pergunta?",
                ["opcao 1", "opcao 2"],
            )

        assert result is False

    @pytest.mark.asyncio
    async def test_enviar_whatsapp_poll_without_api_key_returns_false(self) -> None:
        """enviar_whatsapp_poll com EVOLUTION_API_KEY vazio retorna False (cobre lines 237-238)."""
        from app.services import notificacao
        from app.services.notificacao import NotificationService

        with patch.object(notificacao.settings, "evolution_api_key", "", create=True):
            result = await NotificationService.enviar_whatsapp_poll(
                "5511999999999", "Pergunta?", ["op1", "op2"]
            )

        assert result is False

    @pytest.mark.asyncio
    async def test_enviar_whatsapp_media_exception_returns_false(self) -> None:
        """enviar_whatsapp_media captura exception e retorna False (cobre lines 263-264, 283-285)."""
        from app.services.notificacao import NotificationService

        fake_client = _AsyncCtxExplode(ConnectionError("evolution offline"))

        with patch("app.services.notificacao.httpx.AsyncClient", return_value=fake_client):
            result = await NotificationService.enviar_whatsapp_media(
                "5511999999999",
                "https://example.com/file.pdf",
                "document",
                "doc.pdf",
                caption="legenda teste",
            )

        assert result is False

    @pytest.mark.asyncio
    async def test_enviar_whatsapp_media_without_api_key_returns_false(self) -> None:
        """enviar_whatsapp_media com EVOLUTION_API_KEY vazio retorna False (cobre lines 263-264)."""
        from app.services import notificacao
        from app.services.notificacao import NotificationService

        with patch.object(notificacao.settings, "evolution_api_key", "", create=True):
            result = await NotificationService.enviar_whatsapp_media(
                "5511999999999",
                "https://example.com/img.png",
                "image",
                "img.png",
            )

        assert result is False


# =============================================================================
# 7. app/api/v1/integrations.py — openclaw_status + _dispatch_telegram happy/4xx
# =============================================================================


class TestIntegrationsCoverage:
    """Cobre app/api/v1/integrations.py:302, 426, 663, 701-704."""

    def test_openclaw_status_endpoint_returns_agent_health(self) -> None:
        """GET /api/v1/integrations/openclaw delega para agent_health() (cobre line 302)."""
        from unittest.mock import AsyncMock, patch

        from fastapi.testclient import TestClient

        from app.main import app

        # Mocka agent_health (que eh a dependencia interna)
        with patch(
            "app.api.v1.integrations.agent_health",
            AsyncMock(
                return_value={
                    "status": "ok",
                    "openclaw": {"alive": True, "latency_ms": 5},
                    "llm_provider": {"model": "minimax-m3", "latency_ms": 50},
                    "timestamp": "2026-07-13T10:00:00Z",
                }
            ),
        ):
            client = TestClient(app)
            resp = client.get("/api/v1/integrations/openclaw")

        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"

    @pytest.mark.asyncio
    async def test_dispatch_telegram_http_200_returns_none(self) -> None:
        """_dispatch_telegram happy path HTTP 200 nao levanta (cobre line 426)."""
        from app.api.v1.integrations import _dispatch_telegram

        class FakeResp:
            status_code = 200
            text = '{"ok":true}'

        class FakeClient:
            def __init__(self, *args: object, **kwargs: object) -> None:
                pass

            async def __aenter__(self) -> FakeClient:
                return self

            async def __aexit__(self, *args: object) -> None:
                pass

            async def post(self, *args: object, **kwargs: object) -> FakeResp:
                return FakeResp()

        payload = {"bot_token": "dummy", "chat_id": 123, "text": "ola"}

        with patch("app.api.v1.integrations.httpx.AsyncClient", FakeClient):
            # NAO deve levantar
            await _dispatch_telegram(payload)

    @pytest.mark.asyncio
    async def test_dispatch_telegram_http_4xx_raises_runtime_error(self) -> None:
        """_dispatch_telegram com HTTP >= 400 raise RuntimeError (cobre line 430)."""
        from app.api.v1.integrations import _dispatch_telegram

        class FakeResp:
            status_code = 401
            text = "unauthorized bot"

        class FakeClient:
            def __init__(self, *args: object, **kwargs: object) -> None:
                pass

            async def __aenter__(self) -> FakeClient:
                return self

            async def __aexit__(self, *args: object) -> None:
                pass

            async def post(self, *args: object, **kwargs: object) -> FakeResp:
                return FakeResp()

        payload = {"bot_token": "dummy", "chat_id": 123, "text": "ola"}

        with patch("app.api.v1.integrations.httpx.AsyncClient", FakeClient):
            with pytest.raises(RuntimeError, match="telegram HTTP 401"):
                await _dispatch_telegram(payload)

    def test_n8n_error_webhook_audit_log_failure_is_fail_soft(self) -> None:
        """n8n_error_webhook: DB exception durante audit log NAO retorna 500 (fail-soft) (cobre 701-704).

        Se AuditService.log explodir, o endpoint DEVE retornar 200 com status=queued
        + incrementar metrica Prometheus (fail-soft LGPD art. 37).
        """
        import hashlib
        import hmac

        from unittest.mock import patch

        from fastapi.testclient import TestClient

        from app.main import app

        # Setup: precisa de N8N_WEBHOOK_SECRET para passar HMAC check
        secret = "n8n-webhook-test-secret-2026-07-13"
        payload = {
            "workflow_name": "01 - Test Sprint8",
            "execution_id": "exec-fail-soft-test",
            "error": {
                "name": "NodeApiError",
                "message": "ECONNREFUSED test",
                "http_code": 500,
            },
        }
        body = json.dumps(payload).encode("utf-8")
        sig = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()

        with patch.dict(os.environ, {"N8N_WEBHOOK_SECRET": secret}):
            # Forca DB exception dentro do AuditService.log
            with patch("app.api.v1.integrations.AuditService.log") as mock_log:
                mock_log.side_effect = RuntimeError("DB offline")

                client = TestClient(app)
                resp = client.post(
                    "/api/v1/integrations/n8n/error",
                    content=body,
                    headers={
                        "Content-Type": "application/json",
                        "X-N8N-Signature": sig,
                    },
                )

        # Fail-soft: 200 OK mesmo com audit failure
        assert resp.status_code == 200, (
            f"Expected 200 fail-soft, got {resp.status_code}: {resp.text}"
        )
        data = resp.json()
        # audit_id=None quando audit log falhou
        assert data["audit_id"] is None
        # Status eh 'queued' (nao 'accepted') — fail-soft marker
        assert data["status"] == "queued"


# =============================================================================
# 8. app/api/v1/lgpd_direitos_v2.py — _truncate_ip / _parse_payload / _scrub helpers + D32 endpoint
# =============================================================================


class TestLGPDDireitosV2Helpers:
    """Cobre helpers privados em lgpd_direitos_v2.py: _truncate_ip, _parse_payload, _scrub."""

    def test_truncate_ip_ipv4_normal(self) -> None:
        """_truncate_ip_for_response: IPv4 -> /24 mask (cobre line 775)."""
        from app.api.v1.lgpd_direitos_v2 import _truncate_ip_for_response

        assert _truncate_ip_for_response("203.0.113.42") == "203.0.113.0"

    def test_truncate_ip_ipv6_normal(self) -> None:
        """_truncate_ip_for_response: IPv6 -> primeiros 3 grupos + :: (cobre lines 770-772)."""
        from app.api.v1.lgpd_direitos_v2 import _truncate_ip_for_response

        result = _truncate_ip_for_response("2001:db8:abcd:1234:5678:9abc:def0:1234")
        assert result == "2001:db8:abcd::"

    def test_truncate_ip_none_returns_none(self) -> None:
        """_truncate_ip_for_response(None) -> None (cobre line 768-769)."""
        from app.api.v1.lgpd_direitos_v2 import _truncate_ip_for_response

        assert _truncate_ip_for_response(None) is None
        assert _truncate_ip_for_response("") is None

    def test_truncate_ip_invalid_format_returns_unchanged(self) -> None:
        """_truncate_ip_for_response: IP fora do formato padrao retorna original (cobre line 776)."""
        from app.api.v1.lgpd_direitos_v2 import _truncate_ip_for_response

        # IPv4 com 3 partes (incompleto)
        assert _truncate_ip_for_response("192.168.1") == "192.168.1"

    def test_parse_payload_dict_returns_as_is(self) -> None:
        """_parse_payload: dict retorna mesma referencia (cobre line 781-782)."""
        from app.api.v1.lgpd_direitos_v2 import _parse_payload

        payload = {"key": "value", "nested": {"a": 1}}
        result = _parse_payload(payload)
        assert result is payload  # mesmo objeto

    def test_parse_payload_json_string_returns_parsed(self) -> None:
        """_parse_payload: string JSON valida retorna dict parseado (cobre line 783-785)."""
        from app.api.v1.lgpd_direitos_v2 import _parse_payload

        result = _parse_payload('{"key":"value","num":42}')
        assert result == {"key": "value", "num": 42}

    def test_parse_payload_invalid_json_returns_empty_dict(self) -> None:
        """_parse_payload: string invalida retorna {} (cobre lines 786-787)."""
        from app.api.v1.lgpd_direitos_v2 import _parse_payload

        result = _parse_payload("not valid json {")
        assert result == {}

    def test_parse_payload_none_returns_empty_dict(self) -> None:
        """_parse_payload: None retorna {} (cobre line 788-789)."""
        from app.api.v1.lgpd_direitos_v2 import _parse_payload

        result = _parse_payload(None)
        assert result == {}

    def test_parse_payload_unknown_type_returns_empty_dict(self) -> None:
        """_parse_payload: tipo desconhecido (int, list) retorna {} (cobre line 790)."""
        from app.api.v1.lgpd_direitos_v2 import _parse_payload

        assert _parse_payload(12345) == {}
        assert _parse_payload([1, 2, 3]) == {}

    def test_scrub_payload_pii_removes_sensitive_fields(self) -> None:
        """_scrub_payload_pii remove ip/user_agent/request_id e mantem apenas safe keys (cobre line 800)."""
        from app.api.v1.lgpd_direitos_v2 import _scrub_payload_pii

        payload = {
            "action": "lgpd.access",
            "resource": "cliente:1",
            "canal": "web",
            "ip": "203.0.113.42",  # DEVE ser removido
            "user_agent": "Mozilla/5.0...",  # DEVE ser removido
            "request_id": "req-abc-123",  # DEVE ser removido
            "ip_truncated": "203.0.113.0",  # DEVE ser removido
            "finalidade": "atendimento",  # safe — manter
            "granted": True,  # safe — manter
            "campo_unsafe": "valor qualquer",  # NAO safe — remover
        }
        scrubbed = _scrub_payload_pii(payload)
        assert "ip" not in scrubbed
        assert "user_agent" not in scrubbed
        assert "request_id" not in scrubbed
        assert "ip_truncated" not in scrubbed
        assert "campo_unsafe" not in scrubbed
        # Safe keys preservados
        assert scrubbed["action"] == "lgpd.access"
        assert scrubbed["resource"] == "cliente:1"
        assert scrubbed["canal"] == "web"
        assert scrubbed["finalidade"] == "atendimento"
        assert scrubbed["granted"] is True

    def test_scrub_payload_pii_empty_returns_empty_dict(self) -> None:
        """_scrub_payload_pii com payload vazio/None retorna {}."""
        from app.api.v1.lgpd_direitos_v2 import _scrub_payload_pii

        assert _scrub_payload_pii({}) == {}
        assert _scrub_payload_pii(None) == {}  # type: ignore[arg-type]


# =============================================================================
# 9. app/main.py — Lifespan startup branches (DMS / Retenção desabilitados)
# =============================================================================


class TestMainLifespanConfigGates:
    """Cobre main.py lifespan quando DMS/Retencao estao desabilitados.

    settings.audit_dead_mans_switch_minutes=0   -> NAO spawna task DMS
    settings.retencao_enabled=False             -> NAO spawna task retencao
    """

    def test_lifespan_skips_dms_task_when_disabled(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """audit_dead_mans_switch_minutes=0 NAO cria dead_mans_switch_loop task (cobre main.py:141-150)."""
        # Patch settings.audit_dead_mans_switch_minutes=0 in-place
        from app.config import settings

        monkeypatch.setattr(settings, "audit_dead_mans_switch_minutes", 0)

        from app.main import lifespan

        # Spy: capturar create_task
        created_tasks: list[asyncio.Task] = []
        original_create_task = asyncio.create_task

        def spy_create_task(coro, *, name: str | None = None) -> asyncio.Task:  # type: ignore[no-untyped-def]
            task = original_create_task(coro, name=name)
            created_tasks.append(task)
            task.cancel()
            return task

        monkeypatch.setattr(asyncio, "create_task", spy_create_task)

        app = FastAPI()

        async def run_lifespan() -> None:
            async with lifespan(app):
                pass

        asyncio.run(run_lifespan())

        dms_tasks = [t for t in created_tasks if t.get_name() == "dead_mans_switch_loop"]
        assert len(dms_tasks) == 0, f"DMS task nao deveria ter sido criada: {dms_tasks}"

    def test_lifespan_skips_retencao_task_when_disabled(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """retencao_enabled=False NAO cria retencao_scheduler_loop task (cobre main.py:156-165)."""
        from app.config import settings

        monkeypatch.setattr(settings, "retencao_enabled", False)

        from app.main import lifespan

        created_tasks: list[asyncio.Task] = []
        original_create_task = asyncio.create_task

        def spy_create_task(coro, *, name: str | None = None) -> asyncio.Task:  # type: ignore[no-untyped-def]
            task = original_create_task(coro, name=name)
            created_tasks.append(task)
            task.cancel()
            return task

        monkeypatch.setattr(asyncio, "create_task", spy_create_task)

        app = FastAPI()

        async def run_lifespan() -> None:
            async with lifespan(app):
                pass

        asyncio.run(run_lifespan())

        retencao_tasks = [t for t in created_tasks if t.get_name() == "retencao_scheduler_loop"]
        assert len(retencao_tasks) == 0, (
            f"Retencao task nao deveria ter sido criada: {retencao_tasks}"
        )

    def test_dead_mans_switch_loop_skips_cycle_when_lock_held_by_peer(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """_dead_mans_switch_loop: lock held by peer (lock_token=None) -> pula o ciclo (cobre main.py:69-76)."""
        from app.main import _dead_mans_switch_loop

        # Force interval minimo para rodar rapido
        from app.config import settings

        monkeypatch.setattr(settings, "audit_dead_mans_switch_interval_minutes", 1)

        # acquire_lock/release_lock sao lazy-imported em main.py:60-61 dentro do modulo app.services.redlock
        # Mock acquire_lock para retornar None (peer tem lock)
        monkeypatch.setattr(
            "app.services.redlock.acquire_lock",
            lambda name, ttl_seconds: None,
        )
        # Mock release_lock como no-op
        release_calls: list[str] = []
        monkeypatch.setattr(
            "app.services.redlock.release_lock",
            lambda name, token: release_calls.append(name),
        )

        async def run_loop() -> None:
            task = asyncio.create_task(_dead_mans_switch_loop())
            await asyncio.sleep(0.1)
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

        asyncio.run(run_loop())

        # release_lock NAO deve ter sido chamado (lock_token era None)
        assert release_calls == []

    def test_dead_mans_switch_loop_executes_check_when_lock_acquired(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """_dead_mans_switch_loop: lock acquired -> executa check + release no finally (cobre main.py:73-90).

        Foca na execucao do ciclo: acquire_lock -> session_scope -> check -> release_lock.
        """
        from unittest.mock import MagicMock

        from app.main import _dead_mans_switch_loop

        # sleep original eh capturado em variavel ANTES do patch — usado
        # para yields reais do test runner (sem mockar o sleep do test).
        real_sleep = asyncio.sleep

        # acquire_lock retorna token (lock acquired)
        monkeypatch.setattr(
            "app.services.redlock.acquire_lock",
            lambda name, ttl_seconds: "fake-token-xyz",
        )
        release_calls: list[tuple[str, str]] = []
        monkeypatch.setattr(
            "app.services.redlock.release_lock",
            lambda name, token: release_calls.append((name, token)),
        )

        mock_result = MagicMock()
        mock_result.health.status.value = "healthy"
        mock_result.alerted = False
        mock_result.telegram_sent = False

        scope_called = []

        @contextlib.contextmanager
        def fake_session_scope():
            scope_called.append(True)
            yield MagicMock()

        monkeypatch.setattr("app.db.session_scope", fake_session_scope)
        monkeypatch.setattr("app.main.session_scope", fake_session_scope)
        monkeypatch.setattr(
            "app.jobs.cron_dead_mans_switch.run_dead_mans_switch_check_3lvl",
            lambda db: mock_result,
        )

        # Patch sleep no main module (somente o sleep que a LOOP chama)
        # mas DEIXA o sleep do test runner intacto.
        sleep_calls: list[float] = []

        async def tracked_sleep(seconds: float) -> None:
            sleep_calls.append(seconds)
            # Para todos os sleeps da LOOP (30s init + Ns interval), retorna rapido
            await real_sleep(0)

        monkeypatch.setattr("app.main.asyncio.sleep", tracked_sleep)

        async def run_loop() -> None:
            task = asyncio.create_task(_dead_mans_switch_loop())
            # Da tempo da loop rodar: initial sleep (30s -> 0) + 1 ciclo
            try:
                await asyncio.wait_for(asyncio.shield(task), timeout=2.0)
            except (asyncio.TimeoutError, asyncio.CancelledError):
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass

        asyncio.run(run_loop())

        # sleep foi chamado (initial 30s + interval)
        assert sleep_calls, f"sleep nao foi chamado: {sleep_calls}"
        # fake_session_scope DEVE ter sido chamado
        assert scope_called, "fake_session_scope nao foi invocado — patches nao funcionaram"
        # release_lock DEVE ter sido chamado (finally block)
        assert len(release_calls) >= 1, f"release_lock nao foi chamado: {release_calls}"
        assert release_calls[0] == ("dms-loop", "fake-token-xyz")


# =============================================================================
# Test runner helpers — executa 1 target group isoladamente se invocado direto
# =============================================================================


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])


# =============================================================================
# Test runner helpers — executa 1 target group isoladamente se invocado direto
# =============================================================================


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
