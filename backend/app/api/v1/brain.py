"""brain.py - API endpoints do cerebro (BRAIN6).

Endpoints:
- GET /api/v1/brain/tasks
- GET /api/v1/brain/lessons
- POST /api/v1/brain/lesson
- POST /api/v1/brain/sync
- GET /api/v1/brain/loop-state

LGPD-safe: endpoints NAO expoem PII. Apenas contadores agregados.
"""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

brain_router = APIRouter(prefix="/brain", tags=["brain", "meta"])

BRAIN_DIR = Path("/Users/gustavoalmeida/projetos/Cartorio/.brain")


class LessonCreate(BaseModel):
    """Payload para criar 1 lesson (BRAIN6)."""

    titulo: str = Field(..., min_length=5, max_length=200)
    contexto: str = Field(..., min_length=10, max_length=2000)
    solucao: str = Field(..., min_length=10, max_length=2000)
    codigo_ref: str | None = Field(default=None, max_length=500)


class TaskSummary(BaseModel):
    id: str
    squad: str
    title: str
    status: str
    type: str | None = None


class LessonSummary(BaseModel):
    id: str
    titulo: str
    arquivo: str
    criado_em: str


class LoopState(BaseModel):
    session_id: str
    current_squad: str
    last_task: str
    last_commit: str
    next_action: str
    gates: dict
    tasks_done_today: int
    tasks_pending_today: int


def _read_json_safe(path: Path) -> dict | None:
    try:
        if not path.exists():
            return None
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


@brain_router.get("/tasks", response_model=list[TaskSummary], summary="Lista tasks do .brain/tasks")
async def list_tasks(
    status: str | None = Query(default=None, pattern="^(done|pending|in_progress)$"),
    squad: str | None = Query(default=None, max_length=10),
) -> list[TaskSummary]:
    tasks_dir = BRAIN_DIR / "tasks"
    if not tasks_dir.exists():
        return []

    out: list[TaskSummary] = []
    for f in tasks_dir.glob("*.json"):
        d = _read_json_safe(f) or {}
        if status and d.get("status") != status:
            continue
        if squad and d.get("squad") != squad:
            continue
        out.append(
            TaskSummary(
                id=d.get("id", f.stem),
                squad=d.get("squad", "?"),
                title=d.get("title", ""),
                status=d.get("status", "pending"),
                type=d.get("type"),
            )
        )
    return out


@brain_router.get("/lessons", response_model=list[LessonSummary], summary="Lista lessons do .brain/lessons")
async def list_lessons(
    from_date: str | None = Query(default=None, pattern="^\\d{4}-\\d{2}-\\d{2}$"),
    limit: int = Query(default=50, ge=1, le=500),
) -> list[LessonSummary]:
    lessons_dir = BRAIN_DIR / "lessons"
    if not lessons_dir.exists():
        return []

    out: list[LessonSummary] = []
    for f in sorted(lessons_dir.glob("*.md"), reverse=True)[:limit]:
        # First line is title (# NNN - titulo)
        title = f.stem
        try:
            first_line = f.read_text(encoding="utf-8").splitlines()[0]
            if first_line.startswith("#"):
                title = first_line.lstrip("#").strip()
        except Exception:
            pass
        out.append(
            LessonSummary(
                id=f.stem,
                titulo=title,
                arquivo=str(f),
                criado_em=datetime.fromtimestamp(f.stat().st_mtime).isoformat(),
            )
        )
    return out


@brain_router.post("/lesson", summary="Cria 1 lesson no .brain/lessons")
async def create_lesson(payload: LessonCreate) -> dict:
    lessons_dir = BRAIN_DIR / "lessons"
    lessons_dir.mkdir(parents=True, exist_ok=True)

    # Proximo NNN
    existing = list(lessons_dir.glob("*.md"))
    nums = []
    for f in existing:
        try:
            n = int(f.stem.split("-")[0])
            nums.append(n)
        except (ValueError, IndexError):
            continue
    next_n = (max(nums) + 1) if nums else 130
    slug = payload.titulo.lower().replace(" ", "-")[:50]
    filepath = lessons_dir / f"{next_n:03d}-{slug}.md"

    content = (
        f"# {next_n:03d} - {payload.titulo}\n\n"
        f"## Contexto\n\n{payload.contexto}\n\n"
        f"## Solucao\n\n{payload.solucao}\n\n"
    )
    if payload.codigo_ref:
        content += f"## Codigo\n\n`{payload.codigo_ref}`\n\n"
    content += f"Created: {datetime.now().isoformat()}\n"

    filepath.write_text(content, encoding="utf-8")
    return {"id": filepath.stem, "arquivo": str(filepath), "next_n": next_n}


@brain_router.post("/sync", summary="Forca sync .brain local <-> VPS")
async def trigger_sync() -> dict:
    """Forca rsync bidirecional. Requer SSH Tailscale configurado."""
    import subprocess

    try:
        # Push local -> VPS
        push = subprocess.run(
            [
                "rsync",
                "-avz",
                "--delete",
                str(BRAIN_DIR) + "/",
                "cartorio@vps-cartorio.tail2fe279.ts.net:/var/lib/docker/volumes/cartorio_brain/_data/",
            ],
            capture_output=True,
            text=True,
            timeout=60,
        )
        # Pull VPS -> local
        pull = subprocess.run(
            [
                "rsync",
                "-avz",
                "--delete",
                "cartorio@vps-cartorio.tail2fe279.ts.net:/var/lib/docker/volumes/cartorio_brain/_data/",
                str(BRAIN_DIR) + "/",
            ],
            capture_output=True,
            text=True,
            timeout=60,
        )
        return {
            "push_ok": push.returncode == 0,
            "pull_ok": pull.returncode == 0,
            "push_lines": len(push.stdout.splitlines()),
            "pull_lines": len(pull.stdout.splitlines()),
        }
    except subprocess.TimeoutExpired:
        raise HTTPException(status_code=504, detail="rsync timeout (60s)")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"sync error: {e}")


@brain_router.get("/loop-state", response_model=LoopState, summary="Estado compacto do loop")
async def get_loop_state() -> LoopState:
    """Le .brain/loop-state.json e retorna."""
    state = _read_json_safe(BRAIN_DIR / "loop-state.json")
    if not state:
        raise HTTPException(status_code=404, detail="loop-state.json nao encontrado")

    return LoopState(
        session_id=state.get("session_id", "unknown"),
        current_squad=state.get("current_squad", "?"),
        last_task=state.get("last_task", "?"),
        last_commit=state.get("last_commit", "?"),
        next_action=state.get("next_action", "?"),
        gates=state.get("gates", {}),
        tasks_done_today=state.get("tasks_done_today", 0),
        tasks_pending_today=state.get("tasks_pending_today", 0),
    )
