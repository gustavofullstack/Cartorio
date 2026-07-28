"""Regression tests do LANGUAGE GUARD LATINO (round 2, 2026-07-28).

Evidencia real prod iMessage (campanha personas P7-P10, bot NOVO):
- P7 id 4248: "E não fica sensibility — você está sendo muito corajosa"
- P7 id 4250: "Seu José sounds like uma pessoa maravilhosa"
- P9 id 4272: "essa é a parte mais importante indeed."
- P10: "Liga e explica sua situação — és velho, herdeiro, casa simples."
- P10: "se estiver muito apertado financeiramente, explains that situation"

Root cause: o guard round 1 so cobre ranges NAO-latinos (CJK/cirilico);
ingles e PT-PT sao ASCII/latim puro e passavam batidos ao cliente.

Fix esperado:
1. detect_latin_language_mix() detecta anglicismos e PT-PT em texto PT-BR
   (word boundary, case-insensitive, lista em constante auditavel).
2. Whitelist (WhatsApp, iMessage, e-mail, link, online, app, e-Notariado,
   selfie) NUNCA dispara deteccao.
3. Sanitizer pos-LLM: RETRY 1x (mesmo fluxo do non_latin_retry) com
   instrucao de reescrever em PT-BR; se persistir, STRIP da sentenca
   contaminada; se nada util restar, fallback seguro.
4. Outbound guard: strip da sentenca contaminada preservando conteudo
   util, reason "language_mixing_latin", metrica incrementada.

Padrao: teste FALHA se regredir. Modified by Gustavo Almeida · 2026-07-28
"""

from __future__ import annotations

import os
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.services.pietra_outbound_guard import (
    OutboundAction,
    detect_latin_language_mix,
    get_outbound_guard_metrics,
    reset_outbound_guard_metrics,
    sanitize_outbound,
)

# === Fixtures de transcripts REAIS (personas P7-P10, 2026-07-28) ===

P7_SENSIBILITY_REAL = (
    "Não se preocupe, querida — estamos aqui pra te ajudar. "
    "E não fica sensibility — você está sendo muito corajosa cuidando das coisas."
)

P7_SOUNDS_LIKE_REAL = (
    "Dona Rosa, não precisa pedir desculpa por chorar. "
    "Seu José sounds like uma pessoa maravilhosa — isso é amor de verdade."
)

P9_INDEED_REAL = "Boa pergunta — essa é a parte mais importante indeed."

P10_ES_VELHO_REAL = (
    "Dica importante: Liga e explica sua situação — és velho, herdeiro, casa simples."
)

P10_EXPLAINS_THAT_REAL = (
    "Se estiver muito apertado financeiramente, explains that situation "
    "que eles orientam."
)


@pytest.fixture(scope="module")
def client():
    os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
    os.environ.setdefault("REDIS_URL", "redis://localhost:6379/15")
    os.environ.setdefault("ENV", "test")
    from app.main import app

    return TestClient(app)


def _patch_llm_sequence(monkeypatch, contents: list[str | None]) -> list[dict[str, Any]]:
    """Fake _chat_completion que devolve `contents` em sequencia e conta calls."""
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


class TestDetectLatinLanguageMix:
    @pytest.mark.parametrize(
        "text",
        [
            P7_SENSIBILITY_REAL,
            P7_SOUNDS_LIKE_REAL,
            P9_INDEED_REAL,
            P10_ES_VELHO_REAL,
            P10_EXPLAINS_THAT_REAL,
        ],
    )
    def test_transcripts_reais_detectados(self, text):
        """Os 5 vazamentos reais P7-P10 DEVEM ser detectados."""
        assert detect_latin_language_mix(text)

    @pytest.mark.parametrize(
        "text",
        [
            "O valor fica roughly em torno de R$ 100.",
            "Depende, depending on the situation.",
            "Actually, o prazo é de 5 dias.",
            "Basically, você precisa do RG.",
            "However, o cartório fecha às 17h.",
            "Você estás bem? Tás precisando de algo?",
            "Pode usar a casa de banho ali.",
            "O autocarro passa na porta.",
            "Traz o telemóvel para a videochamada.",
            "Fixe, até amanhã!",
        ],
    )
    def test_lexico_en_ptpt_detectado(self, text):
        """Lexico curado EN/PT-PT detectado em qualquer posicao."""
        assert detect_latin_language_mix(text)

    @pytest.mark.parametrize(
        "text",
        [
            "Me chama no WhatsApp que eu te mando o link.",
            "Posso te atender por iMessage ou e-mail, como preferir.",
            "O agendamento online fica no app.",
            "Reconhecimento de firma online pelo e-Notariado.",
            "Precisa trazer uma selfie segurando o documento.",
            "Sinto muito pela sua perda. Vamos resolver o inventário com calma.",
            "A sede fica na Rua Cel. Antonio Alves Pereira, 850, Centro.",
            "O emolumento da procuração é R$ 68,94 pela tabela do TJMG.",
        ],
    )
    def test_whitelist_e_ptbr_limpo_nao_detectam(self, text):
        """Whitelist (WhatsApp/iMessage/e-mail/link/online/app/e-Notariado/
        selfie) e PT-BR correto NUNCA disparam deteccao."""
        assert not detect_latin_language_mix(text)


