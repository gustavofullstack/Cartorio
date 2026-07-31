"""Orquestração local do pipeline BRAIN ConhecimentoInstitucional.

Lê apenas derivados sanitizados (manifest/units). Nunca acessa corpus bruto,
rede, LLM ou serviços live. Não promove automaticamente para PUBLISHED.
"""

from __future__ import annotations

import json
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Final

from app.models.conhecimento_institucional import EstadoConhecimento
from app.services.conhecimento_classificador import (
    ClassificacaoDocumento,
    classificar_texto_sanitizado,
)
from app.services.conhecimento_institucional import gerar_chave_idempotencia
from app.services.conhecimento_lifecycle import (
    e_consumivel,
    transicionar,
)

CLASSIFIER_NAME: Final[str] = "local_keyword_v1"
SCHEMA_VERSION: Final[int] = 1


@dataclass(frozen=True)
class PipelineSummary:
    """Resumo numérico e opaco — seguro para stdout/CI."""

    sources_total: int
    sources_classified: int
    units_total: int
    units_classified: int
    type_histogram: dict[str, int]
    is_blocked: bool
    automatic_promotion_allowed: bool
    published_eligible: int

    def as_dict(self) -> dict[str, Any]:
        return {
            "schema_version": SCHEMA_VERSION,
            "sources_total": self.sources_total,
            "sources_classified": self.sources_classified,
            "units_total": self.units_total,
            "units_classified": self.units_classified,
            "type_histogram": self.type_histogram,
            "is_blocked": self.is_blocked,
            "automatic_promotion_allowed": self.automatic_promotion_allowed,
            "published_eligible": self.published_eligible,
            "mode": "local_offline_fail_closed",
        }


def carregar_manifest_sanitizado(derived_dir: Path) -> dict[str, Any]:
    """Carrega manifest sanitizado; falha se promoção automática estiver ligada."""
    path = derived_dir / "manifest.sanitized.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("automatic_promotion_allowed") is True:
        raise ValueError("automatic_promotion_allowed deve permanecer false")
    return payload


def carregar_units_sanitizadas(derived_dir: Path) -> list[dict[str, Any]]:
    """Carrega units sanitizadas (JSONL). Não loga o campo text."""
    path = derived_dir / "units.sanitized.jsonl"
    units: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        units.append(json.loads(line))
    return units


def classificar_units_sanitizadas(
    units: list[dict[str, Any]],
    *,
    max_units_per_source: int = 3,
) -> list[dict[str, Any]]:
    """Classifica até N units por source (amostra representativa, custo linear).

    Retorna registros sem o texto original — apenas metadados e classificação.
    """
    por_fonte: dict[str, int] = {}
    resultados: list[dict[str, Any]] = []

    for unit in units:
        source_id = str(unit.get("source_id", ""))
        unit_id = str(unit.get("unit_id", ""))
        text = unit.get("text")
        if not source_id or not unit_id or not isinstance(text, str):
            continue
        contagem = por_fonte.get(source_id, 0)
        if contagem >= max_units_per_source:
            continue
        try:
            classificacao: ClassificacaoDocumento = classificar_texto_sanitizado(
                text,
                unit_id=unit_id,
                classifier_name=CLASSIFIER_NAME,
            )
        except ValueError:
            continue
        por_fonte[source_id] = contagem + 1
        record = {
            "source_id": source_id,
            "unit_id": unit_id,
            "locator": unit.get("locator"),
            "sanitized_text_sha256": unit.get("sanitized_text_sha256"),
            "state": EstadoConhecimento.PENDING_HUMAN_VALIDATION,
            "classification": classificacao.as_dict(),
        }
        # OCR units always force human review flag (already on classification).
        if unit.get("requires_human_review") or unit.get("ocr"):
            record["ocr_requires_human_review"] = True
        resultados.append(record)
    return resultados


