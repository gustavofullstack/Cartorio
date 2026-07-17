"""G7.24.T5 — Testes unitários para o G7 Super Orquestrador.

Cobre:
  - parse_tasks(): regex correto, extrai id/desc/status_raw/done/partial
  - status_cmd(): print correto, contagem done/partial/open
  - next_cmd(): diversidade por squad, fallback se <4 abertas
  - main(): dispatcher correto (status/next/validate)
  - Edge cases: arquivo vazio, malformed, sem tasks

Modified by Gustavo Almeida — G7 Wave 29 A1.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

ROOT = Path(__file__).resolve().parents[2]
G7_ORCH = ROOT / "scripts" / "g7_orchestrator.py"


@pytest.fixture
def orchestrator_module():
    """Importa o módulo g7_orchestrator dinamicamente."""
    import importlib.util

    spec = importlib.util.spec_from_file_location("g7_orchestrator", G7_ORCH)
    assert spec is not None
    assert spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture
def sample_plan_done() -> str:
    """Plano de exemplo com 5 tasks todas [x]."""
    return """# SUPER PLANO TEST
| ID | Task | Done |
|----|------|------|
| G7.01.T1 | task 1 | [x] done |
| G7.01.T2 | task 2 | [x] done |
| G7.02.T1 | task 3 | [x] done |
| G7.02.T2 | task 4 | [x] done |
| G7.03.T1 | task 5 | [x] done |
"""


@pytest.fixture
def sample_plan_mixed() -> str:
    """Plano de exemplo com mix: 2 done, 2 partial, 1 open."""
    return """# SUPER PLANO TEST MIXED
| ID | Task | Done |
|----|------|------|
| G7.01.T1 | task 1 | [x] done |
| G7.01.T2 | task 2 | [x] done |
| G7.02.T1 | task 3 | [~] partial SUI |
| G7.02.T2 | task 4 | [~] partial live |
| G7.03.T1 | task 5 | [ ] open |
"""


class TestParseTasks:
    def test_parses_done_tasks(self, orchestrator_module, sample_plan_done):
        tasks = orchestrator_module.parse_tasks()
        # Não posso injetar texto no parse_tasks (lê arquivo), então uso monkeypatch
        with patch.object(orchestrator_module, "PLANO") as mock_plano:
            mock_plano.exists.return_value = True
            mock_plano.read_text.return_value = sample_plan_done
            tasks = orchestrator_module.parse_tasks()
        assert len(tasks) == 5
        assert all(t["done"] for t in tasks)
        assert not any(t["partial"] for t in tasks)
        assert tasks[0]["id"] == "G7.01.T1"
        assert tasks[0]["desc"] == "task 1"

    def test_parses_mixed_status(self, orchestrator_module, sample_plan_mixed):
        with patch.object(orchestrator_module, "PLANO") as mock_plano:
            mock_plano.exists.return_value = True
            mock_plano.read_text.return_value = sample_plan_mixed
            tasks = orchestrator_module.parse_tasks()
        assert len(tasks) == 5
        assert sum(1 for t in tasks if t["done"]) == 2
        assert sum(1 for t in tasks if t["partial"]) == 2
        assert sum(1 for t in tasks if not t["done"] and not t["partial"]) == 1
        assert tasks[4]["id"] == "G7.03.T1"
        assert tasks[4]["partial"] is False
        assert tasks[4]["done"] is False

    def test_parses_empty_returns_empty_list(self, orchestrator_module):
        with patch.object(orchestrator_module, "PLANO") as mock_plano:
            mock_plano.exists.return_value = True
            mock_plano.read_text.return_value = ""
            tasks = orchestrator_module.parse_tasks()
        assert tasks == []

    def test_parses_missing_file_returns_empty(self, orchestrator_module):
        with patch.object(orchestrator_module, "PLANO") as mock_plano:
            mock_plano.exists.return_value = False
            tasks = orchestrator_module.parse_tasks()
        assert tasks == []

    def test_parses_handles_malformed_rows(self, orchestrator_module):
        bad = """| nonsense row without G7.xx.Ty |
| G7.99.T9 | valid | [x] done |
"""
        with patch.object(orchestrator_module, "PLANO") as mock_plano:
            mock_plano.exists.return_value = True
            mock_plano.read_text.return_value = bad
            tasks = orchestrator_module.parse_tasks()
        assert len(tasks) == 1
        assert tasks[0]["id"] == "G7.99.T9"

    def test_partial_takes_precedence_over_done_marker(self, orchestrator_module):
        # Se tiver [x] no raw mas também [~], done=True (regex startswith [x])
        text = """| G7.01.T1 | both | [x] partial [~] |
