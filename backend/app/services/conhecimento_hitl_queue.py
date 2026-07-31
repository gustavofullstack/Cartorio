"""Fila HITL sanitizada para revisão humana do corpus BRAIN.

Opera somente sobre ``classification.sanitized.json``. Não lê corpus bruto,
não publica e não envia dados a rede/LLM. Prioriza risco e ambiguidade.
"""

from __future__ import annotations

import json
import math
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Final

from app.models.conhecimento_institucional import EstadoConhecimento

SCHEMA_VERSION: Final[int] = 1
PROJECT_ROOT: Final[Path] = Path(__file__).resolve().parents[3]
QUARANTINE_ROOT: Final[Path] = PROJECT_ROOT / ".private" / "brain-ingest-quarantine"
_OPAQUE_ID: Final[re.Pattern[str]] = re.compile(r"[0-9a-f]{64}")

# Prioridade base por tipo (menor = revisa primeiro).
_PRIORIDADE_TIPO: Final[dict[str, int]] = {
    "OUTROS_ATOS": 10,
    "NORMATIVO_CNJ": 20,
    "EMOLUMENTOS": 25,
    "RECONHECIMENTO_PATERNIDADE": 30,
    "TESTAMENTO": 40,
    "INVENTARIO_PARTILHA": 40,
    "USUCAPIAO": 45,
    "DIVORCIO_UNIAO_ESTAVEL": 45,
    "ESCRITURA_COMPRA_VENDA": 50,
    "SUCESSOES_HERANCA": 50,
    "ATA_NOTARIAL": 55,
    "PROCURACAO": 60,
    "RECONHECIMENTO_FIRMA": 60,
    "ESTREMACAO": 65,
    "LISTA_DOCUMENTOS": 70,
}

_DECISOES_VALIDAS: Final[frozenset[str]] = frozenset({"PENDING", "APPROVE", "REJECT", "RECLASSIFY"})


@dataclass(frozen=True)
class HitlQueueSummary:
    """Resumo numérico da fila — seguro para stdout."""

    total_items: int
    by_priority_band: dict[str, int]
    by_type: dict[str, int]
    ocr_flagged: int
    ambiguous: int
    automatic_promotion_allowed: bool
    published_eligible: int

    def as_dict(self) -> dict[str, Any]:
        return {
            "schema_version": SCHEMA_VERSION,
            "total_items": self.total_items,
            "by_priority_band": self.by_priority_band,
            "by_type": self.by_type,
            "ocr_flagged": self.ocr_flagged,
            "ambiguous": self.ambiguous,
            "automatic_promotion_allowed": self.automatic_promotion_allowed,
            "published_eligible": self.published_eligible,
            "mode": "local_offline_hitl_queue",
            "state": EstadoConhecimento.PENDING_HUMAN_VALIDATION,
        }


def _priority_band(score: int) -> str:
    if score <= 25:
        return "P0_critical"
    if score <= 45:
        return "P1_high"
    if score <= 60:
        return "P2_medium"
    return "P3_low"


def _is_ambiguous(source: dict[str, Any]) -> bool:
    hist = source.get("vote_histogram") or {}
    if not isinstance(hist, dict) or len(hist) < 2:
        return False
    counts = sorted((int(v) for v in hist.values()), reverse=True)
    if len(counts) < 2:
        return False
    # Empate ou diferença de 1 voto entre os dois primeiros.
    return counts[0] - counts[1] <= 1


def _nonnegative_int(value: object, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"{field} inválido")
    return value


def _validated_histogram(value: object) -> dict[str, int]:
    if not isinstance(value, dict):
        raise ValueError("vote_histogram inválido")
    histogram: dict[str, int] = {}
    for code, count in value.items():
        if code not in _PRIORIDADE_TIPO:
            raise ValueError("vote_histogram contém tipo fora do catálogo")
        histogram[str(code)] = _nonnegative_int(count, "vote_histogram count")
    return histogram


