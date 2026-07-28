"""Regression tests para pietra_outbound_guard (evidencia real prod 2026-07-28).

Root causes cobertos (campanha iMessage, 2044 mensagens analisadas):
- RC-INFRA: lixo de infra vazava CRU ao cliente em ingles —
  "⚡ Interrupting current task", "model provider is rate-limiting",
  "empty response stream", "Sorry, I encountered an unexpected error".
- RC-LANG: language mixing no meio do PT-BR — russo ("Mas есть uma boa
  notícia") e chines ("então，大概 R$ 22-33").

Fix esperado:
1. Mensagens de sistema/infra sao SUBSTITUIDAS por mensagem humana PT-BR
   (ou o segmento contaminado e removido preservando conteudo util).
2. Segmentos com caracteres nao-latinos (CJK, cirilico) e pontuacao
   full-width sao removidos/normalizados; resposta quebrada vira fallback.
3. NADA disso chega no content final de /api/v1/pietra/chat/completions.
4. Warning e logado e metrica incrementada quando o guard dispara.

Padrao: teste FALHA se regredir. Modified by Gustavo Almeida · 2026-07-28
"""

from __future__ import annotations

import logging
import os

import pytest
from fastapi.testclient import TestClient

from app.services.pietra_outbound_guard import (
    SAFE_FALLBACK,
    OutboundAction,
    contains_non_latin_script,
    detect_infra_leak,
    get_outbound_guard_metrics,
    reset_outbound_guard_metrics,
    sanitize_outbound,
)

# === Transcripts reais capturados em prod iMessage (2026-07-28) ===

INFRA_INTERRUPT_REAL = "⚡ Interrupting current task"

INFRA_RATE_LIMIT_REAL = (
    "The model provider is rate-limiting requests. Please try again shortly."
)

INFRA_EMPTY_STREAM_REAL = "empty response stream"

INFRA_UNEXPECTED_ERROR_REAL = "Sorry, I encountered an unexpected error. Please try again."

INFRA_MIXED_WITH_CONTENT = (
    "O valor da procuração é calculado pela tabela do TJMG. "
    "switched to fallback provider due to timeout"
)

RUSSIAN_MIX_REAL = "Mas есть uma boa notícia: o cartório atende hoje até as 17h."

CHINESE_MIX_REAL = "Certo, então，大概 R$ 22-33 dependendo do ato."

FULLWIDTH_PUNCT_REAL = "O horário é das 09h às 17h。Qualquer dúvida，estou aqui。"

CLEAN_PTBR = (
    "O 2º Tabelionato fica na Rua Cel. Antonio Alves Pereira, 850, Centro. "
    "Atendemos de segunda a sexta, das 09h às 17h."
)

FORBIDDEN_INFRA_TOKENS = (
    "interrupting",
    "rate-limit",
    "rate limiting",
    "empty response",
    "unexpected error",
    "switched to fallback",
    "usage limit",
    "home channel",
    "photon",
    "gateway",
    "timeout",
    "encountered",
)


@pytest.fixture(autouse=True)
def _reset_metrics() -> None:
    reset_outbound_guard_metrics()


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


def _post(client):
    return client.post(
        "/api/v1/pietra/chat/completions",
        json={"messages": [{"role": "user", "content": "quanto custa uma escritura?"}]},
    )


# === Nivel unitario: detector de infra ===


class TestDetectInfraLeak:
    @pytest.mark.parametrize(
        "leak",
        [
            INFRA_INTERRUPT_REAL,
            INFRA_RATE_LIMIT_REAL,
            INFRA_EMPTY_STREAM_REAL,
            INFRA_UNEXPECTED_ERROR_REAL,
            "switched to fallback provider",
            "usage limit reached for today",
            "returning to home channel",
            "photon spectrum cache miss",
            "gateway error upstream",
            "request timeout after 30s",
            "⚡ Interrupting current task — retrying",
        ],
    )
    def test_detecta_variacoes_infra(self, leak: str):
        assert detect_infra_leak(leak) is not None, f"nao detectou: {leak!r}"

    @pytest.mark.parametrize(
        "clean",
        [
            CLEAN_PTBR,
            "O valor é calculado pela tabela de emolumentos vigente.",
            "Posso te orientar sobre o agendamento online.",
            SAFE_FALLBACK,
        ],
    )
    def test_texto_limpo_nao_detecta(self, clean: str):
        assert detect_infra_leak(clean) is None


# === Nivel unitario: detector de idioma nao-latino ===


class TestDetectNonLatin:
    def test_cirilico_detectado(self):
        assert contains_non_latin_script(RUSSIAN_MIX_REAL)

    def test_cjk_detectado(self):
        assert contains_non_latin_script(CHINESE_MIX_REAL)

    def test_ptbr_limpo_nao_detecta(self):
        assert not contains_non_latin_script(CLEAN_PTBR)
        assert not contains_non_latin_script("Ação, coração, índice, útil — tudo ok.")


