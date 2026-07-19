"""G8.12.T1 — PII masking unificado (DRY consolidation).

Ponto de entrada canonico para mascaramento de dados pessoais no backend
do 2º Servico Notarial de Uberlandia. Para LGPD art. 46 (medidas tecnicas
adequadas contra acesso nao autorizado) este modulo NAO introduz novos
regex — apenas agrega os ja existentes sob uma API kind-aware.

Origem da verdade (single-source-of-truth):
- Regex de DETECCAO (13 padroes: cpf/cnpj/rg/cns/cnh/email/phone/etc):
  ``app.services.pii._PATTERNS`` (P0.5 docstring com ordem critica).
- Hashing deterministico com salt: ``app.services.pii.hash_pii``.
- Validacao de DV (CNS/CNH): ``app.services.pii.validate_cns/cnh``.
- Scrub recursivo HTTP/JSON: ``app.utils.output_safety.scrub_response``.
- Scrub recursivo MCP outputs: ``app.services.mcp_pii.scrub_mcp_output``.
- Log masking fail-safe: ``app.services.log_masker.MaskingFilter``.
- Traefik log + token scrub: ``app.services.traefik_log_masker``.
- Format-preserving constant (UI/export LGPD): ``app.services.crypto.mask_*``.
- Partial-reveal (log display): ``app.utils.pii_sanitizer.sanitize_*``.

Decisao G8.12.T1 (cartorio-dev 2026-07-18):
- NAO reescrever ``app.services.pii`` (risco P0.5 — ordem dos regex).
- Criar este wrapper como ponto de entrada recem-criado.
- Para NOVO codigo, prefira ``from app.services.pii_unified import mask``.
- O modulo NAO quebra nenhum import pre-existente: re-exporta tudo.

LGPD Art. 46 / Art. 6 VIII (prevencao + minimizacao):
- Zero CPF/RG/protocolo/escritura em raw pode sair do backend.
- Re-exporta scrubbing + deteccao + hashing ja revisados pela auditoria
  cartorio-lgpd (LGPD-AUDIT-2026-06-23 / 24 / 25).
"""

from __future__ import annotations

import warnings
from typing import Final, Literal

from app.services.mcp_pii import mcp_output_has_raw_cpf, scrub_mcp_output
from app.services.pii import (
    ScrubResult,
    _PATTERNS,  # noqa: F401  (canonical regex map; underscore prefix by convention)
    detect_only,
    hash_pii,
    scrub,
    validate_cnh,
    validate_cns,
)
from app.utils.output_safety import scrub_response, scrub_response_safe

# Re-exporta o pattern CPF canonico como simbolo PUBLICO para que callers
# (e.g. ``app.services.mcp_pii.mcp_output_has_raw_cpf``) NAO dupliquem o
# regex. Origem: ``app.services.pii._PATTERNS["cpf"]`` (P0.5 ordem critica).
_CPF_PATTERN = _PATTERNS["cpf"]

PiiKind = Literal[
    "cpf",
    "cnpj",
    "rg",
    "email",
    "phone",
    "protocolo",
    "escritura",
    "auto",
]

_DEFAULT_PARTIAL_KINDS: Final[frozenset[str]] = frozenset({"cpf", "cnpj"})


def _partial_mask_for(kind: PiiKind, value: str) -> str:
    """Delega para ``app.utils.pii_sanitizer`` conforme kind.

    Mantem compatibilidade exata com testes pre-existentes
    (``tests/test_pii_sanitizer.py``). Cada kind tem um "keep N" proprio:
        - cpf:    keep=6 (ultimos "789-00")
        - cnpj:   keep=8 (ultimos "/0001-90")
        - rg:     keep=3 (ultimos 3 digitos)
        - email:  keep=domain only ("***@example.com")
        - phone:  keep=4 (ultimos 4 digitos)
        - protocolo/escritura/auto: cai em CPF como aproximacao LGPD-by-design.
    """
    from app.utils import pii_sanitizer

    text = value
    if kind == "cpf":
        return pii_sanitizer.sanitize_cpf(text)
    if kind == "cnpj":
        return pii_sanitizer.sanitize_cnpj(text)
    if kind == "rg":
        return pii_sanitizer.sanitize_rg(text)
    if kind == "email":
        return pii_sanitizer.sanitize_email(text)
    if kind == "phone":
        return pii_sanitizer.sanitize_phone(text)
    return pii_sanitizer.sanitize_pii(text)


