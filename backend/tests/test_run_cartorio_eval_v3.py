# noqa: E402
"""Testes para o runner de Evals determinístico V3."""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.run_cartorio_eval_v3 import run_evals  # noqa: E402


def test_run_evals_deterministic() -> None:
    summary = run_evals("deterministic-local")
    assert summary["total_cases"] == 200
    assert summary["passed_cases"] == 200
    assert summary["deterministic_domain_accuracy_pct"] == 100.0
