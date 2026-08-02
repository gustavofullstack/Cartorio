"""Orquestração local do pipeline BRAIN ConhecimentoInstitucional.

Lê apenas derivados sanitizados (manifest/units). Nunca acessa corpus bruto,
rede, LLM ou serviços live. Não promove automaticamente para PUBLISHED.
"""

from __future__ import annotations

import json
import os
from collections import Counter
from collections.abc import Mapping
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from hashlib import sha256
from pathlib import Path
from re import fullmatch
from typing import Any, Final

from app.models.conhecimento_institucional import EstadoConhecimento
from app.services.conhecimento_classificador import (
    ClassificacaoDocumento,
    catalogo_tipos_documento,
    classificar_texto_sanitizado,
)
from app.services.conhecimento_institucional import gerar_chave_idempotencia
from app.services.conhecimento_lifecycle import (
    e_consumivel,
    transicionar,
)

CLASSIFIER_NAME: Final[str] = "local_keyword_v1"
SCHEMA_VERSION: Final[int] = 1
PROJECT_ROOT: Final[Path] = Path(__file__).resolve().parents[3]
QUARANTINE_ROOT: Final[Path] = PROJECT_ROOT / ".private" / "brain-ingest-quarantine"


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
    """Carrega e valida estritamente o contrato do manifest sanitizado."""
    path = _validate_derived_dir(derived_dir) / "manifest.sanitized.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("manifest deve ser um objeto")
    if payload.get("schema_version") != SCHEMA_VERSION:
        raise ValueError("schema_version do manifest inválida")
    if payload.get("mode") != "local_offline_fail_closed":
        raise ValueError("mode do manifest inválido")
    if payload.get("automatic_promotion_allowed") is not False:
        raise ValueError("automatic_promotion_allowed deve permanecer false")
    if not isinstance(payload.get("is_blocked"), bool):
        raise ValueError("is_blocked deve ser booleano")

    for field in ("sources_discovered", "sources_extracted", "units_written"):
        _validar_inteiro_nao_negativo(payload.get(field), field)
    sources = payload.get("sources")
    if not isinstance(sources, list):
        raise ValueError("sources deve ser uma lista")
    if len(sources) != payload["sources_discovered"]:
        raise ValueError("sources_discovered diverge do inventário")

    seen: set[str] = set()
    extracted = 0
    unit_count = 0
    for source in sources:
        if not isinstance(source, dict):
            raise ValueError("source do manifest deve ser um objeto")
        source_id = _validar_sha256(source.get("source_id"), "source_id")
        if source_id in seen:
            raise ValueError("source_id duplicado no manifest")
        seen.add(source_id)
        count = _validar_inteiro_nao_negativo(source.get("unit_count"), "unit_count")
        status = source.get("status")
        if status == "extracted":
            _validar_sha256(source.get("sha256"), "source sha256")
            extracted += 1
            unit_count += count
        elif status != "blocked":
            raise ValueError("status de source inválido")
    if extracted != payload["sources_extracted"]:
        raise ValueError("sources_extracted diverge do inventário")
    if unit_count != payload["units_written"]:
        raise ValueError("units_written diverge do inventário")
    if not payload["is_blocked"] and extracted != len(sources):
        raise ValueError("manifest não bloqueado contém source não extraída")
    if not payload["is_blocked"] and not sources:
        raise ValueError("manifest não bloqueado não pode estar vazio")
    return payload


def carregar_units_sanitizadas(derived_dir: Path) -> list[dict[str, Any]]:
    """Carrega units sanitizadas (JSONL). Não loga o campo text."""
    path = _validate_derived_dir(derived_dir) / "units.sanitized.jsonl"
    units: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        unit = json.loads(line)
        if not isinstance(unit, dict):
            raise ValueError("unit sanitizada deve ser um objeto")
        units.append(unit)
    return units


def classificar_units_sanitizadas(
    units: list[dict[str, Any]],
    *,
    max_units_per_source: int | None = None,
) -> list[dict[str, Any]]:
    """Classifica todas as units; limite explícito serve apenas para amostragem auxiliar.

    Retorna registros sem o texto original — apenas metadados e classificação.
    A execução autoritativa não informa limite e, portanto, não descarta units.
    """
    if max_units_per_source is not None and max_units_per_source <= 0:
        raise ValueError("max_units_per_source deve ser positivo")

    validadas = [_validar_unit_sanitizada(unit) for unit in units]
    unit_ids = [str(unit["unit_id"]) for unit in validadas]
    if len(unit_ids) != len(set(unit_ids)):
        raise ValueError("unit_id duplicado")
    if max_units_per_source is None:
        ordenadas = sorted(
            validadas,
            key=lambda u: (str(u["source_id"]), str(u["locator"]), str(u["unit_id"])),
        )
    else:
        ordenadas = sorted(
            validadas,
            key=lambda u: (
                str(u["source_id"]),
                -len(str(u["text"])),
                str(u["locator"]),
            ),
        )
    por_fonte: dict[str, int] = {}
    resultados: list[dict[str, Any]] = []

    for unit in ordenadas:
        source_id = str(unit["source_id"])
        unit_id = str(unit["unit_id"])
        text = str(unit["text"])
        contagem = por_fonte.get(source_id, 0)
        if max_units_per_source is not None and contagem >= max_units_per_source:
            continue
        classificacao: ClassificacaoDocumento = classificar_texto_sanitizado(
            text,
            unit_id=unit_id,
            classifier_name=CLASSIFIER_NAME,
        )
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


