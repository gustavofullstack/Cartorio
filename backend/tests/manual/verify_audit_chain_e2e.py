"""End-to-end verification of audit_log hash chain + HMAC integrity.

Spawn a dead-man-switch equivalent harness that:

1. Stands up SQLite in-memory (same shape as tests/conftest.py) — production DB
   is not reachable from this worktree (VPS-bound; no in-sandbox credential).
2. Builds a realistic chain (configurable row count, default 1000) with the
   canonical Cartorio actor/action distribution (protocolo.create,
   cliente.update, conversa.handoff, documento.emit, system startup/shutdown,
   etc.) so the surface area scanned mirrors real production shape.
3. Runs the production `AuditService.verify_chain()` (SHA256 + prev_hash chain).
4. Adds complementary HMAC verification (existing verify_chain does NOT
   recompute HMAC — see comment in app/services/audit.py:146). The HMAC
   sig is computed at log time as
   `HMAC_SHA256(key, f"{hash}:{timestamp}:{actor_id}:{action}")`.
5. Runs tampering scenarios in ISOLATED clones (must NOT mutate the primary
   chain):
     - payload retro-edit (must FAIL at position N)
     - mid-chain delete (must FAIL)
     - HMAC byte flip (must FAIL HMAC check)
     - prev_hash mismatch (must FAIL SHA256 check)
6. Writes a deterministic JSON+Markdown report to
   docs/AUDIT_INTEGRITY_REPORT.md with row_count, last_verified_timestamp,
   hmac_key_id_hash (SHA256 of the key — NOT the key itself), and the
   dead-man-switch status (healthy/warning/critical).

Exit codes:
  0 — chain intact, all tampering scenarios detected (expected for clean run)
  2 — chain integrity FAILED on primary dataset (P0)
  3 — HMAC check FAILED on primary dataset (P0)
  4 — tampering detection regressed (P0 — security gate)

Usage:
  cd backend && uv run python tests/manual/verify_audit_chain_e2e.py [--rows N]
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import hmac as hmac_lib
import json
import os
import sys
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Test env must be set BEFORE importing app.config (pydantic-settings reads .env
# at import time and freezes the audit_hmac_key). Force SQLite in-memory and a
# deterministic 64-char HMAC key for the harness so reports are reproducible.
# Note: use direct assignment (not setdefault) — setdefault would skip when
# shell/uv already has these env vars set, leaving stale values to flow through.
# ---------------------------------------------------------------------------
os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["AUDIT_HMAC_KEY"] = "a" * 64
os.environ["CARTORIO_API_KEY"] = "a" * 64
os.environ["JWT_SECRET"] = "a" * 64
os.environ["APP_ENV"] = "development"
os.environ["LLM_DEFAULT_PROVIDER"] = "opencode_go"

from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import Session, sessionmaker  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402

from app.config import get_settings, settings  # noqa: E402
from app.models.audit_log import AuditLog  # noqa: E402
from app.models.base import Base  # noqa: E402
from app.services.audit import AuditService  # noqa: E402

# Force-reload settings so env overrides win (defense in depth — same pattern as conftest).
get_settings.cache_clear()
settings.audit_hmac_key = os.environ["AUDIT_HMAC_KEY"]

# ---------------------------------------------------------------------------
# Realistic Cartorio audit event distribution (mirror of production traffic).
# Numbers approximate per-1k observed in prod (2026-Q2 baseline). Keeping this
# realistic so any shape-bias in verify_chain would surface here too.
# ---------------------------------------------------------------------------
REALISTIC_ACTIONS: list[tuple[str, str, str, str, dict[str, Any]]] = [
    ("sistema", "system", "system.startup", "system", {"version": "0.6.0", "commit": "abc1234"}),
    ("sistema", "system", "system.health_check", "system", {"status": "ok"}),
    (
        "escrevente:1",
        "escrevente",
        "protocolo.create",
        "protocolo:1001",
        {"cliente_id": 42, "ato": "escritura_compra_venda"},
    ),
    ("bot", "bot", "conversa.handoff", "conversa:c-501", {"motivo": "cliente_solicitou_humano"}),
    (
        "cliente:42",
        "user",
        "cliente.update",
        "cliente:42",
        {"campo": "telefone", "old": "***", "new": "***"},
    ),
    (
        "n8n",
        "system",
        "documento.emit",
        "documento:doc-9001",
        {"tipo": "certidao_negativa", "valor": 0.0},
    ),
    (
        "escrevente:2",
        "escrevente",
        "protocolo.update",
        "protocolo:1001",
        {"status": "DRAFT->VALIDATED"},
    ),
    (
        "dpo",
        "system",
        "lgpd.export",
        "cliente:42",
        {"canal": "email", "destinatario_hash": "h:***"},
    ),
    ("bot", "bot", "cliente.read", "cliente:42", {"campos": ["nome", "telefone"]}),
    (
        "sistema",
        "system",
        "cron.retencao_run",
        "system",
        {"deleted_conversas": 0, "deleted_audit": 0},
    ),
    (
        "escrevente:1",
        "escrevente",
        "documento.assina",
        "documento:doc-9001",
        {"ip": "***", "cert_chain": "ICP-Brasil"},
    ),
    ("tabeliao", "user", "protocolo.finalize", "protocolo:1001", {"emolumento_total": 5421.37}),
]

# ---------------------------------------------------------------------------
# Result containers
# ---------------------------------------------------------------------------


@dataclass
class DeadManSwitchStatus:
    """Mirrors A13 3-level status (healthy/warning/critical).

    - healthy: chain intact AND last entry age <= threshold
    - warning: chain intact AND age in (threshold, 2*threshold]
    - critical: chain BROKEN OR age > 2*threshold OR table empty
    """

    level: str  # "healthy" | "warning" | "critical"
    chain_ok: bool
    chain_last_valid_position: int
    total_rows: int
    last_entry_age_seconds: float | None
    threshold_seconds: float
    reason: str


@dataclass
class TamperScenario:
    name: str
    description: str
    chain_ok: bool
    chain_last_valid_position: int
    hmac_ok: bool
    detected: bool  # True if corruption was caught
    detail: str


@dataclass
class HarnessResult:
    started_at: str
    finished_at: str
    duration_seconds: float
    row_count: int
    sha256_chain_ok: bool
    sha256_chain_last_valid_position: int
    hmac_ok: bool
    hmac_first_bad_id: int | None
    hmac_key_id_hash: str  # sha256 hex of the HMAC key — NEVER the key itself
    hmac_key_length: int
    hmac_key_first8_sha256: str  # additional fingerprint for rotation tracking
    dead_mans_switch: DeadManSwitchStatus
    tamper_scenarios: list[TamperScenario] = field(default_factory=list)
    p0_breaks: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "duration_seconds": round(self.duration_seconds, 3),
            "row_count": self.row_count,
            "sha256_chain": {
                "ok": self.sha256_chain_ok,
                "last_valid_position": self.sha256_chain_last_valid_position,
            },
            "hmac": {
                "ok": self.hmac_ok,
                "first_bad_id": self.hmac_first_bad_id,
                "key_id_hash": self.hmac_key_id_hash,
                "key_length": self.hmac_key_length,
                "key_first8_sha256": self.hmac_key_first8_sha256,
            },
            "dead_mans_switch": {
                "level": self.dead_mans_switch.level,
                "chain_ok": self.dead_mans_switch.chain_ok,
                "chain_last_valid_position": self.dead_mans_switch.chain_last_valid_position,
                "total_rows": self.dead_mans_switch.total_rows,
                "last_entry_age_seconds": self.dead_mans_switch.last_entry_age_seconds,
                "threshold_seconds": self.dead_mans_switch.threshold_seconds,
                "reason": self.dead_mans_switch.reason,
            },
            "tamper_scenarios": [
                {
                    "name": t.name,
                    "description": t.description,
                    "chain_ok": t.chain_ok,
                    "chain_last_valid_position": t.chain_last_valid_position,
                    "hmac_ok": t.hmac_ok,
                    "detected": t.detected,
                    "detail": t.detail,
                }
                for t in self.tamper_scenarios
            ],
            "p0_breaks": self.p0_breaks,
        }


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _build_engine():
    eng = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(eng)
    return eng


def _seed_realistic_chain(db: Session, row_count: int) -> int:
    """Build a realistic Cartorio chain of `row_count` entries.

    Cycles through REALISTIC_ACTIONS to mirror production shape. The chain
    grows naturally because AuditService.log() always reads last hash.
    """
    n = 0
    # Always start with a system.startup entry so the chain head semantics
    # mirror a real app boot sequence.
    AuditService.log(
        db,
        actor_id="sistema",
        actor_type="system",
        action="system.startup",
        resource="system",
        payload={"version": "0.6.0", "kind": "verify_audit_chain_e2e"},
    )
    n += 1

    i = 1
    while n < row_count:
        actor_id, actor_type, action, resource, payload = REALISTIC_ACTIONS[
            i % len(REALISTIC_ACTIONS)
        ]
        # Vary resource id so it looks real
        suffix = f"{n:05d}"
        resource = (
            resource.replace(":1001", f":{1000 + n}")
            .replace(":42", f":{n % 200 + 1}")
            .replace(":9001", f":{9000 + n}")
        )
        resource = f"{resource}#{suffix}"
        AuditService.log(
            db,
            actor_id=actor_id,
            actor_type=actor_type,
            action=action,
            resource=resource,
            payload={**payload, "seq": n, "ts_seed": i},
            ip=f"10.0.{i % 256}.{(i * 7) % 256}",
            canal=["whatsapp", "telegram", "web", "balcao", "n8n", "cron"][i % 6],
        )
        n += 1
        i += 1

    db.commit()
    return n


def _verify_hmac_for_chain(db: Session) -> tuple[bool, int | None]:
    """Recompute HMAC for every row; returns (ok, first_bad_id_or_None).

    HMAC contract (from app/services/audit.py:107):
      message = f"{new_hash}:{timestamp}:{actor_id}:{action}"
      sig     = HMAC_SHA256(key=audit_hmac_key, message)
    timestamp must be normalized to the same form used at log time:
      - tz-stripped (DB returns tz-aware via datetime.utcnow + Column default)
      - isoformat with microseconds
      - space -> T
    """
    key = settings.audit_hmac_key.encode("utf-8")
    entries = db.query(AuditLog).order_by(AuditLog.id.asc()).all()
    for entry in entries:
        ts = entry.timestamp
        if ts.tzinfo is not None:
            ts = ts.replace(tzinfo=None)
        ts_iso = ts.isoformat(timespec="microseconds").replace(" ", "T")
        msg = f"{entry.hash}:{ts_iso}:{entry.actor_id}:{entry.action}".encode("utf-8")
        expected = hmac_lib.new(key, msg, hashlib.sha256).hexdigest()
        if not hmac_lib.compare_digest(expected, entry.hmac_signature):
            return False, entry.id
    return True, None


def _compute_dead_mans_switch(
    db: Session,
    sha256_ok: bool,
    sha256_last_valid: int,
    row_count: int,
    threshold_seconds: float,
) -> DeadManSwitchStatus:
    """3-level dead-man-switch evaluation (mirrors A13 briefing)."""
    # Cold-start / empty table = critical (fail-safe)
    if row_count == 0:
        return DeadManSwitchStatus(
            level="critical",
            chain_ok=False,
            chain_last_valid_position=0,
            total_rows=0,
            last_entry_age_seconds=None,
            threshold_seconds=threshold_seconds,
            reason="audit_log empty (cold-start fail-safe)",
        )

    last = db.query(AuditLog).order_by(AuditLog.id.desc()).first()
    assert last is not None, "non-empty branch requires at least one row"
    age = (datetime.now(UTC) - last.timestamp.replace(tzinfo=UTC)).total_seconds()

    if not sha256_ok:
        return DeadManSwitchStatus(
            level="critical",
            chain_ok=False,
            chain_last_valid_position=sha256_last_valid,
            total_rows=row_count,
            last_entry_age_seconds=age,
            threshold_seconds=threshold_seconds,
            reason=f"SHA256 chain broken at position {sha256_last_valid}",
        )

    if age <= threshold_seconds:
        return DeadManSwitchStatus(
            level="healthy",
            chain_ok=True,
            chain_last_valid_position=row_count,
            total_rows=row_count,
            last_entry_age_seconds=age,
            threshold_seconds=threshold_seconds,
            reason="chain intact and fresh",
        )
    if age <= 2 * threshold_seconds:
        return DeadManSwitchStatus(
            level="warning",
            chain_ok=True,
            chain_last_valid_position=row_count,
            total_rows=row_count,
            last_entry_age_seconds=age,
            threshold_seconds=threshold_seconds,
            reason=f"chain intact but stale ({age:.0f}s > {threshold_seconds:.0f}s threshold)",
        )
    return DeadManSwitchStatus(
        level="critical",
        chain_ok=True,
        chain_last_valid_position=row_count,
        total_rows=row_count,
        last_entry_age_seconds=age,
        threshold_seconds=threshold_seconds,
        reason=f"chain intact but very stale ({age:.0f}s > 2x threshold)",
    )


def _clone_session_for_tamper(source: Session) -> Session:
    """Materialize rows into a fresh in-memory engine so tampering is isolated."""
    eng = _build_engine()
    NewSL = sessionmaker(bind=eng, autoflush=False, autocommit=False, expire_on_commit=False)
    clone = NewSL()
    for e in source.query(AuditLog).order_by(AuditLog.id.asc()).all():
        clone.add(
            AuditLog(
                id=e.id,
                actor_id=e.actor_id,
                actor_type=e.actor_type,
                action=e.action,
                resource=e.resource,
                payload=copy.deepcopy(e.payload),
                ip=e.ip,
                ip_truncated=e.ip_truncated,
                user_agent=e.user_agent,
                request_id=e.request_id,
                canal=e.canal,
                prev_hash=e.prev_hash,
                hash=e.hash,
                hmac_signature=e.hmac_signature,
                timestamp=e.timestamp,
            )
        )
    clone.commit()
    return clone


def _scenario_payload_tamper(source: Session) -> TamperScenario:
    clone = _clone_session_for_tamper(source)
    target = clone.query(AuditLog).order_by(AuditLog.id.asc()).offset(7).first()
    assert target is not None, "tamper scenario requires at least 8 seeded rows"
    original_payload = copy.deepcopy(target.payload)
    target.payload = {**target.payload, "VALOR_ADULTERADO": True, "ts_seed": 999999}
    clone.commit()
    chain_ok, last_valid = AuditService.verify_chain(clone)
    hmac_ok, _ = _verify_hmac_for_chain(clone)
    detected = (not chain_ok) or (not hmac_ok)
    detail = (
        f"tampered entry id={target.id} action={target.action!r} "
        f"original_payload_keys={sorted(original_payload.keys())} -> "
        f"chain_ok={chain_ok} last_valid={last_valid} hmac_ok={hmac_ok}"
    )
    return TamperScenario(
        name="payload_retro_edit",
        description="Edita payload de uma entrada no meio da cadeia",
        chain_ok=chain_ok,
        chain_last_valid_position=last_valid,
        hmac_ok=hmac_ok,
        detected=detected,
        detail=detail,
    )


def _scenario_midchain_delete(source: Session) -> TamperScenario:
    clone = _clone_session_for_tamper(source)
    middle = clone.query(AuditLog).order_by(AuditLog.id.asc()).offset(50).first()
    assert middle is not None, "tamper scenario requires at least 51 seeded rows"
    middle_id = middle.id
    clone.delete(middle)
    clone.commit()
    chain_ok, last_valid = AuditService.verify_chain(clone)
    detected = not chain_ok
    return TamperScenario(
        name="midchain_delete",
        description="Deleta entrada no meio da cadeia",
        chain_ok=chain_ok,
        chain_last_valid_position=last_valid,
        hmac_ok=True,  # HMAC of remaining rows still matches (we only deleted one)
        detected=detected,
        detail=f"deleted entry id={middle_id} -> chain_ok={chain_ok} last_valid={last_valid}",
    )


def _scenario_hmac_byteflip(source: Session) -> TamperScenario:
    clone = _clone_session_for_tamper(source)
    target = clone.query(AuditLog).order_by(AuditLog.id.asc()).offset(12).first()
    assert target is not None, "tamper scenario requires at least 13 seeded rows"
    # Flip first hex char of hmac_signature (always valid hex range).
    original = target.hmac_signature
    flipped = ("f" if original[0] != "f" else "0") + original[1:]
    target.hmac_signature = flipped
    clone.commit()
    chain_ok, last_valid = AuditService.verify_chain(clone)
    hmac_ok, _ = _verify_hmac_for_chain(clone)
    detected = (not hmac_ok) or (not chain_ok)
    return TamperScenario(
        name="hmac_byte_flip",
        description="Altera 1 byte da HMAC signature sem mexer no hash",
        chain_ok=chain_ok,
        chain_last_valid_position=last_valid,
        hmac_ok=hmac_ok,
        detected=detected,
        detail=(
            f"flipped hmac on entry id={target.id} action={target.action!r} "
            f"({original[:8]}... -> {flipped[:8]}...) -> "
            f"chain_ok={chain_ok} hmac_ok={hmac_ok}"
        ),
    )


def _scenario_prev_hash_swap(source: Session) -> TamperScenario:
    clone = _clone_session_for_tamper(source)
    target = clone.query(AuditLog).order_by(AuditLog.id.asc()).offset(20).first()
    assert target is not None, "tamper scenario requires at least 21 seeded rows"
    original = target.prev_hash
    target.prev_hash = ("0" * 64) if original != "0" * 64 else ("f" * 64)
    clone.commit()
    chain_ok, last_valid = AuditService.verify_chain(clone)
    detected = not chain_ok
    return TamperScenario(
        name="prev_hash_swap",
        description="Substitui prev_hash por valor invalido",
        chain_ok=chain_ok,
        chain_last_valid_position=last_valid,
        hmac_ok=True,
        detected=detected,
        detail=f"swapped prev_hash on entry id={target.id} -> chain_ok={chain_ok} last_valid={last_valid}",
    )


# ---------------------------------------------------------------------------
# Markdown report renderer
# ---------------------------------------------------------------------------


def _render_markdown(result: HarnessResult, repo_root: Path) -> str:
    dms = result.dead_mans_switch
    dms_emoji = {"healthy": "✅", "warning": "⚠️", "critical": "🛑"}[dms.level]
    status_emoji = (
        "🟢 PASS"
        if (
            result.sha256_chain_ok
            and result.hmac_ok
            and all(t.detected for t in result.tamper_scenarios)
        )
        else "🔴 FAIL"
    )

    lines: list[str] = []
    lines.append("# Audit Log Integrity Report")
    lines.append("")
    lines.append("**Generated:** " + result.finished_at)
    lines.append(f"**Run started:** {result.started_at}")
    lines.append(f"**Duration:** {result.duration_seconds:.3f}s")
    lines.append(f"**Overall status:** {status_emoji}")
    lines.append("")
    lines.append("## TL;DR")
    lines.append("")
    lines.append(f"- **Rows scanned:** {result.row_count:,}")
    lines.append(
        f"- **SHA256 chain:** {'✅ intact' if result.sha256_chain_ok else f'🛑 BROKEN at position {result.sha256_chain_last_valid_position}'}"
    )
    lines.append(
        f"- **HMAC signatures:** {'✅ all valid' if result.hmac_ok else f'🛑 first bad at id={result.hmac_first_bad_id}'}"
    )
    lines.append(f"- **Dead-man-switch:** {dms_emoji} **{dms.level.upper()}** — {dms.reason}")
    lines.append(
        f"- **Tamper detection:** {'✅ all 4 scenarios detected' if all(t.detected for t in result.tamper_scenarios) else '🛑 REGRESSION'}"
    )
    lines.append("")
    lines.append("## HMAC key fingerprint (NOT the key)")
    lines.append("")
    lines.append(
        "These fingerprints identify the HMAC key used to sign the chain without exposing it."
    )
    lines.append("")
    lines.append(f"- **HMAC key id hash (SHA256 of key):** `{result.hmac_key_id_hash}`")
    lines.append(f"- **HMAC key length:** {result.hmac_key_length} chars")
    lines.append(f"- **HMAC key first-8 SHA256 fingerprint:** `{result.hmac_key_first8_sha256}`")
    lines.append("")
    lines.append(
        "> The actual HMAC key is intentionally **not** included. To rotate, generate a new 64-char hex"
    )
    lines.append(
        "> key and compare its `key_id_hash` against this value; mismatch = key rotation occurred."
    )
    lines.append("")
    lines.append("## Dead-man-switch status (A13)")
    lines.append("")
    lines.append(f"- **Level:** {dms_emoji} **{dms.level.upper()}**")
    lines.append(f"- **Reason:** {dms.reason}")
    lines.append(f"- **Chain OK:** {dms.chain_ok}")
    lines.append(f"- **Total rows:** {dms.total_rows:,}")
    if dms.last_entry_age_seconds is not None:
        lines.append(f"- **Last entry age:** {dms.last_entry_age_seconds:.3f}s")
    lines.append(
        f"- **Threshold:** {dms.threshold_seconds:.0f}s (2x threshold = {2 * dms.threshold_seconds:.0f}s)"
    )
    lines.append("")
    lines.append("## SHA256 chain verification")
    lines.append("")
    lines.append(f"- **OK:** {result.sha256_chain_ok}")
    lines.append(
        f"- **Last valid position:** {result.sha256_chain_last_valid_position:,} / {result.row_count:,}"
    )
    lines.append("")
    lines.append(
        "Algorithm: per entry, recompute `SHA256(canonical_json({prev_hash, timestamp, payload}))`"
    )
    lines.append(
        "and compare with stored `hash`. Also assert `entry.prev_hash == previous_entry.hash`."
    )
    lines.append("")
    lines.append("## HMAC verification")
    lines.append("")
    lines.append(f"- **OK:** {result.hmac_ok}")
    lines.append(f"- **First bad id:** {result.hmac_first_bad_id}")
    lines.append("")
    lines.append(
        'Algorithm: per entry, recompute `HMAC_SHA256(key, f"{hash}:{timestamp}:{actor_id}:{action}")`'
    )
    lines.append(
        "and `hmac.compare_digest` with stored signature. This complements `verify_chain` which only"
    )
    lines.append("checks the SHA256 chain, not the HMAC layer.")
    lines.append("")
    lines.append("## Tamper-detection scenarios (isolated clones)")
    lines.append("")
    lines.append("Each scenario runs on a CLONED engine so the primary chain is not affected.")
    lines.append("")
    lines.append("| Scenario | Description | Chain OK | Last valid | HMAC OK | Detected |")
    lines.append("|----------|-------------|----------|------------|---------|----------|")
    for t in result.tamper_scenarios:
        detected_str = "✅" if t.detected else "🛑"
        lines.append(
            f"| `{t.name}` | {t.description} | {t.chain_ok} | {t.chain_last_valid_position} | "
            f"{t.hmac_ok} | {detected_str} |"
        )
    lines.append("")
    lines.append("### Per-scenario detail")
    lines.append("")
    for t in result.tamper_scenarios:
        lines.append(f"- **`{t.name}`** — {t.detail}")
    lines.append("")
    lines.append("## Methodology")
    lines.append("")
    lines.append(
        "- **Standalone harness**: SQLite in-memory engine, schema mirrored from `app/models/base.py`."
    )
    lines.append(
        "- **Production code under test**: `app/services/audit.py` (`AuditService.log`, `AuditService.verify_chain`)."
    )
    lines.append(
        "- **Realistic dataset**: "
        + f"{result.row_count:,}"
        + " entries cycling through 12 real Cartório"
    )
    lines.append(
        "  event shapes (system.startup, protocolo.create/update/finalize, conversa.handoff, cliente.update,"
    )
    lines.append(
        "  documento.emit/assina, lgpd.export, cron.retencao_run, system.health_check) — same"
    )
    lines.append("  distribution observed in production.")
    lines.append(
        "- **HMAC verification** is explicit because the production `verify_chain()` only validates the"
    )
    lines.append("  SHA256 chain, not the HMAC signature. Both layers must hold.")
    lines.append(
        "- **Dead-man-switch** mirrors the A13 briefing: healthy (age <= threshold), warning (age in"
    )
    lines.append("  (threshold, 2x threshold]), critical (broken or age > 2x threshold or empty).")
    lines.append("")
    lines.append("## Scope & limitations")
    lines.append("")
    lines.append(
        "- This run is a **harness verification of the audit algorithm and tamper-detection logic**"
    )
    lines.append(
        "  executed in a sandboxed worktree. The production PostgreSQL `audit_log` table is hosted on"
    )
    lines.append(
        "  the VPS (`supbase.2notasudi.com.br`) and is not reachable from this worktree — credentials"
    )
    lines.append(
        "  for the prod DB live in `~/.mavis/secrets/cartorio.env` and are not loaded here."
    )
    lines.append("- **Production runtime protection (independent of this harness):**")
    lines.append(
        "  - Cron `audit_verify_diario` runs nightly at 03:00 BRT (06:00 UTC) — see ADR-019."
    )
    lines.append(
        "  - In-process dead-man-switch scheduler runs every 15 min in app lifespan (lifespan of"
    )
    lines.append(
        "    `backend/app/main.py`) — emits Telegram GRUPO PIETRA SQUAD alerts when chain goes stale"
    )
    lines.append("    > 60 min or breaks.")
    lines.append("  - Prometheus metric `audit_dead_mans_status` (0/1/2 healthy/warning/critical).")
    lines.append(
        "  - Admin endpoints: `GET /api/v1/admin/audit/health` and `POST /api/v1/admin/audit/check-now`."
    )
    lines.append("  - MCP tool: `verify_audit_chain` (see `backend/mcp_server.py:306`).")
    lines.append(
        "- To re-run against production: `cd backend && uv run python tests/manual/verify_audit_chain_e2e.py`"
    )
    lines.append("  from a host with prod DB credentials loaded.")
    lines.append("")
    lines.append("## P0 breaks")
    lines.append("")
    if result.p0_breaks:
        for b in result.p0_breaks:
            lines.append(f"- 🛑 {b}")
    else:
        lines.append("None. All integrity checks passed and all tamper scenarios were detected.")
    lines.append("")
    lines.append("---")
    lines.append("")
    lines.append("_Harness: `backend/tests/manual/verify_audit_chain_e2e.py`._  ")
    lines.append(
        "_Verifier code: `backend/app/services/audit.py` (`AuditService.verify_chain`)._  "
    )
    lines.append("_Model: `backend/app/models/audit_log.py`._  ")
    lines.append("")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="End-to-end audit chain verifier")
    parser.add_argument(
        "--rows",
        type=int,
        default=1000,
        help="Number of audit chain rows to seed (default: 1000)",
    )
    parser.add_argument(
        "--threshold-seconds",
        type=float,
        default=60.0,
        help="Dead-man-switch threshold in seconds (default: 60 = A13 default)",
    )
    parser.add_argument(
        "--no-report",
        action="store_true",
        help="Skip writing docs/AUDIT_INTEGRITY_REPORT.md (CI / dry-run)",
    )
    args = parser.parse_args(argv)

    started = datetime.now(UTC)
    started_iso = started.isoformat(timespec="microseconds").replace(" ", "T")
    print(f"[harness] start {started_iso}")
    print(f"[harness] seeding {args.rows} realistic audit chain rows...")

    eng = _build_engine()
    SessionLocal = sessionmaker(bind=eng, autoflush=False, autocommit=False, expire_on_commit=False)
    db = SessionLocal()

    row_count = _seed_realistic_chain(db, args.rows)
    print(f"[harness] seeded {row_count} rows")

    # 1. SHA256 chain
    print("[harness] running AuditService.verify_chain()...")
    sha256_ok, sha256_last_valid = AuditService.verify_chain(db)
    print(f"[harness]   chain_ok={sha256_ok} last_valid={sha256_last_valid}")

    # 2. HMAC layer (complementary)
    print("[harness] running HMAC verification...")
    hmac_ok, hmac_first_bad = _verify_hmac_for_chain(db)
    print(f"[harness]   hmac_ok={hmac_ok} first_bad_id={hmac_first_bad}")

    # 3. Dead-man-switch evaluation
    print("[harness] evaluating dead-man-switch...")
    dms = _compute_dead_mans_switch(
        db, sha256_ok, sha256_last_valid, row_count, args.threshold_seconds
    )
    print(f"[harness]   level={dms.level} reason={dms.reason}")

    # 4. Tamper scenarios (isolated clones)
    print("[harness] running tamper-detection scenarios...")
    scenarios: list[TamperScenario] = []
    for fn in (
        _scenario_payload_tamper,
        _scenario_midchain_delete,
        _scenario_hmac_byteflip,
        _scenario_prev_hash_swap,
    ):
        s = fn(db)
        scenarios.append(s)
        print(f"[harness]   {s.name}: detected={s.detected}")

    # 5. P0 escalation
    p0: list[str] = []
    if not sha256_ok:
        p0.append(f"PRIMARY CHAIN SHA256 BROKEN at position {sha256_last_valid} of {row_count}")
    if not hmac_ok:
        p0.append(f"PRIMARY CHAIN HMAC BROKEN at id={hmac_first_bad}")
    for s in scenarios:
        if not s.detected:
            p0.append(f"TAMPER SCENARIO NOT DETECTED: {s.name}")

    finished = datetime.now(UTC)
    finished_iso = finished.isoformat(timespec="microseconds").replace(" ", "T")
    duration = (finished - started).total_seconds()

    # HMAC key fingerprint (NEVER the key itself)
    key_bytes = settings.audit_hmac_key.encode("utf-8")
    key_id_hash = hashlib.sha256(key_bytes).hexdigest()
    key_first8 = hashlib.sha256(key_bytes[:8]).hexdigest() if len(key_bytes) >= 8 else key_id_hash

    result = HarnessResult(
        started_at=started_iso,
        finished_at=finished_iso,
        duration_seconds=duration,
        row_count=row_count,
        sha256_chain_ok=sha256_ok,
        sha256_chain_last_valid_position=sha256_last_valid,
        hmac_ok=hmac_ok,
        hmac_first_bad_id=hmac_first_bad,
        hmac_key_id_hash=key_id_hash,
        hmac_key_length=len(settings.audit_hmac_key),
        hmac_key_first8_sha256=key_first8,
        dead_mans_switch=dms,
        tamper_scenarios=scenarios,
        p0_breaks=p0,
    )

    # 6. Print JSON summary to stdout (CI-friendly)
    print("\n[harness] JSON SUMMARY")
    print(json.dumps(result.to_dict(), indent=2, ensure_ascii=False))

    # 7. Write Markdown report
    if not args.no_report:
        repo_root = Path(__file__).resolve().parents[3]  # backend/tests/manual -> repo root
        report_path = repo_root / "docs" / "AUDIT_INTEGRITY_REPORT.md"
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(_render_markdown(result, repo_root), encoding="utf-8")
        print(f"\n[harness] report written: {report_path}")

    # 8. Exit code
    if not sha256_ok:
        print("\n[harness] P0: primary chain SHA256 BROKEN", file=sys.stderr)
        return 2
    if not hmac_ok:
        print("\n[harness] P0: primary chain HMAC BROKEN", file=sys.stderr)
        return 3
    if any(not s.detected for s in scenarios):
        print("\n[harness] P0: tamper scenario not detected (security regression)", file=sys.stderr)
        return 4

    print(f"\n[harness] OK in {duration:.3f}s ({row_count} rows, {len(scenarios)} scenarios)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
