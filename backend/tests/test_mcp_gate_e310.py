"""E3.10 — Gate formal MCP: inventário, schema, erros estruturados, PII, HITL.

Prova o gate de produção do servidor MCP (protocolo 2025-03-26, montado em
/mcp) de forma offline:

  1. DESCOBERTA: 14/14 tools discoverable via introspecção do FastMCP
     (list_tools) — sem hardcode de nomes; apenas a contagem 14 é pinada.
  2. SCHEMA: cada tool tem name/description não-vazios e `parameters` é
     JSON Schema objeto válido (type=object, properties dict).
  3. ERROS ESTRUTURADOS: falhas internas das tools de envio retornam
     {sucesso: False, erro, mensagem, tipo_erro} — padrão de
     test_mcp_tool_errors_e206.py, nunca str(exc) cru.
  4. PII SCRUB em tool errors: token de bot, CPF e telefone fake injetados
     na exceção NUNCA aparecem no resultado.
  5. HITL: sucesso de cartorio_criar_protocolo mantém estado DRAFT e
     próxima ação de validação humana.
  6. AUTH (boundary HTTP): sem API key -> 401; key inválida -> 401;
     sem key configurada -> 503 fail-closed. (Suíte completa existente:
     tests/test_mcp_http_auth.py — referenciada, não duplicada aqui além
     do smoke fail-closed.)
  7. TIMEOUT: exceções de timeout internas (asyncio.TimeoutError) também
     saem como erro estruturado + scrubbed. Timeout de rede real contra
     Telegram/Evolution em prod: BLOCKED (exige sandbox com latência
     injetada — fora do escopo offline).

Modified by Gustavo Almeida — E3.10 gate formal.
"""

from __future__ import annotations

import asyncio
import contextlib
import importlib.util
import sys
from pathlib import Path
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[1]
MCP_SERVER = ROOT / "mcp_server.py"

EXPECTED_TOOL_COUNT = 15  # snapshot E3.10 + Stage 7 — introspecção, não lista de nomes

# Formato realista de bot token Telegram: casa _BOT_TOKEN_RE do mcp_server
# (bot\d+:[A-Za-z0-9_-]{10,}) para exercitar _strip_secrets de verdade.
FAKE_TOKEN = "123456789:AAfakeTokenGateE310-abcdefghij"
FAKE_CPF = "123.456.789-09"
FAKE_PHONE = "5534999998888"


@pytest.fixture(scope="module")
def mcp_module():
    """Importa mcp_server.py dinamicamente (arquivo solto, não pacote)."""
    spec = importlib.util.spec_from_file_location("mcp_server", MCP_SERVER)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    sys.modules.pop("mcp_server", None)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def mcp_tools(mcp_module) -> dict[str, Any]:
    """Descoberta real via introspecção do FastMCP (sem hardcode de nomes)."""
    tools = asyncio.run(mcp_module.mcp.list_tools())
    return {t.name: t for t in tools}


def _assert_no_leak(result: Any) -> None:
    blob = str(result)
    assert FAKE_TOKEN not in blob
    assert "bot" + FAKE_TOKEN not in blob
    assert FAKE_CPF not in blob
    assert FAKE_PHONE not in blob


# ============================================================
# 1+2. Descoberta 14/14 + schema válido
# ============================================================