"""
        with patch.object(orchestrator_module, "PLANO") as mock_plano:
            mock_plano.exists.return_value = True
            mock_plano.read_text.return_value = text
            tasks = orchestrator_module.parse_tasks()
        assert len(tasks) == 1
        # done wins se startswith [x]
        assert tasks[0]["done"] is True


class TestStatusCmd:
    def test_status_prints_progress_pct(self, orchestrator_module, sample_plan_mixed, capsys):
        with patch.object(orchestrator_module, "PLANO") as mock_plano, \
             patch.object(orchestrator_module, "STATE") as mock_state:
            mock_plano.exists.return_value = True
            mock_plano.read_text.return_value = sample_plan_mixed
            mock_state.exists.return_value = False
            rc = orchestrator_module.status_cmd()
        assert rc == 0
        out = capsys.readouterr().out
        assert "Tasks parsed: 5" in out
        assert "done: 2" in out
        assert "partial: 2" in out
        assert "Progress: 40.0%" in out
        assert "G7.03.T1" in out  # Next open listed

    def test_status_with_loop_state_json(self, orchestrator_module, sample_plan_done, capsys):
        with patch.object(orchestrator_module, "PLANO") as mock_plano, \
             patch.object(orchestrator_module, "STATE") as mock_state:
            mock_plano.exists.return_value = True
            mock_plano.read_text.return_value = sample_plan_done
            mock_state.exists.return_value = True
            mock_state.read_text.return_value = json.dumps(
                {"status": "g7_wave28_done_92pct", "metrics": {"g7_wave": 28}}
            )
            rc = orchestrator_module.status_cmd()
        assert rc == 0
        out = capsys.readouterr().out
        assert "loop-state: g7_wave28_done_92pct wave=28" in out
        assert "Progress: 100.0%" in out


class TestNextCmd:
    def test_next_picks_diverse_squads(self, orchestrator_module, capsys):
        # 12 tasks abertas em 12 squads diferentes
        rows = "\n".join(f"| G7.{s:02d}.T1 | squad {s} | [ ] open |" for s in range(1, 13))
        plan = f"# PLANO\n| ID | T | Done |\n|----|---|------|\n{rows}\n"
        with patch.object(orchestrator_module, "PLANO") as mock_plano:
            mock_plano.exists.return_value = True
            mock_plano.read_text.return_value = plan
            rc = orchestrator_module.next_cmd()
        assert rc == 0
        out = capsys.readouterr().out
        assert "NEXT WAVE (4 tasks / 4 agents):" in out
        # Deve ter pego 4 tasks de squads diferentes
        assert "G7.01.T1" in out
        assert "G7.02.T1" in out
        assert "G7.03.T1" in out
        assert "G7.04.T1" in out
        # 4 reins diferentes
        for rein in ["cartorio-dev", "cartorio-n8n", "cartorio-lgpd", "cartorio-sre"]:
            assert rein in out

    def test_next_fallback_when_fewer_than_4_unique_squads(self, orchestrator_module, capsys):
        # Só 2 squads, mas 6 tasks abertas (mesmo squad). Deve pegar 4 mesmo assim.
        rows = "\n".join(f"| G7.01.T{i} | task {i} | [ ] open |" for i in range(1, 7))
        plan = f"# PLANO\n| ID | T | Done |\n|----|---|------|\n{rows}\n"
        with patch.object(orchestrator_module, "PLANO") as mock_plano:
            mock_plano.exists.return_value = True
            mock_plano.read_text.return_value = plan
            rc = orchestrator_module.next_cmd()
        assert rc == 0
        out = capsys.readouterr().out
        # Deve ter 4 tasks mesmo sendo do mesmo squad
        assert "G7.01.T1" in out
        assert "G7.01.T2" in out
        assert "G7.01.T3" in out
        assert "G7.01.T4" in out


class TestMain:
    def test_main_no_args_defaults_to_status(self, orchestrator_module, capsys):
        with patch.object(orchestrator_module, "PLANO") as mock_plano, \
             patch.object(orchestrator_module, "STATE") as mock_state, \
             patch.object(sys, "argv", ["g7_orchestrator.py"]):
            mock_plano.exists.return_value = True
            mock_plano.read_text.return_value = "| G7.01.T1 | x | [x] d |"
            mock_state.exists.return_value = False
            rc = orchestrator_module.main()
        assert rc == 0
        out = capsys.readouterr().out
        assert "Tasks parsed: 1" in out

    def test_main_unknown_command_returns_2(self, orchestrator_module):
        with patch.object(sys, "argv", ["g7_orchestrator.py", "foobar"]):
            rc = orchestrator_module.main()
        assert rc == 2

    def test_main_validate_invokes_super_validator(self, orchestrator_module):
        fake_proc = subprocess.CompletedProcess(args=[], returncode=0, stdout="", stderr="")
        with patch.object(sys, "argv", ["g7_orchestrator.py", "validate"]), \
             patch.object(subprocess, "run", return_value=fake_proc) as mock_run:
            rc = orchestrator_module.main()
        assert rc == 0
        mock_run.assert_called_once()
        called_args = mock_run.call_args[0][0]
        assert "g7_super_validator.py" in str(called_args)


class TestIntegrationWithRealPlan:
    """Integração com SUPER_PLANO_G7_100_TASKS.md real (snapshot Wave 28)."""

    def test_real_plan_parses_at_least_100_tasks(self, orchestrator_module):
        tasks = orchestrator_module.parse_tasks()
        # Plano G7 tem 100 tasks em 25 squads (4 cada)
        assert len(tasks) >= 100, f"Esperado ≥100, achou {len(tasks)}"

    def test_real_plan_progress_is_above_85pct(self, orchestrator_module):
        tasks = orchestrator_module.parse_tasks()
        done = sum(1 for t in tasks if t["done"])
        pct = 100.0 * done / len(tasks)
        # Wave 28 consolidada reporta ~92%
        assert pct >= 85.0, f"Esperado ≥85% (Wave 28 ~92%), achou {pct:.1f}%"