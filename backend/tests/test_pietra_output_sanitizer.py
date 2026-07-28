"""Regression tests do sanitizador deterministico pos-LLM da Pietra.

Cobre as falhas P0 do RELATORIO_HUMANIDADE_2026-07-28:
- Vazamento multilingue (CJK/cirilico/kana/hangul/grego/arabe) -> retry 1x
  com system extra PT-BR; se persistir -> fallback seguro deterministico.
- Artifact "[This response was interrupted..." NUNCA vai ao cliente; se a
  resposta era so isso, trata como retry.
- Vazamento de vocab interno residual ("via Photon (iMessage)", Photon,
  Spectrum) removido sem destruir texto legitimo.
- Texto PT-BR normal passa INTOCADO (sem retry, sem reescrita).

Padrao: teste FALHA se regredir. Modified by Gustavo Almeida · 2026-07-28
"""

from __future__ import annotations

import os
from typing import Any

import pytest
from fastapi.testclient import TestClient


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


class TestNonLatinRetryAndFallback:
    def test_cjk_detectado_retry_e_fallback(self, client, monkeypatch):
        """CJK nas 2 tentativas -> fallback seguro deterministico, 2 calls."""
        calls = _patch_llm_sequence(
            monkeypatch,
            ["Claro, 大致估算 o valor fica em torno de R$ 100.", "还是会有其他费用。"],
        )
        body = _post(client, "quanto custa?")
        content = body["choices"][0]["message"]["content"]
        assert content == "Desculpe, tive uma instabilidade. Pode repetir, por gentileza?"
        assert len(calls) == 2
        # Retry carrega system extra exigindo PT-BR puro.
        retry_systems = [m for m in calls[1]["messages"] if m["role"] == "system"]
        assert any("APENAS em portugues brasileiro" in m["content"] for m in retry_systems)

    def test_cjk_no_primeiro_retry_recupera_ptbr(self, client, monkeypatch):
        """CJK na 1a resposta, PT-BR limpo no retry -> devolve o retry, 2 calls."""
        calls = _patch_llm_sequence(
            monkeypatch,
            ["祥细 vou te explicar.", "Claro! Vou te explicar com calma."],
        )
        body = _post(client, "como funciona?")
        content = body["choices"][0]["message"]["content"]
        assert content == "Claro! Vou te explicar com calma."
        assert len(calls) == 2

    @pytest.mark.parametrize(
        "leak",
        [
            "Mas есть uma boa noticia.",  # cirilico
            "안녕하세요, posso ajudar?",  # hangul
            "こんにちは, tudo bem?",  # hiragana
            "مرحبا, como vai?",  # arabe
            "Γεια σου, em que posso ajudar?",  # grego
        ],
    )
    def test_outros_scripts_disparam_fallback(self, client, monkeypatch, leak):
        """Qualquer script nao-latino persistente cai no fallback seguro."""
        calls = _patch_llm_sequence(monkeypatch, [leak, leak])
        body = _post(client)
        content = body["choices"][0]["message"]["content"]
        assert content == "Desculpe, tive uma instabilidade. Pode repetir, por gentileza?"
        assert len(calls) == 2


class TestInterruptedArtifactStrip:
    def test_artifact_no_meio_do_texto_removido(self, client, monkeypatch):
        """Artifact removido preservando o texto util restante (sem retry)."""
        calls = _patch_llm_sequence(
            monkeypatch,
            [
                "Posso te ajudar com isso. "
                "[This response was interrupted by a user correction.] "
                "O documento necessario e o RG."
            ],
        )
        body = _post(client)
        content = body["choices"][0]["message"]["content"]
        assert "interrupted" not in content.lower()
        assert "[" not in content
        assert "Posso te ajudar com isso." in content
        assert "O documento necessario e o RG." in content
        assert len(calls) == 1

    def test_artifact_sozinho_trata_como_retry(self, client, monkeypatch):
        """Resposta que era SO o artifact -> retry 1x (nunca vaza ao cliente)."""
        calls = _patch_llm_sequence(
            monkeypatch,
            [
                "[This response was interrupted by a user correction.]",
                "Desculpe a demora. Pode me dizer novamente o que precisa?",
            ],
        )
        body = _post(client)
        content = body["choices"][0]["message"]["content"]
        assert "interrupted" not in content.lower()
        assert "Desculpe a demora." in content
        assert len(calls) == 2

    def test_artifact_sozinho_retry_tambem_artifact_cai_fallback(self, client, monkeypatch):
        """Artifact nas 2 tentativas -> fallback seguro (artifact nunca vaza)."""
        calls = _patch_llm_sequence(
            monkeypatch,
            [
                "[This response was interrupted",
                "[This response was interrupted by a user correction.]",
            ],
        )
        body = _post(client)
        content = body["choices"][0]["message"]["content"]
        assert "interrupted" not in content.lower()
        assert content == "Desculpe, tive uma instabilidade. Pode repetir, por gentileza?"
        assert len(calls) == 2


class TestInternalVocabStrip:
    def test_via_photon_imessage_removido(self, client, monkeypatch):
        """Vazamento REAL observado (Maria T4): 'via Photon (iMessage)' some."""
        calls = _patch_llm_sequence(
            monkeypatch,
            [
                "Que bom que conseguiu! Como e via Photon (iMessage), posso te ajudar por aqui mesmo."
            ],
        )
        body = _post(client)
        content = body["choices"][0]["message"]["content"]
        assert "Photon" not in content
        assert "photon" not in content.lower()
        assert "iMessage" not in content
        assert "Que bom que conseguiu!" in content
        assert len(calls) == 1

    @pytest.mark.parametrize(
        "text,forbidden",
        [
            ("Vou registrar no Spectrum agora mesmo.", "Spectrum"),
            ("O Photon cuida do envio da mensagem.", "Photon"),
        ],
    )
    def test_tokens_internos_soltos_removidos(self, client, monkeypatch, text, forbidden):
        """Tokens Photon/Spectrum soltos sao removidos sem retry."""
        calls = _patch_llm_sequence(monkeypatch, [text])
        body = _post(client)
        content = body["choices"][0]["message"]["content"]
        assert forbidden.lower() not in content.lower()
        assert len(calls) == 1


class TestCleanPtBrUntouched:
    def test_texto_ptbr_normal_intocado(self, client, monkeypatch):
        """PT-BR limpo passa EXATAMENTE como veio, sem retry."""
        original = (
            "Sinto muito pela sua perda. Vamos resolver o inventario com calma. "
            "A sede fica na Rua Cel. Antonio Alves Pereira, 850, Centro."
        )
        calls = _patch_llm_sequence(monkeypatch, [original])
        body = _post(client)
        content = body["choices"][0]["message"]["content"]
        assert content == original
        assert len(calls) == 1

    def test_acentos_e_cedilha_nao_sao_nao_latinos(self, client, monkeypatch):
        """Acentuacao PT-BR (á, ç, ã, é) NUNCA dispara retry."""
        original = "Atencao: o coracao da questao e a emancipacao do imovel, ok?"
        calls = _patch_llm_sequence(monkeypatch, [original])
        body = _post(client)
        assert body["choices"][0]["message"]["content"] == original
        assert len(calls) == 1


class TestProvidersDownUnchanged:
    def test_providers_down_nao_dispara_retry(self, client, monkeypatch):
        """msg=None (providers down) NAO chama retry — fallback estrutural cuida."""
        calls = _patch_llm_sequence(monkeypatch, [None])
        body = _post(client)
        content = body["choices"][0]["message"]["content"]
        assert "Pietra" in content
        assert len(calls) == 1
