"""Security contract tests for private ZIP staging."""

from __future__ import annotations

import json
import stat
import sys
import zipfile
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts import brain_corpus_stage_zip as staging  # noqa: E402


@pytest.fixture
def private_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    root = tmp_path / ".private" / "brain-ingest-quarantine"
    monkeypatch.setattr(staging, "QUARANTINE_ROOT", root)
    return root


def _zip(path: Path, members: dict[str, bytes], *, compression: int = zipfile.ZIP_STORED) -> None:
    with zipfile.ZipFile(path, "w", compression=compression) as archive:
        for name, content in members.items():
            archive.writestr(name, content)


def test_stage_is_atomic_private_and_idempotently_verifies_existing_batch(
    tmp_path: Path, private_root: Path
) -> None:
    archive = tmp_path / "corpus.zip"
    _zip(archive, {"Cartorio/a.docx": b"doc-a", "Cartorio/b.pdf": b"doc-b"})
    destination = private_root / "batch"

    first = staging.stage_zip(archive, destination)
    second = staging.stage_zip(archive, destination)

    assert first.already_staged is False
    assert second.already_staged is True
    assert first.files == second.files == 2
    assert (destination / "a.docx").read_bytes() == b"doc-a"
    manifest_text = (destination / "MANIFEST.private.json").read_text(encoding="utf-8")
    manifest = json.loads(manifest_text)
    assert manifest["filenames_disclosed"] is False
    assert "a.docx" not in manifest_text
    assert "b.pdf" not in manifest_text


@pytest.mark.parametrize("unsafe", ["../escape.txt", "/absolute.txt", "safe/../../x.txt"])
def test_stage_rejects_path_traversal(
    tmp_path: Path, private_root: Path, unsafe: str
) -> None:
    archive = tmp_path / "unsafe.zip"
    _zip(archive, {unsafe: b"blocked"})
    destination = private_root / "batch"

    with pytest.raises(staging.StagingFailure, match="unsafe_member_path"):
        staging.stage_zip(archive, destination)
    assert not destination.exists()


def test_stage_rejects_symlink_member(tmp_path: Path, private_root: Path) -> None:
    archive = tmp_path / "symlink.zip"
    info = zipfile.ZipInfo("Cartorio/link.txt")
    info.create_system = 3
    info.external_attr = (stat.S_IFLNK | 0o777) << 16
    with zipfile.ZipFile(archive, "w") as output:
        output.writestr(info, "target")

    with pytest.raises(staging.StagingFailure, match="non_regular_member"):
        staging.stage_zip(archive, private_root / "batch")


def test_stage_rejects_casefold_collision(tmp_path: Path, private_root: Path) -> None:
    archive = tmp_path / "collision.zip"
    _zip(archive, {"Cartorio/A.txt": b"one", "Cartorio/a.txt": b"two"})

    with pytest.raises(staging.StagingFailure, match="normalized_path_collision"):
        staging.stage_zip(archive, private_root / "batch")


def test_stage_rejects_zip_bomb_ratio(tmp_path: Path, private_root: Path) -> None:
    archive = tmp_path / "bomb.zip"
    _zip(
        archive,
        {"Cartorio/compressed.txt": b"A" * 1_000_000},
        compression=zipfile.ZIP_DEFLATED,
    )

    with pytest.raises(staging.StagingFailure, match="compression_ratio_limit"):
        staging.stage_zip(archive, private_root / "batch")


def test_stage_rejects_unsupported_extension(tmp_path: Path, private_root: Path) -> None:
    archive = tmp_path / "unsupported.zip"
    _zip(archive, {"Cartorio/run.exe": b"blocked"})

    with pytest.raises(staging.StagingFailure, match="unsupported_extension"):
        staging.stage_zip(archive, private_root / "batch")


def test_stage_rejects_destination_outside_private_root(
    tmp_path: Path, private_root: Path
) -> None:
    archive = tmp_path / "corpus.zip"
    _zip(archive, {"Cartorio/a.txt": b"safe"})

    with pytest.raises(staging.StagingFailure, match="destination_outside_quarantine"):
        staging.stage_zip(archive, tmp_path / "outside")


def test_existing_batch_mismatch_never_overwrites(
    tmp_path: Path, private_root: Path
) -> None:
    archive = tmp_path / "corpus.zip"
    _zip(archive, {"Cartorio/a.txt": b"original"})
    destination = private_root / "batch"
    staging.stage_zip(archive, destination)
    (destination / "a.txt").write_bytes(b"tampered")

    with pytest.raises(staging.StagingFailure, match="existing_content_mismatch"):
        staging.stage_zip(archive, destination)
    assert (destination / "a.txt").read_bytes() == b"tampered"
