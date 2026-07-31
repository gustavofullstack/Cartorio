#!/usr/bin/env python3
"""Offline, fail-closed extraction boundary for private BRAIN corpus documents.

The script intentionally has no network, LLM, embedding, hyperlink, or logging
integration. It writes sanitized derivatives only below the input quarantine.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import multiprocessing
import queue
import re
import shutil
import subprocess
import sys
import zipfile
from collections import Counter
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Final
from xml.etree import ElementTree

ALLOWED_EXTENSIONS: Final[frozenset[str]] = frozenset({".docx", ".odt", ".pdf", ".txt"})
DEFAULT_QUARANTINE: Final[Path] = (
    Path(__file__).resolve().parents[1]
    / ".private/brain-ingest-quarantine/2026-07-31-ce236ba32b01"
)
MAX_SOURCE_BYTES: Final[int] = 50 * 1024 * 1024
MAX_ARCHIVE_MEMBER_BYTES: Final[int] = 20 * 1024 * 1024
MAX_ARCHIVE_UNCOMPRESSED_BYTES: Final[int] = 50 * 1024 * 1024
MAX_UNIT_CHARS: Final[int] = 12_000
EXTRACTION_TIMEOUT_SECONDS: Final[float] = 30.0

WORD_NAMESPACE: Final[str] = (
    "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
)
ODT_TEXT_NAMESPACE: Final[str] = "{urn:oasis:names:tc:opendocument:xmlns:text:1.0}"


@dataclass(frozen=True)
class PatternSpec:
    """A PII pattern whose values never leave the process unsanitized."""

    kind: str
    pattern: re.Pattern[str]


PII_PATTERNS: Final[tuple[PatternSpec, ...]] = (
    PatternSpec("email", re.compile(r"(?i)\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b")),
    PatternSpec(
        "cnpj", re.compile(r"(?<!\d)\d{2}\.?\d{3}\.?\d{3}/?\d{4}-?\d{2}(?!\d)")
    ),
    PatternSpec("cpf", re.compile(r"(?<!\d)\d{3}\.?\d{3}\.?\d{3}-?\d{2}(?!\d)")),
    PatternSpec(
        "phone",
        re.compile(
            r"(?<!\d)(?:\+?55[ .-]*)?(?:\(?\d{2}\)?[ .-]*)?9?\d{4,5}[ .-]?\d{4}(?!\d)"
        ),
    ),
    PatternSpec("cep", re.compile(r"(?<!\d)\d{5}-?\d{3}(?!\d)")),
    PatternSpec("rg", re.compile(r"(?i)\bR\.?G\.?\s*:?\s*\d{5,14}\b")),
)
URL_PATTERN: Final[re.Pattern[str]] = re.compile(
    r"(?i)\b(?:https?|ftp)://[^\s<>{}\[\]]+"
)


class ExtractionFailure(Exception):
    """A safe, categorical extraction failure suitable for the sanitized report."""

    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


@dataclass(frozen=True)
class ExtractionError:
    """Sanitized error data; it never contains a source filename or exception message."""

    source_id: str
    format: str
    stage: str
    code: str

    def as_dict(self) -> dict[str, str]:
        return {
            "source_id": self.source_id,
            "format": self.format,
            "stage": self.stage,
            "code": self.code,
        }


@dataclass(frozen=True)
class IngestionResult:
    """Numerical result for callers and the intentionally minimal CLI output."""

    sources_discovered: int
    sources_extracted: int
    units_written: int
    is_blocked: bool

    def summary(self) -> dict[str, int | bool]:
        return {
            "sources_discovered": self.sources_discovered,
            "sources_extracted": self.sources_extracted,
            "units_written": self.units_written,
            "is_blocked": self.is_blocked,
        }


def run_ingestion(
    source_quarantine: Path, derived_dir: Path | None = None
) -> IngestionResult:
    """Extract supported local files into sanitized, blocking-on-error private derivatives."""
    source_root = source_quarantine.resolve(strict=True)
    if not source_root.is_dir():
        raise ValueError("source quarantine must be a directory")

    output_root = (derived_dir or source_root / "derived").resolve()
    _validate_output_location(source_root, output_root)
    output_root.mkdir(parents=True, exist_ok=True)

    source_paths = list(_iter_source_files(source_root, output_root))
    errors: list[ExtractionError] = []
    sources: list[dict[str, object]] = []
    units: list[dict[str, str]] = []
    extracted_sources = 0

    for source_path in source_paths:
        source_id = _source_id(source_root, source_path)
        extension = source_path.suffix.lower()
        source_format = extension.removeprefix(".") or "unknown"
        if source_path.is_symlink():
            errors.append(
                ExtractionError(
                    source_id, source_format, "inventory", "symlink_rejected"
                )
            )
            sources.append(
                {
                    "source_id": source_id,
                    "format": source_format,
                    "sha256": None,
                    "byte_size": source_path.lstat().st_size,
                    "status": "blocked",
                    "unit_count": 0,
                    "pii_counts": {},
                }
            )
            continue

        byte_size = source_path.stat().st_size
        source_record: dict[str, object] = {
            "source_id": source_id,
            "format": source_format,
            "sha256": None,
            "byte_size": byte_size,
            "status": "blocked",
            "unit_count": 0,
            "pii_counts": {},
        }

        if extension not in ALLOWED_EXTENSIONS:
            errors.append(
                ExtractionError(
                    source_id, source_format, "inventory", "unsupported_extension"
                )
            )
            sources.append(source_record)
            continue
        if byte_size > MAX_SOURCE_BYTES:
            errors.append(
                ExtractionError(
                    source_id, source_format, "inventory", "source_too_large"
                )
            )
            sources.append(source_record)
            continue

        source_record["sha256"] = _sha256_file(source_path)

        try:
            raw_units = _extract_units_with_timeout(source_path, extension)
        except ExtractionFailure as failure:
            errors.append(
                ExtractionError(source_id, source_format, "extract", failure.code)
            )
            sources.append(source_record)
            continue

        sanitized_units, pii_counts = _sanitize_units(source_id, raw_units)
        if not sanitized_units:
            errors.append(
                ExtractionError(source_id, source_format, "extract", "empty_extraction")
            )
            sources.append(source_record)
            continue

        source_record["status"] = "extracted"
        source_record["unit_count"] = len(sanitized_units)
        source_record["pii_counts"] = dict(sorted(pii_counts.items()))
        sources.append(source_record)
        units.extend(sanitized_units)
        extracted_sources += 1

    is_blocked = bool(errors)
    manifest = {
        "schema_version": 1,
        "mode": "local_offline_fail_closed",
        "is_blocked": is_blocked,
        "sources_discovered": len(source_paths),
        "sources_extracted": extracted_sources,
        "units_written": len(units),
        "sources": sources,
    }
    error_report = {
        "schema_version": 1,
        "is_blocked": is_blocked,
        "error_count": len(errors),
        "errors": [error.as_dict() for error in errors],
    }
    _write_derivatives(output_root, manifest, units, error_report)
    return IngestionResult(len(source_paths), extracted_sources, len(units), is_blocked)


def _validate_output_location(source_root: Path, output_root: Path) -> None:
    """Permit derivatives only below the private source quarantine, never alongside it."""
    try:
        relative_output = output_root.relative_to(source_root)
    except ValueError as error:
        raise ValueError(
            "derived output must stay inside the source quarantine"
        ) from error
    if not relative_output.parts:
        raise ValueError(
            "derived output must be a subdirectory of the source quarantine"
        )


def _iter_source_files(source_root: Path, output_root: Path) -> Iterable[Path]:
    """Enumerate only non-derived local filesystem entries in deterministic order."""
    for candidate in sorted(source_root.rglob("*")):
        if candidate.is_relative_to(output_root):
            continue
        if candidate.is_file() or candidate.is_symlink():
            yield candidate


def _source_id(source_root: Path, source_path: Path) -> str:
    """Create an opaque source reference without emitting its private pathname."""
    relative_path = source_path.relative_to(source_root).as_posix()
    return hashlib.sha256(relative_path.encode("utf-8")).hexdigest()


def _sha256_file(source_path: Path) -> str:
    """Hash a source file without retaining its data in memory or outputting content."""
    digest = hashlib.sha256()
    with source_path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _extract_units(source_path: Path, extension: str) -> list[tuple[str, str]]:
    """Route a locally supported document to its format-specific, side-effect-free reader."""
    try:
        if extension == ".txt":
            return _extract_txt(source_path)
        if extension == ".docx":
            return _extract_docx(source_path)
        if extension == ".odt":
            return _extract_odt(source_path)
        if extension == ".pdf":
            return _extract_pdf(source_path)
    except (OSError, UnicodeError, zipfile.BadZipFile, ElementTree.ParseError):
        raise ExtractionFailure("malformed_document") from None
    raise ExtractionFailure("unsupported_extension")


def _extract_units_with_timeout(
    source_path: Path, extension: str
) -> list[tuple[str, str]]:
    """Run each local parser in an isolated process with a hard fail-closed timeout."""
    context = multiprocessing.get_context("spawn")
    result_queue: multiprocessing.Queue[tuple[str, object]] = context.Queue(maxsize=1)
    worker = context.Process(
        target=_extract_worker, args=(str(source_path), extension, result_queue)
    )
    worker.start()
    try:
        status, payload = result_queue.get(timeout=EXTRACTION_TIMEOUT_SECONDS)
    except queue.Empty:
        _terminate_worker(worker)
        raise ExtractionFailure("extraction_timeout") from None
    finally:
        result_queue.close()

    worker.join(timeout=1)
    if worker.is_alive():
        _terminate_worker(worker)
        raise ExtractionFailure("worker_exit_timeout")
    if status != "ok":
        raise ExtractionFailure(str(payload))
    if not isinstance(payload, list):
        raise ExtractionFailure("invalid_worker_result")
    return payload


def _extract_worker(
    source_path: str,
    extension: str,
    result_queue: multiprocessing.Queue[tuple[str, object]],
) -> None:
    """Return only local extraction data or a categorical failure through an in-memory queue."""
    try:
        result_queue.put(("ok", _extract_units(Path(source_path), extension)))
    except ExtractionFailure as failure:
        result_queue.put(("error", failure.code))
    except Exception:
        result_queue.put(("error", "worker_failure"))


def _terminate_worker(worker: multiprocessing.Process) -> None:
    """Stop a stuck local parser and reap it before the next corpus item is considered."""
    worker.terminate()
    worker.join(timeout=1)
    if worker.is_alive():
        worker.kill()
        worker.join(timeout=1)


def _extract_txt(source_path: Path) -> list[tuple[str, str]]:
    """Extract UTF-8 text by line so every resulting unit remains traceable."""
    try:
        text = source_path.read_text(encoding="utf-8", errors="strict")
    except UnicodeDecodeError:
        raise ExtractionFailure("decode_failure") from None
    return [
        (f"line:{index}", line)
        for index, line in enumerate(text.splitlines(), start=1)
        if line.strip()
    ]


def _extract_docx(source_path: Path) -> list[tuple[str, str]]:
    """Extract DOCX paragraph text directly from its local OOXML archive."""
    xml_data = _read_archive_member(source_path, "word/document.xml")
    root = ElementTree.fromstring(xml_data)
    paragraphs = root.findall(f".//{WORD_NAMESPACE}p")
    return _paragraph_units(paragraphs, WORD_NAMESPACE, "paragraph")


def _extract_odt(source_path: Path) -> list[tuple[str, str]]:
    """Extract ODT paragraph text directly from its local OpenDocument archive."""
    xml_data = _read_archive_member(source_path, "content.xml")
    root = ElementTree.fromstring(xml_data)
    paragraphs = root.findall(f".//{ODT_TEXT_NAMESPACE}p")
    return _paragraph_units(paragraphs, None, "paragraph")


def _read_archive_member(source_path: Path, member_name: str) -> bytes:
    """Read a required XML part after rejecting archive expansion beyond fixed local limits."""
    with zipfile.ZipFile(source_path) as archive:
        infos = archive.infolist()
        if (
            len(infos) > 10_000
            or sum(info.file_size for info in infos) > MAX_ARCHIVE_UNCOMPRESSED_BYTES
        ):
            raise ExtractionFailure("archive_too_large")
        try:
            member = archive.getinfo(member_name)
        except KeyError:
            raise ExtractionFailure("missing_document_xml") from None
        if member.file_size > MAX_ARCHIVE_MEMBER_BYTES:
            raise ExtractionFailure("archive_member_too_large")
        return archive.read(member)


def _paragraph_units(
    paragraphs: list[ElementTree.Element],
    text_namespace: str | None,
    locator_prefix: str,
) -> list[tuple[str, str]]:
    """Preserve paragraph positions while avoiding document filenames in locators."""
    units: list[tuple[str, str]] = []
    for index, paragraph in enumerate(paragraphs, start=1):
        if text_namespace is None:
            text = "".join(paragraph.itertext()).strip()
        else:
            text_tag = f"{text_namespace}t"
            text = "".join(node.text or "" for node in paragraph.iter(text_tag)).strip()
        if text:
            units.append((f"{locator_prefix}:{index}", text))
    return units


def _extract_pdf(source_path: Path) -> list[tuple[str, str]]:
    """Extract PDF pages with local Poppler, suppressing parser diagnostics and bounding runtime."""
    pdftotext = shutil.which("pdftotext")
    if pdftotext is None:
        raise ExtractionFailure("pdf_dependency_unavailable")
    try:
        completed = subprocess.run(
            [pdftotext, "-enc", "UTF-8", str(source_path), "-"],
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            timeout=25,
        )
    except subprocess.TimeoutExpired:
        raise ExtractionFailure("extraction_timeout") from None
    if completed.returncode != 0:
        raise ExtractionFailure("pdf_extraction_failure") from None
    try:
        extracted_text = completed.stdout.decode("utf-8", errors="strict")
    except UnicodeDecodeError:
        raise ExtractionFailure("pdf_decode_failure") from None
    return [
        (f"page:{index}", page)
        for index, page in enumerate(extracted_text.split("\f"), start=1)
        if page.strip()
    ]


def _sanitize_units(
    source_id: str, raw_units: list[tuple[str, str]]
) -> tuple[list[dict[str, str]], Counter[str]]:
    """Redact local text before it becomes any persisted derivative."""
    pii_counts: Counter[str] = Counter()
    sanitized_units: list[dict[str, str]] = []
    for locator, raw_text in raw_units:
        sanitized_text, unit_counts = _sanitize_text(raw_text)
        pii_counts.update(unit_counts)
        for chunk_locator, chunk_text in _chunk_unit(locator, sanitized_text):
            sanitized_units.append(
                {
                    "source_id": source_id,
                    "locator": chunk_locator,
                    "unit_id": _sha256_text(f"{source_id}:{chunk_locator}"),
                    "sanitized_text_sha256": _sha256_text(chunk_text),
                    "text": chunk_text,
                }
            )
    return sanitized_units, pii_counts


def _sanitize_text(raw_text: str) -> tuple[str, Counter[str]]:
    """Replace recognized PII and URLs; only PII categories and counts are retained."""
    pii_counts: Counter[str] = Counter()
    sanitized_text = raw_text
    for spec in PII_PATTERNS:
        sanitized_text, replacements = spec.pattern.subn(
            f"[REDACTED:{spec.kind.upper()}]", sanitized_text
        )
        if replacements:
            pii_counts[spec.kind] += replacements
    sanitized_text = URL_PATTERN.sub("[LINK_REMOVED]", sanitized_text)
    return sanitized_text, pii_counts


def _chunk_unit(locator: str, text: str) -> Iterable[tuple[str, str]]:
    """Bound persisted unit size without losing a deterministic local locator."""
    if len(text) <= MAX_UNIT_CHARS:
        yield locator, text
        return
    for part, offset in enumerate(range(0, len(text), MAX_UNIT_CHARS), start=1):
        yield f"{locator}/part:{part}", text[offset : offset + MAX_UNIT_CHARS]


def _sha256_text(text: str) -> str:
    """Return a deterministic digest for an already-local, non-emitted string."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _write_derivatives(
    output_root: Path,
    manifest: dict[str, object],
    units: list[dict[str, str]],
    error_report: dict[str, object],
) -> None:
    """Atomically replace only files in the designated private derived directory."""
    _atomic_write_json(output_root / "manifest.sanitized.json", manifest)
    _atomic_write_text(
        output_root / "units.sanitized.jsonl",
        "".join(
            json.dumps(unit, ensure_ascii=False, sort_keys=True) + "\n"
            for unit in units
        ),
    )
    _atomic_write_json(output_root / "errors.blocking.json", error_report)


def _atomic_write_json(target: Path, payload: dict[str, object]) -> None:
    """Serialize deterministic metadata without paths, source names, or exception text."""
    _atomic_write_text(
        target, json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    )


def _atomic_write_text(target: Path, content: str) -> None:
    """Write derivative files atomically so interrupted runs never expose partial JSON."""
    temporary = target.with_name(f".{target.name}.tmp")
    temporary.write_text(content, encoding="utf-8")
    temporary.replace(target)


def main(argv: list[str] | None = None) -> int:
    """Run the local-only pipeline and print only aggregate, PII-free numerical status."""
    parser = argparse.ArgumentParser(
        description="Offline sanitized BRAIN corpus ingestion"
    )
    parser.add_argument("--source", type=Path, default=DEFAULT_QUARANTINE)
    parser.add_argument("--derived", type=Path, default=None)
    arguments = parser.parse_args(argv)
    try:
        result = run_ingestion(arguments.source, arguments.derived)
    except (OSError, ValueError):
        print(json.dumps({"is_blocked": True, "reason": "invalid_local_path"}))
        return 2
    print(json.dumps(result.summary(), sort_keys=True))
    return 2 if result.is_blocked else 0


if __name__ == "__main__":
    sys.exit(main())
