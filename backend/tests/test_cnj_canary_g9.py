"""G9.S4.T1 (E3.08) — Canary PII: PII canário inserida NUNCA sai raw.

Tripwire de regressão LGPD: um CPF canário de formato conhecido
(529.982.247-25, matematicamente válido, usado apenas em teste) e um
token canário sintético não-PII (CANARY_CPF_G9_S4T1, tripwire de
rastreabilidade) são injetados em cada superfície de saída do sistema.
O teste FALHA se qualquer saída ecoar o CPF canário sem máscara.

Superfícies cobertas (offline, sem DB/LLM real):
  (a) app.services.pii.scrub — 1a/2a camada (input/pre-LLM).
  (b) app.services.cartorio_agent.sanitize_bot_output e _offline_reply
      degraded — 3a camada (output do agente, inclusive fallback).
  (c) payload do streaming massive-dump CNJ — _scrub_payload_value +
      construção do item streamada, com fixture de audit entries
      sintéticas (mesma lógica do endpoint, sem DB).

O token canário NÃO é PII: ele sobrevive ao scrub de propósito, servindo
como marcador rastreável de "onde o registro canário foi parar". Ao lado
dele, o CPF canário tem de estar SEMPRE mascarado.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any

import pytest

from app.api.v1.cnj_export import _scrub_payload_value
from app.services.cartorio_agent import _offline_reply, sanitize_bot_output
from app.services.pii import scrub

CANARY_CPF = "529.982.247-25"
CANARY_CPF_DIGITS = "52998224725"
CANARY_TOKEN = "CANARY_CPF_G9_S4T1"
CPF_MASK = "[CPF_REDACTED]"


def _assert_canary_safe(output: str) -> None:
    """Contrato único: raw nunca aparece; máscara presente; token rastreável."""
    assert CANARY_CPF not in output, f"CPF canário raw vazou: {output!r}"
    assert CANARY_CPF_DIGITS not in output, f"CPF canário (dígitos) raw vazou: {output!r}"
    assert CANARY_TOKEN in output, f"token canário sumiu — registro não rastreável: {output!r}"


# ============================================================
# (a) pii.scrub — camadas 1/2
# ============================================================


class TestPIIScrubCanary:
    @pytest.mark.parametrize(
        "texto",
        [
            f"meu cpf é {CANARY_CPF} ref {CANARY_TOKEN}",
            f"{CANARY_TOKEN}: titular CPF {CANARY_CPF_DIGITS}",  # dígitos puros
            f"protocolo {CANARY_TOKEN} gerado para {CANARY_CPF} ok",
            f"{CANARY_CPF} {CANARY_TOKEN}",  # adjacente
        ],
    )
    def test_scrub_never_leaks_canary(self, texto: str) -> None:
        result = scrub(texto)
        _assert_canary_safe(result.text)
        assert result.redaction_count >= 1
        assert result.findings.get("cpf", 0) >= 1
        assert CPF_MASK in result.text

    def test_scrub_canary_serialized_blob(self) -> None:
        """Canary dentro de blob JSON-like (caminho de payload)."""
        blob = json.dumps(
            {"token": CANARY_TOKEN, "cpf": CANARY_CPF, "nota": "ok"}, ensure_ascii=False
        )
        result = scrub(blob)
        _assert_canary_safe(result.text)


# ============================================================
# (b) cartorio_agent — camada 3 (output do bot)
# ============================================================


class TestAgentOutputCanary:
    def test_sanitize_bot_output_llm_echoing_canary(self) -> None:
        """LLM ecoando PII mascarada de volta NUNCA devolve raw ao usuário."""
        llm_echo = (
            f"Claro! Confirmo seu CPF {CANARY_CPF} "
            f"(atendimento {CANARY_TOKEN}). Posso ajudar em algo mais?"
        )
        saida = sanitize_bot_output(llm_echo)
        _assert_canary_safe(saida)
        assert CPF_MASK in saida

    def test_sanitize_bot_output_canary_digits_only(self) -> None:
        llm_echo = f"Recebi {CANARY_CPF_DIGITS} para o ticket {CANARY_TOKEN}."
        saida = sanitize_bot_output(llm_echo)
        _assert_canary_safe(saida)

    def test_offline_reply_degraded_never_leaks_canary(self) -> None:
        """Fallback degraded (LLM down) também passa pelo output scrub.

        A intent 'dados' devolve ack LGPD fixo (não ecoa o input), então o
        contrato aqui é: raw do canary NUNCA aparece, mesmo que o reply
        venha a ecoar input do cliente em intents que ecoam.
        """
        texto_cliente = f"quero certidão, meu cpf {CANARY_CPF} ref {CANARY_TOKEN}"
        tools: list[str] = []
        reply = _offline_reply(texto_cliente, "dados", tools, degraded=True)
        assert CANARY_CPF not in reply.text
        assert CANARY_CPF_DIGITS not in reply.text
        assert "lentidão" in reply.text  # prefixo degraded preservado

    def test_offline_reply_non_degraded_canary_in_history(self) -> None:
        texto_cliente = "e aí?"
        historico = [f"cliente informou cpf {CANARY_CPF} ticket {CANARY_TOKEN}"]
        reply = _offline_reply(texto_cliente, "memoria", [], history=historico)
        # intent 'memoria' não ecoa histórico, mas se ecoasse o scrub pega.
        assert CANARY_CPF not in reply.text
        assert CANARY_CPF_DIGITS not in reply.text


# ============================================================
# (c) massive-dump streaming — fixture de audit entries sintéticas
# ============================================================


def _synthetic_audit_entries() -> list[dict[str, Any]]:
    """Fixture: entradas de audit log sintéticas com canary em todas as
    posições que o endpoint massive-dump serializa (payload + top-level
    identifier fields + campos de integridade)."""
    base_hash = "ab" * 32
    return [
        {
            "id": 900001,
            "actor_id": f"dpo-{CANARY_CPF}",
            "actor_type": "dpo",
            "action": "cnj.export.massive_dump",
            "resource": f"cnj_export:{CANARY_TOKEN}",
            "payload": {
                "token": CANARY_TOKEN,
                "cpf": CANARY_CPF,
                "cpf_numerico": int(CANARY_CPF_DIGITS),
                "nested": {"titular": f"cpf {CANARY_CPF}", "ok": True},
                "lista": [CANARY_CPF, "sem pii", 87.5, None],
            },
            "ip_truncated": "10.0.0.0/24",
            "user_agent": f"Mozilla cpf={CANARY_CPF_DIGITS}",
            "request_id": f"req-{CANARY_TOKEN}-{CANARY_CPF_DIGITS}",
            "canal": "telegram",
            "prev_hash": "00" * 32,
            "hash": base_hash,
            "hmac_signature": "cd" * 64,
            "hmac_kid": "kid-canary",
            "timestamp": datetime(2026, 7, 25, 12, 0, 0, tzinfo=UTC),
        },
        {
            "id": 900002,
            "actor_id": "system",
            "actor_type": "system",
            "action": "test.cnj.canary",
            "resource": f"test:{CANARY_TOKEN}",
            "payload": {"token": CANARY_TOKEN, "sem_pii": "valor limpo"},
            "ip_truncated": None,
            "user_agent": None,
            "request_id": None,
            "canal": "cron",
            "prev_hash": base_hash,
            "hash": "ef" * 32,
            "hmac_signature": "cd" * 64,
            "hmac_kid": "kid-canary",
            "timestamp": datetime(2026, 7, 25, 12, 0, 1, tzinfo=UTC),
        },
    ]


def _stream_items(entries: list[dict[str, Any]]) -> str:
    """Replica 1:1 a construção do item em massive_dump_cnj._stream_audit_logs
    (app/api/v1/cnj_export.py) — scrub por folha no payload e nos campos
    top-level; integridade (hash/prev_hash/hmac/kid) verbatim."""
    chunks = ["[\n"]
    first = True
    for log in entries:
        if not first:
            chunks.append(",\n")
        first = False
        item = {
            "id": log["id"],
            "actor_id": _scrub_payload_value(log["actor_id"]),
            "actor_type": log["actor_type"],
            "action": log["action"],
            "resource": _scrub_payload_value(log["resource"]),
            "payload": _scrub_payload_value(log["payload"]),
            "ip_truncated": log["ip_truncated"],
            "user_agent": _scrub_payload_value(log["user_agent"]),
            "request_id": _scrub_payload_value(log["request_id"]),
            "canal": _scrub_payload_value(log["canal"]),
            "prev_hash": log["prev_hash"],
            "hash": log["hash"],
            "hmac_signature": log["hmac_signature"],
            "hmac_kid": log["hmac_kid"],
            "timestamp": log["timestamp"].isoformat() if log["timestamp"] else None,
        }
        chunks.append(json.dumps(item, ensure_ascii=False))
    chunks.append("\n]")
    return "".join(chunks)


class TestMassiveDumpStreamCanary:
    def test_stream_never_serializes_canary_raw(self) -> None:
        entries = _synthetic_audit_entries()
        streamed = _stream_items(entries)

        # Contrato canário sobre o stream INTEIRO (não só um item).
        assert CANARY_CPF not in streamed
        assert CANARY_CPF_DIGITS not in streamed
        assert CANARY_TOKEN in streamed  # tripwire rastreável

        # Stream permanece JSON válido e completo (scrub por folha).
        items = json.loads(streamed)
        assert isinstance(items, list) and len(items) == len(entries)

        alvo = next(i for i in items if i["action"] == "cnj.export.massive_dump")
        assert alvo["payload"]["cpf"] == CPF_MASK
        assert alvo["payload"]["cpf_numerico"] == CPF_MASK
        assert alvo["payload"]["nested"]["titular"] == f"cpf {CPF_MASK}"
        assert alvo["payload"]["lista"][0] == CPF_MASK
        # Não-PII preservado: bool/None/float/string limpa intactos.
        assert alvo["payload"]["nested"]["ok"] is True
        assert alvo["payload"]["lista"][1] == "sem pii"
        assert alvo["payload"]["lista"][2] == 87.5
        assert alvo["payload"]["lista"][3] is None
        # Top-level identifier fields mascarados.
        assert CPF_MASK in str(alvo["actor_id"])
        assert CPF_MASK in str(alvo["user_agent"])
        assert CPF_MASK in str(alvo["request_id"])

    def test_stream_preserves_integrity_fields_verbatim(self) -> None:
        """Cadeia SHA256/HMAC não pode ser tocada pelo scrub (CNJ verifica)."""
        entries = _synthetic_audit_entries()
        items = json.loads(_stream_items(entries))
        for original, streamed in zip(entries, items, strict=True):
            assert streamed["prev_hash"] == original["prev_hash"]
            assert streamed["hash"] == original["hash"]
            assert streamed["hmac_signature"] == original["hmac_signature"]
            assert streamed["hmac_kid"] == original["hmac_kid"]
            assert streamed["timestamp"] == original["timestamp"].isoformat()

    def test_scrub_payload_value_tolerates_exotic_shapes(self) -> None:
        """Payload malformado/exótico não derruba o stream e não vaza canary."""
        exotic: dict[str, Any] = {
            "token": CANARY_TOKEN,
            "tupla": (CANARY_CPF, "x"),
            "bytes_like": b"cpf 529.982.247-25".decode(),
            "profundo": {"n1": {"n2": {"n3": [CANARY_CPF_DIGITS]}}},
        }
        result = _scrub_payload_value(exotic)
        blob = json.dumps(result, ensure_ascii=False, default=str)
        assert CANARY_CPF not in blob
        assert CANARY_CPF_DIGITS not in blob
        assert CANARY_TOKEN in blob
