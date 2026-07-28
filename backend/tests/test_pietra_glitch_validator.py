"""Regression tests do VALIDADOR ANTI-GLITCH (round 2, 2026-07-28).

Evidencia real prod iMessage (campanha personas):
- P8: "Na hora de reconhecer, só diz que é prosetão"
- P9 id 4272: "Carta minecraft:" no meio da resposta sobre poderes
- P7 id 4254: "o valor exato só o escribente calcula quandoolhar a documentação"
- P6 (bot antigo): palavra corrompida "ISSA"

Root cause: modelo rapido com temperatura alta gera tokens fora do
vocabulario PT-BR; nenhuma camada validava lexico de saida.

Fix esperado (abordagem leve, SEM dependencia pesada):
1. detect_glitch_tokens(): constante auditavel de padroes suspeitos +
   heuristicas (token >15 chars sem hifen; ALLCAPS fora de whitelist de
   siglas; bigrama impossivel tipo "carta minecraft").
2. Vocabulario PT-BR legitimo (procuração, tabelionato, apostilamento,
   Uberlândia) NUNCA e detectado.
3. Sanitizer pos-LLM: retry 1x; se persistir, sentenca fora (fallback
   seguro se nada util restar). NUNCA strip cego sem retry.
4. Outbound guard: strip da sentenca com glitch, reason "token_glitch".

Padrao: teste FALHA se regredir. Modified by Gustavo Almeida · 2026-07-28
"""

from __future__ import annotations

import os
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.services.pietra_outbound_guard import (
    OutboundAction,
    detect_glitch_tokens,
    get_outbound_guard_metrics,
    reset_outbound_guard_metrics,
    sanitize_outbound,
)

# === Fixtures de transcripts REAIS (personas P6-P9) ===

P8_PROSETAO_REAL = (
    'Na hora de reconhecer, só diz que é prosetão — "é meu primeiro emprego, '
    'nunca fiz isso" — eles vão entender.'
)

P9_CARTA_MINECRAFT_REAL = (
    "Poderes adicionais recomendados: transigir e dar em pagamento.\n"
    "Carta minecraft:\n"
    "O tabelião aqui vai adaptar a minuta padrão com base no seu caso."
)

P7_QUANDOOLHAR_REAL = (
    "Mas o valor exato só o escribente calcula quandoolhar a documentação."
)

P6_ISSA_REAL = "O valor da escritura ISSA calculado pela tabela do TJMG."


@pytest.fixture(scope="module")
def client():
    os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
    os.environ.setdefault("REDIS_URL", "redis://localhost:6379/15")
    os.environ.setdefault("ENV", "test")
    from app.main import app

    return TestClient(app)


def _patch_llm_sequence(monkeypatch, contents: list[str | None]) -> list[dict[str, Any]]:
    calls: list[dict[str, Any]] = []

    async def fake(messages, tools=None, **kwargs):
        calls.append({"messages": messages, "tools": tools, **kwargs})
        content = contents[min(len(calls) - 1, len(contents) - 1)]
        if content is None:
            return None, "none", "all providers down"
        return {"content": content}, "minimax_direct:MiniMax-M3", ""

    monkeypatch.setattr("app.services.cartorio_agent._chat_completion", fake)
    return calls


def _post(client, text: str = "oi") -> dict:
    r = client.post(
        "/api/v1/pietra/chat/completions",
        json={"messages": [{"role": "user", "content": text}]},
    )
    assert r.status_code == 200
    return r.json()


class TestDetectGlitchTokens:
    @pytest.mark.parametrize(
        "text",
        [
            P8_PROSETAO_REAL,
            P9_CARTA_MINECRAFT_REAL,
            P7_QUANDOOLHAR_REAL,
            P6_ISSA_REAL,
        ],
    )
    def test_glitches_reais_detectados(self, text):
        """Os 4 glitches reais da campanha DEVEM ser detectados."""
        assert detect_glitch_tokens(text)

    @pytest.mark.parametrize(
        "text",
        [
            "A procuração pública custa R$ 68,94.",
            "O tabelionato atende das 09h às 17h.",
            "O apostilamento segue a Convenção de Haia.",
            "Nossa sede fica em Uberlândia, no Centro.",
            "Traga RG, CPF e comprovante de residência.",
            "O ITBI e o IPTU do imóvel precisam estar em dia.",
            "A LGPD protege seus dados pessoais.",
            "Reconhecimento de firma por semelhança ou autenticidade.",
        ],
    )
    def test_vocabulario_legitimo_nao_detectado(self, text):
        """Vocabulario PT-BR/notarial legitimo NUNCA dispara o validador."""
        assert not detect_glitch_tokens(text)

    def test_bigrama_impossivel_detectado(self):
        assert detect_glitch_tokens("Carta minecraft: o tabelião adapta.")

    def test_token_longo_sem_hifen_suspeito(self):
        """Token >15 chars sem hifen e fora de vocabulario plausivel."""
        assert detect_glitch_tokens("O valor fica asdkfjqwertzxcvbhgf por ora.")

    def test_siglas_legitimas_nao_sao_glitch(self):
        """Siglas do dominio (CRM/RG/CPF/IPTU/LGPD/OAB) nao sao glitch."""
        assert not detect_glitch_tokens("O CRM não substitui o RG ou CPF.")