def mask(
    kind: PiiKind,
    value: str | None,
    *,
    partial: bool = False,
) -> str:
    """Single entry-point kind-aware PII masking.

    Args:
        kind: Tipo de PII. Use ``"auto"`` para deixar o detector decidir
              (delegando para ``app.services.pii.scrub``).
        value: Valor raw a mascarar. ``None`` ou string vazia -> ``""``
               (sem excecao).
        partial: Se ``False`` (default), retorna mascara LGPD full
                 (``"[KIND_REDACTED]"`` ou equivalente, via ``scrub``).
                 Se ``True``, retorna mascara de exibicao com
                 ``***789-00``-style (ultimos N chars) via
                 ``app.utils.pii_sanitizer`` (LGPD display-safe para
                 logs internos). NUNCA use ``partial=True`` em
                 respostas HTTP publicas ou pra LLM externa.

    Returns:
        String mascarada. Sempre string (nunca ``None``). Para ``"auto"``
        sem deteccao, devolve o input original (idempotente).

    Examples:
        >>> mask("cpf", "123.456.789-00")
        '[CPF_REDACTED]'
        >>> mask("cpf", "123.456.789-00", partial=True)
        '***789-00'
        >>> mask("email", "gustavo@gmail.com", partial=True)
        '***@gmail.com'
        >>> mask("cpf", None)
        ''
        >>> mask("auto", "texto sem PII aqui")
        'texto sem PII aqui'

    LGPD Art. 46 / 6 VIII: este helper NAO eh bala de prata. Complementa
    o pipeline 3-camadas (Pydantic validators -> Sentry before_send ->
    log MaskingFilter). Continue usando ``scrub`` no caminho de saida
    HTTP para defesa em profundidade.
    """
    if value is None or not isinstance(value, str) or not value.strip():
        return ""
    normalized = value.strip()
    if not partial:
        if kind == "auto":
            result = scrub(normalized)
            return result.text
        result = scrub(normalized)
        return result.text
    return _partial_mask_for(kind, normalized)


def mask_safe(value: str | None) -> str:
    """Atalho para ``mask("auto", value, partial=False)`` — full LGPD scrub.

    Para codigo que nao sabe o ``kind`` especifico da PII (mensagens
    livres, payloads de webhook, etc). Equivalente a chamar
    ``app.services.pii.scrub(text).text``.
    """
    return mask("auto", value, partial=False)


def mask_email_display(email: str | None) -> str:
    """Mascara email para exibicao publica (delegacao a ``crypto.mask_email_display``).

    Mantida por compat semantica com ``mask_email_display`` original;
    ``app.services.crypto.mask_email_display`` continua sendo a fonte
    canonica desta funcao (LGPD export + privacy policy).
    """
    from app.services.crypto import mask_email_display as _impl

    return _impl(email)


def mask_nome(nome: str | None) -> str:
    """Mascara nome para exibicao publica (delegacao a ``crypto.mask_nome``)."""
    from app.services.crypto import mask_nome as _impl

    return _impl(nome)


def has_raw_pii(value: str) -> bool:
    """True se algum padrao de PII for detectado (delegacao a ``detect_only``).

    Equivalente idiomático a ``bool(detect_only(text))`` — usado em
    gates de pre-LLM (LGPD art. 6 VIII — prevencao).
    """
    return bool(detect_only(value))


def deprecation_notice(legacy_module: str) -> None:
    """Emite ``DeprecationWarning`` apontando para este modulo unificado.

    Use SOMENTE em paths transicao (callers legacy) para sinalizar
    migracao futura. NAO capturar com ``warnings.filterwarnings("ignore")``
    — isso mascara o sinal de debt tecnico (LGPD by design: debt visivel
    == risco visivel).
    """
    warnings.warn(
        f"Use 'app.services.pii_unified' instead of '{legacy_module}'. "
        "Reason: G8.12.T1 DRY consolidation (LGPD review 2026-07-18).",
        DeprecationWarning,
        stacklevel=3,
    )


__all__ = [
    "PiiKind",
    "ScrubResult",
    "_CPF_PATTERN",
    "deprecation_notice",
    "detect_only",
    "has_raw_pii",
    "hash_pii",
    "mask",
    "mask_email_display",
    "mask_nome",
    "mask_safe",
    "mcp_output_has_raw_cpf",
    "scrub",
    "scrub_mcp_output",
    "scrub_response",
    "scrub_response_safe",
    "validate_cnh",
    "validate_cns",
]
