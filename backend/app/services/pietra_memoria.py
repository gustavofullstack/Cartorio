"""Servico de memoria persistente para AGENT PIETRA.

P0 (Gustavo 2026-07-27): "O CANAL TEM QUE TER TOTAL ACESSO A MEMORIA!!
TUDO VIA REDIS E POSTGRESS TEM QUE SALVAR TUDO BEM OTIMIZADO COM O
PRIMARY KEY TELEFONE DO CLIENTE!!"

Arquitetura de memoria em 2 camadas:
  L1: Redis SETEX (TTL 30min) - session state rapido
      Chave: pietra:session:{telefone_hash}:{session_id}
  L2: Postgres memoria_conversa (retencao maxima de 365 dias)
      PRIMARY KEY operacional: (telefone_hash, session_id, created_at)

Fallback automatico: se Redis cair, cai para Postgres session_state
(sem TTL, com cleanup periodico). Se ambos falharem, retorna [] mas
NAO quebra o atendimento (graceful degradation).

Modified by Gustavo Almeida · 20227-07-27
"""

from __future__ import annotations

import datetime as dt
import json
import logging
import os
from typing import Any, Optional

import redis
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.models.base import utc_now_naive

logger = logging.getLogger(__name__)

REDIS_URL = os.environ.get("REDIS_URL", "redis://cartorio_memory-cache:6379/0")
REDIS_TTL_SECONDS = 1800  # 30 min


_redis_client: Optional[redis.Redis] = None


def get_redis() -> Optional[redis.Redis]:
    """Singleton do cliente Redis (lazy init + auto-reconnect)."""
    global _redis_client
    redis_url = os.environ.get("REDIS_URL", "redis://cartorio_memory-cache:6379/0")
    if _redis_client is not None:
        try:
            _redis_client.ping()
            return _redis_client
        except Exception:
            _redis_client = None

    try:
        _redis_client = redis.Redis.from_url(
            redis_url,
            socket_connect_timeout=2,
            socket_timeout=2,
            decode_responses=True,
        )
        _redis_client.ping()
        logger.info("redis connected")
    except Exception as e:
        logger.warning("redis connect failed: %s", e)
        _redis_client = None

    return _redis_client


def _redis_key(telefone_hash: str, session_id: str) -> str:
    return f"pietra:session:{telefone_hash}:{session_id}"


def salvar_mensagem(
    db: Session,
    *,
    telefone_hash: str,
    session_id: str,
    role: str,
    content: str,
    metadata: dict[str, Any] | None = None,
    canal: str = "imessage",
) -> bool:
    """Persiste 1 mensagem em Redis (TTL) + Postgres (permanente).

    Returns True se gravou pelo menos em uma das camadas.
    """
    if role not in ("user", "assistant", "system", "tool"):
        raise ValueError(f"role invalida: {role!r}")

    now = utc_now_naive()
    metadata_json = json.dumps(metadata or {}, ensure_ascii=False, default=str)

    # 1. Postgres (persistente)
    postgres_ok = False
    try:
        db.execute(
            text("""
                INSERT INTO memoria_conversa
                    (telefone_hash, session_id, canal, role, content, metadata_json, created_at, updated_at)
                VALUES
                    (:telefone_hash, :session_id, :canal, :role, :content, CAST(:metadata AS jsonb), :now, :now)
            """),
            {
                "telefone_hash": telefone_hash,
                "session_id": session_id,
                "canal": canal,
                "role": role,
                "content": content,
                "metadata": metadata_json,
                "now": now,
            },
        )
        postgres_ok = True
    except Exception as e:
        logger.error("postgres memoria insert failed: %s", e)
        db.rollback()

    # 2. Redis (rapido, TTL)
    r = get_redis()
    redis_ok = False
    if r is not None:
        try:
            key = _redis_key(telefone_hash, session_id)
            # Append em uma lista Redis (max 50 mensagens por sessao)
            entry = json.dumps(
                {
                    "role": role,
                    "content": content,
                    "metadata": metadata or {},
                    "created_at": now.isoformat(),
                },
                ensure_ascii=False,
                default=str,
            )
            r.lpush(key, entry)
            r.ltrim(key, 0, 49)  # manter ultimas 50
            r.expire(key, REDIS_TTL_SECONDS)
            redis_ok = True
        except Exception as e:
            logger.warning("redis memoria append failed: %s", e)

    return postgres_ok or redis_ok


