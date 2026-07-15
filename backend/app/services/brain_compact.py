"""brain_compact.py - BRAIN7 compact loop-state.json.

Reduz `completed_tasks` para os 30 mais recentes e `sessions` para as 5 mais
recentes. Preserva todos os outros campos canonicos (version, metrics,
milestones, next_priorities, loops_active, etc). Sobrescreve o arquivo.

Idempotente: rodar 2x na mesma entrada produz mesmo resultado.

LGPD-safe: nao toca PII.
"""
from __future__ import annotations

import datetime as dt
import json
from pathlib import Path
from typing import Any

DEFAULT_LOOP_STATE_PATH = Path(
    "/Users/gustavoalmeida/projetos/Cartorio/.brain/loop-state.json"
)
MAX_COMPLETED_TASKS = 30
MAX_SESSIONS = 5


def _read_loop_state(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"loop-state.json nao encontrado em {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def _write_loop_state(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def compact_loop_state(
    loop_state_path: Path = DEFAULT_LOOP_STATE_PATH,
    max_completed_tasks: int = MAX_COMPLETED_TASKS,
    max_sessions: int = MAX_SESSIONS,
) -> dict[str, Any]:
    """Compacta loop-state.json mantendo os N mais recentes.

    Args:
        loop_state_path: caminho do loop-state.json.
        max_completed_tasks: max de completed_tasks a manter (default 30).
        max_sessions: max de sessions a manter (default 5).

    Returns:
        dict com contadores before/after + ok.
    """
    loop_state_path = Path(loop_state_path)
    payload = _read_loop_state(loop_state_path)

    before_tasks = payload.get("completed_tasks") or []
    before_sessions = payload.get("sessions") or []

    if not isinstance(before_tasks, list):
        before_tasks = []
    if not isinstance(before_sessions, list):
        before_sessions = []

    after_tasks = before_tasks[-max_completed_tasks:]
    after_sessions = before_sessions[-max_sessions:]

    payload["completed_tasks"] = after_tasks
    payload["sessions"] = after_sessions
    payload["last_compact_at"] = dt.datetime.now(dt.timezone.utc).isoformat()

    _write_loop_state(loop_state_path, payload)

    return {
        "ok": True,
        "before_tasks": len(before_tasks),
        "after_tasks": len(after_tasks),
        "tasks_removed": len(before_tasks) - len(after_tasks),
        "before_sessions": len(before_sessions),
        "after_sessions": len(after_sessions),
        "sessions_removed": len(before_sessions) - len(after_sessions),
        "path": str(loop_state_path),
    }