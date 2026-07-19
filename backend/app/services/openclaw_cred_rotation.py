"""G8.04.T3 — Validação segura de rotação de credenciais OpenClaw (local).

API local de *planejamento* de rotação — **nunca** aceita, loga ou persiste
tokens/raw secrets. Apenas fingerprints (prefixos sha256, opcionalmente
com prefixo `fp:`).

Contrato de segurança (LGPD / secret hygiene):
- Fingerprints curtos (sha256 hex prefix).
- Rejeita valor que pareça secret completo: ``len > 40`` e sem prefixo ``fp:``.
- Não loga o valor bruto; erros usam apenas classificação (safe/unsafe/empty).

API:
- ``assert_safe_fingerprint(value)`` — levanta ValueError se não for fingerprint.
- ``validate_rotation_plan(old_token_fp, new_token_fp)`` — plano ok/fail.
- ``rotation_checklist()`` — passos operacionais (backup → dual-write → …).

Modified by Gustavo Almeida — G8.04.T3 Wave 32.
"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from typing import Any

# Prefixos de fingerprint permitidos (não-secret).
FP_PREFIX = "fp:"

# Limite: hex prefix de sha256 costuma ser 8–64 chars. Acima de 40 sem `fp:`
# trata-se como possível secret completo e é rejeitado (spec G8.04.T3).
MAX_FP_BODY_LEN = 40
# Corpo mínimo (sha256[:8] é o padrão do repo em deps._key_fingerprint).
MIN_FP_BODY_LEN = 8
# Corpo máximo mesmo com `fp:` (sha256 completo = 64 hex).
MAX_FP_WITH_PREFIX_BODY = 64

# Hex (sha256 prefix) — case-insensitive.
_HEX_RE = re.compile(r"^[0-9a-fA-F]+$")

# Checklist canônico de rotação (ordem importa).
ROTATION_STEPS: tuple[str, ...] = (
    "backup",
    "dual-write window",
    "swap",
    "revoke old",
    "verify health",
)


class UnsafeCredentialError(ValueError):
    """Valor parece secret completo ou não é fingerprint seguro."""


@dataclass(frozen=True, slots=True)
class RotationPlanResult:
    """Resultado de validação do plano de rotação (sem secrets)."""

    ok: bool
    old_fp: str
    new_fp: str
    reasons: tuple[str, ...] = field(default_factory=tuple)
    checklist: tuple[str, ...] = field(default_factory=tuple)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _looks_like_full_secret(value: str) -> bool:
    """True se o valor parece secret completo (len>40 e sem prefixo fp:).

    Spec G8.04.T3: nunca aceitar/logar raw tokens longos; rejeitar se
    ``len > 40`` e não há prefixo ``fp:``.
    """
    if not value:
        return False
    stripped = value.strip()
    if stripped.lower().startswith(FP_PREFIX):
        return False
    return len(stripped) > MAX_FP_BODY_LEN


def _normalize_fingerprint(value: str) -> str:
    """Normaliza fingerprint para forma canônica ``fp:<hex_lower>``.

    Aceita:
    - ``fp:abc123…`` (com prefixo)
    - ``abc123…`` hex curto (sem prefixo, len ≤ 40)

    Raises:
        UnsafeCredentialError: empty, full-secret-like, non-hex, tamanho inválido.
    """
    if value is None:  # type: ignore[comparison-overlap]
        raise UnsafeCredentialError("fingerprint empty")
    if not isinstance(value, str):
        raise UnsafeCredentialError("fingerprint must be str")

    raw = value.strip()
    if not raw:
        raise UnsafeCredentialError("fingerprint empty")

    if _looks_like_full_secret(raw):
        # Não incluir o valor no exception message (evita leak em logs/traceback).
        raise UnsafeCredentialError(
            "rejected: value looks like full secret (len>40 without fp: prefix)"
        )

    if raw.lower().startswith(FP_PREFIX):
        body = raw[len(FP_PREFIX) :].strip()
        max_body = MAX_FP_WITH_PREFIX_BODY
    else:
        body = raw
        max_body = MAX_FP_BODY_LEN

    if not body:
        raise UnsafeCredentialError("fingerprint body empty")
    if len(body) < MIN_FP_BODY_LEN:
        raise UnsafeCredentialError(f"fingerprint too short (min {MIN_FP_BODY_LEN} hex chars)")
    if len(body) > max_body:
        raise UnsafeCredentialError(
            f"fingerprint too long (max {max_body} hex chars for this form)"
        )
    if not _HEX_RE.match(body):
        raise UnsafeCredentialError("fingerprint must be hex (sha256 prefix)")

    return f"{FP_PREFIX}{body.lower()}"


def assert_safe_fingerprint(value: str) -> str:
    """Valida e normaliza um fingerprint. Nunca loga o valor bruto.

    Returns:
        Forma canônica ``fp:<hex_lower>``.

    Raises:
        UnsafeCredentialError: se parece secret ou formato inválido.
    """
    return _normalize_fingerprint(value)


def is_safe_fingerprint(value: str) -> bool:
    """True se o valor é um fingerprint aceitável (não secret)."""
    try:
        _normalize_fingerprint(value)
        return True
    except UnsafeCredentialError:
        return False


def validate_rotation_plan(
    old_token_fp: str,
    new_token_fp: str,
) -> RotationPlanResult:
    """Valida plano de rotação usando **apenas** fingerprints (não tokens).

    Regras:
    - Ambos devem ser fingerprints seguros (sha256 prefix / ``fp:…``).
    - Rejeita se qualquer um parecer secret completo.
    - old e new devem ser distintos.
    - Em sucesso, anexa ``rotation_checklist()`` ao resultado.

    Args:
        old_token_fp: fingerprint do token atual (não o token).
        new_token_fp: fingerprint do token novo (não o token).

    Returns:
        RotationPlanResult com ok, fps normalizados e reasons.
        Nunca inclui raw secrets.
    """
    reasons: list[str] = []
    old_norm: str | None = None
    new_norm: str | None = None

    try:
        old_norm = _normalize_fingerprint(old_token_fp)
    except UnsafeCredentialError as exc:
        reasons.append(f"old_token_fp: {exc}")

    try:
        new_norm = _normalize_fingerprint(new_token_fp)
    except UnsafeCredentialError as exc:
        reasons.append(f"new_token_fp: {exc}")

    if old_norm is not None and new_norm is not None and old_norm == new_norm:
        reasons.append("old and new fingerprints must differ")

    ok = not reasons
    return RotationPlanResult(
        ok=ok,
        old_fp=old_norm or "",
        new_fp=new_norm or "",
        reasons=tuple(reasons),
        checklist=tuple(ROTATION_STEPS) if ok else (),
    )


def rotation_checklist() -> list[str]:
    """Passos operacionais de rotação (local, sem secrets).

    Ordem canônica:
    1. backup — snapshot de config/env (sem commitar secrets)
    2. dual-write window — aceitar old+new durante transição
    3. swap — promover new como primary
    4. revoke old — invalidar old após dual-write
    5. verify health — probe OpenClaw /health + smoke
    """
    return list(ROTATION_STEPS)


__all__ = [
    "FP_PREFIX",
    "MAX_FP_BODY_LEN",
    "MIN_FP_BODY_LEN",
    "ROTATION_STEPS",
    "UnsafeCredentialError",
    "RotationPlanResult",
    "assert_safe_fingerprint",
    "is_safe_fingerprint",
    "validate_rotation_plan",
    "rotation_checklist",
]