class TestGateDiscovery:
    def test_exactly_14_tools_discoverable(self, mcp_tools) -> None:
        assert len(mcp_tools) == EXPECTED_TOOL_COUNT, (
            f"Esperado {EXPECTED_TOOL_COUNT} tools via introspecção, "
            f"achou {len(mcp_tools)}: {sorted(mcp_tools)}"
        )

    def test_tool_names_unique_and_prefixed(self, mcp_tools) -> None:
        names = list(mcp_tools)
        assert len(names) == len(set(names))
        # Convenção do servidor: tools de domínio usam prefixo cartorio_;
        # tools de plataforma (super_*) são a exceção documentada.
        for name in names:
            assert name.startswith(("cartorio_", "super_")), f"nome fora da convenção: {name}"

    def test_every_tool_has_valid_schema(self, mcp_tools) -> None:
        for name, tool in mcp_tools.items():
            assert isinstance(tool.name, str) and tool.name, f"{name}: name vazio"
            assert isinstance(tool.description, str) and tool.description.strip(), (
                f"{name}: description vazia"
            )
            params = tool.parameters
            assert isinstance(params, dict), f"{name}: parameters não é dict"
            assert params.get("type") == "object", f"{name}: parameters.type != object"
            assert isinstance(params.get("properties", {}), dict), (
                f"{name}: parameters.properties inválido"
            )

    def test_descriptions_carry_lgpd_or_pii_guidance_where_relevant(self, mcp_tools) -> None:
        """Tools que tocam PII/mutação devem declarar governança na description."""
        joined = {name: (tool.description or "").lower() for name, tool in mcp_tools.items()}
        # criar_protocolo: mutação sensível — description deve mencionar HITL/LGPD/DRAFT.
        criar = next(n for n in joined if "criar_protocolo" in n)
        assert any(k in joined[criar] for k in ("hitl", "lgpd", "draft", "valida")), (
            f"description de {criar} sem guidance de governança: {joined[criar]!r}"
        )


# ============================================================
# 3+4+7. Erros estruturados + PII scrub + timeout (offline)
# ============================================================


class TestGateStructuredErrors:
    """Padrão reusado de test_mcp_tool_errors_e206.py — gate formal E3.10."""

    def _assert_structured(self, result: Any, exc_name: str) -> None:
        assert isinstance(result, dict)
        assert result["sucesso"] is False
        assert result["erro"] == "SEND_FAILED"
        assert isinstance(result["mensagem"], str)
        assert result["tipo_erro"] == exc_name
        _assert_no_leak(result)

    async def test_send_tool_timeout_error_is_structured_and_scrubbed(
        self, mcp_module, monkeypatch
    ) -> None:
        """Timeout interno (asyncio.TimeoutError) -> erro estruturado, sem leak."""

        async def _slow(chat_id, question, options):
            raise asyncio.TimeoutError(f"poll timeout para {FAKE_PHONE} cpf {FAKE_CPF}")

        monkeypatch.setattr("app.api.v1.telegram._send_poll", _slow)
        result = await mcp_module.cartorio_enviar_telegram_poll(123, "P?", ["a", "b"])
        self._assert_structured(result, "TimeoutError")

    async def test_send_tool_runtime_error_with_bot_token_scrubbed(
        self, mcp_module, monkeypatch
    ) -> None:
        async def _boom(chat_id, doc_url, filename, caption=None):
            raise RuntimeError(
                f"POST https://api.telegram.org/bot{FAKE_TOKEN}/sendDocument "
                f"500 chat={FAKE_PHONE} cpf={FAKE_CPF}"
            )

        monkeypatch.setattr("app.api.v1.telegram._send_document", _boom)
        result = await mcp_module.cartorio_enviar_telegram_media(
            123, "https://x/doc.pdf", "document", "doc.pdf"
        )
        self._assert_structured(result, "RuntimeError")

    async def test_whatsapp_tool_error_scrubbed(self, mcp_module, monkeypatch) -> None:
        async def _boom(number, message_id, emoji):
            raise RuntimeError(f"Evolution 500 {FAKE_PHONE} {FAKE_CPF}")

        monkeypatch.setattr(
            "app.services.notificacao.NotificationService.enviar_whatsapp_reaction",
            staticmethod(_boom),
        )
        result = await mcp_module.cartorio_enviar_whatsapp_reaction(FAKE_PHONE, "mid", "👍")
        self._assert_structured(result, "RuntimeError")


# ============================================================
# 5. HITL DRAFT preservado
# ============================================================


