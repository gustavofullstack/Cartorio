"""Tests for brain_sync.py (BRAIN6 incremental VPS sync).

Validates:
- snapshot write shape (.brain/snapshots/YYYY-MM-DD.json)
- diff detection (added/removed/changed) entre 2 snapshots
- index.md section update com containers prod (added/removed)
- idempotencia (rodar 2x nao quebra, mesmo estado)
- snapshot nao vazio quando brain tem arquivos
- snapshot retorna estrutura esperada
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest

from app.services import brain_sync


@pytest.fixture
def tmp_brain(tmp_path: Path) -> Path:
    """Simula .brain/ local com snapshots dir."""
    brain = tmp_path / ".brain"
    (brain / "snapshots").mkdir(parents=True)
    (brain / "loop-state.json").write_text(
        json.dumps({"session_id": "test-1", "current_squad": "BRAIN"}),
        encoding="utf-8",
    )
    (brain / "index.md").write_text("# Index\n\n## Containers prod\n\nvazio\n", encoding="utf-8")
    return brain


@pytest.fixture
def fake_containers() -> list[dict[str, Any]]:
    """Lista simulada de containers rodando (output de `docker service ls`)."""
    return [
        {"name": "cartorio_api", "replicas": "1/1", "image": "cartorio-api:0.6.0"},
        {"name": "cartorio_redis", "replicas": "1/1", "image": "redis:7-alpine"},
        {"name": "cartorio_n8n", "replicas": "1/1", "image": "n8n:1.94"},
    ]


def test_create_snapshot_writes_dated_file(tmp_brain: Path, fake_containers: list[dict]) -> None:
    """sync_vps_incremental deve gravar .brain/snapshots/YYYY-MM-DD.json."""
    with patch.object(brain_sync, "_list_containers", return_value=fake_containers):
        result = brain_sync.sync_vps_incremental(brain_dir=tmp_brain)

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    snap_path = tmp_brain / "snapshots" / f"{today}.json"
    assert snap_path.exists()
    payload = json.loads(snap_path.read_text(encoding="utf-8"))
    assert payload["date"] == today
    assert payload["containers_count"] == len(fake_containers)
    assert result["snapshot_file"] == str(snap_path)


def test_snapshot_contains_container_state(tmp_brain: Path, fake_containers: list[dict]) -> None:
    """Snapshot deve ter state completo dos containers (added/removed/changed)."""
    with patch.object(brain_sync, "_list_containers", return_value=fake_containers):
        brain_sync.sync_vps_incremental(brain_dir=tmp_brain)

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    payload = json.loads((tmp_brain / "snapshots" / f"{today}.json").read_text())
    containers_state = payload["containers"]
    assert "cartorio_api" in containers_state
    assert containers_state["cartorio_api"]["replicas"] == "1/1"
    assert containers_state["cartorio_api"]["image"] == "cartorio-api:0.6.0"


def test_diff_detects_added_container(tmp_brain: Path) -> None:
    """2o sync com container novo deve aparecer como 'added' no diff."""
    initial = [
        {"name": "cartorio_api", "replicas": "1/1", "image": "cartorio-api:0.6.0"},
    ]
    with patch.object(brain_sync, "_list_containers", return_value=initial):
        brain_sync.sync_vps_incremental(brain_dir=tmp_brain)

    with patch.object(
        brain_sync,
        "_list_containers",
        return_value=initial + [{"name": "cartorio_redis", "replicas": "1/1", "image": "redis:7"}],
    ):
        diff = brain_sync.diff_against_last(brain_dir=tmp_brain)

    assert "cartorio_redis" in diff["added"]
    assert diff["removed"] == []
    assert diff["changed"] == []


def test_diff_detects_removed_container(tmp_brain: Path) -> None:
    """2o sync sem um container deve aparecer como 'removed'."""
    initial = [
        {"name": "cartorio_api", "replicas": "1/1", "image": "v1"},
        {"name": "cartorio_redis", "replicas": "1/1", "image": "redis:7"},
    ]
    with patch.object(brain_sync, "_list_containers", return_value=initial):
        brain_sync.sync_vps_incremental(brain_dir=tmp_brain)

    with patch.object(
        brain_sync,
        "_list_containers",
        return_value=[initial[0]],  # removeu redis
    ):
        diff = brain_sync.diff_against_last(brain_dir=tmp_brain)

    assert "cartorio_redis" in diff["removed"]
    assert diff["added"] == []


def test_diff_detects_changed_image(tmp_brain: Path) -> None:
    """Container com mesma name mas image diferente deve aparecer como 'changed'."""
    initial = [{"name": "cartorio_api", "replicas": "1/1", "image": "v0.6.0"}]
    with patch.object(brain_sync, "_list_containers", return_value=initial):
        brain_sync.sync_vps_incremental(brain_dir=tmp_brain)

    with patch.object(
        brain_sync,
        "_list_containers",
        return_value=[{"name": "cartorio_api", "replicas": "1/1", "image": "v0.6.1"}],
    ):
        diff = brain_sync.diff_against_last(brain_dir=tmp_brain)

    assert "cartorio_api" in diff["changed"]
    assert "image" in diff["changed_detail"]["cartorio_api"]


def test_diff_is_idempotent_when_no_changes(tmp_brain: Path) -> None:
    """Rodar sync 2x sem mudanca entre rodadas: diff = vazio."""
    containers = [{"name": "cartorio_api", "replicas": "1/1", "image": "v1"}]
    with patch.object(brain_sync, "_list_containers", return_value=containers):
        brain_sync.sync_vps_incremental(brain_dir=tmp_brain)

    with patch.object(brain_sync, "_list_containers", return_value=containers):
        diff = brain_sync.diff_against_last(brain_dir=tmp_brain)

    assert diff["added"] == []
    assert diff["removed"] == []
    assert diff["changed"] == []
    assert diff["unchanged_count"] == 1


def test_index_md_is_updated_with_containers_section(tmp_brain: Path) -> None:
    """sync_vps_incremental deve atualizar secao 'Containers prod' em index.md."""
    containers = [
        {"name": "cartorio_api", "replicas": "1/1", "image": "v1"},
        {"name": "cartorio_redis", "replicas": "1/1", "image": "redis:7"},
    ]
    with patch.object(brain_sync, "_list_containers", return_value=containers):
        brain_sync.sync_vps_incremental(brain_dir=tmp_brain)

    index_md = (tmp_brain / "index.md").read_text(encoding="utf-8")
    assert "## Containers prod" in index_md
    assert "cartorio_api" in index_md
    assert "cartorio_redis" in index_md
    assert "v1" in index_md


def test_no_containers_returns_empty_snapshot(tmp_brain: Path) -> None:
    """Se nenhum container, snapshot existe mas containers_count=0."""
    with patch.object(brain_sync, "_list_containers", return_value=[]):
        result = brain_sync.sync_vps_incremental(brain_dir=tmp_brain)

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    snap = json.loads((tmp_brain / "snapshots" / f"{today}.json").read_text())
    assert snap["containers_count"] == 0
    assert snap["containers"] == {}
    assert result["ok"] is True


def test_sync_when_no_previous_snapshot_returns_added(
    tmp_brain: Path, fake_containers: list[dict]
) -> None:
    """Primeira execucao (sem snapshot anterior) deve listar tudo como added."""
    with patch.object(brain_sync, "_list_containers", return_value=fake_containers):
        brain_sync.sync_vps_incremental(brain_dir=tmp_brain)

    with patch.object(brain_sync, "_list_containers", return_value=fake_containers):
        # limpa snapshot e roda de novo para simular "primeira vez"
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        (tmp_brain / "snapshots" / f"{today}.json").unlink()
        diff = brain_sync.diff_against_last(brain_dir=tmp_brain)

    assert set(diff["added"]) == {"cartorio_api", "cartorio_redis", "cartorio_n8n"}
    assert diff["removed"] == []
