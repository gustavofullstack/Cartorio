"""G8.19.T1 — Verificador de integridade da blockchain do audit_log.

Complementa `AuditService.verify_chain` (que para no primeiro indice
quebrado) com uma funcao que enumera TODOS os pontos de quebra — util
para detectar:

- tamper mid-chain (entry 3 editada, entries 3..N quebradas)
- HMAC forjado (assinatura inconsistente mesmo com hash consistente)
- edicao retroativa que preserva prev_hash mas viola hash/HMAC

LGPD art. 37 (continuidade da auditoria) + art. 50 (boa-fe). Nao
modifica audit_log — apenas LE (AGENTS.md regra READ-only).

Invocado por:
- `scripts/audit_integrity_check.py` (CLI ad-hoc + dead-man's-switch 15min)
- testes em `tests/test_audit_integrity_g8.py`

Deltas vs G8.07.T2 (AuditService.verify_hash_sequence):
- retorna `list[int]` (todos os indices quebrados), nao `dict` com 1 posicao
- suporta checagem HMAC alem do hash chain
- integra com `from_db()` e `verify_full_chain()` para uso one-shot
- `integrity_score` em [0, 1] para metricas Prometheus

Nao toca em `app/services/audit.py` (chain builder intocavel).
"""

from __future__ import annotations

import hashlib
import hmac as _hmac
import json
from typing import Any

from sqlalchemy.orm import Session

from app.config import settings
from app.models.audit_log import AuditLog


# Largura do prev_hash canonico para chain head (None -> zeros)
_CHAIN_HEAD_PLACEHOLDER = "0" * 64


def _canonical_block(prev_hash: str, payload: dict[str, Any], timestamp: str) -> str:
    """Bloco canonico (mesma serializacao usada em AuditService._canonical_block)."""
    block = {
        "prev_hash": prev_hash,
        "timestamp": timestamp,
        "payload": payload,
    }
    return json.dumps(block, sort_keys=True, separators=(",", ":"), default=str)


def _compute_hash(prev_hash: str, payload: dict[str, Any], timestamp: str) -> str:
    return hashlib.sha256(
        _canonical_block(prev_hash, payload, timestamp).encode("utf-8")
    ).hexdigest()


def _compute_hmac_signature(
    *,
    new_hash: str,
    timestamp: str,
    actor_id: str,
    action: str,
    hmac_key: bytes,
) -> str:
    """Reproduz o HMAC gravado em AuditService.log (linha 107 de audit.py).

    `hmac_signature = HMAC-SHA256(key, f"{new_hash}:{timestamp}:{actor_id}:{action}")`
    """
    message = f"{new_hash}:{timestamp}:{actor_id}:{action}".encode("utf-8")
    return _hmac.new(hmac_key, message, hashlib.sha256).hexdigest()


def _normalize_timestamp(ts: Any) -> str:
    """Normaliza timestamp para o formato usado em `_canonical_block`.

    AuditService.log() formata com `.replace(tzinfo=None).isoformat(timespec='microseconds')`
    trocando o espaco do Postgres por `T`. Aqui replicamos o mesmo shape
    para que o SHA256 recalculado bata com o armazenado.
    """
    if hasattr(ts, "tzinfo") and ts.tzinfo is not None:
        ts = ts.replace(tzinfo=None)
    if hasattr(ts, "isoformat"):
        ts_iso = ts.isoformat(timespec="microseconds")
    else:
        ts_iso = str(ts)
    return ts_iso.replace(" ", "T")


