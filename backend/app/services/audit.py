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
import json
from datetime import datetime, UTC
from typing import Any

from sqlalchemy.orm import Session

from app.models.audit_log import AuditLog
from app.services.audit_keys import sign_audit_entry as _sign_via_registry


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

    # ------------------------------------------------------------------
    # Canonicalizador "SQL trigger" (fn_auto_audit, migracao 0020)
    # ------------------------------------------------------------------
    #
    # O trigger PL/pgSQL `fn_auto_audit()` (6 tabelas PII) escreve em
    # audit_log DIRETO no banco, canonicalizando assim (migracao 0020):
    #
    #   v_canonical := '{"payload":' || v_payload::text
    #       || ',"prev_hash":"' || v_prev_hash
    #       || '","timestamp":"' || v_ts || '"}';
    #
    # `v_payload::text` (jsonb::text) difere do json.dumps Python:
    #   - chaves ordenadas por (length, bytewise) — ordem interna do JSONB,
    #     NAO alfabetica;
    #   - separadores com espaco (", " entre pares, ": " apos chave);
    #   - UTF-8 raw (sem escape \uXXXX);
    #   - numericos normalizados pelo JSONB.
    #
    # Sem este mirror, verify_chain quebra na 1a entrada escrita pelo
    # trigger (prod: posicao 668, id 670, 2026-07-09 — 158 entradas
    # sistematicas, prova de divergencia de formato, NAO de tampering:
    # prev_hash linkage e 100% continuo nas 1130 entradas).
    #
    # REVIEW cartorio-lgpd obrigatorio (superficie audit).
    # ------------------------------------------------------------------

    @classmethod
    def _jsonb_text(cls, value: Any) -> str:
        """Mimetiza Postgres `jsonb::text` (ordem (len,bytewise), separadores com espaco)."""
        if isinstance(value, dict):
            keys = sorted(value.keys(), key=lambda k: (len(str(k)), str(k).encode()))
            parts = [
                f"{json.dumps(str(k), ensure_ascii=False)}: {cls._jsonb_text(value[k])}"
                for k in keys
            ]
            return "{" + ", ".join(parts) + "}"
        if isinstance(value, (list, tuple)):
            return "[" + ", ".join(cls._jsonb_text(v) for v in value) + "]"
        if value is True:
            return "true"
        if value is False:
            return "false"
        if value is None:
            return "null"
        return json.dumps(value, ensure_ascii=False, default=str)

    @classmethod
    def _canonical_block_sql_trigger(
        cls, prev_hash: str | None, payload: dict, timestamp: str
    ) -> str:
        """Canonical block no formato do trigger fn_auto_audit (migracao 0020)."""
        return (
            '{"payload":'
            + cls._jsonb_text(payload)
            + ',"prev_hash":"'
            + (prev_hash or ("0" * 64))
            + '","timestamp":"'
            + timestamp
            + '"}'
        )

    @classmethod
    def _compute_hash_sql_trigger(cls, prev_hash: str | None, payload: dict, timestamp: str) -> str:
        canonical = cls._canonical_block_sql_trigger(prev_hash, payload, timestamp)
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    @staticmethod
    def _is_trigger_written(entry: "AuditLog") -> bool:
        """Entradas escritas pelo trigger fn_auto_audit (nao pelo AuditService.log).

        Marcadores estaveis (migracao 0020): user_agent default
        'auto_audit_trigger' e actor_id 'auto_audit' (quando o request
        nao seta GUCs app.current_actor_id / app.user_agent).
        """
        return (entry.user_agent or "") == "auto_audit_trigger" or (
            entry.actor_id or ""
        ) == "auto_audit"

    @classmethod
    def _compute_hash(cls, prev_hash: str | None, payload: dict, timestamp: str) -> str:
        canonical = cls._canonical_block(prev_hash, payload, timestamp)
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    @staticmethod
    def _compute_hmac(message: str) -> tuple[str, str]:
        """Assina message via registry de chaves HMAC (G8.19.T2).

        Returns:
            Tupla ``(kid, hmac_sig)``. ``kid`` identifica qual chave
            do registry foi usada; ``hmac_sig`` eh o hex digest SHA256.

        Backward-compat:
            Continua funcionando sem mudanca de comportamento (kid=""
            eh registrado via bootstrap para a chave historica).
        """
        kid, sig = _sign_via_registry(message.encode("utf-8"))
        return kid, sig

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

        # ``audit_log.timestamp`` e uma coluna legada ``TIMESTAMP`` sem timezone.
        # Materializamos uma unica vez em UTC-naive para que o mesmo instante seja
        # canonicalizado, assinado e persistido, independente do timezone da sessao.
        timestamp = datetime.now(UTC).replace(tzinfo=None)
        timestamp_iso = timestamp.isoformat(timespec="microseconds")
        new_hash = cls._compute_hash(prev_hash, payload, timestamp_iso)
        hmac_kid, hmac_sig = cls._compute_hmac(f"{new_hash}:{timestamp_iso}:{actor_id}:{action}")

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
            hmac_kid=hmac_kid,
            timestamp=timestamp,
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

        Turno 24+ 2026-06-29: Normaliza timestamp removendo tzinfo (mesmo formato usado
        em `log()` que faz `.replace(tzinfo=None).isoformat(timespec='microseconds')`).
        Sem isso, entradas com timestamp tz-aware (do DB) sao formatadas com '+00:00'
        e o hash computado diverge do hash armazenado.

        Turno 25+ 2026-06-29: Converte timestamp de "YYYY-MM-DD HH:MM:SS.ffffff" (PostgreSQL
        format com espaco) para "YYYY-MM-DDTHH:MM:SS.ffffff" (ISO com T, usado pelo
        `isoformat()` Python que computou o hash original). Tambem normaliza prev_hash
        para "0"*64 quando None (chain head).
        """
        entries = db.query(AuditLog).order_by(AuditLog.id.asc()).all()
        prev_hash: str | None = None
        last_valid = 0
        for i, entry in enumerate(entries):
            # Normaliza timestamp removendo tzinfo e convertendo space -> T
            ts = entry.timestamp
            if ts.tzinfo is not None:
                ts = ts.replace(tzinfo=None)
            timestamp_iso = ts.isoformat(timespec="microseconds")
            # Converte "2026-06-22 22:12:18.297643" -> "2026-06-22T22:12:18.297643"
            timestamp_iso = timestamp_iso.replace(" ", "T")
            # Normaliza prev_hash: chain head usa None (que vira "0"*64 no compute)
            prev_for_hash = prev_hash if prev_hash else "0" * 64
            expected = cls._compute_hash(prev_for_hash, entry.payload, timestamp_iso)
            # Compara prev_hash considerando chain head: ambos sao None
            entry_prev = entry.prev_hash if entry.prev_hash else "0" * 64
            if entry_prev != prev_for_hash:
                # Link quebrado: NENHUM fallback e valido (possivel tampering).
                return False, last_valid
            if entry.hash != expected:
                # Fallback controlado: entrada escrita pelo trigger fn_auto_audit
                # (migracao 0020) canonicaliza via jsonb::text — formato distinto
                # do Python. So aceita se recomputar EXATAMENTE no formato SQL;
                # qualquer divergencia continua quebrando a cadeia (fail-closed).
                # REVIEW cartorio-lgpd.
                if cls._is_trigger_written(entry):
                    expected_sql = cls._compute_hash_sql_trigger(
                        prev_for_hash, entry.payload, timestamp_iso
                    )
                    if entry.hash == expected_sql:
                        prev_hash = entry.hash
                        last_valid = i + 1
                        continue
                # Chain quebrada — retorna posicao do ultimo valido
                return False, last_valid
            prev_hash = entry.hash
            last_valid = i + 1
        return True, len(entries)

    @classmethod
    def verify_hash_sequence(
        cls,
        entries: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """G8.07.T2 — valida sequência de hashes **offline** (sem DB).

        Cada item de `entries` deve ter:
          - payload: dict
          - timestamp: str ISO (com T, microseconds se possível)
          - hash: str hex SHA256
          - prev_hash: str | None (None ou zeros = head)

        Returns:
            dict com chain_ok, last_valid_position, total, broken_at (ou None),
            detail (mensagem curta sem PII).
        """
        prev_hash: str | None = None
        last_valid = 0
        for i, entry in enumerate(entries):
            payload = entry.get("payload") or {}
            if not isinstance(payload, dict):
                return {
                    "chain_ok": False,
                    "last_valid_position": last_valid,
                    "total": len(entries),
                    "broken_at": i,
                    "detail": "payload_not_dict",
                }
            ts = str(entry.get("timestamp") or "").replace(" ", "T")
            stored_hash = str(entry.get("hash") or "")
            entry_prev_raw = entry.get("prev_hash")
            entry_prev = entry_prev_raw if entry_prev_raw else "0" * 64
            prev_for_hash = prev_hash if prev_hash else "0" * 64
            expected = cls._compute_hash(prev_for_hash, payload, ts)
            if entry_prev != prev_for_hash or stored_hash != expected:
                return {
                    "chain_ok": False,
                    "last_valid_position": last_valid,
                    "total": len(entries),
                    "broken_at": i,
                    "detail": "hash_mismatch_or_prev_break",
                }
            prev_hash = stored_hash
            last_valid = i + 1
        return {
            "chain_ok": True,
            "last_valid_position": last_valid,
            "total": len(entries),
            "broken_at": None,
            "detail": "ok",
        }