class TestOutboundGuardLatinStrip:
    def setup_method(self):
        reset_outbound_guard_metrics()

    def test_sentenca_contaminada_removida_preservando_util(self):
        """Strip da sentenca EN preservando o conteudo util ao redor."""
        text = (
            "Dona Rosa, seus filhos estão com você. "
            "Seu José sounds like uma pessoa maravilhosa. "
            "O cartório vai ajudar a resolver tudo com carinho."
        )
        out = sanitize_outbound(text, channel="imessage")
        assert out.action is OutboundAction.SANITIZED
        assert "sounds like" not in out.sanitized_text
        assert "seus filhos estão com você" in out.sanitized_text
        assert "resolver tudo com carinho" in out.sanitized_text
        assert "language_mixing_latin" in out.reasons

    def test_so_contaminacao_vira_fallback(self):
        """Resposta que era so contaminacao latina -> SAFE_FALLBACK."""
        out = sanitize_outbound("Indeed.", channel="imessage")
        assert out.action is OutboundAction.FALLBACK
        assert "indeed" not in out.sanitized_text.lower()
        assert "language_mixing_latin" in out.reasons

    def test_ptpt_removido(self):
        """PT-PT ('és velho') removido preservando o resto da dica."""
        text = (
            "Liga e explica sua situação: herdeiro, casa simples. "
            "Você és velho demais para isso."
        )
        out = sanitize_outbound(text, channel="imessage")
        assert "és velho" not in out.sanitized_text
        assert "casa simples" in out.sanitized_text

    def test_metrica_incrementada(self):
        sanitize_outbound(P7_SOUNDS_LIKE_REAL, channel="imessage")
        metrics = get_outbound_guard_metrics()
        assert metrics.get("language_mixing_latin", 0) >= 1

    def test_ptbr_limpo_passa_intocado(self):
        clean = "O reconhecimento de firma custa R$ 11,21 e é feito na hora."
        out = sanitize_outbound(clean, channel="imessage")
        assert out.action is OutboundAction.PASS
        assert out.sanitized_text == clean


class TestSanitizerLatinRetryFlow:
    """Fluxo retry 1x -> strip -> fallback no endpoint (sem strip cego)."""

    def test_latin_mix_dispara_retry_e_recupera(self, client, monkeypatch):
        """1a resposta com 'sounds like', retry PT-BR limpo -> devolve retry."""
        calls = _patch_llm_sequence(
            monkeypatch,
            [P7_SOUNDS_LIKE_REAL, "Seu José parecia uma pessoa maravilhosa."],
        )
        body = _post(client, "meu marido faleceu")
        content = body["choices"][0]["message"]["content"]
        assert content == "Seu José parecia uma pessoa maravilhosa."
        assert len(calls) == 2
        retry_systems = [m for m in calls[1]["messages"] if m["role"] == "system"]
        assert any("portugu" in m["content"].lower() for m in retry_systems)

    def test_retry_persistente_faz_strip_da_sentenca(self, client, monkeypatch):
        """Retry ainda contaminado -> STRIP da sentenca, preservando util.

        NAO pode ser strip cego sem retry: o retry precisa ter acontecido
        (2 calls) antes do strip.
        """
        dirty = (
            "Você foi casada 40 anos com um homem que te amava. "
            "Isso é amor de verdade indeed. "
            "Cuida dos meninos porque eles precisam de você."
        )
        calls = _patch_llm_sequence(monkeypatch, [P9_INDEED_REAL, dirty])
        body = _post(client)
        content = body["choices"][0]["message"]["content"]
        assert "indeed" not in content
        assert "casada 40 anos" in content
        assert "precisam de você" in content
        assert len(calls) == 2  # retry aconteceu ANTES do strip

    def test_retry_persistente_sem_util_cai_fallback(self, client, monkeypatch):
        """Contaminacao total persistente -> fallback seguro deterministico."""
        calls = _patch_llm_sequence(
            monkeypatch, ["Actually indeed basically.", "Indeed roughly."]
        )
        body = _post(client)
        content = body["choices"][0]["message"]["content"]
        assert content == "Desculpe, tive uma instabilidade. Pode repetir, por gentileza?"
        assert len(calls) == 2

    def test_ptbr_limpo_nao_dispara_retry(self, client, monkeypatch):
        """PT-BR limpo (mesmo com whitelist) NAO dispara retry."""
        clean = (
            "Posso te atender por WhatsApp ou iMessage. "
            "O agendamento online é pelo app, ou mando o link por e-mail."
        )
        calls = _patch_llm_sequence(monkeypatch, [clean])
        body = _post(client)
        assert body["choices"][0]["message"]["content"] == clean
        assert len(calls) == 1
