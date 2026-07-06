"""Coverage boost T091b — brain.py endpoints (v22 plan batch 3).

Era 64.8% (70 miss). Foco em exercitar:
- list_tasks com filtros
- list_lessons com from_date + limit
- create_lesson (file write)
- get_loop_state (file read com fallback)
- _read_json_safe (filesystem utility)

Mock BRAIN_DIR para tmpdir auto-contido.
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.v1.brain import brain_router
from app.api.v1.brain import _read_json_safe


@pytest.fixture
def tmp_brain(tmp_path: Path):
    """Substitui BRAIN_DIR por tmpdir para testes isolados."""
    fake_brain = tmp_path / "fake_brain"
    fake_brain.mkdir()
    (fake_brain / "lessons").mkdir()
    (fake_brain / "tasks").mkdir()
    yield fake_brain


@pytest.fixture
def brain_app(tmp_brain: Path):
    """FastAPI app isolada com brain_router montado."""
    app = FastAPI()
    app.include_router(brain_router)
    return app


# ============================================================================
# _read_json_safe
# ============================================================================


class TestReadJsonSafe:
    def test_existing_valid_json(self, tmp_brain: Path):
        f = tmp_brain / "x.json"
        f.write_text('{"a": 1, "b": [2, 3]}')
        assert _read_json_safe(f) == {"a": 1, "b": [2, 3]}

    def test_nonexistent_returns_none(self, tmp_brain: Path):
        assert _read_json_safe(tmp_brain / "nope.json") is None

    def test_malformed_json_returns_none(self, tmp_brain: Path):
        f = tmp_brain / "broken.json"
        f.write_text("{not json}")
        assert _read_json_safe(f) is None


# ============================================================================
# Endpoints
# ============================================================================


class TestListTasksEndpoint:
    def test_returns_empty_when_tasks_dir_missing(self, brain_app: FastAPI, tmp_brain: Path):
        import shutil

        shutil.rmtree(tmp_brain / "tasks")
        client = TestClient(brain_app)
        with patch("app.api.v1.brain.BRAIN_DIR", tmp_brain):
            r = client.get("/brain/tasks")
        assert r.status_code == 200
        assert r.json() == []

    def test_returns_parsed_tasks(self, brain_app: FastAPI, tmp_brain: Path):
        (tmp_brain / "tasks" / "T001.json").write_text(
            json.dumps(
                {
                    "id": "T001",
                    "squad": "a",
                    "title": "task 1",
                    "status": "done",
                    "type": "feat",
                }
            )
        )
        client = TestClient(brain_app)
        with patch("app.api.v1.brain.BRAIN_DIR", tmp_brain):
            r = client.get("/brain/tasks")
        assert r.status_code == 200
        body = r.json()
        assert len(body) == 1
        assert body[0]["id"] == "T001"
        assert body[0]["status"] == "done"

    def test_filters_by_status(self, brain_app: FastAPI, tmp_brain: Path):
        (tmp_brain / "tasks" / "T001.json").write_text(
            json.dumps({"id": "T1", "squad": "a", "title": "x", "status": "done"})
        )
        (tmp_brain / "tasks" / "T002.json").write_text(
            json.dumps({"id": "T2", "squad": "b", "title": "y", "status": "pending"})
        )
        client = TestClient(brain_app)
        with patch("app.api.v1.brain.BRAIN_DIR", tmp_brain):
            r = client.get("/brain/tasks", params={"status": "done"})
        ids = [t["id"] for t in r.json()]
        assert ids == ["T1"]


class TestListLessonsEndpoint:
    def test_returns_empty_when_lessons_dir_missing(self, brain_app: FastAPI, tmp_brain: Path):
        import shutil

        shutil.rmtree(tmp_brain / "lessons")
        client = TestClient(brain_app)
        with patch("app.api.v1.brain.BRAIN_DIR", tmp_brain):
            r = client.get("/brain/lessons")
        assert r.status_code == 200
        assert r.json() == []

    def test_parses_first_line_as_title(self, brain_app: FastAPI, tmp_brain: Path):
        (tmp_brain / "lessons" / "130-test.md").write_text(
            "# 130 - Titulo da Lesson\n\nConteudo..."
        )
        client = TestClient(brain_app)
        with patch("app.api.v1.brain.BRAIN_DIR", tmp_brain):
            r = client.get("/brain/lessons")
        assert r.status_code == 200
        body = r.json()
        assert len(body) == 1
        assert body[0]["titulo"] == "130 - Titulo da Lesson"

    def test_respects_limit_query(self, brain_app: FastAPI, tmp_brain: Path):
        for i in range(5):
            (tmp_brain / "lessons" / f"13{i}-l.md").write_text(f"# {i}\n")
        client = TestClient(brain_app)
        with patch("app.api.v1.brain.BRAIN_DIR", tmp_brain):
            r = client.get("/brain/lessons", params={"limit": 2})
        assert len(r.json()) == 2


class TestCreateLessonEndpoint:
    def test_creates_lesson_file(self, brain_app: FastAPI, tmp_brain: Path):
        client = TestClient(brain_app)
        with patch("app.api.v1.brain.BRAIN_DIR", tmp_brain):
            r = client.post(
                "/brain/lesson",
                json={
                    "titulo": "Test Lesson pytest v22",
                    "contexto": "Contexto valido com mais de 10 chars",
                    "solucao": "Solucao valida com mais de 10 chars",
                    "codigo_ref": "app/test.py",
                },
            )
        assert r.status_code == 200
        body = r.json()
        assert body["id"].startswith("130-")  # default (sem lessons existentes)
        # Arquivo criado e conteudo presente
        files = list((tmp_brain / "lessons").glob("*.md"))
        assert len(files) == 1
        content = files[0].read_text()
        assert "Test Lesson pytest v22" in content
        assert "app/test.py" in content

    def test_validates_min_length(self, brain_app: FastAPI, tmp_brain: Path):
        client = TestClient(brain_app)
        with patch("app.api.v1.brain.BRAIN_DIR", tmp_brain):
            r = client.post(
                "/brain/lesson",
                json={
                    "titulo": "abc",  # < 5 chars
                    "contexto": "x" * 100,
                    "solucao": "y" * 100,
                },
            )
        assert r.status_code == 422  # Pydantic validation


class TestLoopStateEndpoint:
    def test_404_when_state_missing(self, brain_app: FastAPI, tmp_brain: Path):
        client = TestClient(brain_app)
        with patch("app.api.v1.brain.BRAIN_DIR", tmp_brain):
            r = client.get("/brain/loop-state")
        assert r.status_code == 404

    def test_returns_state_when_present(self, brain_app: FastAPI, tmp_brain: Path):
        (tmp_brain / "loop-state.json").write_text(
            json.dumps(
                {
                    "session_id": "s-001",
                    "current_squad": "alpha",
                    "last_task": "T100",
                    "last_commit": "abc123",
                    "next_action": "implement J091",
                    "gates": {"ruff": True, "tests": True, "coverage": False},
                    "tasks_done_today": 5,
                    "tasks_pending_today": 3,
                }
            )
        )
        client = TestClient(brain_app)
        with patch("app.api.v1.brain.BRAIN_DIR", tmp_brain):
            r = client.get("/brain/loop-state")
        assert r.status_code == 200
        body = r.json()
        assert body["session_id"] == "s-001"
        assert body["tasks_done_today"] == 5