def _score_tipo(code: str, votes: int, confidences: list[str]) -> Decimal:
    """Pontuação ponderada; OUTROS_ATOS perde desempate para tipos específicos."""
    if not confidences:
        avg = Decimal("0.35")
    else:
        avg = sum((Decimal(c) for c in confidences), start=Decimal("0")) / len(confidences)
    penalty = Decimal("0.55") if code == "OUTROS_ATOS" else Decimal("1")
    return Decimal(votes) * avg * penalty


def agregar_classificacao_por_fonte(
    unit_classifications: list[dict[str, Any]],
    *,
    source_content_hashes: Mapping[str, str],
) -> list[dict[str, Any]]:
    """Escolhe o tipo dominante por source_id (voto × confiança; OUTROS penalizado)."""
    catalogo = catalogo_tipos_documento()
    hashes_validados = {
        _validar_sha256(source_id, "source_id"): _validar_sha256(content_hash, "source sha256")
        for source_id, content_hash in source_content_hashes.items()
    }
    buckets: dict[str, list[dict[str, Any]]] = {}
    seen_units: set[str] = set()
    for item in unit_classifications:
        if not isinstance(item, dict) or not isinstance(item.get("classification"), dict):
            raise ValueError("classificação de unit inválida")
        source_id = _validar_sha256(item.get("source_id"), "source_id")
        if source_id not in hashes_validados:
            raise ValueError("classificação referencia source desconhecida")
        unit_id = _validar_sha256(item.get("unit_id"), "unit_id")
        if unit_id in seen_units:
            raise ValueError("classificação duplicada para unit_id")
        seen_units.add(unit_id)
        _validar_sha256(item.get("sanitized_text_sha256"), "sanitized_text_sha256")
        classification = item["classification"]
        code = str(classification.get("document_type_code") or "")
        if code not in catalogo:
            raise ValueError("document_type_code fora do catálogo")
        if classification.get("display_name") != catalogo[code]:
            raise ValueError("display_name diverge do catálogo")
        if classification.get("classifier_name") != CLASSIFIER_NAME:
            raise ValueError("classifier_name divergente")
        if classification.get("requires_human_validation") is not True:
            raise ValueError("classificação deve exigir validação humana")
        if item.get("state") != EstadoConhecimento.PENDING_HUMAN_VALIDATION:
            raise ValueError("estado da classificação inválido")
        try:
            confidence = Decimal(str(classification.get("confidence")))
        except InvalidOperation:
            raise ValueError("confidence inválida") from None
        if not confidence.is_finite() or not Decimal("0") <= confidence <= Decimal("1"):
            raise ValueError("confidence fora do intervalo")
        _validar_sha256(classification.get("idempotency_key"), "classification idempotency_key")
        buckets.setdefault(source_id, []).append(item)
    if set(buckets) != set(hashes_validados):
        raise ValueError("conjunto de sources classificadas incompleto")

    agregados: list[dict[str, Any]] = []
    for source_id, items in sorted(buckets.items()):
        counter: Counter[str] = Counter()
        confidences: dict[str, list[str]] = {}
        ocr_flag = False
        for item in items:
            code = str(item["classification"]["document_type_code"])
            counter[code] += 1
            confidences.setdefault(code, []).append(
                str(item["classification"]["confidence"])
            )
            if item.get("ocr_requires_human_review"):
                ocr_flag = True
        winner_code = max(
            counter.keys(),
            key=lambda c: (_score_tipo(c, counter[c], confidences[c]), c),
        )
        winner_votes = counter[winner_code]
        sample = next(
            i for i in items if i["classification"]["document_type_code"] == winner_code
        )
        content_set_hash = _hash_conjunto_ordenado(
            hashes_validados[source_id],
            items,
        )
        version_key = gerar_chave_idempotencia(content_set_hash, 1)
        score = _score_tipo(winner_code, winner_votes, confidences[winner_code])
        agregados.append(
            {
                "source_id": source_id,
                "document_type_code": winner_code,
                "display_name": sample["classification"]["display_name"],
                "votes": winner_votes,
                "samples_classified": len(items),
                "vote_histogram": dict(sorted(counter.items())),
                "score": float(score.quantize(Decimal("0.0001"))),
                "state": EstadoConhecimento.CLASSIFIED,
                "next_state": EstadoConhecimento.PENDING_HUMAN_VALIDATION,
                "requires_human_validation": True,
                "automatic_promotion_allowed": False,
                "version_idempotency_key": version_key,
                "content_set_sha256": content_set_hash,
                "consumable": e_consumivel(EstadoConhecimento.CLASSIFIED),
                "ocr_requires_human_review": ocr_flag,
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
    source_hashes = {
        str(source["source_id"]): str(source["sha256"])
        for source in manifest["sources"]
        if source["status"] == "extracted"
    }
    if not is_blocked:
        _validar_coerencia_manifest_units(manifest, units, source_hashes)
    unit_results = classificar_units_sanitizadas(units) if units else []
    source_results = (
        agregar_classificacao_por_fonte(
            unit_results,
            source_content_hashes=source_hashes,
        )
        if unit_results
        else []
    )
    if not is_blocked and {str(item["source_id"]) for item in source_results} != set(source_hashes):
        raise ValueError("nem todas as sources receberam classificação")

    # Avança estado lógico no payload (sem DB / sem publish).
    for item in source_results:
        item["state"] = avancar_para_validacao_humana()

    histogram: Counter[str] = Counter(str(item["document_type_code"]) for item in source_results)
    summary = PipelineSummary(
        sources_total=int(manifest["sources_discovered"]),
        sources_classified=len(source_results),
        units_total=int(manifest["units_written"]),
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


def _validar_sha256(value: object, field: str) -> str:
    if not isinstance(value, str) or fullmatch(r"[0-9a-f]{64}", value) is None:
        raise ValueError(f"{field} deve ser SHA-256 hexadecimal")
    return value


def _validar_inteiro_nao_negativo(value: object, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"{field} deve ser inteiro não negativo")
    return value


def _validar_unit_sanitizada(unit: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(unit, dict):
        raise ValueError("unit sanitizada deve ser um objeto")
    _validar_sha256(unit.get("source_id"), "source_id")
    _validar_sha256(unit.get("unit_id"), "unit_id")
    expected_hash = _validar_sha256(
        unit.get("sanitized_text_sha256"),
        "sanitized_text_sha256",
    )
    locator = unit.get("locator")
    text = unit.get("text")
    if not isinstance(locator, str) or not locator.strip():
        raise ValueError("locator obrigatório")
    if not isinstance(text, str) or not text.strip():
        raise ValueError("text sanitizado obrigatório")
    actual_hash = sha256(text.encode("utf-8")).hexdigest()
    if actual_hash != expected_hash:
        raise ValueError("sanitized_text_sha256 diverge do texto")
    return unit


def _hash_conjunto_ordenado(source_content_hash: str, items: list[dict[str, Any]]) -> str:
    units = sorted(
        (
            _validar_sha256(item.get("unit_id"), "unit_id"),
            _validar_sha256(item.get("sanitized_text_sha256"), "sanitized_text_sha256"),
        )
        for item in items
    )
    canonical = json.dumps(
        {
            "classifier_name": CLASSIFIER_NAME,
            "schema_version": SCHEMA_VERSION,
            "source_content_sha256": source_content_hash,
            "units": units,
        },
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    )
    return sha256(canonical.encode("utf-8")).hexdigest()


def _validar_coerencia_manifest_units(
    manifest: dict[str, Any],
    units: list[dict[str, Any]],
    source_hashes: Mapping[str, str],
) -> None:
    if len(units) != manifest["units_written"]:
        raise ValueError("quantidade de units diverge do manifest")
    validated = [_validar_unit_sanitizada(unit) for unit in units]
    counts = Counter(str(unit["source_id"]) for unit in validated)
    if set(counts) != set(source_hashes):
        raise ValueError("units referenciam conjunto de sources divergente")
    expected_counts = {
        str(source["source_id"]): int(source["unit_count"])
        for source in manifest["sources"]
        if source["status"] == "extracted"
    }
    if counts != Counter(expected_counts):
        raise ValueError("unit_count por source diverge do manifest")


def escrever_classificacao_sanitizada(derived_dir: Path, payload: dict[str, Any]) -> Path:
    """Persiste classification.sanitized.json apenas dentro de derived/."""
    safe_derived = _validate_derived_dir(derived_dir)
    safe_derived.chmod(0o700)
    target = safe_derived / "classification.sanitized.json"
    temporary = target.with_name(f".{target.name}.tmp")
    content = json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        temporary.replace(target)
        target.chmod(0o600)
    except BaseException:
        temporary.unlink(missing_ok=True)
        raise
    return target


def _validate_derived_dir(derived_dir: Path) -> Path:
    """Confina leitura e escrita ao ``derived`` de um lote privado real."""
    root = QUARANTINE_ROOT.resolve(strict=True)
    candidate = derived_dir.resolve(strict=True)
    if not candidate.is_dir() or candidate.name != "derived":
        raise ValueError("derived inválido")
    try:
        relative = candidate.relative_to(root)
    except ValueError as error:
        raise ValueError("derived fora da quarentena") from error
    if len(relative.parts) < 2:
        raise ValueError("derived deve pertencer a um lote da quarentena")
    return candidate


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