class TestGateHITL:
    async def test_criar_protocolo_sucesso_nasce_draft(self, mcp_module, monkeypatch) -> None:
        svc_payload = {
            "status": "criado",
            "numero": "2026-00099",
            "protocolo_id": 99,
            "estado": "DRAFT",
            "proxima_acao": (
                "Aguardando validacao humana do escrevente. "
                "O protocolo NAO sera processado ate confirmacao no painel admin."
            ),
            "cliente_id": 7,
        }

        @contextlib.contextmanager
        def _fake_scope():
            yield object()

        monkeypatch.setattr("app.db.session_scope", _fake_scope)
        monkeypatch.setattr(
            "app.services.protocolo.criar_protocolo_svc", lambda *a, **k: dict(svc_payload)
        )
        result = await mcp_module.cartorio_criar_protocolo(
            tipo="certidao_negativa",
            cliente_cpf=FAKE_CPF,
            cliente_nome="Cliente X",
            consentimento_lgpd=True,
        )
        assert result["estado"] == "DRAFT"
        assert "validacao humana" in result["proxima_acao"]

    async def test_criar_protocolo_lgpd_gate_sem_consentimento(self, mcp_module) -> None:
        result = await mcp_module.cartorio_criar_protocolo(
            tipo="certidao_negativa",
            cliente_cpf=FAKE_CPF,
            cliente_nome="Cliente X",
            consentimento_lgpd=False,
        )
        assert result["erro"] == "LGPD_BLOCKED"
        _assert_no_leak(result)

    async def test_criar_protocolo_internal_error_scrubbed(self, mcp_module, monkeypatch) -> None:
        @contextlib.contextmanager
        def _fake_scope():
            yield object()

        def _boom(*args, **kwargs):
            raise RuntimeError(f"insert falhou cpf {FAKE_CPF} tel {FAKE_PHONE}")

        monkeypatch.setattr("app.db.session_scope", _fake_scope)
        monkeypatch.setattr("app.services.protocolo.criar_protocolo_svc", _boom)
        result = await mcp_module.cartorio_criar_protocolo(
            tipo="certidao_negativa",
            cliente_cpf=FAKE_CPF,
            cliente_nome="Cliente X",
            consentimento_lgpd=True,
        )
        assert result["erro"] == "INTERNAL_ERROR"
        _assert_no_leak(result)


# ============================================================
# 6. Auth boundary (smoke fail-closed; suíte completa: test_mcp_http_auth.py)
# ============================================================


class TestGateAuthBoundary:
    """Referência: tests/test_mcp_http_auth.py cobre a matriz completa
    (sem key -> 401, key errada -> 401, key ok -> 200, key não configurada
    -> 503 fail-closed). Aqui apenas o smoke offline do gate fail-closed."""

    def test_auth_boundary_fail_closed_smoke(self, mcp_module, monkeypatch) -> None:
        from fastapi.testclient import TestClient

        monkeypatch.setattr(mcp_module.settings, "mcp_api_key", "gate-key")
        headers = {
            "accept": "application/json, text/event-stream",
            "content-type": "application/json",
        }
        init_req = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2025-03-26",
                "capabilities": {},
                "clientInfo": {"name": "gate-e310", "version": "1.0"},
            },
        }
        with TestClient(mcp_module.mcp_app()) as client:
            assert client.post("/", json=init_req, headers=headers).status_code == 401
            assert (
                client.post(
                    "/", json=init_req, headers={**headers, "authorization": "Bearer wrong"}
                ).status_code
                == 401
            )
            ok = client.post(
                "/", json=init_req, headers={**headers, "authorization": "Bearer gate-key"}
            )
            assert ok.status_code == 200

        # Fail-closed quando key não configurada.
        monkeypatch.setattr(mcp_module.settings, "mcp_api_key", None)
        with TestClient(mcp_module.mcp_app()) as client:
            assert (
                client.post(
                    "/", json=init_req, headers={**headers, "authorization": "Bearer x"}
                ).status_code
                == 503
            )
