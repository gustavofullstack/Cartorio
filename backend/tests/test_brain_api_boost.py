"""Tests to boost coverage of app/api/v1/brain.py endpoints.

Targets the following uncovered lines:
- exception blocks in lessons, sync, snapshots, sessions, context restore.
- filter logic and limits.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.v1.brain import brain_router


@pytest.fixture
def tmp_brain(tmp_path: Path):
    fake_brain = tmp_path / "fake_brain"
    fake_brain.mkdir()
    (fake_brain / "lessons").mkdir()
    (fake_brain / "tasks").mkdir()
    (fake_brain / "snapshots").mkdir()
    (fake_brain / "memory").mkdir()
    return fake_brain


@pytest.fixture
def client(tmp_brain: Path):
    app = FastAPI()
    app.include_router(brain_router)

    # Patch modules global paths
    with (
        patch("app.api.v1.brain.BRAIN_DIR", tmp_brain),
        patch("app.api.v1.brain.SNAPSHOTS_DIR", tmp_brain / "snapshots"),
        patch("app.api.v1.brain.MEMORY_DIR", tmp_brain / "memory"),
    ):
        yield TestClient(app)


def test_list_tasks_squad_filter(client: TestClient, tmp_brain: Path) -> None:
    """GET /brain/tasks supports squad filtering."""
    (tmp_brain / "tasks" / "T1.json").write_text(
        json.dumps({"id": "T1", "squad": "A", "status": "done"})
    )
    (tmp_brain / "tasks" / "T2.json").write_text(
        json.dumps({"id": "T2", "squad": "B", "status": "done"})
    )

    r = client.get("/brain/tasks", params={"squad": "A"})
    assert r.status_code == 200
    ids = [t["id"] for t in r.json()]
    assert ids == ["T1"]


def test_list_lessons_read_exception_handling(client: TestClient, tmp_brain: Path) -> None:
    """list_lessons gracefully handles read_text exceptions (line 124-125)."""
    (tmp_brain / "lessons" / "131-test.md").write_text("# Title\nContent")

    with patch("pathlib.Path.read_text", side_effect=Exception("Read fail")):
        r = client.get("/brain/lessons")
        assert r.status_code == 200
        assert len(r.json()) == 1
        assert r.json()[0]["titulo"] == "131-test"  # fallback to stem


def test_create_lesson_non_numeric_files_ignored(client: TestClient, tmp_brain: Path) -> None:
    """create_lesson ignores existing files that are not NNN-numbered (line 146-150)."""
    (tmp_brain / "lessons" / "broken-slug.md").write_text("content")
    (tmp_brain / "lessons" / "135-ok.md").write_text("content")

    r = client.post(
        "/brain/lesson",
        json={
            "titulo": "New Lesson",
            "contexto": "Context with 10+ chars",
            "solucao": "Solution with 10+ chars",
        },
    )
    assert r.status_code == 200
    # O proximo deve ser max(135) + 1 = 136 (broken-slug.md e ignorado)
    assert r.json()["next_n"] == 136


def test_trigger_sync_timeout(client: TestClient) -> None:
    """trigger_sync returns 504 on subprocess timeout (line 206-207)."""
    with patch("subprocess.run", side_effect=subprocess.TimeoutExpired(cmd=[], timeout=60)):
        r = client.post("/brain/sync")
        assert r.status_code == 504
        assert "timeout" in r.json()["detail"]


def test_trigger_sync_generic_exception(client: TestClient) -> None:
    """trigger_sync returns 500 on other subprocess errors (line 208-209)."""
    with patch("subprocess.run", side_effect=RuntimeError("rsync missing")):
        r = client.post("/brain/sync")
        assert r.status_code == 500
        assert "sync error" in r.json()["detail"]


def test_list_snapshots_missing_dir(client: TestClient, tmp_brain: Path) -> None:
    """list_snapshots returns empty list if SNAPSHOTS_DIR missing (line 297)."""
    import shutil

    shutil.rmtree(tmp_brain / "snapshots")

    r = client.get("/brain/snapshots")
    assert r.status_code == 200
    assert r.json() == []


def test_list_snapshots_read_json_failure(client: TestClient, tmp_brain: Path) -> None:
    """list_snapshots skips invalid snapshot files (line 303)."""
    (tmp_brain / "snapshots" / "invalid.json").write_text("{broken json")

    r = client.get("/brain/snapshots")
    assert r.status_code == 200
    assert r.json() == []


def test_get_snapshot_corrupted_json(client: TestClient, tmp_brain: Path) -> None:
    """get_snapshot returns 500 if snapshot JSON is corrupted (line 328-331)."""
    (tmp_brain / "snapshots" / "snap1.json").write_text("{broken json")

    r = client.get("/brain/snapshots/snap1")
    assert r.status_code == 500


def test_list_sessions_missing_dir(client: TestClient, tmp_brain: Path) -> None:
    """list_sessions returns empty list if MEMORY_DIR missing (line 355)."""
    import shutil

    shutil.rmtree(tmp_brain / "memory")

    r = client.get("/brain/sessions")
    assert r.status_code == 200
    assert r.json() == []


def test_list_sessions_exception_handling(client: TestClient, tmp_brain: Path) -> None:
    """list_sessions gracefully handles session file read errors (line 378-379)."""
    (tmp_brain / "memory" / "2026-01-01.md").write_text("content")

    with patch("pathlib.Path.read_text", side_effect=Exception("Disk error")):
        r = client.get("/brain/sessions")
        assert r.status_code == 200
        assert len(r.json()) == 1
        assert r.json()[0]["title"] is None
        assert r.json()[0]["commits_count"] == 0


def test_list_sessions_limit_respected(client: TestClient, tmp_brain: Path) -> None:
    """list_sessions limit break check (line 402)."""
    for i in range(5):
        (tmp_brain / "memory" / f"2026-01-0{i}.md").write_text("content")

    r = client.get("/brain/sessions", params={"limit": 2})
    assert r.status_code == 200
    assert len(r.json()) == 2


def test_restore_context_corrupted_json(client: TestClient, tmp_brain: Path) -> None:
    """restore_context returns 500 if snapshot JSON is corrupted (line 424-427)."""
    (tmp_brain / "snapshots" / "snap1.json").write_text("{broken json")

    r = client.get("/brain/context/restore/snap1")
    assert r.status_code == 500


def test_restore_context_missing_fields_parsing(client: TestClient, tmp_brain: Path) -> None:
    """restore_context fallback values when snapshot JSON lacks index, files, or loop_state (line 428-459)."""
    (tmp_brain / "snapshots" / "snap1.json").write_text(
        json.dumps(
            {
                "snapshot_id": "snap1",
                "exported_at": "2026-01-01T12:00:00",
                # files is empty dictionary, so files.get("loop-state.json") returns None
            }
        )
    )

    r = client.get("/brain/context/restore/snap1")
    assert r.status_code == 200
    body = r.json()
    assert body["loop_state"] == {}
    assert body["index_md"] == ""
    assert body["lessons_count"] == 0
    assert body["key_files"] == {}


def test_restore_context_invalid_loop_state_json(client: TestClient, tmp_brain: Path) -> None:
    """restore_context returns empty loop_state if loop-state.json has broken content (line 434-437)."""
    (tmp_brain / "snapshots" / "snap1.json").write_text(
        json.dumps(
            {
                "snapshot_id": "snap1",
                "exported_at": "2026-01-01T12:00:00",
                "files": {"loop-state.json": {"content": "{broken json"}},
            }
        )
    )

    r = client.get("/brain/context/restore/snap1")
    assert r.status_code == 200
    assert r.json()["loop_state"] == {}


def test_current_context_read_exception_handling(client: TestClient, tmp_brain: Path) -> None:
    """current_context handles exception when reading index.md (line 487-488)."""
    (tmp_brain / "index.md").write_text("Index Content")

    with patch("pathlib.Path.read_text", side_effect=Exception("Read fail")):
        r = client.get("/brain/context/current")
        assert r.status_code == 200
        assert r.json()["index_md"] == ""


def test_get_snapshot_detail_happy_path(client: TestClient, tmp_brain: Path) -> None:
    """get_snapshot_detail returns details of a valid snapshot (line 331)."""
    (tmp_brain / "snapshots" / "snap1.json").write_text(
        json.dumps(
            {
                "snapshot_id": "snap1",
                "exported_at": "2026-01-01T12:00:00",
                "files": {"STRUCTURE.md": {"content": "ok"}},
            }
        )
    )

    r = client.get("/brain/snapshots/snap1")
    assert r.status_code == 200
    assert r.json()["files"]["STRUCTURE.md"]["content"] == "ok"