class TestOutboundGuardGlitchStrip:
    def setup_method(self):
        reset_outbound_guard_metrics()

    def test_sentenca_com_glitch_removida_preservando_util(self):
        out = sanitize_outbound(P9_CARTA_MINECRAFT_REAL, channel="imessage")
        assert out.action is OutboundAction.SANITIZED
        assert "minecraft" not in out.sanitized_text.lower()
        assert "minuta padrão" in out.sanitized_text
        assert "token_glitch" in out.reasons

    def test_so_glitch_vira_fallback(self):
        out = sanitize_outbound("quandoolhar", channel="imessage")
        assert out.action is OutboundAction.FALLBACK
        assert "quandoolhar" not in out.sanitized_text
        assert "token_glitch" in out.reasons

    def test_metrica_incrementada(self):
        sanitize_outbound(P8_PROSETAO_REAL, channel="imessage")
        metrics = get_outbound_guard_metrics()
        assert metrics.get("token_glitch", 0) >= 1

    def test_texto_limpo_passa_intocado(self):
        clean = "O reconhecimento de firma por semelhança custa R$ 11,21."
        out = sanitize_outbound(clean, channel="imessage")
        assert out.action is OutboundAction.PASS
        assert out.sanitized_text == clean


class TestSanitizerGlitchRetryFlow:
    def test_glitch_dispara_retry_e_recupera(self, client, monkeypatch):
        """1a resposta com 'prosetão', retry limpo -> devolve retry."""
        calls = _patch_llm_sequence(
            monkeypatch,
            [P8_PROSETAO_REAL, "Na hora de reconhecer, é só avisar que é sua primeira vez."],
        )
        body = _post(client, "primeiro emprego")
        content = body["choices"][0]["message"]["content"]
        assert content == "Na hora de reconhecer, é só avisar que é sua primeira vez."
        assert len(calls) == 2
        retry_systems = [m for m in calls[1]["messages"] if m["role"] == "system"]
        assert any("portugu" in m["content"].lower() for m in retry_systems)

    def test_retry_persistente_faz_strip_da_sentenca(self, client, monkeypatch):
        """Retry ainda com glitch -> strip da sentenca, preservando util."""
        dirty_retry = (
            "Poderes adicionais: transigir e dar em pagamento.\n"
            "Carta minecraft:\n"
            "O tabelião vai adaptar a minuta padrão com base no seu caso."
        )
        calls = _patch_llm_sequence(monkeypatch, [P9_CARTA_MINECRAFT_REAL, dirty_retry])
        body = _post(client)
        content = body["choices"][0]["message"]["content"]
        assert "minecraft" not in content.lower()
        assert "minuta padrão" in content
        assert len(calls) == 2  # retry ANTES do strip

    def test_retry_persistente_sem_util_cai_fallback(self, client, monkeypatch):
        """Glitch total persistente -> fallback seguro deterministico."""
        calls = _patch_llm_sequence(monkeypatch, ["quandoolhar", "ISSA"])
        body = _post(client)
        content = body["choices"][0]["message"]["content"]
        assert content == "Desculpe, tive uma instabilidade. Pode repetir, por gentileza?"
        assert len(calls) == 2

    def test_texto_limpo_nao_dispara_retry(self, client, monkeypatch):
        """PT-BR notarial correto NAO dispara retry."""
        clean = (
            "A procuração lavrada no tabelionato de Uberlândia pode ser "
            "apostilada conforme a Convenção de Haia."
        )
        calls = _patch_llm_sequence(monkeypatch, [clean])
        body = _post(client)
        assert body["choices"][0]["message"]["content"] == clean
        assert len(calls) == 1
