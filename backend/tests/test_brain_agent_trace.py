"""Security contract for the private, chained BRAIN agent ledger."""

from __future__ import annotations

import json
import stat
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.brain_agent_trace import append_trace  # noqa: E402


def _append(ledger: Path, *, agent: str = "cartorio-lgpd", notes: str = "safe") -> dict:
    return append_trace(
        agent=agent,
        action="review",
        gate="T3",
        result="ok",
        evidence_ref="gate:T3",
        notes=notes,
        ledger_path=ledger,
    )


def test_trace_is_hash_chained_and_owner_only(tmp_path: Path) -> None:
    ledger = tmp_path / "private" / "agent-trace.jsonl"
    first = _append(ledger)
    second = _append(ledger, agent="codex-root")

    assert first["previous_hash"] == "0" * 64
    assert second["previous_hash"] == first["record_sha256"]
    assert stat.S_IMODE(ledger.parent.stat().st_mode) == 0o700
    assert stat.S_IMODE(ledger.stat().st_mode) == 0o600
    assert stat.S_IMODE(ledger.with_name(".agent-trace.jsonl.lock").stat().st_mode) == 0o600


def test_trace_rejects_tampered_chain(tmp_path: Path) -> None:
    ledger = tmp_path / "private" / "agent-trace.jsonl"
    _append(ledger)
    record = json.loads(ledger.read_text(encoding="utf-8"))
    record["result"] = "tampered"
    ledger.write_text(json.dumps(record) + "\n", encoding="utf-8")

    with pytest.raises(ValueError, match="hash inválido"):
        _append(ledger)


@pytest.mark.parametrize(
    "unsafe",
    [
        "(34) 99999-0000",
        "12.345.678/0001-00",
        "RG 12.345.678",
        "38400-000",
        "/private/customer/source.docx",
        "4/0AXXXXXXXXXXXXXXXXXXXXXXXXXXXXX",
    ],
)
def test_trace_rejects_pii_paths_and_secrets(tmp_path: Path, unsafe: str) -> None:
    ledger = tmp_path / "private" / "agent-trace.jsonl"
    with pytest.raises(ValueError):
        _append(ledger, notes=unsafe)


def test_trace_accepts_only_real_agent_allowlist(tmp_path: Path) -> None:
    ledger = tmp_path / "private" / "agent-trace.jsonl"
    for agent in ("cartorio-documentos", "cartorio-dev", "cartorio-lgpd", "codex-root"):
        _append(ledger, agent=agent)
    with pytest.raises(ValueError, match="allowlist"):
        _append(ledger, agent="grok")


def test_trace_lock_serializes_concurrent_appends(tmp_path: Path) -> None:
    ledger = tmp_path / "private" / "agent-trace.jsonl"
    with ThreadPoolExecutor(max_workers=4) as pool:
        records = list(pool.map(lambda _: _append(ledger), range(12)))

    persisted = [json.loads(line) for line in ledger.read_text(encoding="utf-8").splitlines()]
    assert len(records) == len(persisted) == 12
    assert persisted[0]["previous_hash"] == "0" * 64
    assert all(
        current["previous_hash"] == previous["record_sha256"]
        for previous, current in zip(persisted, persisted[1:], strict=False)
    )


def test_trace_rejects_arbitrary_evidence_path(tmp_path: Path) -> None:
    ledger = tmp_path / "private" / "agent-trace.jsonl"
    with pytest.raises(ValueError, match="referência opaca"):
        append_trace(
            agent="cartorio-lgpd",
            action="review",
            gate="T3",
            result="ok",
            evidence_ref="raw/customer-name.docx",
            ledger_path=ledger,
        )


def test_trace_accepts_sha256_opaco_mesmo_com_sequencia_numerica(tmp_path: Path) -> None:
    ledger = tmp_path / "private" / "agent-trace.jsonl"
    record = append_trace(
        agent="cartorio-documentos",
        action="inventory",
        gate="T1",
        result="ok",
        evidence_ref="sha256:" + "0123456789" * 6 + "0123",
        ledger_path=ledger,
    )
    assert str(record["evidence_ref"]).startswith("sha256:")