def recuperar_historico(
    db: Session,
    *,
    telefone_hash: str,
    session_id: str | None = None,
    limit: int = 50,
    canal: str = "imessage",
) -> list[dict[str, Any]]:
    """Recupera historico de mensagens.

    Prioridade:
    1. Redis (rapido, mas TTL 30min)
    2. Postgres (permanente, sempre disponivel)

    Args:
        telefone_hash: PRIMARY KEY do cliente
        session_id: se None, retorna todas as sessoes
        limit: max mensagens
    """
    # Tentar Redis primeiro
    r = get_redis()
    if r is not None and session_id:
        try:
            key = _redis_key(telefone_hash, session_id)
            entries = r.lrange(key, 0, limit - 1)
            if entries:
                return [json.loads(e) for e in entries]
        except Exception as e:
            logger.warning("redis lrange failed: %s", e)

    # Fallback Postgres
    try:
        if session_id:
            stmt = text("""
                SELECT role, content, metadata_json, created_at
                FROM memoria_conversa
                WHERE telefone_hash = :tel AND session_id = :sid
                ORDER BY created_at DESC
                LIMIT :limit
            """)
            params = {"tel": telefone_hash, "sid": session_id, "limit": limit}
        else:
            stmt = text("""
                SELECT role, content, metadata_json, created_at
                FROM memoria_conversa
                WHERE telefone_hash = :tel AND canal = :canal
                ORDER BY created_at DESC
                LIMIT :limit
            """)
            params = {"tel": telefone_hash, "canal": canal, "limit": limit}
        rows = db.execute(stmt, params).fetchall()
        # Inverter (mais antiga primeiro)
        return [
            {
                "role": r[0],
                "content": r[1],
                "metadata": r[2] if isinstance(r[2], dict) else json.loads(r[2] or "{}"),
                "created_at": r[3].isoformat() if r[3] else None,
            }
            for r in reversed(rows)
        ]
    except Exception as e:
        logger.error("postgres memoria query failed: %s", e)
        return []


def salvar_session_state(
    db: Session,
    *,
    telefone_hash: str,
    session_id: str,
    state: dict[str, Any],
    last_intent: str | None = None,
    active_topic: str | None = None,
) -> bool:
    """Salva session state em Redis (rapido) + Postgres (backup)."""
    now = utc_now_naive()
    expires_at = now + dt.timedelta(seconds=REDIS_TTL_SECONDS)
    state_json = json.dumps(state, ensure_ascii=False, default=str)

    # 1. Redis SETEX
    r = get_redis()
    redis_ok = False
    if r is not None:
        try:
            r.setex(
                _redis_key(telefone_hash, session_id) + ":state",
                REDIS_TTL_SECONDS,
                state_json,
            )
            redis_ok = True
        except Exception as e:
            logger.warning("redis setex state failed: %s", e)

    # 2. Postgres (fallback)
    postgres_ok = False
    try:
        db.execute(
            text("""
                INSERT INTO session_state
                    (telefone_hash, session_id, state_json, last_intent, active_topic, last_updated, expires_at)
                VALUES
                    (:tel, :sid, CAST(:state AS jsonb), :li, :at, :now, :exp)
                ON CONFLICT (telefone_hash, session_id) DO UPDATE
                SET state_json = CAST(:state AS jsonb),
                    last_intent = :li,
                    active_topic = :at,
                    last_updated = :now,
                    expires_at = :exp
            """),
            {
                "tel": telefone_hash,
                "sid": session_id,
                "state": state_json,
                "li": last_intent,
                "at": active_topic,
                "now": now,
                "exp": expires_at,
            },
        )
        postgres_ok = True
        db.commit()
    except Exception as e:
        logger.error("postgres session_state upsert failed: %s", e)
        db.rollback()

    return redis_ok or postgres_ok


def recuperar_session_state(
    db: Session,
    *,
    telefone_hash: str,
    session_id: str,
) -> dict[str, Any]:
    """Recupera session state (Redis > Postgres)."""
    r = get_redis()
    if r is not None:
        try:
            raw = r.get(_redis_key(telefone_hash, session_id) + ":state")
            if raw:
                return json.loads(raw)
        except Exception as e:
            logger.warning("redis get state failed: %s", e)

    try:
        row = db.execute(
            text("""
                SELECT state_json, last_intent, active_topic, expires_at
                FROM session_state
                WHERE telefone_hash = :tel AND session_id = :sid
                  AND expires_at > NOW()
            """),
            {"tel": telefone_hash, "sid": session_id},
        ).fetchone()
        if row:
            state = row[0] if isinstance(row[0], dict) else json.loads(row[0] or "{}")
            if row[1]:
                state["last_intent"] = row[1]
            if row[2]:
                state["active_topic"] = row[2]
            return state
    except Exception as e:
        logger.error("postgres session_state query failed: %s", e)

    return {}


def stats_memoria(db: Session, telefone_hash: str) -> dict[str, Any]:
    """Estatisticas de memoria de um cliente (para dashboard)."""
    try:
        row = db.execute(
            text("""
                SELECT
                    COUNT(*) AS total_msgs,
                    COUNT(DISTINCT session_id) AS total_sessoes,
                    MIN(created_at) AS primeira_msg,
                    MAX(created_at) AS ultima_msg,
                    COUNT(*) FILTER (WHERE role = 'user') AS msgs_user,
                    COUNT(*) FILTER (WHERE role = 'assistant') AS msgs_assistant
                FROM memoria_conversa
                WHERE telefone_hash = :tel
            """),
            {"tel": telefone_hash},
        ).fetchone()
        if row:
            return {
                "telefone_hash": telefone_hash,
                "total_msgs": row[0] or 0,
                "total_sessoes": row[1] or 0,
                "primeira_msg": row[2].isoformat() if row[2] else None,
                "ultima_msg": row[3].isoformat() if row[3] else None,
                "msgs_user": row[4] or 0,
                "msgs_assistant": row[5] or 0,
            }
    except Exception as e:
        logger.error("stats_memoria failed: %s", e)
    return {
        "telefone_hash": telefone_hash,
        "total_msgs": 0,
        "total_sessoes": 0,
    }
