"""Testes do compose wrapper G8.23.T2 — Wave 52.

Cobre:
- Pipeline invokes literal_keys scanner.
- gitleaks é invocado apenas se o binário existir.
- Fail-fast interrompe no primeiro achado crítico.
- Exit 0 quando todos os scanners estão clean.
- Trufflehog opt-in (default off) e excluído quando binary ausente.
- Cache hash / cache hit / cache bypass.
- CLI parsing + JSON output.
- ScanResult dataclass (is_critical, render_text).
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

# Garante que scripts/ (raiz) esteja no path.
ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

import check_no_literal_keys_compose as cnlkc  # noqa: E402

SCRIPT_PATH = ROOT / "scripts" / "check_no_literal_keys_compose.py"


# ============================================================================
# Helpers.
# ============================================================================
def _run_cli(*args: str) -> subprocess.CompletedProcess[str]:
    """Executa o wrapper como subprocess (igual pre-commit faz)."""
    return subprocess.run(
        [sys.executable, str(SCRIPT_PATH), *args],
        capture_output=True,
        text=True,
        cwd=str(ROOT),
        timeout=60,
    )


# ============================================================================
# Test: invocation contract.
# ============================================================================
def test_main_invokes_literal_keys(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """literal_keys deve sempre rodar (não tem dependência binária)."""
    captured: list[list[str]] = []

    def fake_run(cmd, *args, **kwargs):  # type: ignore[no-untyped-def]
        captured.append(cmd)

        # Return success for the literal_keys invocation.
        class _R:
            returncode = 0
            stdout = "OK"
            stderr = ""

        return _R()

    monkeypatch.setattr(cnlkc.subprocess, "run", fake_run)
    rc = cnlkc.main(["--no-cache", "--scanner", "literal_keys"])
    assert rc == 0
    assert len(captured) == 1
    cmd = captured[0]
    assert cmd[0] == sys.executable
    assert "check_no_literal_keys.py" in cmd[1]
    assert "--severity" in cmd
    assert "low" in cmd


def test_main_invokes_gitleaks_if_available(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """gitleaks entra na pipeline quando shutil.which retorna path."""
    monkeypatch.setattr(
        cnlkc.shutil, "which", lambda n: f"/usr/bin/{n}" if n == "gitleaks" else None
    )
    captured: list[list[str]] = []

    def fake_run(cmd, *args, **kwargs):  # type: ignore[no-untyped-def]
        captured.append(cmd)

        class _R:
            returncode = 0
            stdout = ""
            stderr = ""

        return _R()

    monkeypatch.setattr(cnlkc.subprocess, "run", fake_run)
    rc = cnlkc.main(["--no-cache", "--scanner", "literal_keys", "--scanner", "gitleaks"])
    assert rc == 0
    assert len(captured) == 2
    assert captured[1][0] == "gitleaks"


def test_main_skips_gitleaks_when_not_installed(monkeypatch: pytest.MonkeyPatch) -> None:
    """gitleaks ausente → status=skipped, rc=0, não bloqueia."""
    monkeypatch.setattr(cnlkc.shutil, "which", lambda n: None)
    rc = cnlkc.main(["--no-cache", "--scanner", "gitleaks"])
    assert rc == 0


def test_main_fails_fast_on_first_critical(monkeypatch: pytest.MonkeyPatch) -> None:
    """Quando literal_keys viola, gitleaks NÃO é invocado (fail-fast)."""
    invocations: list[str] = []

    def fake_run(cmd, *args, **kwargs):  # type: ignore[no-untyped-def]
        invocations.append(Path(cmd[1]).name if len(cmd) > 1 else cmd[0])

        class _R:
            returncode = 1
            stdout = "VIOLATION: sk-proj-FAKE\n"
            stderr = ""

        return _R()

    monkeypatch.setattr(cnlkc.subprocess, "run", fake_run)
    monkeypatch.setattr(cnlkc.shutil, "which", lambda n: f"/usr/bin/{n}")
    rc = cnlkc.main(
        [
            "--no-cache",
            "--scanner",
            "literal_keys",
            "--scanner",
            "gitleaks",
        ]
    )
    assert rc == 1
    assert invocations == ["check_no_literal_keys.py"]  # gitleaks nunca rodou


def test_main_runs_everything_with_no_fail_fast(monkeypatch: pytest.MonkeyPatch) -> None:
    """--no-fail-fast mantém a pipeline completa mesmo após critical."""
    invocations: list[str] = []

    def fake_run(cmd, *args, **kwargs):  # type: ignore[no-untyped-def]
        # Use cmd[0] (program name) — for python invocations, this is sys.executable.
        # For gitleaks, cmd[0] is "gitleaks".
        invocations.append(cmd[0])
        if cmd[0] == "gitleaks":
            return _R(0, "", "")
        return _R(1, "VIOLATION\n", "")

    class _R:
        def __init__(self, rc: int, out: str, err: str) -> None:
            self.returncode = rc
            self.stdout = out
            self.stderr = err

    monkeypatch.setattr(cnlkc.subprocess, "run", fake_run)
    monkeypatch.setattr(cnlkc.shutil, "which", lambda n: f"/usr/bin/{n}")
    rc = cnlkc.main(
        [
            "--no-cache",
            "--scanner",
            "literal_keys",
            "--scanner",
            "gitleaks",
            "--no-fail-fast",
        ]
    )
    assert rc == 1  # literal_keys failed → critical
    assert invocations == [sys.executable, "gitleaks"]


def test_main_returns_0_when_clean(monkeypatch: pytest.MonkeyPatch) -> None:
    """Todos os scanners rc=0 → exit 0."""

    def fake_run(cmd, *args, **kwargs):  # type: ignore[no-untyped-def]
        class _R:
            returncode = 0
            stdout = "OK"
            stderr = ""

        return _R()

    monkeypatch.setattr(cnlkc.subprocess, "run", fake_run)
    monkeypatch.setattr(cnlkc.shutil, "which", lambda n: f"/usr/bin/{n}")
    rc = cnlkc.main(
        [
            "--no-cache",
            "--scanner",
            "literal_keys",
            "--scanner",
            "gitleaks",
        ]
    )
    assert rc == 0


# ============================================================================
# Test: CLI parsing.
# ============================================================================
def test_cli_severity_is_forwarded_to_literal_keys(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """--severity critical deve aparecer no comando literal_keys."""
    captured: list[list[str]] = []

    def fake_run(cmd, *args, **kwargs):  # type: ignore[no-untyped-def]
        captured.append(cmd)

        class _R:
            returncode = 0
            stdout = ""
            stderr = ""

        return _R()

    monkeypatch.setattr(cnlkc.subprocess, "run", fake_run)
    cnlkc.main(["--no-cache", "--severity", "critical", "--scanner", "literal_keys"])
    cmd = captured[0]
    assert "--severity" in cmd
    assert "critical" in cmd


def test_cli_report_only_is_forwarded(monkeypatch: pytest.MonkeyPatch) -> None:
    """--report-only deve propagar ao literal_keys (cmd contains flag)."""
    captured: list[list[str]] = []

    class _R:
        def __init__(self, rc: int, out: str, err: str) -> None:
            self.returncode = rc
            self.stdout = out
            self.stderr = err

    def fake_run(cmd, *args, **kwargs):  # type: ignore[no-untyped-def]
        captured.append(cmd)
        # Real literal_keys --report-only retorna 0 mesmo com achados.
        return _R(0, "REPORT\n", "")

    monkeypatch.setattr(cnlkc.subprocess, "run", fake_run)
    rc = cnlkc.main(
        [
            "--no-cache",
            "--scanner",
            "literal_keys",
            "--report-only",
        ]
    )
    assert rc == 0
    assert "--report-only" in captured[0]


def test_cli_default_scanners_excludes_trufflehog() -> None:
    """Default NÃO inclui trufflehog (lento, opt-in)."""
    args = cnlkc.parse_args([])
    assert "trufflehog" not in args.scanners
    assert "literal_keys" in args.scanners
    assert "gitleaks" in args.scanners


def test_cli_json_output_is_machine_readable(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """--json imprime array parseável."""
    monkeypatch.setattr(cnlkc.shutil, "which", lambda n: None)

    def fake_run(cmd, *args, **kwargs):  # type: ignore[no-untyped-def]
        class _R:
            returncode = 0
            stdout = "OK"
            stderr = ""

        return _R()

    monkeypatch.setattr(cnlkc.subprocess, "run", fake_run)
    rc = cnlkc.main(["--no-cache", "--scanner", "literal_keys", "--json"])
    out = capsys.readouterr().out
    assert rc == 0
    payload = json.loads(out)
    assert isinstance(payload, list)
    assert payload[0]["name"] == "literal_keys"
    assert payload[0]["status"] == "ok"
    assert "stdout" not in payload[0]
    assert "stderr" not in payload[0]


# ============================================================================
# Test: ScanResult dataclass.
# ============================================================================
def test_scan_result_is_critical_for_violation() -> None:
    r = cnlkc.ScanResult(name="x", status="violation", returncode=1)
    assert r.is_critical is True


def test_scan_result_is_critical_for_error() -> None:
    r = cnlkc.ScanResult(name="x", status="error", returncode=2)
    assert r.is_critical is True


def test_scan_result_not_critical_for_ok() -> None:
    r = cnlkc.ScanResult(name="x", status="ok", returncode=0)
    assert r.is_critical is False


def test_scan_result_not_critical_for_skipped() -> None:
    r = cnlkc.ScanResult(name="x", status="skipped", returncode=0, skipped_reason="no")
    assert r.is_critical is False


def test_render_text_clean_summary() -> None:
    results = [
        cnlkc.ScanResult(name="literal_keys", status="ok", returncode=0, duration_ms=120),
        cnlkc.ScanResult(
            name="gitleaks",
            status="skipped",
            returncode=0,
            skipped_reason="not installed",
        ),
    ]
    text = cnlkc.render_text(results)
    assert "OK" in text
    assert "SKIP" in text
    assert "All 1 scanner(s) clean" in text


def test_render_text_failure_summary() -> None:
    results = [
        cnlkc.ScanResult(
            name="literal_keys",
            status="violation",
            returncode=1,
            stdout="VIOLATION: sk-proj-FAKE",
        ),
    ]
    text = cnlkc.render_text(results)
    assert "FAIL" in text
    assert "scanner(s) flagged critical findings" in text
    assert "diagnostics redacted" in text
    assert "sk-proj-FAKE" not in text


# ============================================================================
# Test: Cache contract.
# ============================================================================
def test_cache_key_changes_with_severity() -> None:
    args_low = cnlkc.parse_args(["--severity", "low", "--all-files"])
    args_high = cnlkc.parse_args(["--severity", "critical", "--all-files"])
    assert cnlkc._cache_key(args_low) != cnlkc._cache_key(args_high)


def test_cache_read_returns_none_when_missing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(cnlkc, "CACHE_DIR", tmp_path / "cache")
    assert cnlkc._read_cache("missing", ttl=60) is None


def test_cache_round_trip_excludes_diagnostic_output(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(cnlkc, "CACHE_DIR", tmp_path / "cache")
    results = [
        cnlkc.ScanResult(
            name="literal_keys",
            status="ok",
            returncode=0,
            stdout="scanner diagnostic that must not persist",
            stderr="another diagnostic that must not persist",
            findings=[{"match": "must not persist"}],
        ),
    ]
    key = "abc123"
    cnlkc._write_cache(key, results)
    cached_payload = (tmp_path / "cache" / f"v2-{key}.json").read_text(encoding="utf-8")
    assert "diagnostic" not in cached_payload
    assert "must not persist" not in cached_payload
    out = cnlkc._read_cache(key, ttl=60)
    assert out is not None
    assert out[0].name == "literal_keys"
    assert out[0].stdout == ""
    assert out[0].stderr == ""
    assert out[0].findings == []


def test_cache_expires_after_ttl(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """TTL expirado → cache miss."""
    monkeypatch.setattr(cnlkc, "CACHE_DIR", tmp_path / "cache")
    results = [cnlkc.ScanResult(name="x", status="ok", returncode=0)]
    cnlkc._write_cache("k", results)
    cache_file = tmp_path / "cache" / "v2-k.json"
    import os
    import time

    old_time = time.time() - 7200
    os.utime(cache_file, (old_time, old_time))
    assert cnlkc._read_cache("k", ttl=60) is None


def test_clear_cache_wipes_directory(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """--clear-cache deve apagar o diretório."""
    cache = tmp_path / "cache"
    cache.mkdir()
    (cache / "stale.json").write_text("{}")
    monkeypatch.setattr(cnlkc, "CACHE_DIR", cache)
    monkeypatch.setattr(cnlkc.shutil, "which", lambda n: None)

    def fake_run(cmd, *args, **kwargs):  # type: ignore[no-untyped-def]
        class _R:
            returncode = 0
            stdout = ""
            stderr = ""

        return _R()

    monkeypatch.setattr(cnlkc.subprocess, "run", fake_run)
    cnlkc.main(["--no-cache", "--clear-cache", "--scanner", "literal_keys"])
    assert not (cache / "stale.json").exists()


def test_cache_does_not_reuse_legacy_diagnostic_entry(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Legacy files remain local but are never loaded by the hardened cache."""
    cache = tmp_path / "cache"
    cache.mkdir()
    (cache / "legacy.json").write_text(
        json.dumps([{"stdout": "legacy diagnostic", "returncode": 0}]), encoding="utf-8"
    )
    monkeypatch.setattr(cnlkc, "CACHE_DIR", cache)

    assert cnlkc._read_cache("legacy", ttl=60) is None
    assert (cache / "legacy.json").exists()


