"""Dead code audit — gera relatorio consolidado de dead code em backend/app/.

HITL: NUNCA remove codigo. Apenas reporta.

Ferramentas consolidadas:
  - ruff check --select F401,F841   (unused imports + unused vars)
  - pyflakes app/                   (broad unused import/variable scan)
  - vulture app/ --min-confidence N (unused functions/classes, unreachable code)
  - coverage report --skip-covered   (arquivos < 100% cobertura)

Outputs:
  - docs/DEAD_CODE_AUDIT_<date>.json  (raw data)
  - stdout summary

Cache:
  - Se docs/DEAD_CODE_AUDIT_<date>.json existe e foi criado ha < CACHE_TTL_SEC,
    re-imprime em vez de re-rodar linters (--no-cache bypassa).

Usage:
  python3 scripts/dead_code_audit.py                # roda tudo, cache 1h
  python3 scripts/dead_code_audit.py --no-cache     # bypassa cache
  python3 scripts/dead_code_audit.py --vulture-min 90  # vulture mais estrito

Modified by Gustavo Almeida + cartorio-dev - G8.12.T4 (2026-07-18).
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
BACKEND_DIR = REPO_ROOT / "backend"
APP_DIR = BACKEND_DIR / "app"
DOCS_DIR = REPO_ROOT / "docs"

CACHE_TTL_SEC = 3600  # 1h
LINTER_TIMEOUT_SEC = 60
RUN_DATE = datetime.now(timezone.utc).strftime("%Y-%m-%d")
DEFAULT_REPORT_PATH = DOCS_DIR / f"DEAD_CODE_AUDIT_{RUN_DATE}.json"

# IGNORE files that vulture flag falso-positivo porque nao entende framework
# (FastAPI endpoints, Pydantic ConfigDict etc). Auditoria reportara mas
# HITL reviewer pode cruzar com main.py / router includes.
FALSE_POSITIVE_GLOBS = (
    "app/audit*",  # audit chain - G8 P0 cartorio-lgpd
    "app/pii.py",  # PII service - G8 P0 cartorio-lgpd
    "app/audit_context.py",
)

# Locais onde existe cobertura 100% no test suite - cobertura coverage gaps
# nao sao dead code, apenas funcoes utilitarias ainda nao exercitadas.
PROTECTED_COVERAGE_THRESHOLD = 100.0


def _is_protected(path: Path) -> bool:
    rel = path.relative_to(BACKEND_DIR).as_posix()
    return any(rel.startswith(p.replace("*", "")) for p in FALSE_POSITIVE_GLOBS)


def run_subprocess(
    args: list[str], timeout: int = LINTER_TIMEOUT_SEC, cwd: Path | None = None
) -> subprocess.CompletedProcess[str]:
    """Run subprocess com timeout duro e tratamento de erro estruturado."""
    try:
        return subprocess.run(
            args,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=cwd or BACKEND_DIR,
            check=False,
        )
    except subprocess.TimeoutExpired as e:
        return subprocess.CompletedProcess(
            args=args,
            returncode=-1,
            stdout="",
            stderr=f"TIMEOUT after {e.timeout}s",
        )
    except FileNotFoundError as e:
        return subprocess.CompletedProcess(
            args=args,
            returncode=-1,
            stdout="",
            stderr=f"EXECUTABLE NOT FOUND: {e}",
        )


def run_ruff_unused() -> dict[str, Any]:
    """Ruff F401 (unused import) + F841 (unused variable local)."""
    out = run_subprocess(
        [
            "uv",
            "run",
            "ruff",
            "check",
            "--select",
            "F401,F841",
            "app/",
            "--output-format",
            "json",
        ],
    )
    findings: list[dict[str, Any]] = []
    if out.stdout.strip():
        try:
            findings = json.loads(out.stdout)
        except json.JSONDecodeError:
            findings = []
    return {
        "tool": "ruff",
        "rules": "F401,F841",
        "returncode": out.returncode,
        "stderr": out.stderr.strip(),
        "findings": findings,
        "count": len(findings),
    }


def run_pyflakes() -> dict[str, Any]:
    """Pyflakes - deteccao ampla de undefined/unused."""
    out = run_subprocess(
        ["uv", "run", "python", "-m", "pyflakes", "app/"],
        timeout=120,
    )
    lines = [ln for ln in out.stdout.splitlines() if ln.strip()]
    findings = []
    for line in lines:
        m = re.match(
            r"^(.+?):(\d+):\d+\s+('[^']+'\s+(?:imported|local variable|may be unused|defined but not used|shadowing)[^']*)$",
            line,
        )
        if m:
            findings.append(
                {
                    "file": m.group(1),
                    "line": int(m.group(2)),
                    "message": m.group(3).strip(),
                }
            )
    return {
        "tool": "pyflakes",
        "returncode": out.returncode,
        "stderr": out.stderr.strip(),
        "findings": findings,
        "raw_lines": lines,
        "count": len(findings),
    }


def run_vulture(min_confidence: int = 80) -> dict[str, Any]:
    """Vulture - detecta funcoes/classes nao usadas e branches inalcancaveis."""
    out = run_subprocess(
        [
            "uv",
            "run",
            "vulture",
            "app/",
            "--min-confidence",
            str(min_confidence),
        ],
        timeout=180,
    )
    lines = [ln for ln in out.stdout.splitlines() if ln.strip()]
    findings = []
    for line in lines:
        # vulture format: path:line: message
        m = re.match(
            r"^(.+?):(\d+):\s+(unused [^']+?)(?:\s+\((\d+)%\s+confidence\))?$", line
        )
        if m:
            findings.append(
                {
                    "file": m.group(1),
                    "line": int(m.group(2)),
                    "message": m.group(3).strip(),
                    "confidence": int(m.group(4) or min_confidence),
                }
            )
        else:
            findings.append({"raw": line})
    return {
        "tool": "vulture",
        "min_confidence": min_confidence,
        "returncode": out.returncode,
        "stderr": out.stderr.strip(),
        "findings": findings,
        "raw_lines": lines,
        "count": len(findings),
    }


def run_coverage_gaps() -> dict[str, Any]:
    """Carrega .coverage existente e lista arquivos com cobertura < 100%.

    Lida com 2 cenarios:
      1. .coverage existe: parse sqlite para identificar arquivos uncovered.
      2. .coverage nao existe: roda pytest --cov --override-ini addopts=--cov=app
         SEM coverage gate (--cov-fail-under=0) para gerar dados.
    """
    coverage_file = BACKEND_DIR / ".coverage"
    if not coverage_file.exists():
        # Fall back: roda test suite com cov mas SEM gate
        out = run_subprocess(
            [
                "uv",
                "run",
                "pytest",
                "tests/",
                "-q",
                "--ignore=tests/test_dead_code_audit_g8.py",
                "--override-ini=addopts=--cov=app --cov-report= -m 'not smoke and not integration and not e2e'",
            ],
            timeout=600,
        )
        return {
            "tool": "coverage",
            "coverage_data_present": False,
            "pytest_invoked": True,
            "pytest_returncode": out.returncode,
            "pytest_stderr_tail": (out.stderr or "")[-500:],
            "files": [],
            "total_uncovered_files": 0,
        }

    # Parse .coverage via coverage json (renamed from old --format=json)
    cov_json_path = BACKEND_DIR / "coverage_audit_temp.json"
    cov_out = run_subprocess(
        [
            "uv",
            "run",
            "coverage",
            "json",
            "--data-file=.coverage",
            "--omit=app/api/v1/whatsapp.py,app/api/v1/telegram.py,app/api/v2/*,app/integrations/*,app/core/*,app/services/cartorio_agent.py,app/services/chat_pipeline.py,app/services/chatwoot_handoff.py",
            "-o",
            "coverage_audit_temp.json",
        ],
        timeout=60,
    )
    files: list[dict[str, Any]] = []
    if cov_json_path.exists():
        try:
            data = json.loads(cov_json_path.read_text())
            for fname, f_info in data.get("files", {}).items():
                summary = f_info.get("summary", {})
                pct_covered = summary.get("percent_covered", 0.0)
                files.append(
                    {
                        "file": fname,
                        "summary_pct": round(pct_covered, 2),
                        "statements": summary.get("num_statements", 0),
                        "missing_lines": summary.get("missing_lines", []),
                        "excluded_lines": summary.get("excluded_lines", []),
                    }
                )
        except (json.JSONDecodeError, OSError):
            pass
        finally:
            try:
                cov_json_path.unlink()
            except OSError:
                pass
    return {
        "tool": "coverage",
        "coverage_data_present": True,
        "coverage_json_returncode": cov_out.returncode,
        "files": files,
        "total_uncovered_files": sum(
            1 for f in files if f["summary_pct"] < PROTECTED_COVERAGE_THRESHOLD
        ),
        "total_zero_coverage_files": sum(1 for f in files if f["summary_pct"] == 0.0),
    }
    return {
        "tool": "coverage",
        "coverage_data_present": True,
        "files": files,
        "total_uncovered_files": sum(
            1 for f in files if f["summary_pct"] < PROTECTED_COVERAGE_THRESHOLD
        ),
        "total_zero_coverage_files": sum(1 for f in files if f["summary_pct"] == 0.0),
    }


def collect_summary(results: dict[str, Any]) -> dict[str, Any]:
    return {
        "unused_imports": results["ruff_unused"].get("count", 0),
        "ruff_total": results["ruff_unused"].get("count", 0),
        "pyflakes_total": results["pyflakes"].get("count", 0),
        "vulture_suspicions": results["vulture"].get("count", 0),
        "vulture_min_confidence": results["vulture"].get("min_confidence", 80),
        "uncovered_files": results["coverage_gaps"].get("total_uncovered_files", 0),
        "zero_coverage_files": results["coverage_gaps"].get(
            "total_zero_coverage_files", 0
        ),
        "ruff_clean": results["ruff_unused"]["count"] == 0,
        "pyflakes_clean": results["pyflakes"]["count"] == 0,
        "vulture_clean": results["vulture"]["count"] == 0,
    }


def select_top_candidates(
    results: dict[str, Any], limit: int = 10
) -> list[dict[str, Any]]:
    """Seleciona top-N achados por severidade para revisao humana HITL.

    Score: zero_coverage > vulture > pyflakes > ruff.
    """
    candidates: list[tuple[int, dict[str, Any]]] = []

    # Zero-coverage files (orphan modules): highest priority
    for f in results["coverage_gaps"].get("files", []):
        if f["summary_pct"] == 0.0:
            candidates.append(
                (
                    100,
                    {
                        "kind": "orphan_module",
                        "file": f["file"],
                        "stmts": f["statements"],
                        "missing_lines": f.get("missing_lines", []),
                        "note": "Zero test coverage. Check se esta registrado no main.py / router includes. Pode ser orfao.",
                    },
                )
            )

    # Vulture functions (unreachable or unused symbols)
    for v in results["vulture"].get("findings", []):
        if "file" not in v:
            continue
        if _is_protected(Path(v["file"])):
            continue
        score = v.get("confidence", 80)
        if "unreachable" in v.get("message", "").lower():
            kind = "unreachable"
            score = 95
        elif "unused variable" in v.get("message", "").lower():
            kind = "unused_variable"
            score = 60  # Often stylistic (__exit__ signature)
        elif "unused function" in v.get("message", "").lower():
            kind = "unused_function"
            score = 85  # Likely FastAPI endpoint - flag but don't auto-remove
        elif "unused" in v.get("message", "").lower():
            kind = "unused_class_or_import"
            score = 80
        else:
            kind = "vulture_other"
        candidates.append(
            (
                score,
                {
                    "kind": kind,
                    "file": v["file"],
                    "line": v.get("line"),
                    "message": v.get("message"),
                    "confidence": v.get("confidence"),
                    "note": "Static analysis - HITL deve validar manualmente.",
                },
            )
        )

    candidates.sort(key=lambda x: (-x[0], x[1]["file"]))
    return [c[1] for c in candidates[:limit]]


def maybe_use_cache(out_path: Path, ttl: int, force: bool) -> dict[str, Any] | None:
    """Retorna payload cacheado se .json existe e foi criado ha < ttl segundos."""
    if force or not out_path.exists():
        return None
    age = time.time() - out_path.stat().st_mtime
    if age > ttl:
        return None
    try:
        cached = json.loads(out_path.read_text())
        cached["_cache_hit"] = True
        cached["_cache_age_seconds"] = round(age, 1)
        return cached
    except (json.JSONDecodeError, OSError):
        return None


def build_payload(no_cache: bool, vulture_min: int) -> dict[str, Any]:
    out_path = DEFAULT_REPORT_PATH
    cached = maybe_use_cache(out_path, CACHE_TTL_SEC, no_cache)
    if cached is not None:
        print(
            f"[cache] report re-usado (age={cached['_cache_age_seconds']}s, ttl={CACHE_TTL_SEC}s). Use --no-cache para forçar."
        )
        # Re-sincroniza cache_hit flag no disco para consumidores externos
        # (CI, testes) verem _cache_hit=true via re-leitura do JSON.
        DOCS_DIR.mkdir(exist_ok=True)
        out_path.write_text(json.dumps(cached, indent=2, sort_keys=False) + "\n")
        return cached

    print("[1/4] ruff F401/F841 (unused imports + unused vars)...")
    ruff_result = run_ruff_unused()
    print(f"      {ruff_result['count']} achados")

    print("[2/4] pyflakes app/...")
    pyflakes_result = run_pyflakes()
    print(f"      {pyflakes_result['count']} achados")

    print(f"[3/4] vulture app/ --min-confidence {vulture_min}...")
    vulture_result = run_vulture(min_confidence=vulture_min)
    print(f"      {vulture_result['count']} achados")

    print("[4/4] coverage gaps...")
    coverage_result = run_coverage_gaps()
    print(
        f"      {coverage_result.get('total_uncovered_files', 0)} arquivos com cobertura < 100% "
        f"({coverage_result.get('total_zero_coverage_files', 0)} zero coverage)"
    )

    results = {
        "ruff_unused": ruff_result,
        "pyflakes": pyflakes_result,
        "vulture": vulture_result,
        "coverage_gaps": coverage_result,
    }

    summary = collect_summary(results)
    top_candidates = select_top_candidates(results, limit=10)

    payload = {
        "_meta": {
            "schema": "dead-code-audit/1.0",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "repo_root": str(REPO_ROOT),
            "app_dir": str(APP_DIR),
            "policy": "NUNCA remove codigo. Apenas reporta. Decisao humana via review (HITL).",
            "task_id": "G8.12.T4",
        },
        "summary": summary,
        "results": results,
        "top_candidates_hitl": top_candidates,
        "_cache_hit": False,
    }
    DOCS_DIR.mkdir(exist_ok=True)
    out_path.write_text(json.dumps(payload, indent=2, sort_keys=False) + "\n")
    print(f"[done] report -> {out_path}")
    return payload


def print_console_summary(payload: dict[str, Any]) -> None:
    s = payload["summary"]
    print("\n" + "=" * 72)
    print("DEAD CODE AUDIT SUMMARY (G8.12.T4)")
    print("=" * 72)
    print(
        f"  ruff F401/F841 (unused imports/vars):  {s['ruff_total']}    {'[CLEAN]' if s['ruff_clean'] else '[CHECK]'}"
    )
    print(
        f"  pyflakes (broad unused scan):         {s['pyflakes_total']}    {'[CLEAN]' if s['pyflakes_clean'] else '[CHECK]'}"
    )
    print(
        f"  vulture (>= {s['vulture_min_confidence']}% conf functions/classes):    {s['vulture_suspicions']}    {'[CLEAN]' if s['vulture_clean'] else '[CHECK]'}"
    )
    print(
        f"  coverage gaps (< 100%):               {s['uncovered_files']}    ({s['zero_coverage_files']} zero-coverage)"
    )
    print(
        f"  HITL candidates (top 10):             {len(payload['top_candidates_hitl'])}"
    )
    print("-" * 72)
    for i, c in enumerate(payload["top_candidates_hitl"], 1):
        loc = f"{c['file']}:{c.get('line', '?')}"
        print(f"  {i:2d}. [{c['kind']:20s}] {loc}  -- {c.get('note', '')[:60]}")
    print("=" * 72)
    print(f"Policy: {payload['_meta']['policy']}")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Dead code audit — reporta, nunca remove (HITL)."
    )
    parser.add_argument(
        "--no-cache",
        action="store_true",
        help="Bypassa cache TTL e roda todos os linters novamente.",
    )
    parser.add_argument(
        "--vulture-min",
        type=int,
        default=80,
        help="Vulture min-confidence (default: 80).",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_REPORT_PATH,
        help="Caminho do JSON de output.",
    )
    args = parser.parse_args()

    try:
        payload = build_payload(no_cache=args.no_cache, vulture_min=args.vulture_min)
    except Exception as e:
        print(f"[FATAL] audit failed: {type(e).__name__}: {e}", file=sys.stderr)
        return 2
    print_console_summary(payload)
    return 0


if __name__ == "__main__":
    sys.exit(main())