def agregar_classificacao_por_fonte(
    unit_classifications: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Escolhe o tipo dominante por source_id (voto majoritário, empate = primeiro)."""
    buckets: dict[str, list[dict[str, Any]]] = {}
    for item in unit_classifications:
        buckets.setdefault(str(item["source_id"]), []).append(item)

    agregados: list[dict[str, Any]] = []
    for source_id, items in sorted(buckets.items()):
        counter: Counter[str] = Counter()
        confidences: dict[str, list[str]] = {}
        for item in items:
            code = str(item["classification"]["document_type_code"])
            counter[code] += 1
            confidences.setdefault(code, []).append(str(item["classification"]["confidence"]))
        winner_code, winner_votes = counter.most_common(1)[0]
        sample = next(i for i in items if i["classification"]["document_type_code"] == winner_code)
        content_hash = str(items[0].get("sanitized_text_sha256") or ("0" * 64))
        # identity for future version registration (hash of first unit — opaque)
        version_key = gerar_chave_idempotencia(
            content_hash if len(content_hash) == 64 else "0" * 64,
            1,
        )
        agregados.append(
            {
                "source_id": source_id,
                "document_type_code": winner_code,
                "display_name": sample["classification"]["display_name"],
                "votes": winner_votes,
                "samples_classified": len(items),
                "vote_histogram": dict(sorted(counter.items())),
                "state": EstadoConhecimento.CLASSIFIED,
                "next_state": EstadoConhecimento.PENDING_HUMAN_VALIDATION,
                "requires_human_validation": True,
                "automatic_promotion_allowed": False,
                "version_idempotency_key": version_key,
                "consumable": e_consumivel(EstadoConhecimento.CLASSIFIED),
            }
        )
    return agregados


def avancar_para_validacao_humana(
    estado_atual: str = EstadoConhecimento.CLASSIFIED,
    *,
    actor_id: str = "pipeline:local_keyword_v1",
    reason: str = "classificacao local concluida; HITL obrigatorio",
) -> str:
    """CLASSIFIED → PENDING_HUMAN_VALIDATION (nunca além)."""
    resultado = transicionar(
        estado_atual,
        EstadoConhecimento.PENDING_HUMAN_VALIDATION,
        actor_id=actor_id,
        reason=reason,
    )
    return resultado.to_state


def executar_pipeline_classificacao(derived_dir: Path) -> tuple[PipelineSummary, dict[str, Any]]:
    """Pipeline completo offline a partir de ``derived/``.

    Retorna (summary, payload_sanitizado). O payload NÃO contém texto de units.
    """
    manifest = carregar_manifest_sanitizado(derived_dir)
    is_blocked = bool(manifest.get("is_blocked"))
    units = carregar_units_sanitizadas(derived_dir) if not is_blocked else []
    unit_results = classificar_units_sanitizadas(units) if units else []
    source_results = agregar_classificacao_por_fonte(unit_results)

    # Avança estado lógico no payload (sem DB / sem publish).
    for item in source_results:
        item["state"] = avancar_para_validacao_humana()

    histogram: Counter[str] = Counter(str(item["document_type_code"]) for item in source_results)
    summary = PipelineSummary(
        sources_total=int(manifest.get("sources_discovered") or 0),
        sources_classified=len(source_results),
        units_total=int(manifest.get("units_written") or len(units)),
        units_classified=len(unit_results),
        type_histogram=dict(sorted(histogram.items())),
        is_blocked=is_blocked,
        automatic_promotion_allowed=False,
        published_eligible=0,  # fail-closed: nada publicado automaticamente
    )
    payload = {
        "schema_version": SCHEMA_VERSION,
        "mode": "local_offline_fail_closed",
        "automatic_promotion_allowed": False,
        "is_blocked": is_blocked,
        "summary": summary.as_dict(),
        "sources": source_results,
        "unit_classifications_count": len(unit_results),
        # unit-level details omitidos do artefato principal para reduzir superfície;
        # hashes e códigos bastam para HITL posterior.
        "unit_classifications": [
            {
                "source_id": u["source_id"],
                "unit_id": u["unit_id"],
                "document_type_code": u["classification"]["document_type_code"],
                "confidence": u["classification"]["confidence"],
                "idempotency_key": u["classification"]["idempotency_key"],
                "state": u["state"],
            }
            for u in unit_results
        ],
    }
    return summary, payload


def escrever_classificacao_sanitizada(derived_dir: Path, payload: dict[str, Any]) -> Path:
    """Persiste classification.sanitized.json apenas dentro de derived/."""
    target = derived_dir / "classification.sanitized.json"
    temporary = target.with_name(f".{target.name}.tmp")
    temporary.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    temporary.replace(target)
    return target


__all__ = [
    "CLASSIFIER_NAME",
    "PipelineSummary",
    "agregar_classificacao_por_fonte",
    "avancar_para_validacao_humana",
    "carregar_manifest_sanitizado",
    "carregar_units_sanitizadas",
    "classificar_units_sanitizadas",
    "escrever_classificacao_sanitizada",
    "executar_pipeline_classificacao",
]