# ============================================================================
# Test: Tool detection.
# ============================================================================
def test_tool_exists_detects_binary(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(cnlkc.shutil, "which", lambda n: "/usr/bin/foo" if n == "foo" else None)
    assert cnlkc._tool_exists("foo") is True
    assert cnlkc._tool_exists("missing") is False


# ============================================================================
# Test: Trufflehog excludes noisy paths.
# ============================================================================
def test_trufflehog_excludes_venv(monkeypatch: pytest.MonkeyPatch) -> None:
    """trufflehog command deve trazer --exclude-paths para venvs."""
    monkeypatch.setattr(
        cnlkc.shutil, "which", lambda n: "/usr/bin/trufflehog" if n == "trufflehog" else None
    )
    captured: list[list[str]] = []

    def fake_run(cmd, *args, **kwargs):  # type: ignore[no-untyped-def]
        captured.append(cmd)

        class _R:
            returncode = 0
            stdout = ""
            stderr = ""

        return _R()

    monkeypatch.setattr(cnlkc.subprocess, "run", fake_run)
    args = cnlkc.parse_args(["--scanner", "trufflehog"])
    args.all_files = True
    result = cnlkc.run_trufflehog(args)
    assert result.status == "ok"
    cmd = captured[0]
    assert "--exclude-paths" in cmd
    assert ".venv" in cmd
    assert "trae-agent/.venv" in cmd


def test_trufflehog_skipped_when_no_binary(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(cnlkc.shutil, "which", lambda n: None)
    args = cnlkc.parse_args(["--scanner", "trufflehog"])
    result = cnlkc.run_trufflehog(args)
    assert result.status == "skipped"
    assert "not installed" in result.skipped_reason


# ============================================================================
# Test: Real subprocess smoke test (no cache, fast).
# ============================================================================
def test_cli_smoke_clean_repo_returns_zero() -> None:
    """Smoke test end-to-end: repo está clean, exit 0."""
    proc = _run_cli("--no-cache")
    assert "All 2 scanner(s) clean" in proc.stdout or "All 1 scanner(s) clean" in proc.stdout
    assert proc.returncode == 0