def verify_hash_sequence(entries: list[dict[str, Any]]) -> list[int]:
    """Verifica integridade da cadeia e retorna TODOS os indices quebrados.

    G8.19.T1 — enumera divergencias em chain + HMAC, nao para no primeiro.

    Cada entry esperada (chaves):
      - id: int (posicao logica na chain)
      - actor_id: str
      - action: str
      - payload: dict
      - timestamp: datetime | str ISO
      - prev_hash: str | None (None ou zeros = chain head)
      - hash: str hex SHA256
      - hmac_signature: str

    Regras:
      1. Chain rule (entry N): `prev_hash[N] == hash[N-1]` (ou zeros se N=0)
      2. Hash rule (entry N): `hash[N] == SHA256(prev_hash_canonico, payload, timestamp)`
      3. HMAC rule (entry N): `hmac_signature[N] == HMAC(key, f"{hash}:{timestamp}:{actor_id}:{action}")`

    Args:
        entries: lista ordenada por `id` ASC.

    Returns:
        Lista de indices (0-based) onde qualquer regra falhou. Lista
        vazia = cadeia integra. Entry com multiplas falhas aparece 1 vez.
    """
    broken: list[int] = []
    prev_hash_observed: str | None = None

    for i, entry in enumerate(entries):
        payload = entry.get("payload") or {}
        timestamp = _normalize_timestamp(entry.get("timestamp"))
        stored_hash = str(entry.get("hash") or "")
        stored_hmac = str(entry.get("hmac_signature") or "")
        actor_id = str(entry.get("actor_id") or "")
        action = str(entry.get("action") or "")
        entry_prev_raw = entry.get("prev_hash")
        entry_prev_norm = entry_prev_raw if entry_prev_raw else _CHAIN_HEAD_PLACEHOLDER
        prev_for_hash = prev_hash_observed if prev_hash_observed else _CHAIN_HEAD_PLACEHOLDER

        # Regra 1: chain — prev_hash do entry deve apontar para o hash do entry anterior
        chain_ok = entry_prev_norm == prev_for_hash

        # Regra 2: hash — recalcula SHA256 sobre o bloco canonico
        expected_hash = _compute_hash(prev_for_hash, payload, timestamp)
        hash_ok = stored_hash == expected_hash

        # Regra 3: HMAC — recalcula assinatura com a chave do servidor
        hmac_key = settings.audit_hmac_key.encode("utf-8")
        expected_hmac = _compute_hmac_signature(
            new_hash=stored_hash,
            timestamp=timestamp,
            actor_id=actor_id,
            action=action,
            hmac_key=hmac_key,
        )
        hmac_ok = (
            stored_hmac is not None
            and expected_hmac is not None
            and _hmac.compare_digest(stored_hmac, expected_hmac)
        )

        if not (chain_ok and hash_ok and hmac_ok):
            broken.append(i)
            # NAO atualiza prev_hash_observed — chain quebrada, todo o
            # restante tambem sera reportado (regra t024 retro-edit).
            # Mas ainda sim, continuamos a iteracao para detectar todos
            # os pontos onde a chain subsequente quebra.
        else:
            prev_hash_observed = stored_hash

    return broken


def from_db(db: Session) -> list[dict[str, Any]]:
    """Carrega audit_log ordenado por id ASC como lista de dicts canonicos.

    Stream-friendly: usa `.yield_per()` para tabelas grandes (10k+ entries).
    Caller itera com `for batch in from_db(): ...` ou materializa com
    `list(from_db())`.

    Returns:
        Generator[dict, None, None] — cada dict tem as chaves esperadas
        por `verify_hash_sequence()`.
    """

    def _gen() -> Any:
        # `.yield_per(500)` evita carregar 100k entries na memoria de uma vez.
        for entry in db.query(AuditLog).order_by(AuditLog.id.asc()).yield_per(500):
            yield {
                "id": entry.id,
                "actor_id": entry.actor_id,
                "actor_type": entry.actor_type,
                "action": entry.action,
                "resource": entry.resource,
                "payload": entry.payload or {},
                "timestamp": entry.timestamp,
                "prev_hash": entry.prev_hash,
                "hash": entry.hash,
                "hmac_signature": entry.hmac_signature,
            }

    # Type hint para mypy (yield_per retorna Query, nao generator tipado)
    return _gen()  # type: ignore[no-any-return]


def verify_full_chain(db: Session) -> dict[str, Any]:
    """Verifica a cadeia inteira e retorna resumo.

    Args:
        db: SQLAlchemy Session.

    Returns:
        dict com:
          - total_entries: int
          - broken_indices: list[int]
          - integrity_score: float em [0.0, 1.0]
              = (total - len(broken)) / total  (1.0 = intacto)
          - chain_intact: bool (broken_indices vazio)
          - first_break_id: int | None (id do primeiro entry quebrado, ou None)
          - error: str | None (mensagem curta sem PII, se houve erro de I/O)
    """
    try:
        entries_iter = from_db(db)
        # Materializa em lista — verify_hash_sequence precisa de acesso
        # aleatorio por indice (i-1 lookup). Para 10k+ entries, chunkizar
        # internamente seria otimo, mas a performance do SHA256 + HMAC
        # em Python eh da ordem de ~5ms/entry — 10k = 50s, aceitavel
        # para o dead-man's-switch de 15min (roda em background).
        entries = list(entries_iter)
        broken = verify_hash_sequence(entries)
    except Exception as exc:  # noqa: BLE001
        return {
            "total_entries": 0,
            "broken_indices": [],
            "integrity_score": 0.0,
            "chain_intact": False,
            "first_break_id": None,
            "error": f"io_error:{type(exc).__name__}",
        }

    total = len(entries)
    integrity_score = (total - len(broken)) / total if total > 0 else 1.0
    first_break_id: int | None = None
    if broken and broken[0] < len(entries):
        first_break_id = int(entries[broken[0]].get("id", broken[0]))

    return {
        "total_entries": total,
        "broken_indices": broken,
        "integrity_score": integrity_score,
        "chain_intact": len(broken) == 0,
        "first_break_id": first_break_id,
        "error": None,
    }


__all__ = ["verify_hash_sequence", "from_db", "verify_full_chain"]
