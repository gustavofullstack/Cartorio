"""AuditService - log append-only com hash chain e HMAC.

Garantias:
1. Append-only: cada entrada referencia o hash da anterior (blockchain-style)
2. Tamper-evident: edicao retroativa invalida a cadeia inteira a partir do ponto
3. HMAC-signed: alem do hash chain, cada entrada tem assinatura HMAC da chave
   do servidor - quem edita o banco sem a chave nao consegue forjar
4. Replay-resistant: timestamp + request_id em cada entrada

Para verificar integridade: percorre do mais antigo pro mais novo,
recalculando hash(prev_hash, payload, timestamp) e comparando.

LGPD art. 37 (continuidade da auditoria): alem da integridade, o audit_log
precisa estar VIVO (recebendo mutacoes regularmente). Se parar de receber
entries por mais de `AUDIT_DEAD_MANS_SWITCH_MINUTES` (default 60min), isso
indica perda de rastreabilidade juridica — alerta automatico via:

- `app.jobs.cron_dead_mans_switch.run_dead_mans_switch_check_3lvl()` (3-level:
  healthy/warning/critical, executado pelo scheduler in-process a cada
  `AUDIT_DEAD_MANS_SWITCH_INTERVAL_MINUTES` = 15min no lifespan da app).
- Endpoint admin: GET /api/v1/admin/audit/health (X-API-Key, 3-level read-only)
- Endpoint admin: POST /api/v1/admin/audit/check-now (X-API-Key, forca check +
  envia Telegram GRUPO PIETRA SQUAD se stale).
- Metrica Prometheus: `audit_dead_mans_status` (0=healthy, 1=warning,
  2=critical). Exposta via /api/v1/metrics/prometheus.
- Alert Telegram GRUPO PIETRA SQUAD via `AUDIT_ALERT_TELEGRAM_CHAT_ID` (env).

Shape 3-level (briefing A13):
- healthy: idade <= threshold (default 60min)
- warning: idade entre 1x e 2x threshold
- critical: idade > 2x threshold OU tabela vazia (cold start, fail-safe)

Shape 4-level legacy (mantido para compat com `/health/audit-freshness` e
`/admin/audit/dead-mans-switch/check` da implementacao anterior):
- healthy / stale / critical / empty
"""

from __future__ import annotations

import hashlib
import hmac
import json
from datetime import datetime, UTC
from typing import Any

from sqlalchemy.orm import Session

from app.config import settings
from app.models.audit_log import AuditLog


class AuditIntegrityError(Exception):
    """Lancada quando a cadeia de audit log esta corrompida."""


class AuditService:
    @staticmethod
    def _canonical_block(prev_hash: str | None, payload: dict, timestamp: str) -> str:
        block = {
            "prev_hash": prev_hash or ("0" * 64),
            "timestamp": timestamp,
            "payload": payload,
        }
        return json.dumps(block, sort_keys=True, separators=(",", ":"), default=str)

    @classmethod
    def _compute_hash(cls, prev_hash: str | None, payload: dict, timestamp: str) -> str:
        canonical = cls._canonical_block(prev_hash, payload, timestamp)
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    @staticmethod
    def _compute_hmac(message: str) -> str:
        key = settings.audit_hmac_key.encode("utf-8")
        return hmac.new(key, message.encode("utf-8"), hashlib.sha256).hexdigest()

    @classmethod
    def log(
        cls,
        db: Session,
        *,
        actor_id: str,
        action: str,
        resource: str,
        payload: dict[str, Any],
        actor_type: str = "user",
        ip: str | None = None,
        user_agent: str | None = None,
        request_id: str | None = None,
        canal: str | None = None,
    ) -> AuditLog:
        """Insere entrada append-only na cadeia.

        LGPD-by-design (D5, cartorio-lgpd review 2026-06-24):
        - `ip` recebe IP COMPLETO (acesso restrito DPO via /audit/replay).
        - `ip_truncated` eh gerado AUTOMATICAMENTE via utils.ip.truncate_ip()
          (IPv4 → /24, IPv6 → /32). Default output em queries/metricas.
        Caller NAO precisa passar `ip_truncated` — eh derivado de `ip`.
        """
        from app.utils.ip import truncate_ip

        last = db.query(AuditLog).order_by(AuditLog.id.desc()).first()
        prev_hash = last.hash if last else None

        now = datetime.now(UTC)
        timestamp = now.replace(tzinfo=None).isoformat(timespec="microseconds")
        new_hash = cls._compute_hash(prev_hash, payload, timestamp)
        hmac_sig = cls._compute_hmac(f"{new_hash}:{timestamp}:{actor_id}:{action}")

        entry = AuditLog(
            actor_id=actor_id,
            actor_type=actor_type,
            action=action,
            resource=resource,
            payload=payload,
            ip=ip,
            ip_truncated=truncate_ip(ip),  # LGPD D5 — output /24 ou /32
            user_agent=user_agent,
            request_id=request_id,
            canal=canal,
            prev_hash=prev_hash,
            hash=new_hash,
            hmac_signature=hmac_sig,
            timestamp=now,
        )
        db.add(entry)
        db.commit()
        db.refresh(entry)
        return entry

    @classmethod
    def log_system_action(cls, action: str, payload: dict[str, Any]) -> AuditLog:
        """Helper para eventos do sistema (startup/shutdown/health)."""
        from app.db import session_scope

        with session_scope() as db:
            return cls.log(
                db,
                actor_id="system",
                actor_type="system",
                action=action,
                resource="system",
                payload=payload,
            )

    @classmethod
    def verify_chain(cls, db: Session) -> tuple[bool, int]:
        """Verifica integridade da cadeia inteira.
        Retorna (ok, ultima_posicao_valida).
        """
        entries = db.query(AuditLog).order_by(AuditLog.id.asc()).all()
        prev_hash: str | None = None
        for i, entry in enumerate(entries):
            timestamp_iso = entry.timestamp.isoformat(timespec="microseconds")
            expected = cls._compute_hash(prev_hash, entry.payload, timestamp_iso)
            if entry.prev_hash != prev_hash or entry.hash != expected:
                return False, i
            prev_hash = entry.hash
        return True, len(entries)
