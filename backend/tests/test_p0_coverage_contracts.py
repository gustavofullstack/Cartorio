"""Coverage contracts for fail-closed branches added by the Pietra P0 hotfix."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch
from zoneinfo import ZoneInfo

import pytest

from app.services.agendamento import (
    AgendamentoService,
    ClienteNotFoundError,
    ProtocoloNotFoundError,
)
from app.services.graph_evidence_ledger import ChainedEvidenceLedger
from app.services.lgpd_memory_retention import (
    MemoryErasureUnavailableError,
    erase_subject_memory,
    purge_expired_memory,
)
from app.services.pietra_outbound_guard import (
    correct_legal_falsehoods,
    detect_glitch_tokens,
    detect_infra_leak,
    detect_latin_language_mix,
    sanitize_outbound,
    strip_glitch_sentences,
    strip_institutional_falsehoods,
    strip_latin_mix_sentences,
)
from app.services.whatsapp_access import (
    decide_whatsapp_access,
    hmac_sender,
    normalize_whatsapp_number,
    pseudonymous_sender_id,
)


def test_whatsapp_allowlist_edge_contracts() -> None:
    assert normalize_whatsapp_number("123") is None
    with pytest.raises(ValueError, match="at least 32"):
        hmac_sender("+5511999999999", hmac_key="short")
    with pytest.raises(ValueError, match="at least 32"):
        pseudonymous_sender_id("synthetic", hmac_key="short")

    disabled = decide_whatsapp_access(
        "not-a-number",
        sender_id_alt=None,
        allowed_sender_hashes="",
        hmac_key="short",
        restrict_inbound=False,
    )
    assert disabled.allowed and disabled.reason == "allowlist_disabled"

    not_normalizable = decide_whatsapp_access(
        "not-a-number",
        sender_id_alt=None,
        allowed_sender_hashes="a" * 64,
        hmac_key="k" * 32,
        restrict_inbound=True,
    )
    assert not_normalizable.reason == "sender_not_normalizable"


def test_graph_ledger_empty_and_broken_contracts(tmp_path: Path) -> None:
    missing = ChainedEvidenceLedger(tmp_path / "missing.jsonl")
    assert missing.verify_chain() is True

    empty_path = tmp_path / "empty.jsonl"
    empty_path.write_text("\n  \n", encoding="utf-8")
    empty = ChainedEvidenceLedger(empty_path)
    assert empty.get_last_hash() == "0" * 64
    assert empty.verify_chain() is True

    broken_path = tmp_path / "broken.jsonl"
    broken = ChainedEvidenceLedger(broken_path)
    entry = broken.append_entry("P0", "PASS", {"synthetic": True})
    entry["previous_hash"] = "f" * 64
    broken_path.write_text(json.dumps(entry) + "\n", encoding="utf-8")
    assert broken.verify_chain() is False

    entry["previous_hash"] = "0" * 64
    entry["entry_hash"] = "f" * 64
    broken_path.write_text(json.dumps(entry) + "\n", encoding="utf-8")
    assert broken.verify_chain() is False


def test_memory_erasure_and_retention_fail_closed(db_session, monkeypatch) -> None:
    with pytest.raises(ValueError, match="positivo"):
        purge_expired_memory(db_session, now=datetime.now(), conversation_days=0)

    monkeypatch.setattr("app.services.pietra_memoria.get_redis", lambda: None)
    with pytest.raises(MemoryErasureUnavailableError, match="Redis indisponivel"):
        erase_subject_memory(db_session, telefone_hash="a" * 64)


def test_agendamento_error_duration_and_cache_contracts() -> None:
    assert "Cliente #7" in str(ClienteNotFoundError(7))
    assert "Protocolo #8" in str(ProtocoloNotFoundError(8))

    local = ZoneInfo("America/Sao_Paulo")
    now = datetime(2026, 8, 10, 10, 0, tzinfo=local)
    future = datetime(2026, 8, 11, 10, 0, tzinfo=local)
    with pytest.raises(ValueError, match="duração"):
        AgendamentoService._validar_regras_temporais(future, 0, agora=now)

    cached = [{"id": 1}]
    with patch(
        "app.services.agendamento_cache.get_agendamentos_pendentes_cached",
        return_value=cached,
    ):
        assert AgendamentoService.listar_agendamentos_pendentes(MagicMock()) == cached
    with patch(
        "app.services.agendamento_cache.get_agendamentos_proximos_cached",
        return_value=cached,
    ):
        assert AgendamentoService.listar_agendamentos_proximos(MagicMock()) == cached


def test_outbound_edge_detectors_and_sanitizers() -> None:
    assert detect_infra_leak("") is None
    assert detect_latin_language_mix("") is None
    assert detect_latin_language_mix("Actually, o valor depende do ato") is not None
    latin_clean, latin_changed = strip_latin_mix_sentences(
        "O valor será confirmado. Actually, it varies."
    )
    assert latin_changed and "confirmado" in latin_clean and "Actually" not in latin_clean

    assert detect_glitch_tokens("") is None
    assert detect_glitch_tokens("Carta minecraft") is not None
    assert detect_glitch_tokens("superextraordinariamente") is not None
    assert detect_glitch_tokens("ISSA") == "ISSA"
    glitch_clean, glitch_changed = strip_glitch_sentences("A sede está correta. Carta minecraft.")
    assert glitch_changed and "sede" in glitch_clean and "minecraft" not in glitch_clean

    institutional, institutional_changed = strip_institutional_falsehoods(
        "Victor Hugo é integrante. Existe outra unidade."
    )
    assert institutional_changed
    assert "Rua Cel. Antônio Alves Pereira" in institutional
    assert "Victor Hugo é integrante" not in institutional

    legal, legal_changed = correct_legal_falsehoods(
        "O testamento público exige quatro testemunhas."
    )
    assert legal_changed and "duas testemunhas" in legal
    uncertain, uncertain_changed = correct_legal_falsehoods(
        "Acho que a escritura não precisa de validação."
    )
    assert uncertain_changed and "confirmação jurídica" in uncertain

    result = sanitize_outbound(
        "O valor será confirmado. Actually, it varies. Carta minecraft. "
        "Existe outra unidade. O testamento público exige quatro testemunhas."
    )
    assert "language_mixing_latin" in result.reasons
    assert "token_glitch" in result.reasons
    assert "institutional_falsehood" in result.reasons
    assert "legal_falsehood" in result.reasons
