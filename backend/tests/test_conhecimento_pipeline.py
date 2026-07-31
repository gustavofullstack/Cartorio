"""Pipeline offline de classificação — opera só sobre derivados sanitizados."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.models.conhecimento_institucional import EstadoConhecimento
from app.services.conhecimento_pipeline import (
    classificar_units_sanitizadas,
    executar_pipeline_classificacao,
    escrever_classificacao_sanitizada,
)


def _write_derived(tmp_path: Path, *, blocked: bool = False) -> Path:
    derived = tmp_path / "derived"
    derived.mkdir()
    units = [
        {
            "source_id": "a" * 64,
            "unit_id": "u1" + ("0" * 62),
            "locator": "paragraph:1",
            "sanitized_text_sha256": "1" * 64,
            "text": (
                "Minuta de testamento publico com testamenteiro e clausulas restritivas."
            ),
        },
        {
            "source_id": "a" * 64,
            "unit_id": "u2" + ("0" * 62),
            "locator": "paragraph:2",
            "sanitized_text_sha256": "2" * 64,
            "text": "Revogacao de testamento anterior e herdeiro testamentario.",
        },
        {
            "source_id": "b" * 64,
            "unit_id": "u3" + ("0" * 62),
            "locator": "paragraph:1",
            "sanitized_text_sha256": "3" * 64,
            "text": (
                "Tabela de emolumentos e taxa de fiscalizacao com selo de fiscalizacao."
            ),
        },
    ]
    manifest = {
        "schema_version": 1,
        "mode": "local_offline_fail_closed",
        "automatic_promotion_allowed": False,
        "is_blocked": blocked,
        "sources_discovered": 2,
        "sources_extracted": 0 if blocked else 2,
        "units_written": 0 if blocked else 3,
        "sources": [],
    }
    (derived / "manifest.sanitized.json").write_text(
        json.dumps(manifest), encoding="utf-8"
    )
    if not blocked:
        (derived / "units.sanitized.jsonl").write_text(
            "".join(json.dumps(u, ensure_ascii=False) + "\n" for u in units),
            encoding="utf-8",
        )
    else:
        (derived / "units.sanitized.jsonl").write_text("", encoding="utf-8")
    return derived


def test_pipeline_classifica_sem_publicar(tmp_path: Path) -> None:
    derived = _write_derived(tmp_path)
    summary, payload = executar_pipeline_classificacao(derived)

    assert summary.is_blocked is False
    assert summary.automatic_promotion_allowed is False
    assert summary.published_eligible == 0
    assert summary.sources_classified == 2
    assert "TESTAMENTO" in summary.type_histogram
    assert "EMOLUMENTOS" in summary.type_histogram

    for source in payload["sources"]:
        assert source["state"] == EstadoConhecimento.PENDING_HUMAN_VALIDATION
        assert source["requires_human_validation"] is True
        assert source["consumable"] is False
        assert "text" not in source

    # Artefato não deve conter trechos do texto-fonte (display_name do catálogo é ok).
    blob = json.dumps(payload)
    assert "Minuta de testamento publico com testamenteiro" not in blob
    assert "selo de fiscalizacao com selo" not in blob
    assert "clausulas restritivas" not in blob


def test_pipeline_bloqueado_nao_classifica(tmp_path: Path) -> None:
    derived = _write_derived(tmp_path, blocked=True)
    summary, payload = executar_pipeline_classificacao(derived)
    assert summary.is_blocked is True
    assert summary.sources_classified == 0
    assert payload["sources"] == []


def test_pipeline_recusa_promocao_automatica(tmp_path: Path) -> None:
    derived = _write_derived(tmp_path)
    manifest_path = derived / "manifest.sanitized.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["automatic_promotion_allowed"] = True
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    with pytest.raises(ValueError, match="automatic_promotion_allowed"):
        executar_pipeline_classificacao(derived)


def test_escreve_classification_somente_em_derived(tmp_path: Path) -> None:
    derived = _write_derived(tmp_path)
    summary, payload = executar_pipeline_classificacao(derived)
    path = escrever_classificacao_sanitizada(derived, payload)
    assert path.parent == derived
    assert path.name == "classification.sanitized.json"
    loaded = json.loads(path.read_text(encoding="utf-8"))
    assert loaded["summary"]["published_eligible"] == 0
    assert summary.units_classified >= 2


def test_classificar_units_limita_por_fonte() -> None:
    units = [
        {
            "source_id": "s" * 64,
            "unit_id": f"u{i}" + ("0" * 62),
            "locator": f"paragraph:{i}",
            "sanitized_text_sha256": str(i) * 64,
            "text": "testamento publico com testamenteiro e clausulas",
        }
        for i in range(10)
    ]
    results = classificar_units_sanitizadas(units, max_units_per_source=3)
    assert len(results) == 3
