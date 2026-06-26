"""brain.py - API endpoints do cerebro (BRAIN6 + BRAIN8).

Endpoints:
- GET /api/v1/brain/tasks
- GET /api/v1/brain/lessons
- POST /api/v1/brain/lesson
- POST /api/v1/brain/sync
- GET /api/v1/brain/loop-state
- GET /api/v1/brain/snapshots (BRAIN8 — list cross-session snapshots)
- POST /api/v1/brain/snapshots/restore (BRAIN8 — restore context from snapshot)
- GET /api/v1/brain/context/restore/{snapshot_id} (BRAIN8 — read restored context)
- GET /api/v1/brain/sessions (BRAIN8 — list all sessions for context loop)

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
SNAPSHOTS_DIR = BRAIN_DIR / "snapshots"
MEMORY_DIR = BRAIN_DIR / "memory"


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


# ────────────────────────────────────────────────────────────────────────
# BRAIN8 — Cross-session context sync & restoration
# ────────────────────────────────────────────────────────────────────────


class SnapshotSummary(BaseModel):
    """Metadata de 1 snapshot (BRAIN8)."""

    snapshot_id: str
    exported_at: str
    label: str | None = None
    file_count: int
    total_size_bytes: int
    by_type: dict[str, int] = Field(default_factory=dict)


class SnapshotDetail(BaseModel):
    """Detalhes completos de 1 snapshot (BRAIN8)."""

    snapshot_id: str
    exported_at: str
    label: str | None = None
    files: dict[str, dict[str, str]]  # {path: {content, hash, size}}


class SessionSummary(BaseModel):
    """Resumo de 1 sessao (BRAIN8 — context loop engineer)."""

    session_id: str
    date: str
    file: str
    size_bytes: int
    title: str | None = None
    commits_count: int = 0
    squads_touched: list[str] = Field(default_factory=list)


class ContextRestoreResponse(BaseModel):
    """Resposta de restauracao de contexto (BRAIN8)."""

    snapshot_id: str
    exported_at: str
    loop_state: dict
    index_md: str
    lessons_count: int
    tasks_count: int
    memory_files: list[str]
    key_files: dict[str, str]  # arquivos criticos restaurados


@brain_router.get(
    "/snapshots",
    response_model=list[SnapshotSummary],
    summary="Lista snapshots cross-session (BRAIN8)",
)
async def list_snapshots(
    limit: int = Query(default=20, ge=1, le=100),
) -> list[SnapshotSummary]:
    """Lista todos os snapshots disponiveis em .brain/snapshots/.

    Snapshots sao backups completos do estado cerebral, usados para:
    - Cross-session context restoration (recuperar 100% apos compact)
    - Diff entre sessoes (ver o que mudou)
    - Disaster recovery (rollback)
    """
    if not SNAPSHOTS_DIR.exists():
        return []

    out: list[SnapshotSummary] = []
    for f in sorted(SNAPSHOTS_DIR.glob("*.json"), reverse=True)[:limit]:
        d = _read_json_safe(f)
        if not d:
            continue
        stats = d.get("stats", {})
        out.append(
            SnapshotSummary(
                snapshot_id=d.get("snapshot_id", f.stem),
                exported_at=d.get("exported_at", "?"),
                label=d.get("label"),
                file_count=stats.get("total_files", len(d.get("files", {}))),
                total_size_bytes=stats.get("total_size_bytes", 0),
                by_type=stats.get("by_type", {}),
            )
        )
    return out


@brain_router.get(
    "/snapshots/{snapshot_id}",
    response_model=SnapshotDetail,
    summary="Detalhes de 1 snapshot (BRAIN8)",
)
async def get_snapshot_detail(snapshot_id: str) -> SnapshotDetail:
    """Retorna arquivos completos do snapshot para restauracao."""
    snap_path = SNAPSHOTS_DIR / f"{snapshot_id}.json"
    if not snap_path.exists():
        raise HTTPException(
            status_code=404, detail=f"snapshot {snapshot_id!r} nao encontrado"
        )
    d = _read_json_safe(snap_path)
    if not d:
        raise HTTPException(status_code=500, detail="snapshot corrompido")
    return SnapshotDetail(
        snapshot_id=d.get("snapshot_id", snapshot_id),
        exported_at=d.get("exported_at", "?"),
        label=d.get("label"),
        files=d.get("files", {}),
    )


@brain_router.get(
    "/sessions",
    response_model=list[SessionSummary],
    summary="Lista sessoes anteriores (BRAIN8 — context loop)",
)
async def list_sessions(
    limit: int = Query(default=30, ge=1, le=200),
) -> list[SessionSummary]:
    """Lista todas as sessoes (memory/YYYY-MM-DD.md + SESSION_*.md).

    Usado pelo Context Loop Engineer para:
    - Navegar historico de sessoes
    - Encontrar sessao relevante antes de iniciar trabalho
    - Diff entre sessoes
    """
    if not MEMORY_DIR.exists():
        return []

    out: list[SessionSummary] = []
    for f in sorted(MEMORY_DIR.glob("*.md"), reverse=True):
        size = f.stat().st_size
        title: str | None = None
        commits_count = 0
        squads: set[str] = set()
        try:
            content = f.read_text(encoding="utf-8")
            lines = content.splitlines()
            # Extrai titulo da primeira linha # ...
            for line in lines[:5]:
                if line.startswith("# ") and not line.startswith("# /"):
                    title = line.lstrip("#").strip()
                    break
            # Conta commits no formato [hash]
            import re

            commits_count = len(re.findall(r"`[0-9a-f]{7}`", content))
            # Detecta squads mencionados
            squad_match = re.findall(r"SQUAD\s+([A-Z0-9]+)", content)
            squads.update(squad_match)
        except Exception:
            pass

        # Detecta tipo: SESSION_*.md vs YYYY-MM-DD.md
        if f.name.startswith("SESSION_"):
            session_id = f.stem.replace("SESSION_", "")
            date = session_id.split("-")[:3]
            date_str = "-".join(date) if len(date) >= 3 else f.stem
        else:
            session_id = f.stem
            date_str = f.stem

        out.append(
            SessionSummary(
                session_id=session_id,
                date=date_str,
                file=str(f),
                size_bytes=size,
                title=title,
                commits_count=commits_count,
                squads_touched=sorted(squads),
            )
        )
        if len(out) >= limit:
            break
    return out


@brain_router.get(
    "/context/restore/{snapshot_id}",
    response_model=ContextRestoreResponse,
    summary="Restaura contexto completo de 1 snapshot (BRAIN8)",
)
async def restore_context(snapshot_id: str) -> ContextRestoreResponse:
    """Restaura contexto completo de um snapshot para retomada de sessao.

    Retorna:
    - loop_state (estado compacto do cerebro no momento do snapshot)
    - index_md (pagina de indice 1-pagina)
    - lessons_count + tasks_count (catalogos)
    - memory_files (lista de arquivos de memoria)
    - key_files (arquivos criticos: STRUCTURE.md, loop-state.json, index.md, ...)
    """
    snap_path = SNAPSHOTS_DIR / f"{snapshot_id}.json"
    if not snap_path.exists():
        raise HTTPException(
            status_code=404, detail=f"snapshot {snapshot_id!r} nao encontrado"
        )
    d = _read_json_safe(snap_path)
    if not d:
        raise HTTPException(status_code=500, detail="snapshot corrompido")

    files = d.get("files", {})

    # Restaura loop-state do snapshot
    loop_state: dict = {}
    loop_state_raw = files.get("loop-state.json", {})
    if isinstance(loop_state_raw, dict) and loop_state_raw.get("content"):
        try:
            loop_state = json.loads(loop_state_raw["content"])
        except Exception:
            loop_state = {}

    # Index markdown
    index_md = ""
    index_raw = files.get("index.md", {})
    if isinstance(index_raw, dict):
        index_md = index_raw.get("content", "")

    # Lessons + tasks count (walk filesystem do snapshot)
    lessons_count = sum(1 for k in files if k.startswith("lessons/") and k.endswith(".md"))
    tasks_count = sum(1 for k in files if k.startswith("tasks/") and k.endswith(".json"))

    # Memory files list
    memory_files = sorted(k for k in files if k.startswith("memory/") and k.endswith(".md"))

    # Key files (estrutura)
    key_files: dict[str, str] = {}
    for k in ("STRUCTURE.md", "loop-state.json", "agents/README.md", "api-specs/README.md"):
        f = files.get(k, {})
        if isinstance(f, dict) and f.get("content"):
            key_files[k] = f["content"]

    return ContextRestoreResponse(
        snapshot_id=d.get("snapshot_id", snapshot_id),
        exported_at=d.get("exported_at", "?"),
        loop_state=loop_state,
        index_md=index_md,
        lessons_count=lessons_count,
        tasks_count=tasks_count,
        memory_files=memory_files,
        key_files=key_files,
    )


@brain_router.get(
    "/context/current",
    summary="Contexto atual (alias para restoration live)",
)
async def current_context() -> dict:
    """Retorna contexto live: loop-state + index + lessons count + tasks count.

    Equivalente a /context/restore/{latest_snapshot} mas SEMPRE live.
    Ideal para um agent iniciar uma sessao.
    """
    loop_state = _read_json_safe(BRAIN_DIR / "loop-state.json") or {}
    index_md = ""
    index_path = BRAIN_DIR / "index.md"
    if index_path.exists():
        try:
            index_md = index_path.read_text(encoding="utf-8")
        except Exception:
            pass

    lessons_count = 0
    if (BRAIN_DIR / "lessons").exists():
        lessons_count = len(list((BRAIN_DIR / "lessons").glob("*.md")))

    tasks_count = 0
    if (BRAIN_DIR / "tasks").exists():
        tasks_count = len(list((BRAIN_DIR / "tasks").glob("*.json")))

    return {
        "loop_state": loop_state,
        "index_md": index_md,
        "lessons_count": lessons_count,
        "tasks_count": tasks_count,
        "memory_files": sorted(
            str(p) for p in MEMORY_DIR.glob("*.md") if MEMORY_DIR.exists()
        ),
    }
