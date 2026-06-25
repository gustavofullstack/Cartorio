"""Testes do Cross-session Context Sync (BRAIN8)."""
from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

import pytest

# Monkey-patch BRAIN_ROOT e SNAPSHOTS_DIR antes de importar
_test_dir = tempfile.mkdtemp(prefix="brain_test_")
os.environ["BRAIN_TEST_DIR"] = _test_dir

# Cria estrutura minima de brain fake
_brain = Path(_test_dir) / "brain"
_brain.mkdir()
(_brain / "memory").mkdir()
(_brain / "lessons").mkdir()
(_brain / "snapshots").mkdir()
(_brain / "loop-state.json").write_text(json.dumps({
    "current_squad": "TEST",
    "pytest_passed": 100,
    "gates": {"mypy": 0, "ruff": 0},
}, indent=2))
(_brain / "index.md").write_text("# Brain Index\n\nStatus: OK\n")
(_brain / "lessons" / "lessons-sessao.md").write_text(
    "# Lessons\n\n## L999\nTeste lesson\n"
)

# Agora importa brain.sync
import sys
sys.path.insert(0, str(_brain.parent))
import brain.sync as sync_mod
sync_mod.BRAIN_ROOT = _brain
sync_mod.SNAPSHOTS_DIR = _brain / "snapshots"


def test_export_snapshot_cria_arquivo() -> None:
    snap = sync_mod.export_snapshot(label="test-export")
    assert snap["label"] == "test-export"
    assert snap["stats"]["total_files"] >= 3  # index, lessons, loop-state
    assert "loop-state.json" in snap["files"]
    assert "index.md" in snap["files"]


def test_list_snapshots_retorna_criados() -> None:
    sync_mod.export_snapshot(label="list-test-1")
    sync_mod.export_snapshot(label="list-test-2")
    snaps = sync_mod.list_snapshots()
    assert len(snaps) >= 2
    labels = [s["label"] for s in snaps]
    assert "list-test-1" in labels or "list-test-2" in labels


def test_import_snapshot_restaura_arquivos() -> None:
    # Modifica brain e exporta
    (_brain / "index.md").write_text("# Brain Index v1\n")
    snap = sync_mod.export_snapshot(label="before-restore")
    snap_id = snap["snapshot_id"]

    # Modifica brain novamente
    (_brain / "index.md").write_text("# Brain Index MODIFIED\n")

    # Restaura
    snap_file = f"{snap_id}.json"
    result = sync_mod.import_snapshot(snap_file)
    assert "error" not in result
    assert result["restored"] >= 1

    # Verifica que restaurou
    content = (_brain / "index.md").read_text()
    assert "v1" in content  # versao antes da modificacao


def test_diff_snapshots_detecta_mudancas() -> None:
    # Cria snapshot A
    (_brain / "index.md").write_text("# Index A\n")
    snap_a = sync_mod.export_snapshot(label="diff-a")
    snap_a_id = snap_a["snapshot_id"]

    # Modifica
    (_brain / "index.md").write_text("# Index B MODIFICADO\n")

    # Cria snapshot B
    snap_b = sync_mod.export_snapshot(label="diff-b")
    snap_b_id = snap_b["snapshot_id"]

    # Diff
    diff = sync_mod.diff_snapshots(f"{snap_a_id}.json", f"{snap_b_id}.json")
    assert "error" not in diff
    assert "index.md" in diff["modified"]


def test_diff_snapshots_detecta_adicoes() -> None:
    # Snapshot A
    (_brain / "lessons" / "old.md").write_text("# Old\n")
    snap_a = sync_mod.export_snapshot(label="add-a")
    snap_a_id = snap_a["snapshot_id"]

    # Adiciona novo arquivo
    (_brain / "lessons" / "new.md").write_text("# New\n")

    # Snapshot B
    snap_b = sync_mod.export_snapshot(label="add-b")
    snap_b_id = snap_b["snapshot_id"]

    # Diff
    diff = sync_mod.diff_snapshots(f"{snap_a_id}.json", f"{snap_b_id}.json")
    assert "lessons/new.md" in diff["added"]


def test_cleanup_snapshots_remove_antigos() -> None:
    # Cria 5 snapshots
    for i in range(5):
        (_brain / "index.md").write_text(f"# V{i}\n")
        sync_mod.export_snapshot(label=f"cleanup-{i}")

    result = sync_mod.cleanup_snapshots(keep_last=2)
    assert result["deleted"] == 3
    assert result["kept"] == 2

    # Verifica que apenas 2 restam
    remaining = list(_brain.glob("snapshots/*.json"))
    assert len(remaining) == 2


def test_export_idempotente() -> None:
    """Exportar 2x com mesmo conteudo nao deve falhar."""
    snap1 = sync_mod.export_snapshot(label="idem")
    snap2 = sync_mod.export_snapshot(label="idem-2")
    # IDs diferentes (incluem timestamp)
    assert snap1["snapshot_id"] != snap2["snapshot_id"]


def test_snapshot_inclui_py_files() -> None:
    """Snapshot inclui arquivos Python (sync.py, etc)."""
    snap = sync_mod.export_snapshot(label="include-py")
    py_files = [k for k in snap["files"] if k.endswith(".py")]
    # Deve incluir pelo menos sync.py
    assert any("sync.py" in f for f in py_files)


def test_snapshot_inclui_stats_por_tipo() -> None:
    """Snapshot tem stats agregados por tipo de arquivo."""
    snap = sync_mod.export_snapshot(label="stats-test")
    stats = snap["stats"]
    assert "by_type" in stats
    assert stats["by_type"]["md"] >= 1
    assert stats["by_type"]["json"] >= 1
    assert "total_files" in stats
    assert "total_size_bytes" in stats
