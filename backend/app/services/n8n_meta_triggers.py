"""G8.06.T4 — Parse/validate pg_notify payloads for n8n critical metadata.

Companion of ``infra/supabase/triggers_n8n_notify_g8.sql``:

- Channel: ``cartorio_meta``
- Tables: ``protocolos``, ``atendimentos``
- Events: INSERT + UPDATE OF status (status change only)

API (pure / no live DB):

- ``expected_channel()`` — canal LISTEN esperado
- ``parse_notify_payload(raw)`` — JSON do pg_notify → dict tipado
- ``validate_sql_file_exists()`` — garante SQL no repo
- ``sql_structure_ok()`` — smoke estático do arquivo SQL (sem Postgres)

n8n consumer: LISTEN ``cartorio_meta`` ou bridge HTTP; ver
``docs/N8N_META_TRIGGERS_G8.md``.

Modified by Gustavo Almeida — G8.06.T4.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Final, Mapping

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

EXPECTED_CHANNEL: Final[str] = "cartorio_meta"

SQL_REL_PATH: Final[str] = "infra/supabase/triggers_n8n_notify_g8.sql"

CRITICAL_TABLES: Final[frozenset[str]] = frozenset({"protocolos", "atendimentos"})

ALLOWED_OPS: Final[frozenset[str]] = frozenset({"INSERT", "UPDATE"})

# Keys always present in the SQL payload (nullable values ok)
REQUIRED_PAYLOAD_KEYS: Final[tuple[str, ...]] = (
    "channel",
    "table",
    "op",
    "id",
    "status",
)

# Markers that must appear in the SQL file (structure gate, offline)
_SQL_MUST_CONTAIN: Final[tuple[str, ...]] = (
    "pg_notify",
    "cartorio_meta",
    "notify_cartorio_meta",
    "trg_cartorio_meta_protocolos",
    "trg_cartorio_meta_atendimentos",
    "AFTER INSERT OR UPDATE",
    "public.protocolos",
    "public.atendimentos",
)


# ---------------------------------------------------------------------------
# Types
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class MetaNotifyPayload:
    """Payload canônico do canal cartorio_meta (LGPD-safe)."""

    channel: str
    table: str
    op: str
    id: int
    status: str
    old_status: str | None = None
    protocolo_id: int | None = None
    numero: str | None = None
    ts: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


# ---------------------------------------------------------------------------
# Path helpers
# ---------------------------------------------------------------------------


def repo_root(start: Path | None = None) -> Path:
    """Resolve repo root (pasta com ``backend/`` + ``infra/``)."""
    cur = (start or Path(__file__).resolve()).resolve()
    if cur.is_file():
        cur = cur.parent
    for candidate in (cur, *cur.parents):
        if (candidate / "backend" / "app").is_dir() and (candidate / "infra").is_dir():
            return candidate
    # Fallback: backend/app/services → parents[3]
    return Path(__file__).resolve().parents[3]


def sql_file_path(root: Path | None = None) -> Path:
    """Caminho absoluto do SQL G8.06.T4."""
    return (root or repo_root()) / SQL_REL_PATH


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def expected_channel() -> str:
    """Canal Postgres LISTEN/NOTIFY usado pelos triggers G8.06.T4."""
    return EXPECTED_CHANNEL


def parse_notify_payload(
    raw: str | bytes | Mapping[str, Any] | None,
    *,
    strict_channel: bool = True,
) -> MetaNotifyPayload:
    """Parse o payload text/JSON emitido por ``pg_notify('cartorio_meta', ...)``.

    Args:
        raw: string JSON, bytes UTF-8, ou mapping já decodificado.
        strict_channel: se True, exige ``channel == cartorio_meta``.

    Returns:
        ``MetaNotifyPayload`` validado.

    Raises:
        ValueError: payload vazio, JSON inválido, keys faltando, table/op inválidos.
        TypeError: tipo de entrada não suportado.
    """
    if raw is None:
        raise ValueError("notify payload is empty")

    data: Any
    if isinstance(raw, Mapping):
        data = dict(raw)
    elif isinstance(raw, bytes):
        if not raw:
            raise ValueError("notify payload is empty")
        try:
            data = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ValueError(f"invalid notify JSON bytes: {exc}") from exc
    elif isinstance(raw, str):
        text = raw.strip()
        if not text:
            raise ValueError("notify payload is empty")
        try:
            data = json.loads(text)
        except json.JSONDecodeError as exc:
            raise ValueError(f"invalid notify JSON: {exc}") from exc
    else:
        raise TypeError(f"unsupported notify payload type: {type(raw).__name__}")

    if not isinstance(data, dict):
        raise ValueError("notify payload must be a JSON object")

    missing = [k for k in REQUIRED_PAYLOAD_KEYS if k not in data]
    if missing:
        raise ValueError(f"notify payload missing keys: {missing}")

    channel = str(data.get("channel") or "").strip()
    if strict_channel and channel != EXPECTED_CHANNEL:
        raise ValueError(f"unexpected channel {channel!r}; expected {EXPECTED_CHANNEL!r}")

    table = str(data.get("table") or "").strip()
    if table not in CRITICAL_TABLES:
        raise ValueError(f"unexpected table {table!r}; allowed: {sorted(CRITICAL_TABLES)}")

    op = str(data.get("op") or "").strip().upper()
    if op not in ALLOWED_OPS:
        raise ValueError(f"unexpected op {op!r}; allowed: {sorted(ALLOWED_OPS)}")

    try:
        row_id = int(data["id"])
    except (TypeError, ValueError) as exc:
        raise ValueError(f"invalid id: {data.get('id')!r}") from exc

    status = data.get("status")
    if status is None or str(status).strip() == "":
        raise ValueError("status is required")
    status_s = str(status).strip()

    old_status_raw = data.get("old_status")
    old_status: str | None
    if old_status_raw is None or old_status_raw == "":
        old_status = None
    else:
        old_status = str(old_status_raw)

    protocolo_id: int | None = None
    if data.get("protocolo_id") is not None and data.get("protocolo_id") != "":
        try:
            protocolo_id = int(data["protocolo_id"])
        except (TypeError, ValueError) as exc:
            raise ValueError(f"invalid protocolo_id: {data.get('protocolo_id')!r}") from exc

    numero_raw = data.get("numero")
    numero: str | None
    if numero_raw is None or numero_raw == "":
        numero = None
    else:
        numero = str(numero_raw)

    ts_raw = data.get("ts")
    ts = None if ts_raw is None or ts_raw == "" else str(ts_raw)

    return MetaNotifyPayload(
        channel=channel or EXPECTED_CHANNEL,
        table=table,
        op=op,
        id=row_id,
        status=status_s,
        old_status=old_status,
        protocolo_id=protocolo_id,
        numero=numero,
        ts=ts,
    )


def validate_sql_file_exists(root: Path | None = None) -> Path:
    """Garante que o SQL dos triggers existe no repo.

    Returns:
        Path absoluto do arquivo.

    Raises:
        FileNotFoundError: se o arquivo não existir.
    """
    path = sql_file_path(root)
    if not path.is_file():
        raise FileNotFoundError(f"G8.06.T4 SQL missing: {path}")
    return path


def sql_structure_ok(root: Path | None = None) -> tuple[bool, list[str]]:
    """Valida estrutura estática do SQL (offline, sem Postgres).

    Returns:
        ``(ok, missing_markers)`` — ok True se todos os markers presentes.
    """
    path = validate_sql_file_exists(root)
    text = path.read_text(encoding="utf-8")
    missing = [m for m in _SQL_MUST_CONTAIN if m not in text]
    return (not missing, missing)


def read_sql(root: Path | None = None) -> str:
    """Lê o conteúdo do SQL G8.06.T4 (utf-8)."""
    return validate_sql_file_exists(root).read_text(encoding="utf-8")


__all__ = [
    "ALLOWED_OPS",
    "CRITICAL_TABLES",
    "EXPECTED_CHANNEL",
    "MetaNotifyPayload",
    "REQUIRED_PAYLOAD_KEYS",
    "SQL_REL_PATH",
    "expected_channel",
    "parse_notify_payload",
    "read_sql",
    "repo_root",
    "sql_file_path",
    "sql_structure_ok",
    "validate_sql_file_exists",
]
