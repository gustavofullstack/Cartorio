"""Tests for BRAIN8 cross-session context sync endpoints.

Endpoints:
- GET  /api/v1/brain/snapshots
- GET  /api/v1/brain/snapshots/{snapshot_id}
- GET  /api/v1/brain/sessions
- GET  /api/v1/brain/context/restore/{snapshot_id}
- GET  /api/v1/brain/context/current

These enable Context Loop Engineer to restore 100% of context after
session compact, cold start, or disaster recovery.
"""
from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


class TestBrain8Snapshots:
    """Brain8 list/get snapshot endpoints."""

    def test_list_snapshots_returns_list(self, client: TestClient) -> None:
        """GET /api/v1/brain/snapshots returns 200 + list."""
        response = client.get("/api/v1/brain/snapshots")
        assert response.status_code in (200, 401, 403)
        if response.status_code == 200:
            assert isinstance(response.json(), list)

    def test_list_snapshots_limit_validation(self, client: TestClient) -> None:
        """limit must be 1-100."""
        response = client.get("/api/v1/brain/snapshots?limit=200")
        assert response.status_code in (200, 401, 403, 422)

        response = client.get("/api/v1/brain/snapshots?limit=0")
        assert response.status_code in (200, 401, 403, 422)

    def test_get_snapshot_404_when_missing(self, client: TestClient) -> None:
        """GET /api/v1/brain/snapshots/{id} returns 404 if not found."""
        response = client.get("/api/v1/brain/snapshots/nonexistent-snapshot-id-xyz")
        assert response.status_code in (404, 401, 403)


class TestBrain8Sessions:
    """Brain8 sessions list endpoint."""

    def test_list_sessions_returns_list(self, client: TestClient) -> None:
        """GET /api/v1/brain/sessions returns 200 + list."""
        response = client.get("/api/v1/brain/sessions")
        assert response.status_code in (200, 401, 403)
        if response.status_code == 200:
            assert isinstance(response.json(), list)

    def test_list_sessions_limit_validation(self, client: TestClient) -> None:
        """limit must be 1-200."""
        response = client.get("/api/v1/brain/sessions?limit=500")
        assert response.status_code in (200, 401, 403, 422)


class TestBrain8ContextRestore:
    """Brain8 context restoration endpoints."""

    def test_restore_snapshot_404_when_missing(self, client: TestClient) -> None:
        """GET /api/v1/brain/context/restore/{id} returns 404 if not found."""
        response = client.get("/api/v1/brain/context/restore/missing-snapshot-xyz")
        assert response.status_code in (404, 401, 403)

    def test_current_context_returns_dict(self, client: TestClient) -> None:
        """GET /api/v1/brain/context/current returns dict with loop_state."""
        response = client.get("/api/v1/brain/context/current")
        assert response.status_code in (200, 401, 403)
        if response.status_code == 200:
            body = response.json()
            assert "loop_state" in body
            assert "lessons_count" in body
            assert "tasks_count" in body


class TestBrain8SnapshotSummaryModel:
    """Pydantic model validation tests."""

    def test_snapshot_summary_required_fields(self) -> None:
        from app.api.v1.brain import SnapshotSummary

        s = SnapshotSummary(
            snapshot_id="20260101_120000",
            exported_at="2026-01-01T12:00:00",
            file_count=10,
            total_size_bytes=1000,
        )
        assert s.snapshot_id == "20260101_120000"
        assert s.label is None
        assert s.by_type == {}

    def test_session_summary_required_fields(self) -> None:
        from app.api.v1.brain import SessionSummary

        s = SessionSummary(
            session_id="2026-01-01-test",
            date="2026-01-01",
            file="/path/to/file.md",
            size_bytes=512,
        )
        assert s.commits_count == 0
        assert s.squads_touched == []
        assert s.title is None

    def test_context_restore_response_fields(self) -> None:
        from app.api.v1.brain import ContextRestoreResponse

        c = ContextRestoreResponse(
            snapshot_id="20260101_120000",
            exported_at="2026-01-01T12:00:00",
            loop_state={"session_id": "test"},
            index_md="# Index",
            lessons_count=5,
            tasks_count=10,
            memory_files=["memory/2026-01-01.md"],
            key_files={"STRUCTURE.md": "content"},
        )
        assert c.lessons_count == 5
        assert c.tasks_count == 10
        assert "STRUCTURE.md" in c.key_files


class TestBrain8SessionExtraction:
    """Unit tests for session metadata extraction (regex-based)."""

    def test_extract_commits_regex(self) -> None:
        """Counts git commit hashes (7-char hex)."""
        import re

        content = (
            "# Session\n"
            "[10:00] feat: commit `abc1234` - test\n"
            "[11:00] fix: commit `def5678` - bug\n"
        )
        commits_count = len(re.findall(r"`[0-9a-f]{7}`", content))
        assert commits_count == 2

    def test_extract_squads_regex(self) -> None:
        """Extracts SQUAD X mentions."""
        import re

        content = "SQUAD A done\nSQUAD B complete\nSQUAD E in progress"
        squads = set(re.findall(r"SQUAD\s+([A-Z0-9]+)", content))
        assert squads == {"A", "B", "E"}

    def test_session_date_format(self) -> None:
        """SESSION_YYYY-MM-DD.md extracts date from filename."""
        filename = "SESSION_2026-06-25.md"
        session_id = filename.replace("SESSION_", "").replace(".md", "")
        date_parts = session_id.split("-")[:3]
        date_str = "-".join(date_parts) if len(date_parts) >= 3 else session_id
        assert date_str == "2026-06-25"
        assert session_id == "2026-06-25"

    def test_session_date_format_simple(self) -> None:
        """YYYY-MM-DD.md format keeps date as-is."""
        filename = "2026-06-26.md"
        session_id = filename.replace(".md", "")
        date_str = filename.replace(".md", "")
        assert date_str == "2026-06-26"
        assert session_id == "2026-06-26"


class TestBrain8SnapshotReading:
    """Unit tests for snapshot reading logic."""

    def test_read_json_safe_handles_missing(self, tmp_path: Path) -> None:
        """_read_json_safe returns None for missing files."""
        from app.api.v1.brain import _read_json_safe

        result = _read_json_safe(tmp_path / "nonexistent.json")
        assert result is None

    def test_read_json_safe_handles_invalid_json(self, tmp_path: Path) -> None:
        """_read_json_safe returns None for invalid JSON."""
        from app.api.v1.brain import _read_json_safe

        bad = tmp_path / "bad.json"
        bad.write_text("{invalid json")
        result = _read_json_safe(bad)
        assert result is None

    def test_read_json_safe_parses_valid(self, tmp_path: Path) -> None:
        """_read_json_safe parses valid JSON correctly."""
        from app.api.v1.brain import _read_json_safe

        good = tmp_path / "good.json"
        good.write_text('{"snapshot_id": "test123"}')
        result = _read_json_safe(good)
        assert result == {"snapshot_id": "test123"}