def build_hitl_queue(classification_payload: dict[str, Any]) -> dict[str, Any]:
    """Monta fila priorizada a partir do payload de classificação sanitizado."""
    if not isinstance(classification_payload, dict):
        raise ValueError("classification payload inválido")
    if classification_payload.get("automatic_promotion_allowed") is not False:
        raise ValueError("automatic_promotion_allowed deve permanecer false")
    is_blocked = classification_payload.get("is_blocked")
    if not isinstance(is_blocked, bool):
        raise ValueError("is_blocked inválido")
    if is_blocked:
        return {
            "schema_version": SCHEMA_VERSION,
            "mode": "local_offline_hitl_queue",
            "is_blocked": True,
            "automatic_promotion_allowed": False,
            "published_eligible": 0,
            "items": [],
            "summary": HitlQueueSummary(
                total_items=0,
                by_priority_band={},
                by_type={},
                ocr_flagged=0,
                ambiguous=0,
                automatic_promotion_allowed=False,
                published_eligible=0,
            ).as_dict(),
            "instructions": _instructions(),
        }

    sources = classification_payload.get("sources")
    if not isinstance(sources, list):
        raise ValueError("sources deve ser uma lista")
    items: list[dict[str, Any]] = []
    for index, source in enumerate(sources):
        if not isinstance(source, dict):
            raise ValueError("source inválido")
        source_id = str(source.get("source_id") or "")
        if _OPAQUE_ID.fullmatch(source_id) is None:
            raise ValueError("source_id inválido")
        doc_type = str(source.get("document_type_code") or "")
        if doc_type not in _PRIORIDADE_TIPO:
            raise ValueError("document_type_code fora do catálogo")
        version_key = str(source.get("version_idempotency_key") or "")
        if _OPAQUE_ID.fullmatch(version_key) is None:
            raise ValueError("version_idempotency_key inválida")
        base = _PRIORIDADE_TIPO[doc_type]
        histogram = _validated_histogram(source.get("vote_histogram"))
        source_for_ambiguity = {"vote_histogram": histogram}
        ambiguous = _is_ambiguous(source_for_ambiguity)
        ocr = source.get("ocr_requires_human_review")
        if not isinstance(ocr, bool):
            raise ValueError("ocr_requires_human_review inválido")
        samples = _nonnegative_int(source.get("samples_classified"), "samples_classified")
        votes = _nonnegative_int(source.get("votes"), "votes")
        score = source.get("score")
        if (
            isinstance(score, bool)
            or not isinstance(score, (int, float))
            or not math.isfinite(score)
            or score < 0
        ):
            raise ValueError("score inválido")
        # Ajustes de prioridade (menor = mais urgente).
        priority = base
        if ocr:
            priority -= 15
        if ambiguous:
            priority -= 10
        if samples <= 1:
            priority -= 5
        if doc_type == "OUTROS_ATOS":
            priority -= 5
        priority = max(1, priority)

        items.append(
            {
                "queue_id": f"hitl-{index + 1:04d}",
                "source_id": source_id,
                "document_type_code": doc_type,
                "suggested_state": EstadoConhecimento.PENDING_HUMAN_VALIDATION,
                "priority": priority,
                "priority_band": _priority_band(priority),
                "votes": votes,
                "samples_classified": samples,
                "vote_histogram": histogram,
                "score": score,
                "ambiguous": ambiguous,
                "ocr_requires_human_review": ocr,
                "version_idempotency_key": version_key,
                "requires_human_validation": True,
                "automatic_promotion_allowed": False,
                "consumable": False,
                "decision": "PENDING",
                "allowed_decisions": sorted(_DECISOES_VALIDAS),
                "reviewer_id": None,
                "rationale": None,
                # Nunca inclui texto, path ou nome de arquivo.
            }
        )

    items.sort(key=lambda i: (int(i["priority"]), str(i["source_id"])))

    by_band: dict[str, int] = {}
    by_type: dict[str, int] = {}
    ocr_flagged = 0
    ambiguous_count = 0
    for item in items:
        band = str(item["priority_band"])
        by_band[band] = by_band.get(band, 0) + 1
        code = str(item["document_type_code"])
        by_type[code] = by_type.get(code, 0) + 1
        if item["ocr_requires_human_review"]:
            ocr_flagged += 1
        if item["ambiguous"]:
            ambiguous_count += 1

    summary = HitlQueueSummary(
        total_items=len(items),
        by_priority_band=dict(sorted(by_band.items())),
        by_type=dict(sorted(by_type.items())),
        ocr_flagged=ocr_flagged,
        ambiguous=ambiguous_count,
        automatic_promotion_allowed=False,
        published_eligible=0,
    )
    return {
        "schema_version": SCHEMA_VERSION,
        "mode": "local_offline_hitl_queue",
        "is_blocked": False,
        "automatic_promotion_allowed": False,
        "published_eligible": 0,
        "summary": summary.as_dict(),
        "items": items,
        "instructions": _instructions(),
    }


def _instructions() -> dict[str, str]:
    return {
        "decision_field": "decision in {PENDING, APPROVE, REJECT, RECLASSIFY}",
        "approve_effect": "PENDING_HUMAN_VALIDATION -> APPROVED (ainda NÃO publica)",
        "publish_separate": "publicar_versao() é passo separado após APPROVED",
        "reject_effect": "PENDING_HUMAN_VALIDATION -> REJECTED (terminal)",
        "reclassify_effect": "mantém PENDING; reviewer sugere document_type_code",
        "pii_rule": "nunca colar texto bruto, CPF, nome de arquivo ou path na rationale",
        "lgpd_signoff": "publicação exige sign-off cartorio-lgpd quando aplicável",
    }


def load_classification(derived_dir: Path) -> dict[str, Any]:
    safe_derived = _validate_derived_dir(derived_dir)
    path = safe_derived / "classification.sanitized.json"
    return json.loads(path.read_text(encoding="utf-8"))


def write_hitl_queue(derived_dir: Path, payload: dict[str, Any]) -> Path:
    safe_derived = _validate_derived_dir(derived_dir)
    safe_derived.chmod(0o700)
    target = safe_derived / "hitl_queue.sanitized.json"
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
    """Allow HITL reads/writes only in a real ``derived`` quarantine directory."""
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


def build_and_write_hitl_queue(derived_dir: Path) -> tuple[HitlQueueSummary, Path]:
    classification = load_classification(derived_dir)
    queue = build_hitl_queue(classification)
    path = write_hitl_queue(derived_dir, queue)
    summary = HitlQueueSummary(
        total_items=int(queue["summary"]["total_items"]),
        by_priority_band=dict(queue["summary"]["by_priority_band"]),
        by_type=dict(queue["summary"]["by_type"]),
        ocr_flagged=int(queue["summary"]["ocr_flagged"]),
        ambiguous=int(queue["summary"]["ambiguous"]),
        automatic_promotion_allowed=False,
        published_eligible=0,
    )
    return summary, path


__all__ = [
    "HitlQueueSummary",
    "build_and_write_hitl_queue",
    "build_hitl_queue",
    "load_classification",
    "write_hitl_queue",
]
