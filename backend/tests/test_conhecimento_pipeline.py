"""Pipeline offline de classificação — opera só sobre derivados sanitizados."""

from __future__ import annotations

import json
from hashlib import sha256
from pathlib import Path

import pytest

from app.services import conhecimento_pipeline as pipeline_module

from app.models.conhecimento_institucional import EstadoConhecimento
from app.services.conhecimento_pipeline import (
    agregar_classificacao_por_fonte,
    classificar_units_sanitizadas,
    executar_pipeline_classificacao,
    escrever_classificacao_sanitizada,
)


def _unit(source_id: str, locator: str, text: str) -> dict[str, object]:
    return {
        "source_id": source_id,
        "unit_id": sha256(f"{source_id}:{locator}".encode()).hexdigest(),
        "locator": locator,
        "sanitized_text_sha256": sha256(text.encode()).hexdigest(),
        "text": text,
    }


@pytest.fixture(autouse=True)
def _private_quarantine(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root = tmp_path / ".private" / "brain-ingest-quarantine"
    root.mkdir(parents=True)
    monkeypatch.setattr(pipeline_module, "QUARANTINE_ROOT", root)


def _write_derived(tmp_path: Path, *, blocked: bool = False) -> Path:
    derived = tmp_path / ".private" / "brain-ingest-quarantine" / "batch" / "derived"
    derived.mkdir(parents=True)
    units = [
        _unit(
            "a" * 64,
            "paragraph:1",
            "Minuta de testamento publico com testamenteiro e clausulas restritivas.",
        ),
        _unit(
            "a" * 64,
            "paragraph:2",
            "Revogacao de testamento anterior e herdeiro testamentario.",
        ),
        _unit(
            "b" * 64,
            "paragraph:1",
            "Tabela de emolumentos e taxa de fiscalizacao com selo de fiscalizacao.",
        ),
    ]
    sources = [
        {
            "source_id": "a" * 64,
            "sha256": "c" * 64 if not blocked else None,
            "status": "extracted" if not blocked else "blocked",
            "unit_count": 2 if not blocked else 0,
        },
        {
            "source_id": "b" * 64,
            "sha256": "d" * 64 if not blocked else None,
            "status": "extracted" if not blocked else "blocked",
            "unit_count": 1 if not blocked else 0,
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
        "sources": sources,
    }
    (derived / "manifest.sanitized.json").write_text(json.dumps(manifest), encoding="utf-8")
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
    assert path.stat().st_mode & 0o777 == 0o600
    assert derived.stat().st_mode & 0o777 == 0o700
    assert path.name == "classification.sanitized.json"
    loaded = json.loads(path.read_text(encoding="utf-8"))
    assert loaded["summary"]["published_eligible"] == 0
    assert summary.units_classified >= 2


def test_pipeline_recusa_derived_fora_da_quarentena(tmp_path: Path) -> None:
    outside = tmp_path / "outside" / "derived"
    outside.mkdir(parents=True)
    with pytest.raises(ValueError, match="fora da quarentena"):
        executar_pipeline_classificacao(outside)


def test_classificar_units_limita_por_fonte() -> None:
    units = [
        _unit(
            "a" * 64,
            f"paragraph:{i}",
            f"testamento publico com testamenteiro e clausulas parte {i}",
        )
        for i in range(10)
    ]
    results = classificar_units_sanitizadas(units, max_units_per_source=3)
    assert len(results) == 3


def test_classificacao_autoritativa_processa_todas_as_units() -> None:
    units = [_unit("a" * 64, f"paragraph:{i}", f"testamento publico parte {i}") for i in range(12)]
    assert len(classificar_units_sanitizadas(units)) == 12


def test_pipeline_rejeita_hash_de_texto_divergente() -> None:
    unit = _unit("a" * 64, "paragraph:1", "testamento publico")
    unit["sanitized_text_sha256"] = "f" * 64
    with pytest.raises(ValueError, match="diverge do texto"):
        classificar_units_sanitizadas([unit])


def test_pipeline_rejeita_source_id_nao_hexadecimal() -> None:
    unit = _unit("a" * 64, "paragraph:1", "testamento publico")
    unit["source_id"] = "z" * 64
    with pytest.raises(ValueError, match="source_id deve ser SHA-256"):
        classificar_units_sanitizadas([unit])


def test_identidade_da_fonte_depende_de_todo_conjunto_ordenado() -> None:
    first = classificar_units_sanitizadas(
        [
            _unit("a" * 64, "paragraph:1", "testamento publico"),
            _unit("a" * 64, "paragraph:2", "testamenteiro nomeado"),
        ]
    )
    changed = classificar_units_sanitizadas(
        [
            _unit("a" * 64, "paragraph:1", "testamento publico"),
            _unit("a" * 64, "paragraph:2", "testamenteiro substituido"),
        ]
    )
    reordered = list(reversed(first))
    key_first = agregar_classificacao_por_fonte(first, source_content_hashes={"a" * 64: "c" * 64})[
        0
    ]["version_idempotency_key"]
    key_changed = agregar_classificacao_por_fonte(
        changed, source_content_hashes={"a" * 64: "c" * 64}
    )[0]["version_idempotency_key"]
    key_reordered = agregar_classificacao_por_fonte(
        reordered, source_content_hashes={"a" * 64: "c" * 64}
    )[0]["version_idempotency_key"]
    assert key_first != key_changed
    assert key_first == key_reordered


def test_agregacao_rejeita_tipo_fora_do_catalogo() -> None:
    results = classificar_units_sanitizadas([_unit("a" * 64, "paragraph:1", "testamento publico")])
    results[0]["classification"]["document_type_code"] = "UNKNOWN"
    with pytest.raises(ValueError, match="fora do catálogo"):
        agregar_classificacao_por_fonte(
            results,
            source_content_hashes={"a" * 64: "c" * 64},
        )
