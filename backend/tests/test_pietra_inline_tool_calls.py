"""Regression tests: tool_call INLINE do MiniMax (`]<]minimax[>[<tool_call>…`)
nunca vaza no content do canal /api/v1/pietra/chat/completions.

Root cause (evidencia real prod 2026-07-28, campanha bulk 10K):
- O upstream MiniMax as vezes emite o tool call como MARKUP INLINE no content
  em vez do campo estruturado `tool_calls`. O thin-shell repassava cru ao
  cliente → vazava `]<]minimax[>`, `<invoke name="cartorio_calcular_emolumento">`
  (internal vocab leak P0) e a REGRA DE OURO (tool call antes de valor) morria
  porque o caller (Hermes) nao recebia tool_calls estruturados.

Fix esperado:
1. Content com markup inline parseavel → resposta vira finish_reason=tool_calls
   com tool_calls estruturados (caller executa via MCP); content limpo do markup.
2. Markup nao-parseavel/truncado → markup removido, texto saneado entregue.
3. NUNCA vazar "minimax", "<invoke", "<tool_call", "]<]" no content final.

Padrao: teste FALHA se regredir. Modified by Gustavo Almeida · 2026-07-28
"""

from __future__ import annotations

import os
from typing import Any

import pytest
from fastapi.testclient import TestClient

# Transcripts reais capturados em prod (2026-07-28 09:35 UTC, bulk10k emol).
INLINE_TOOL_CALL_REAL = (
    "Vou consultar a tabela de emolumentos vigente para te informar o valor "
    "correto.]<]minimax[>[<tool_call>\n]<]minimax[>["
    '<invoke name="cartorio_calcular_emolumento">]<]minimax[>[<act>procuracao]'
    "<]minimax[>[</act>]<]minimax[>[</invoke>"
)

INLINE_TOOL_CALL_PARAM_INVOKE = (
    "Deixa eu consultar o valor.]<]minimax[>[<tool_call>\n]<]minimax[>["
    '<invoke name="cartorio_calcular_emolumento">]<]minimax[>[<invoke name="ato">'
    "divórcio extrajudicial]<]minimax[>[</invoke>"
)

INLINE_TOOL_CALL_TRUNCATED = (
    "Vou consultar a tabela.]<]minimax[>[<tool_call>\n]<]minimax[>["
    '<invoke name="cartorio_calcular_emolumen'
)

# Variantes reais capturadas em prod pós-deploy 57653357 (2026-07-28 13:0x UTC)
# — o upstream improvisa MAIS de um formato de tool call inline.
INLINE_FUNCTION_CALLS_ANTHROPIC_STYLE = (
    "<function_calls>\n"
    '<invoke name="cartorio_calcular_emolumento">\n'
    '<parameter name="ato">procuracao</parameter>\n'
    "</invoke>\n"
    "</function_calls>"
)

INLINE_TOOL_CALL_JSON_MARKER = (
    "Vou consultar a tabela de emolumentos vigente para te passar o valor exato."
    '[TOOL_CALL]\n{"name": "cartorio_calcular_emolumento", "arguments": {"ato": "procuracao"}}'
)

INLINE_TOOL_CALL_JSON_TRUNCATED = (
    "Deixa eu verificar.[TOOL_CALL]\n"
    '{"name": "cartorio_calcular_emolumen'
)

LEAK_TOKENS = ("minimax", "<invoke", "<tool_call", "]<]", "<act>", "</act>",
               "<function_calls", "</function_calls", "[tool_call]", "<parameter")


@pytest.fixture(scope="module")
def client():
    os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
    os.environ.setdefault("REDIS_URL", "redis://localhost:6379/15")
    os.environ.setdefault("ENV", "test")
    from app.main import app

    return TestClient(app)


def _patch_llm(monkeypatch, content: str):
    async def fake(messages, tools=None, **kwargs):
        return {"content": content}, "minimax_direct:MiniMax-M3", ""

    monkeypatch.setattr("app.services.cartorio_agent._chat_completion", fake)


def _post(client) -> Any:
    return client.post(
        "/api/v1/pietra/chat/completions",
        json={"messages": [{"role": "user", "content": "quanto custa uma procuração?"}]},
    )


