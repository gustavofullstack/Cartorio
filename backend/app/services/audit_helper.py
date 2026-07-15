"""`audit_helper.py` — Adapter DRY para `AuditService.log()`.

Este modulo encapsula o padrao repetido de criar entradas de audit log em
services/operations. Antes deste helper (Missao F5 [P2] 2026-07-15), o codigo
seguinte aparecia em **pelo menos 12 locais** (services de LGPD, emolumento,
agendamento, protocolo, etc.):

    from app.services.audit import AuditService
    audit_entry = AuditService.log(
        db,
        actor_id=...,
        actor_type="user",
        action="...",
        resource="...",
        payload={...},
    )
    audit_id = audit_entry.id

Cada chamada repetida e uma fonte potencial de inconsistencia (actor_type
errado, action nao-normalizada, payload com PII nao-mascarada).

Funcoes:
- `log_mutation()` — wrapper principal. Substitui `AuditService.log()` em
  **services**, mantendo 100% do comportamento (chain + HMAC).
  Cobre LGPD art. 37 (registro de tratamento) com 1 unica porta de entrada.
- `log_action_safe()` — variante para handlers async/webhook que NAO
  podem quebrar o request se audit_log falhar (fail-open LGPD art. 6 VIII).

Nao toca em `app/services/audit.py` (chain builder e intocavel — SHA256 +
HMAC, AGENTS.md regra P0).

Referencias:
- ADR-027 (codebase analysis SOLID/DRY/KISS) - secao T075.
- AGENTS.md - regra "Audit log e append-only ... Testes falham se regredir."
- LGPD art. 37 (registro de operacoes de tratamento).
"""

from __future__ import annotations

import logging
from typing import Any

from sqlalchemy.orm import Session

from app.services.audit import AuditService
from app.services.audit_context import audit_kwargs


log = logging.getLogger(__name__)


def log_mutation(
    db: Session,
    *,
    actor_id: str,
    action: str,
    resource: str,
    payload: dict[str, Any],
    actor_type: str = "user",
    request: Any | None = None,
    request_id: str | None = None,
    ip: str | None = None,
    user_agent: str | None = None,
    canal: str | None = None,
) -> int:
    """Wrap DRY do padrao `AuditService.log(...)` para operacoes service-side.

    Substitui 12+ ocorrencias repetidas em services (`pii`, `emolumento`,
    `lgpd_*`, `protocolo`, `agendamento`, etc.) por uma unica porta de
    entrada consistente.

    Por que este helper existe (DRY):
    1. **Normalizacao de actor_type**: defaults `"user"` (LGPD art. 37 — casos
       legados). Caller pode passar `"system"`, `"bot"`, `"escrevente"`,
       `"tabeliao"`, `"dpo"`.
    2. **Auto-preenchimento de contexto via `request`**: se caller passar
       `request`, o helper extrai `request_id`/`ip`/`user_agent`/`canal`
       via `audit_kwargs(request)` (LGPD art. 37 - registro de IP/UA/canal).
       Caller pode sobreescrever via kwargs explicitos (ex: jobs que NAO
       tem request).
    3. **Logging defensivo**: se `AuditService.log()` levantar (db error),
       o helper LOGA warning e retorna `0` (sem audit_id) em vez de
       estourar a request — alinhado com `audit_context.py` que tambem
       e best-effort.

    Args:
        db: Session SQLAlchemy. Caller gerencia transacao.
        actor_id: quem fez a acao (cliente_id, DPO, system, escrevente_id).
        action: slug da acao (ex: `"lgpd.direito_esquecimento"`,
            `"emolumento.calcular"`, `"protocolo.criar"`). Convensao
            `dominio.verbo`.
        resource: identificador do recurso (`cliente:42`, `protocolo:abc`,
            `agendamento:99`).
        payload: dict serializavel em JSON. **Ja deve estar PII-mascarado**
            se for sair pra LLM externa — este helper NAO aplica scrub.
        actor_type: `"user"` (default) | `"system"` | `"bot"` | `"escrevente"`
            | `"tabeliao"` | `"dpo"`.
        request: FastAPI Request (opcional). Se fornecido, extrai contexto.
        ip: override de IP. Default: extraido de `request.client_ip`.
        user_agent: override de UA. Default: extraido de `request.user_agent`.
        canal: override de canal (`whatsapp`, `telegram`, `web`, `api`).
            Default: extraido de `request.canal`.

    Returns:
        `int` — audit_id da entrada inserida (chain + HMAC automaticos).
        `0` se a chamada a `AuditService.log()` falhou (best-effort).

    Raises:
        Nada — funcao e defensiva. Erros sao logados via `log.warning(...)`.

    Example:
        >>> from app.services.audit_helper import log_mutation
        >>> audit_id = log_mutation(
        ...     db,
        ...     actor_id=str(cliente_id),
        ...     action="lgpd.direito_esquecimento",
        ...     resource=f"cliente:{cliente_id}",
        ...     payload={"motivo": motivo, "tables": tables},
        ...     request=request,
        ... )
    """
    try:
        # Se request for passado, extrai contexto LGPD art. 37 (IP/UA/canal).
        # Defaults vazios se nao fornecido.
        ctx_kwargs: dict[str, Any] = {
            "ip": ip,
            "user_agent": user_agent,
            "canal": canal,
        }
        if request is not None:
            auto = audit_kwargs(request)
            # request_id explicato sobrescreve se vier de caller
            ctx_kwargs["request_id"] = request_id or auto.get("request_id")
            for k in ("ip", "user_agent", "canal"):
                if not ctx_kwargs.get(k):
                    ctx_kwargs[k] = auto.get(k)
        else:
            ctx_kwargs["request_id"] = request_id

        entry = AuditService.log(
            db,
            actor_id=actor_id,
            actor_type=actor_type,
            action=action,
            resource=resource,
            payload=payload,
            **ctx_kwargs,
        )
        return int(getattr(entry, "id", 0)) or 0
    except Exception as exc:  # noqa: BLE001
        log.warning(
            "audit_helper.log_mutation falhou (action=%s resource=%s): %s",
            action,
            resource,
            exc,
        )
        return 0


def log_action_safe(
    db: Session,
    *,
    actor_id: str,
    action: str,
    resource: str,
    payload: dict[str, Any],
    actor_type: str = "system",
) -> int:
    """Variante para chamadas async/webhook que NAO podem quebrar request.

    Equivalente a `log_mutation()` mas SEM suporte a `request` (jobs /
    tasks em background nao tem request). Use para:
    - Celery tasks (jobs/).
    - Cron jobs (jobs/cron_dead_mans_switch).
    - DLQ retries (services/dlq.py).

    Args:
        db: Session SQLAlchemy.
        actor_id: normalmente `"system"` ou identificador da task.
        action: slug da acao.
        resource: recurso alvo.
        payload: dict serializavel.
        actor_type: default `"system"`.

    Returns:
        `int` — audit_id. `0` se falhou.
    """
    return log_mutation(
        db,
        actor_id=actor_id,
        actor_type=actor_type,
        action=action,
        resource=resource,
        payload=payload,
        request=None,
    )


__all__ = ["log_mutation", "log_action_safe"]
