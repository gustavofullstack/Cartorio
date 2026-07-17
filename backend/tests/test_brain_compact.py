"""Tests for brain_compact.py (BRAIN7 compact loop-state).

Validates:
- completed_tasks reduzido para os ultimos 30
- sessions reduzido para as ultimas 5
- metrics/milestones/next_priorities mantidos
- compact_loop_state sobrescreve arquivo
- idempotencia (compactar 2x = mesmo resultado)
- compact loop-state preserva estrutura canonica (version, status, current_sprint)
- edge cases: lista <30 mantem intacta, lista >30 trunca
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.services import brain_compact


@pytest.fixture
def tmp_loop_state(tmp_path: Path) -> Path:
    """loop-state.json com volume realista (50 completed_tasks, 8 sessions)."""
    brain = tmp_path / ".brain"
    brain.mkdir(parents=True)
    loop_state = {
        "version": "2.10.0",
        "status": "running",
        "current_sprint": "Sprint 50",
        "current_session": "loop-2026-07-15",
        "metrics": {
            "services_swarm_up": "8/8",
            "pytest": 2500,
            "coverage": "94%",
        },
        "milestones": [
            {"id": "1", "title": "Milestone A", "status": "done"},
            {"id": "2", "title": "Milestone B", "status": "done"},
        ],
        "next_priorities": ["task A", "task B", "task C"],
        "completed_tasks": [f"T{i:03d}" for i in range(50)],
        "sessions": [
            {
                "id": f"session-{i}",
                "started_at": f"2026-07-{15 - i:02d}T00:00:00-03:00",
                "plan_file": f"plan-{i}.md",
                "mode": "YOLO",
                "paused": [],
            }
            for i in range(8)
        ],
        "squad_progress": {"squad-core": 7, "squad-security": 7},
        "loops_active": {"master-loop": "running"},
        "last_updated": "2026-07-15T10:00:00",
    }
    path = brain / "loop-state.json"
    path.write_text(json.dumps(loop_state), encoding="utf-8")
    return path


def test_completed_tasks_reduced_to_last_30(tmp_loop_state: Path) -> None:
    """completed_tasks deve ficar apenas com os 30 mais recentes."""
    result = brain_compact.compact_loop_state(loop_state_path=tmp_loop_state)
    payload = json.loads(tmp_loop_state.read_text(encoding="utf-8"))
    assert len(payload["completed_tasks"]) == 30
    # garante que sao os ULTIMOS (T020..T049), nao os primeiros
    assert payload["completed_tasks"][0] == "T020"
    assert payload["completed_tasks"][-1] == "T049"
    assert result["tasks_removed"] == 20


def test_sessions_reduced_to_last_5(tmp_loop_state: Path) -> None:
    """sessions deve ficar apenas com as 5 mais recentes."""
    brain_compact.compact_loop_state(loop_state_path=tmp_loop_state)
    payload = json.loads(tmp_loop_state.read_text(encoding="utf-8"))
    assert len(payload["sessions"]) == 5
    # garante que sao as ultimas (session-0..session-4 invertidos -> session-3..session-7)
    session_ids = [s["id"] for s in payload["sessions"]]
    assert session_ids == ["session-3", "session-4", "session-5", "session-6", "session-7"]


def test_metrics_milestones_priorities_preserved(tmp_loop_state: Path) -> None:
    """metrics, milestones e next_priorities NAO podem ser alterados."""
    before = json.loads(tmp_loop_state.read_text(encoding="utf-8"))
    brain_compact.compact_loop_state(loop_state_path=tmp_loop_state)
    after = json.loads(tmp_loop_state.read_text(encoding="utf-8"))
    assert after["metrics"] == before["metrics"]
    assert after["milestones"] == before["milestones"]
    assert after["next_priorities"] == before["next_priorities"]


def test_top_level_fields_preserved(tmp_loop_state: Path) -> None:
    """version/status/current_sprint/current_session/loops_active preservados."""
    brain_compact.compact_loop_state(loop_state_path=tmp_loop_state)
    payload = json.loads(tmp_loop_state.read_text(encoding="utf-8"))
    assert payload["version"] == "2.10.0"
    assert payload["status"] == "running"
    assert payload["current_sprint"] == "Sprint 50"
    assert payload["current_session"] == "loop-2026-07-15"
    assert payload["loops_active"] == {"master-loop": "running"}
    assert payload["squad_progress"] == {"squad-core": 7, "squad-security": 7}


def test_compact_is_idempotent(tmp_loop_state: Path) -> None:
    """Rodar compact 2x deve produzir mesmo resultado (modulo last_compact_at)."""
    brain_compact.compact_loop_state(loop_state_path=tmp_loop_state)
    first = json.loads(tmp_loop_state.read_text(encoding="utf-8"))
    first.pop("last_compact_at", None)
    result = brain_compact.compact_loop_state(loop_state_path=tmp_loop_state)
    second = json.loads(tmp_loop_state.read_text(encoding="utf-8"))
    second.pop("last_compact_at", None)
    assert first == second
    assert result["tasks_removed"] == 0
    assert result["sessions_removed"] == 0


def test_completed_tasks_below_30_kept_intact(tmp_path: Path) -> None:
    """Se completed_tasks <30, nao trunca nada."""
    brain = tmp_path / ".brain"
    brain.mkdir(parents=True)
    state = {
        "version": "2.10.0",
        "completed_tasks": ["T001", "T002", "T003"],
        "sessions": [{"id": "only-one", "started_at": "2026-07-15"}],
        "metrics": {"pytest": 100},
        "milestones": [],
        "next_priorities": [],
        "loops_active": {},
        "last_updated": "2026-07-15",
    }
    path = brain / "loop-state.json"
    path.write_text(json.dumps(state), encoding="utf-8")

    result = brain_compact.compact_loop_state(loop_state_path=path)
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert len(payload["completed_tasks"]) == 3
    assert len(payload["sessions"]) == 1
    assert result["tasks_removed"] == 0
    assert result["sessions_removed"] == 0


def test_compact_handles_missing_fields_gracefully(tmp_path: Path) -> None:
    """compact_loop_state NAO quebra se completed_tasks/sessions ausentes."""
    brain = tmp_path / ".brain"
    brain.mkdir(parents=True)
    path = brain / "loop-state.json"
    path.write_text(json.dumps({"version": "2.10.0", "metrics": {}}), encoding="utf-8")

    # nao levanta excecao
    brain_compact.compact_loop_state(loop_state_path=path)
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["completed_tasks"] == []
    assert payload["sessions"] == []


def test_compact_returns_summary_dict(tmp_loop_state: Path) -> None:
    """compact_loop_state retorna dict com contadores removed + ok."""
    result = brain_compact.compact_loop_state(loop_state_path=tmp_loop_state)
    assert result["ok"] is True
    assert "tasks_removed" in result
    assert "sessions_removed" in result
    assert "before_tasks" in result
    assert "after_tasks" in result
    assert result["before_tasks"] == 50
    assert result["after_tasks"] == 30
    assert "before_sessions" in result
    assert result["before_sessions"] == 8
    assert "after_sessions" in result
    assert result["after_sessions"] == 5


def test_compact_raises_if_file_missing(tmp_path: Path) -> None:
    """compact_loop_state levanta erro claro se loop-state.json nao existe."""
    missing = tmp_path / ".brain" / "loop-state.json"
    with pytest.raises(FileNotFoundError):
        brain_compact.compact_loop_state(loop_state_path=missing)


def test_compact_invalid_json_raises(tmp_path: Path) -> None:
    """compact_loop_state levanta JSONDecodeError se arquivo corrompido."""
    brain = tmp_path / ".brain"
    brain.mkdir(parents=True)
    path = brain / "loop-state.json"
    path.write_text("not valid json {{", encoding="utf-8")
    with pytest.raises(json.JSONDecodeError):
        brain_compact.compact_loop_state(loop_state_path=path)
