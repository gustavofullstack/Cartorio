"""Fila HITL sanitizada — priorização e fail-closed sem publicação."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.models.conhecimento_institucional import EstadoConhecimento
from app.services.conhecimento_hitl_queue import (
    build_hitl_queue,
    write_hitl_queue,
)


def _classification_payload() -> dict:
    return {
        "schema_version": 1,
        "automatic_promotion_allowed": False,
        "is_blocked": False,
        "sources": [
            {
                "source_id": "a" * 64,
                "document_type_code": "OUTROS_ATOS",
                "display_name": "Outros atos notariais",
                "votes": 1,
                "samples_classified": 1,
                "vote_histogram": {"OUTROS_ATOS": 1},
                "score": 0.2,
                "version_idempotency_key": "d" * 64,
                "ocr_requires_human_review": False,
            },
            {
                "source_id": "b" * 64,
                "document_type_code": "TESTAMENTO",
                "display_name": "Testamento",
                "votes": 2,
                "samples_classified": 3,
                "vote_histogram": {"TESTAMENTO": 2, "SUCESSOES_HERANCA": 1},
                "score": 1.5,
                "version_idempotency_key": "e" * 64,
                "ocr_requires_human_review": True,
            },
            {
                "source_id": "c" * 64,
                "document_type_code": "LISTA_DOCUMENTOS",
                "display_name": "Lista",
                "votes": 3,
                "samples_classified": 3,
                "vote_histogram": {"LISTA_DOCUMENTOS": 3},
                "score": 2.0,
                "version_idempotency_key": "f" * 64,
                "ocr_requires_human_review": False,
            },
        ],
    }


def test_hitl_queue_prioriza_outros_e_ocr() -> None:
    queue = build_hitl_queue(_classification_payload())
    assert queue["automatic_promotion_allowed"] is False
    assert queue["published_eligible"] == 0
    assert queue["summary"]["total_items"] == 3
    items = queue["items"]
    # Menor priority number = primeiro.
    assert items[0]["priority"] <= items[1]["priority"] <= items[2]["priority"]
    # OUTROS ou OCR devem vir antes de LISTA rotineira.
    assert items[-1]["document_type_code"] == "LISTA_DOCUMENTOS"
    assert all(i["decision"] == "PENDING" for i in items)
    assert all(i["suggested_state"] == EstadoConhecimento.PENDING_HUMAN_VALIDATION for i in items)
    assert all(i["consumable"] is False for i in items)
    blob = json.dumps(queue)
    assert "text" not in {k for i in items for k in i}
    assert "Minuta" not in blob


def test_hitl_queue_bloqueia_promocao_automatica() -> None:
    payload = _classification_payload()
    payload["automatic_promotion_allowed"] = True
    with pytest.raises(ValueError, match="automatic_promotion_allowed"):
        build_hitl_queue(payload)


def test_hitl_queue_blocked_classification_empty() -> None:
    queue = build_hitl_queue(
        {
            "automatic_promotion_allowed": False,
            "is_blocked": True,
            "sources": [{"source_id": "a" * 64, "document_type_code": "TESTAMENTO"}],
        }
    )
    assert queue["items"] == []
    assert queue["summary"]["total_items"] == 0


def test_write_hitl_queue(tmp_path: Path) -> None:
    quarantine_root = tmp_path / "brain-ingest-quarantine"
    derived = quarantine_root / "batch" / "derived"
    derived.mkdir(parents=True)
    import app.services.conhecimento_hitl_queue as module

    original_root = module.QUARANTINE_ROOT
    module.QUARANTINE_ROOT = quarantine_root
    queue = build_hitl_queue(_classification_payload())
    try:
        path = write_hitl_queue(derived, queue)
        assert path.name == "hitl_queue.sanitized.json"
        loaded = json.loads(path.read_text(encoding="utf-8"))
        assert loaded["summary"]["published_eligible"] == 0
        assert path.stat().st_mode & 0o777 == 0o600
        assert derived.stat().st_mode & 0o777 == 0o700
    finally:
        module.QUARANTINE_ROOT = original_root


@pytest.mark.parametrize(
    "source",
    [
        {"source_id": "invalid", "document_type_code": "TESTAMENTO"},
        {"source_id": "a" * 64, "document_type_code": "TIPO_INEXISTENTE"},
        "not-a-dict",
    ],
)
def test_hitl_queue_falha_fechada_para_source_invalido(source: object) -> None:
    payload = _classification_payload()
    payload["sources"] = [source]
    with pytest.raises(ValueError):
        build_hitl_queue(payload)


def test_hitl_queue_rejeita_metadado_livre_em_campo_numerico() -> None:
    payload = _classification_payload()
    payload["sources"][0]["score"] = "raw/customer-name.docx"
    with pytest.raises(ValueError, match="score inválido"):
        build_hitl_queue(payload)


def test_hitl_queue_rejeita_output_fora_da_quarentena(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import app.services.conhecimento_hitl_queue as module

    quarantine_root = tmp_path / "brain-ingest-quarantine"
    (quarantine_root / "batch" / "derived").mkdir(parents=True)
    outside = tmp_path / "outside" / "derived"
    outside.mkdir(parents=True)
    monkeypatch.setattr(module, "QUARANTINE_ROOT", quarantine_root)
    with pytest.raises(ValueError, match="fora da quarentena"):
        write_hitl_queue(outside, build_hitl_queue(_classification_payload()))
