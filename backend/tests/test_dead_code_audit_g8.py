"""G8.12.T4 — Testes do dead_code_audit script.

Cobre (3 testes minimos exigidos pela task + 3 extras):

- ``test_script_runs_and_produces_json``: roda o script, espera exit 0 + .json criado
- ``test_json_has_required_keys``: relatorio tem secoes esperadas
- ``test_audit_is_idempotent``: rodar 2x produz mesmo output estrutural (cache)
- ``test_summary_has_clean_flags``: chaves ruff_clean/pyflakes_clean booleanas OK
- ``test_top_candidates_lists_orphans``: zero-coverage modules identificados
- ``test_no_cache_bypasses_ttl``: --no-cache regenera arquivo

Modified by Gustavo Almeida — G8 Wave 45 / Squad 12 (cartorio-dev).
"""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "dead_code_audit.py"
BACKEND = ROOT / "backend"
DEFAULT_REPORT = ROOT / "docs" / "DEAD_CODE_AUDIT_2026-07-18.json"


def _load_module():
    """Importa dead_code_audit.py dinamicamente."""
    spec = importlib.util.spec_from_file_location("dead_code_audit", SCRIPT)
    assert spec is not None and spec.loader is not None
    if "dead_code_audit" in sys.modules:
        del sys.modules["dead_code_audit"]
    mod = importlib.util.module_from_spec(spec)
    sys.modules["dead_code_audit"] = mod
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def mod():
    return _load_module()


def _run_script(*extra_args: str, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    """Executa dead_code_audit.py via subprocess (mesmo caminho que CI fara)."""
    return subprocess.run(
        ["python3", str(SCRIPT), *extra_args],
        capture_output=True,
        text=True,
        timeout=600,
        cwd=cwd or str(ROOT),
    )


def test_script_runs_and_produces_json(mod):
    """Roda o script, espera exit 0 + .json criado."""
    proc = _run_script("--no-cache")
    assert proc.returncode == 0, (
        f"dead_code_audit exited {proc.returncode}\n"
        f"STDOUT: {proc.stdout[-1500:]}\n"
        f"STDERR: {proc.stderr[-1500:]}"
    )
    expected = ROOT / "docs" / f"DEAD_CODE_AUDIT_{mod.RUN_DATE}.json"
    assert expected.exists(), f"Report JSON nao criado em {expected}"
    assert expected.stat().st_size > 0, "Report JSON vazio"


def test_json_has_required_keys(mod):
    """Relatorio tem secoes esperadas."""
    expected = ROOT / "docs" / f"DEAD_CODE_AUDIT_{mod.RUN_DATE}.json"
    payload = json.loads(expected.read_text())
    for required in (
        "_meta",
        "summary",
        "results",
        "top_candidates_hitl",
    ):
        assert required in payload, f"missing key: {required}"
    assert payload["_meta"]["task_id"] == "G8.12.T4"
    assert payload["_meta"]["policy"].startswith("NUNCA remove codigo")
    for tool_key in ("ruff_unused", "pyflakes", "vulture", "coverage_gaps"):
        assert tool_key in payload["results"], f"missing results.{tool_key}"
        assert "count" in payload["results"][tool_key] or "files" in payload["results"][tool_key]


def test_audit_is_idempotent(mod):
    """Rodar 2x (segunda usa cache) produz mesmo output estrutural."""
    proc_a = _run_script("--no-cache")
    assert proc_a.returncode == 0, f"first run failed: {proc_a.stderr}"
    proc_b = _run_script()  # uses cache
    assert proc_b.returncode == 0, f"second run failed: {proc_b.stderr}"
    assert "[cache]" in proc_b.stdout, "second run deveria usar cache"
    # Apenas proc_b escreve no disco (cache hit). Logo a versao final do JSON
    # reflete o estado apos cache hit, com _cache_hit=True.
    payload_b = json.loads(_read_report(mod))
    assert payload_b.get("_cache_hit", False) is True
    # A primeira run (proc_a) NAO emitiu "[cache]" — confirmacao de cold start
    assert "[cache]" not in proc_a.stdout
    # Estrutura estavel entre as duas runs
    for key in ("summary", "results", "top_candidates_hitl"):
        assert key in payload_b


def test_summary_has_clean_flags(mod):
    """Chaves ruff_clean/pyflakes_clean sao booleanas validas."""
    payload = json.loads(_read_report(mod))
    summary = payload["summary"]
    for key in ("ruff_clean", "pyflakes_clean", "vulture_clean"):
        assert key in summary, f"missing summary key {key}"
        assert isinstance(summary[key], bool), f"{key} nao e bool"
    # ruff DEVE estar clean (gate CI)
    assert summary["ruff_clean"] is True, "ruff F401/F841 deveria estar clean"
    # pyflakes clean
    assert summary["pyflakes_clean"] is True


def test_top_candidates_lists_orphans(mod):
    """Wave 46 fix: Zero-coverage modules sao identificados em top_candidates_hitl.

    Após G8.13.T4 + G8.15.T1/T2, varios routers agora aparecem como zero-coverage.
    Aceitamos qualquer orphan_module (>=1) — Top 10 do audit pega os piores.
    """
    payload = json.loads(_read_report(mod))
    candidates = payload["top_candidates_hitl"]
    orphan_kinds = [c for c in candidates if c.get("kind") == "orphan_module"]
    # Pelo menos 1 orphan_module sempre esperado — listagem é top-10
    assert len(orphan_kinds) >= 1, f"esperado >= 1 orphan_module, got {candidates}"
    files = {c["file"] for c in orphan_kinds}
    # Verifica que SÃO módulos do app/ (sanity)
    for f in files:
        assert f.startswith("app/"), f"orphan inesperado fora de app/: {f}"


def test_no_cache_bypasses_ttl(mod):
    """--no-cache regenera arquivo independente do TTL."""
    proc = _run_script("--no-cache")
    assert proc.returncode == 0
    payload = json.loads(_read_report(mod))
    assert payload.get("_cache_hit") is False, "_cache_hit deveria ser False apos --no-cache"


def test_coverage_collection_does_not_recurse_into_its_own_test() -> None:
    """O subprocesso de coverage nao pode chamar novamente este teste."""
    source = SCRIPT.read_text()
    assert "--ignore=tests/test_dead_code_audit_g8.py" in source


def _read_report(mod) -> str:
    p = ROOT / "docs" / f"DEAD_CODE_AUDIT_{mod.RUN_DATE}.json"
    return p.read_text()