class TestInlineToolCallConversion:
    def test_inline_markup_vira_tool_calls_estruturados(self, client, monkeypatch):
        """Markup inline parseavel → finish_reason=tool_calls + tool_calls[0]
        com name cartorio_calcular_emolumento e arguments contendo o ato."""
        _patch_llm(monkeypatch, INLINE_TOOL_CALL_REAL)
        r = _post(client)
        assert r.status_code == 200
        choice = r.json()["choices"][0]
        assert choice["finish_reason"] == "tool_calls"
        tcs = choice["message"]["tool_calls"]
        assert tcs and tcs[0]["function"]["name"] == "cartorio_calcular_emolumento"
        import json as _json

        args = _json.loads(tcs[0]["function"]["arguments"])
        assert "procuracao" in _json.dumps(args).lower().replace("ç", "c")

    def test_content_limpo_de_markup_quando_converte(self, client, monkeypatch):
        """Content textual antes do markup é preservado; markup NUNCA vaza."""
        _patch_llm(monkeypatch, INLINE_TOOL_CALL_REAL)
        r = _post(client)
        content = r.json()["choices"][0]["message"].get("content") or ""
        for token in LEAK_TOKENS:
            assert token not in content.lower(), f"vazou {token!r} no content"
        assert "consultar" in content  # prefixo textual preservado

    def test_param_via_invoke_aninhado(self, client, monkeypatch):
        """Variante com <invoke name='ato'>valor</invoke> também parseia."""
        _patch_llm(monkeypatch, INLINE_TOOL_CALL_PARAM_INVOKE)
        r = _post(client)
        choice = r.json()["choices"][0]
        assert choice["finish_reason"] == "tool_calls"
        args = choice["message"]["tool_calls"][0]["function"]["arguments"]
        assert "divórcio" in args or "divorcio" in args

    def test_markup_truncado_nao_vaza(self, client, monkeypatch):
        """Tool call truncado (max_tokens) → markup removido, texto saneado,
        SEM tool_calls quebrados. Nunca retorna markup cru."""
        _patch_llm(monkeypatch, INLINE_TOOL_CALL_TRUNCATED)
        r = _post(client)
        assert r.status_code == 200
        choice = r.json()["choices"][0]
        content = choice["message"].get("content") or ""
        for token in LEAK_TOKENS:
            assert token not in content.lower(), f"vazou {token!r} no content"
        # truncado nao vira tool_call estruturado invalido
        if choice["finish_reason"] == "tool_calls":
            assert choice["message"]["tool_calls"][0]["function"]["name"]

    def test_resposta_normal_sem_markup_intacta(self, client, monkeypatch):
        """Resposta comum (sem markup) segue fluxo normal stop."""
        _patch_llm(monkeypatch, "Sou a Pietra. O valor é confirmado pelo escrevente.")
        r = _post(client)
        choice = r.json()["choices"][0]
        assert choice["finish_reason"] == "stop"
        assert "escrevente" in choice["message"]["content"]


class TestStripUnitario:
    """Nivel unitario: funcao de extracao em cartorio_agent."""

    def test_extract_basico(self):
        from app.services.cartorio_agent import _extract_inline_tool_calls

        text, calls = _extract_inline_tool_calls(INLINE_TOOL_CALL_REAL)
        assert calls and calls[0]["function"]["name"] == "cartorio_calcular_emolumento"
        assert "]<]" not in text and "consultar" in text

    def test_extract_sem_markup(self):
        from app.services.cartorio_agent import _extract_inline_tool_calls

        text, calls = _extract_inline_tool_calls("Olá, tudo bem?")
        assert calls == [] and text == "Olá, tudo bem?"

    def test_extract_truncado(self):
        from app.services.cartorio_agent import _extract_inline_tool_calls

        text, calls = _extract_inline_tool_calls(INLINE_TOOL_CALL_TRUNCATED)
        assert calls == []  # incompleto → sem tool_call quebrado
        for token in LEAK_TOKENS:
            assert token not in text.lower()

    def test_extract_anthropic_style(self):
        """Formato <function_calls><invoke><parameter> (prod 13:0x UTC)."""
        from app.services.cartorio_agent import _extract_inline_tool_calls

        text, calls = _extract_inline_tool_calls(INLINE_FUNCTION_CALLS_ANTHROPIC_STYLE)
        assert calls and calls[0]["function"]["name"] == "cartorio_calcular_emolumento"
        import json as _json

        args = _json.loads(calls[0]["function"]["arguments"])
        assert args.get("ato") == "procuracao"
        for token in LEAK_TOKENS:
            assert token not in text.lower()

    def test_extract_json_marker(self):
        """Formato [TOOL_CALL] + JSON (prod 13:0x UTC)."""
        from app.services.cartorio_agent import _extract_inline_tool_calls

        text, calls = _extract_inline_tool_calls(INLINE_TOOL_CALL_JSON_MARKER)
        assert calls and calls[0]["function"]["name"] == "cartorio_calcular_emolumento"
        assert "consultar" in text
        for token in LEAK_TOKENS:
            assert token not in text.lower()

    def test_extract_json_truncado(self):
        """[TOOL_CALL] com JSON cortado → strip, sem call quebrado."""
        from app.services.cartorio_agent import _extract_inline_tool_calls

        text, calls = _extract_inline_tool_calls(INLINE_TOOL_CALL_JSON_TRUNCATED)
        assert calls == []
        for token in LEAK_TOKENS:
            assert token not in text.lower()


class TestEndpointVariantesInline:
    def test_anthropic_style_nao_vaza_no_endpoint(self, client, monkeypatch):
        _patch_llm(monkeypatch, INLINE_FUNCTION_CALLS_ANTHROPIC_STYLE)
        r = _post(client)
        choice = r.json()["choices"][0]
        assert choice["finish_reason"] == "tool_calls"
        content = choice["message"].get("content") or ""
        for token in LEAK_TOKENS:
            assert token not in content.lower()

    def test_json_marker_nao_vaza_no_endpoint(self, client, monkeypatch):
        _patch_llm(monkeypatch, INLINE_TOOL_CALL_JSON_MARKER)
        r = _post(client)
        choice = r.json()["choices"][0]
        assert choice["finish_reason"] == "tool_calls"
        content = choice["message"].get("content") or ""
        for token in LEAK_TOKENS:
            assert token not in content.lower()
