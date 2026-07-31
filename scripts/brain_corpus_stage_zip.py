#!/usr/bin/env python3
"""Stage a private BRAIN ZIP into an immutable local quarantine.

The command is deliberately offline and fail-closed. It never prints member
names and never overwrites an existing batch. Existing batches are verified by
content-hash multiset before being accepted as already staged.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import stat
import sys
import tempfile
import unicodedata
import zipfile
from collections import Counter
from dataclasses import dataclass
from datetime import date
from pathlib import Path, PurePosixPath
from typing import BinaryIO, Final

PROJECT_ROOT: Final[Path] = Path(__file__).resolve().parents[1]
QUARANTINE_ROOT: Final[Path] = PROJECT_ROOT / ".private" / "brain-ingest-quarantine"
ALLOWED_EXTENSIONS: Final[frozenset[str]] = frozenset({".docx", ".odt", ".pdf", ".txt"})
MAX_ARCHIVE_BYTES: Final[int] = 512 * 1024 * 1024
MAX_MEMBERS: Final[int] = 500
MAX_MEMBER_BYTES: Final[int] = 64 * 1024 * 1024
MAX_TOTAL_BYTES: Final[int] = 256 * 1024 * 1024
MAX_COMPRESSION_RATIO: Final[int] = 200
COPY_CHUNK_BYTES: Final[int] = 1024 * 1024


class StagingFailure(ValueError):
    """Categorical failure safe for sanitized CLI output."""

    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


@dataclass(frozen=True)
class PlannedMember:
    """Validated archive member and its normalized private target."""

    info: zipfile.ZipInfo
    target: PurePosixPath


@dataclass(frozen=True)
class StagingSummary:
    """PII-free staging outcome."""

    archive_sha256: str
    files: int
    total_uncompressed_bytes: int
    already_staged: bool

    def as_dict(self) -> dict[str, str | int | bool]:
        return {
            "archive_sha256": self.archive_sha256,
            "files": self.files,
            "total_uncompressed_bytes": self.total_uncompressed_bytes,
            "already_staged": self.already_staged,
            "mode": "local_offline_immutable_quarantine",
        }


def stage_zip(archive_path: Path, destination: Path) -> StagingSummary:
    """Validate and atomically stage ``archive_path`` below the private root."""
    if archive_path.is_symlink():
        raise StagingFailure("archive_not_regular")
    archive = archive_path.resolve(strict=True)
    if not archive.is_file():
        raise StagingFailure("archive_not_regular")
    if archive.stat().st_size > MAX_ARCHIVE_BYTES:
        raise StagingFailure("archive_too_large")

    target = destination.resolve(strict=False)
    quarantine_root = QUARANTINE_ROOT.resolve(strict=False)
    if target.parent != quarantine_root or target == quarantine_root:
        raise StagingFailure("destination_outside_quarantine")

    archive_sha256 = _sha256_file(archive)
    try:
        with zipfile.ZipFile(archive) as source:
            planned = _plan_members(source.infolist())
            if source.testzip() is not None:
                raise StagingFailure("archive_crc_failure")
            total = sum(member.info.file_size for member in planned)
            if target.exists():
                _verify_existing_batch(target, source, planned, archive_sha256)
                return StagingSummary(archive_sha256, len(planned), total, True)
            _extract_atomically(target, source, planned, archive_sha256)
    except zipfile.BadZipFile as error:
        raise StagingFailure("invalid_zip") from error
    return StagingSummary(archive_sha256, len(planned), total, False)


def _plan_members(infos: list[zipfile.ZipInfo]) -> list[PlannedMember]:
    if not infos or len(infos) > MAX_MEMBERS:
        raise StagingFailure("invalid_member_count")

    safe: list[tuple[zipfile.ZipInfo, PurePosixPath]] = []
    total = 0
    for info in infos:
        if info.flag_bits & 0x1:
            raise StagingFailure("encrypted_member")
        mode = info.external_attr >> 16
        kind = stat.S_IFMT(mode)
        if kind not in {0, stat.S_IFREG, stat.S_IFDIR}:
            raise StagingFailure("non_regular_member")

        raw_name = info.filename.replace("\\", "/")
        if "\x00" in raw_name:
            raise StagingFailure("unsafe_member_path")
        path = PurePosixPath(unicodedata.normalize("NFC", raw_name))
        if path.is_absolute() or ".." in path.parts or not path.parts:
            raise StagingFailure("unsafe_member_path")
        if info.is_dir():
            continue
        if info.file_size < 0 or info.file_size > MAX_MEMBER_BYTES:
            raise StagingFailure("member_too_large")
        total += info.file_size
        if total > MAX_TOTAL_BYTES:
            raise StagingFailure("archive_uncompressed_limit")
        ratio = info.file_size / max(1, info.compress_size)
        if ratio > MAX_COMPRESSION_RATIO:
            raise StagingFailure("compression_ratio_limit")
        safe.append((info, path))

    if not safe:
        raise StagingFailure("archive_has_no_files")
    roots = {path.parts[0].casefold() for _, path in safe if len(path.parts) > 1}
    strip_root = len(roots) == 1 and all(len(path.parts) > 1 for _, path in safe)

    planned: list[PlannedMember] = []
    collision_keys: set[str] = set()
    for info, path in safe:
        target = PurePosixPath(*path.parts[1:]) if strip_root else path
        if target.suffix.lower() not in ALLOWED_EXTENSIONS:
            raise StagingFailure("unsupported_extension")
        collision_key = target.as_posix().casefold()
        if collision_key in collision_keys:
            raise StagingFailure("normalized_path_collision")
        collision_keys.add(collision_key)
        planned.append(PlannedMember(info, target))
    return planned


def _extract_atomically(
    target: Path,
    source: zipfile.ZipFile,
    planned: list[PlannedMember],
    archive_sha256: str,
) -> None:
    target.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    scratch = Path(tempfile.mkdtemp(prefix=f".{target.name}.", dir=target.parent))
    os.chmod(scratch, 0o700)
    manifest_files: list[dict[str, str | int]] = []
    try:
        for member in planned:
            output = scratch.joinpath(*member.target.parts)
            output.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
            with source.open(member.info, "r") as input_stream, output.open("xb") as output_stream:
                digest, written = _copy_bounded(input_stream, output_stream, member.info.file_size)
            os.chmod(output, 0o600)
            manifest_files.append(
                {
                    "path_sha256": hashlib.sha256(
                        member.target.as_posix().encode("utf-8")
                    ).hexdigest(),
                    "sha256": digest,
                    "bytes": written,
                }
            )
        manifest = {
            "archive_sha256": archive_sha256,
            "source_file_count": len(manifest_files),
            "source_total_bytes": sum(int(item["bytes"]) for item in manifest_files),
            "filenames_disclosed": False,
            "files": sorted(manifest_files, key=lambda item: str(item["path_sha256"])),
        }
        manifest_path = scratch / "MANIFEST.private.json"
        manifest_path.write_text(
            json.dumps(manifest, ensure_ascii=True, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        os.chmod(manifest_path, 0o600)
        scratch.rename(target)
    except Exception:
        shutil.rmtree(scratch, ignore_errors=True)
        raise


def _verify_existing_batch(
    target: Path,
    source: zipfile.ZipFile,
    planned: list[PlannedMember],
    archive_sha256: str,
) -> None:
    if target.is_symlink() or not target.is_dir():
        raise StagingFailure("existing_batch_not_directory")
    manifest_path = target / "MANIFEST.private.json"
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise StagingFailure("existing_manifest_invalid") from error
    if manifest.get("archive_sha256") != archive_sha256:
        raise StagingFailure("existing_archive_hash_mismatch")

    archive_hashes = Counter(_sha256_stream(source.open(member.info)) for member in planned)
    local_files = [
        path
        for path in target.rglob("*")
        if path.is_file()
        and path.name != "MANIFEST.private.json"
        and "derived" not in path.relative_to(target).parts
        and ".av" not in path.relative_to(target).parts
    ]
    if any(path.is_symlink() for path in local_files):
        raise StagingFailure("existing_batch_symlink")
    local_hashes = Counter(_sha256_file(path) for path in local_files)
    if archive_hashes != local_hashes:
        raise StagingFailure("existing_content_mismatch")


def _copy_bounded(source: BinaryIO, target: BinaryIO, declared_size: int) -> tuple[str, int]:
    digest = hashlib.sha256()
    written = 0
    while chunk := source.read(COPY_CHUNK_BYTES):
        written += len(chunk)
        if written > declared_size or written > MAX_MEMBER_BYTES:
            raise StagingFailure("member_size_mismatch")
        digest.update(chunk)
        target.write(chunk)
    if written != declared_size:
        raise StagingFailure("member_size_mismatch")
    return digest.hexdigest(), written


def _sha256_stream(stream: BinaryIO) -> str:
    digest = hashlib.sha256()
    with stream:
        while chunk := stream.read(COPY_CHUNK_BYTES):
            digest.update(chunk)
    return digest.hexdigest()


def _sha256_file(path: Path) -> str:
    with path.open("rb") as stream:
        return _sha256_stream(stream)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Safely stage a private BRAIN ZIP")
    parser.add_argument("archive", type=Path)
    parser.add_argument("--destination", type=Path)
    args = parser.parse_args(argv)
    archive_hash = _sha256_file(args.archive.resolve(strict=True))
    destination = args.destination or (
        QUARANTINE_ROOT / f"{date.today().isoformat()}-{archive_hash[:12]}"
    )
    try:
        summary = stage_zip(args.archive, destination)
    except (OSError, StagingFailure) as error:
        code = error.code if isinstance(error, StagingFailure) else "filesystem_failure"
        print(json.dumps({"ok": False, "reason": code}, sort_keys=True))
        return 2
    print(json.dumps({"ok": True, **summary.as_dict()}, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
