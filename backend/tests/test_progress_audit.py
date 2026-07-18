"""Tests for scripts/progress_audit.py (G8.16.T1).

The script lives at the repo root in ``scripts/progress_audit.py`` while
pytest is configured under ``backend/`` (``testpaths = ["tests"]``). We
import the module via ``sys.path`` injection so we can exercise the pure
functions directly without subprocess overhead.
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = REPO_ROOT / "scripts" / "progress_audit.py"

sys.path.insert(0, str(REPO_ROOT / "scripts"))  # noqa: E402
import progress_audit as pa  # type: ignore[import-not-found]  # noqa: E402


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def tmp_progress(tmp_path: Path) -> Path:
    p = tmp_path / "PROGRESS.md"
    p.write_text(
        "# PROGRESS.md\n\n> Auto-saved.\n\n---\n\n"
        "## 2026-07-10 — Wave 33 legacy block kept\n\n"
        "- **Honest count:** 9/100\n"
        "Modified by Gustavo Almeida — 2026-07-17T10:00:00+00:00\n",
        encoding="utf-8",
    )
    return p


@pytest.fixture()
def tmp_plano(tmp_path: Path) -> Path:
    p = tmp_path / "SUPER_PLANO_G8.md"
    p.write_text(
        "| G8.16.T1 | Task 1 | [x] | cartorio-sre |\n"
        "| G8.16.T2 | Task 2 | [x] | cartorio-dev |\n"
        "| G8.16.T3 | Task 3 | [ ] | cartorio-lgpd |\n"
        "| G8.16.T4 | Task 4 | [x] | cartorio-dev |\n",
        encoding="utf-8",
    )
    return p


# ---------------------------------------------------------------------------
# Pure-function tests (no filesystem mutation outside tmp_path)
# ---------------------------------------------------------------------------


def test_format_wave_block_from_args() -> None:
    entry = pa.ProgressEntry(
        date="2026-07-18",
        wave=46,
        agent="sre",
        honest_pre=50,
        honest_post=51,
        tests=5,
        bullets=[
            "**G8.16.T1** PROGRESS audit automation",
            "scripts/progress_audit.py + 5 tests",
            "Makefile target `progress-audit`",
        ],
        timestamp="2026-07-18T15:00:00+00:00",
    )
    out = entry.render()

    assert "## 2026-07-18 — Wave 46 REAL COMPLETED ✅ (cartorio-sre)" in out
    assert "- **Honest count:** 50 → **51/100** (+1)" in out
    assert "- **G8.16.T1** PROGRESS audit automation" in out
    assert "- **Tests:** 5 passed" in out
    assert out.rstrip().endswith("Modified by Gustavo Almeida — 2026-07-18T15:00:00+00:00")


def test_idempotent_update_replaces_block(tmp_progress: Path) -> None:
    """Running upsert_block twice with same wave replaces in place (no dupe)."""
    entry = pa.ProgressEntry(
        date="2026-07-18",
        wave=46,
        agent="sre",
        honest_pre=50,
        honest_post=51,
        tests=5,
        bullets=["first bullet"],
        timestamp="2026-07-18T15:00:00+00:00",
    )

    new_text_1 = pa.upsert_block(tmp_progress, entry)
    tmp_progress.write_text(new_text_1, encoding="utf-8")

    # Re-run with new bullets — should UPDATE the existing Wave 46 block, not append.
    entry.bullets = ["updated bullet"]
    new_text_2 = pa.upsert_block(tmp_progress, entry)
    tmp_progress.write_text(new_text_2, encoding="utf-8")

    wave_headers = re.findall(
        r"^## \d{4}-\d{2}-\d{2}\s+—\s+Wave (\d+)", new_text_2, flags=re.MULTILINE
    )
    assert wave_headers.count("46") == 1, f"expected exactly 1 Wave 46 header, got {wave_headers}"
    assert "updated bullet" in new_text_2
    assert "first bullet" not in new_text_2
    # Legacy block before should still be present.
    assert "## 2026-07-10 — Wave 33 legacy block kept" in new_text_2


def test_extract_honest_count_from_super_plano(tmp_plano: Path) -> None:
    done, total = pa.count_honest_checkmarks(tmp_plano)
    assert total == 4
    assert done == 3


def test_format_timestamp_brt() -> None:
    """now_brt_date must return a YYYY-MM-DD in BRT (UTC-3)."""
    brt = timezone(timedelta(hours=-3))
    expected = datetime.now(brt).strftime("%Y-%m-%d")
    assert pa.now_brt_date() == expected
    # now_iso must end with +00:00 (UTC)
    assert pa.now_iso().endswith("+00:00")


def test_dry_run_does_not_modify_file(
    tmp_progress: Path, tmp_plano: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    before = tmp_progress.read_text(encoding="utf-8")
    rc = pa.main(
        [
            "--wave",
            "46",
            "--date",
            "2026-07-18",
            "--agent",
            "sre",
            "--honest-pre",
            "50",
            "--honest-post",
            "51",
            "--tests",
            "5",
            "--bullet",
            "**G8.16.T1** dry-run smoke",
            "--plano",
            str(tmp_plano),
            "--file",
            str(tmp_progress),
            "--dry-run",
        ]
    )
    after = tmp_progress.read_text(encoding="utf-8")

    assert rc == 0
    assert before == after, "dry-run must not mutate PROGRESS.md"
    captured = capsys.readouterr()
    assert "## 2026-07-18 — Wave 46 REAL COMPLETED ✅ (cartorio-sre)" in captured.out
    assert "no write" in captured.err


def test_apply_writes_block_and_then_noop_on_second_run(
    tmp_progress: Path, tmp_plano: Path
) -> None:
    """--apply writes the file; a second --apply with same wave is idempotent (replaces)."""
    rc1 = pa.main(
        [
            "--wave",
            "46",
            "--date",
            "2026-07-18",
            "--agent",
            "sre",
            "--honest-pre",
            "50",
            "--honest-post",
            "51",
            "--tests",
            "5",
            "--bullet",
            "first run",
            "--plano",
            str(tmp_plano),
            "--file",
            str(tmp_progress),
            "--apply",
        ]
    )
    assert rc1 == 0
    txt1 = tmp_progress.read_text(encoding="utf-8")
    assert "first run" in txt1
    assert "## 2026-07-18 — Wave 46" in txt1

    rc2 = pa.main(
        [
            "--wave",
            "46",
            "--date",
            "2026-07-18",
            "--agent",
            "sre",
            "--honest-pre",
            "50",
            "--honest-post",
            "51",
            "--tests",
            "5",
            "--bullet",
            "second run replaces",
            "--plano",
            str(tmp_plano),
            "--file",
            str(tmp_progress),
            "--apply",
        ]
    )
    assert rc2 == 0
    txt2 = tmp_progress.read_text(encoding="utf-8")
    assert txt2.count("## 2026-07-18 — Wave 46") == 1
    assert "second run replaces" in txt2
    assert "first run" not in txt2


def test_cli_runs_as_subprocess(tmp_progress: Path) -> None:
    """End-to-end: invoke the script via python3 CLI in --dry-run mode."""
    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT_PATH),
            "--wave",
            "46",
            "--date",
            "2026-07-18",
            "--agent",
            "sre",
            "--tests",
            "5",
            "--bullet",
            "**G8.16.T1** CLI smoke",
            "--file",
            str(tmp_progress),
            "--dry-run",
        ],
        capture_output=True,
        text=True,
        check=True,
        env={**os.environ, "PYTHONPATH": str(REPO_ROOT / "scripts")},
    )
    assert "## 2026-07-18 — Wave 46 REAL COMPLETED ✅ (cartorio-sre)" in result.stdout
    assert "no write" in result.stderr
    assert tmp_progress.read_text(encoding="utf-8").count("## 2026-07-18 — Wave 46") == 0
