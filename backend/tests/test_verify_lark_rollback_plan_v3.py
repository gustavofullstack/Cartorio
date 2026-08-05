"""Testes para o verificador de plano de rollback do Lark (V3)."""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.verify_lark_rollback_plan_v3 import verify_rollback_plan


def test_verify_rollback_plan_dry_run() -> None:
    assert verify_rollback_plan() is True