# === Nivel unitario: sanitize_outbound ===


class TestSanitizeOutbound:
    def test_texto_limpo_passa_intocado(self):
        res = sanitize_outbound(CLEAN_PTBR)
        assert res.action is OutboundAction.PASS
        assert res.sanitized_text == CLEAN_PTBR
        assert res.reasons == ()

    def test_texto_vazio_passa(self):
        res = sanitize_outbound("")
        assert res.action is OutboundAction.PASS
        assert res.sanitized_text == ""

    @pytest.mark.parametrize(
        "leak",
        [
            INFRA_INTERRUPT_REAL,
            INFRA_RATE_LIMIT_REAL,
            INFRA_EMPTY_STREAM_REAL,
            INFRA_UNEXPECTED_ERROR_REAL,
        ],
    )
    def test_infra_integral_vira_fallback_ptbr(self, leak: str):
        res = sanitize_outbound(leak)
        assert res.action is OutboundAction.FALLBACK
        assert res.sanitized_text == SAFE_FALLBACK
        for token in FORBIDDEN_INFRA_TOKENS:
            assert token not in res.sanitized_text.lower()

    def test_infra_misto_preserva_conteudo_util(self):
        res = sanitize_outbound(INFRA_MIXED_WITH_CONTENT)
        assert res.action is OutboundAction.SANITIZED
        assert "tabela do TJMG" in res.sanitized_text
        for token in ("switched to fallback", "timeout"):
            assert token not in res.sanitized_text.lower()

    def test_russo_removido_preserva_ptbr(self):
        res = sanitize_outbound(RUSSIAN_MIX_REAL)
        assert res.action is OutboundAction.SANITIZED
        assert "есть" not in res.sanitized_text
        assert "cartório atende hoje até as 17h" in res.sanitized_text
        assert "language_mixing" in res.reasons

    def test_chines_removido_preserva_valor(self):
        res = sanitize_outbound(CHINESE_MIX_REAL)
        assert res.action is OutboundAction.SANITIZED
        assert "大概" not in res.sanitized_text
        assert "，" not in res.sanitized_text
        assert "R$ 22-33" in res.sanitized_text

    def test_fullwidth_punct_normalizada(self):
        res = sanitize_outbound(FULLWIDTH_PUNCT_REAL)
        assert "。" not in res.sanitized_text
        assert "，" not in res.sanitized_text
        assert "09h às 17h" in res.sanitized_text

    def test_so_cirilico_vira_fallback(self):
        res = sanitize_outbound("есть 大概")
        assert res.action is OutboundAction.FALLBACK
        assert res.sanitized_text == SAFE_FALLBACK

    def test_warning_logado_quando_dispara(self, caplog):
        with caplog.at_level(logging.WARNING, logger="app.services.pietra_outbound_guard"):
            sanitize_outbound(INFRA_INTERRUPT_REAL)
        assert any("outbound guard" in rec.message.lower() for rec in caplog.records)

    def test_metrica_incrementa(self):
        sanitize_outbound(INFRA_INTERRUPT_REAL)
        sanitize_outbound(RUSSIAN_MIX_REAL)
        m = get_outbound_guard_metrics()
        assert m["cartorio_pietra_outbound_guard_intercepted_total"] == 2
        assert m["infra_leak"] >= 1
        assert m["language_mixing"] >= 1


# === Nivel endpoint: nada vaza no /chat/completions ===


class TestEndpointOutboundGuard:
    @pytest.mark.parametrize(
        "leak",
        [
            INFRA_INTERRUPT_REAL,
            INFRA_RATE_LIMIT_REAL,
            INFRA_EMPTY_STREAM_REAL,
            INFRA_UNEXPECTED_ERROR_REAL,
        ],
    )
    def test_infra_nao_vaza_no_endpoint(self, client, monkeypatch, leak):
        _patch_llm(monkeypatch, leak)
        r = _post(client)
        assert r.status_code == 200
        content = r.json()["choices"][0]["message"]["content"]
        lowered = content.lower()
        for token in FORBIDDEN_INFRA_TOKENS:
            assert token not in lowered, f"vazou {token!r}: {content!r}"
        assert "⚡" not in content

    @pytest.mark.parametrize("mix", [RUSSIAN_MIX_REAL, CHINESE_MIX_REAL])
    def test_language_mixing_nao_vaza_no_endpoint(self, client, monkeypatch, mix):
        _patch_llm(monkeypatch, mix)
        r = _post(client)
        content = r.json()["choices"][0]["message"]["content"]
        assert not contains_non_latin_script(content), f"restou nao-latino: {content!r}"
        for punct in ("，", "。", "、", "｜"):
            assert punct not in content

    def test_resposta_limpa_intacta_no_endpoint(self, client, monkeypatch):
        _patch_llm(monkeypatch, CLEAN_PTBR)
        r = _post(client)
        content = r.json()["choices"][0]["message"]["content"]
        assert "Rua Cel. Antonio Alves Pereira, 850" in content
