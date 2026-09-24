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
import os
import queue
import re
import shutil
import subprocess
import sys
import tempfile
import zipfile
from collections import Counter
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import Final
from xml.etree import ElementTree

PROJECT_ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = PROJECT_ROOT / "backend"
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.services.pii import scrub as scrub_pii_canonico  # noqa: E402

ALLOWED_EXTENSIONS: Final[frozenset[str]] = frozenset({".docx", ".odt", ".pdf", ".txt"})
CONTROL_FILENAMES: Final[frozenset[str]] = frozenset({"MANIFEST.private.json"})
DEFAULT_QUARANTINE: Final[Path] = (
    PROJECT_ROOT / ".private/brain-ingest-quarantine/2026-07-31-ce236ba32b01"
)
MAX_SOURCE_BYTES: Final[int] = 50 * 1024 * 1024
MAX_ARCHIVE_MEMBER_BYTES: Final[int] = 20 * 1024 * 1024
MAX_ARCHIVE_UNCOMPRESSED_BYTES: Final[int] = 50 * 1024 * 1024
MAX_UNIT_CHARS: Final[int] = 12_000
EXTRACTION_TIMEOUT_SECONDS: Final[float] = 90.0
OCR_MAX_PAGES: Final[int] = 5
OCR_MAX_RENDERED_BYTES: Final[int] = 80 * 1024 * 1024
OCR_RENDER_TIMEOUT_SECONDS: Final[int] = 60
OCR_PAGE_TIMEOUT_SECONDS: Final[int] = 20

WORD_NAMESPACE: Final[str] = (
    "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
)
WORD_PARAGRAPH: Final[str] = f"{WORD_NAMESPACE}p"
WORD_TABLE: Final[str] = f"{WORD_NAMESPACE}tbl"
WORD_ROW: Final[str] = f"{WORD_NAMESPACE}tr"
WORD_CELL: Final[str] = f"{WORD_NAMESPACE}tc"
WORD_TEXT: Final[str] = f"{WORD_NAMESPACE}t"
WORD_TEXTBOX: Final[str] = f"{WORD_NAMESPACE}txbxContent"
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
RawUnit = tuple[str, str] | tuple[str, str, bool]


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
    output_root.mkdir(mode=0o700, parents=True, exist_ok=True)
    output_root.chmod(0o700)

    source_paths = list(_iter_source_files(source_root, output_root))
    errors: list[ExtractionError] = []
    sources: list[dict[str, object]] = []
    units: list[dict[str, object]] = []
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
            raw_units = _extract_units_with_timeout(source_path, extension, output_root)
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
        "automatic_promotion_allowed": False,
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
        if candidate.name in CONTROL_FILENAMES:
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


def _extract_units(
    source_path: Path, extension: str, scratch_dir: Path | None = None
) -> list[RawUnit]:
    """Route a locally supported document to its format-specific, side-effect-free reader."""
    try:
        if extension == ".txt":
            return _extract_txt(source_path)
        if extension == ".docx":
            return _extract_docx(source_path)
        if extension == ".odt":
            return _extract_odt(source_path)
        if extension == ".pdf":
            return _extract_pdf(source_path, scratch_dir)
    except (OSError, UnicodeError, zipfile.BadZipFile, ElementTree.ParseError):
        raise ExtractionFailure("malformed_document") from None
    raise ExtractionFailure("unsupported_extension")


def _extract_units_with_timeout(
    source_path: Path, extension: str, scratch_dir: Path
) -> list[RawUnit]:
    """Run each local parser in an isolated process with a hard fail-closed timeout."""
    context = multiprocessing.get_context("spawn")
    result_queue: multiprocessing.Queue[tuple[str, object]] = context.Queue(maxsize=1)
    worker = context.Process(
        target=_extract_worker,
        args=(str(source_path), extension, str(scratch_dir), result_queue),
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
    scratch_dir: str,
    result_queue: multiprocessing.Queue[tuple[str, object]],
) -> None:
    """Return only local extraction data or a categorical failure through an in-memory queue."""
    try:
        result_queue.put(
            ("ok", _extract_units(Path(source_path), extension, Path(scratch_dir)))
        )
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
    """Extract DOCX body, tables, textboxes and auxiliary parts with stable locators."""
    xml_data = _read_archive_member(source_path, "word/document.xml")
    root = ElementTree.fromstring(xml_data)
    body = root.find(f".//{WORD_NAMESPACE}body")
    units = _docx_structured_units(body if body is not None else root, "")
    for section, xml_part in _read_docx_auxiliary_parts(source_path):
        auxiliary_root = ElementTree.fromstring(xml_part)
        units.extend(_docx_structured_units(auxiliary_root, f"{section}/"))
    return units


def _read_docx_auxiliary_parts(source_path: Path) -> list[tuple[str, bytes]]:
    """Read only allowlisted local OOXML text parts after applying archive limits."""
    allowed = re.compile(
        r"word/(?:(header|footer)(\d+)\.xml|(footnotes|endnotes|comments)\.xml)"
    )
    parts: list[tuple[str, bytes]] = []
    with zipfile.ZipFile(source_path) as archive:
        infos = archive.infolist()
        _validate_archive_limits(infos)
        for info in infos:
            match = allowed.fullmatch(info.filename)
            if match is None:
                continue
            if info.file_size > MAX_ARCHIVE_MEMBER_BYTES:
                raise ExtractionFailure("archive_member_too_large")
            section = (
                f"{match.group(1)}:{match.group(2)}"
                if match.group(1)
                else str(match.group(3))
            )
            parts.append((section, archive.read(info)))
    return sorted(parts, key=lambda item: item[0])


def _docx_structured_units(
    root: ElementTree.Element, prefix: str
) -> list[tuple[str, str]]:
    """Walk OOXML blocks without counting textbox text again in its parent paragraph."""
    units: list[tuple[str, str]] = []
    paragraph_index = 0
    table_index = 0
    textbox_index = 0

    def add_paragraph(paragraph: ElementTree.Element, locator: str) -> None:
        nonlocal textbox_index
        text = _docx_text_without_textboxes(paragraph)
        if text:
            units.append((f"{prefix}{locator}", text))
        for textbox in paragraph.findall(f".//{WORD_TEXTBOX}"):
            textbox_index += 1
            for inner_index, inner in enumerate(
                textbox.findall(f".//{WORD_PARAGRAPH}"), start=1
            ):
                inner_text = _docx_text_without_textboxes(inner)
                if inner_text:
                    units.append(
                        (
                            f"{prefix}textbox:{textbox_index}/paragraph:{inner_index}",
                            inner_text,
                        )
                    )

    def walk(container: ElementTree.Element) -> None:
        nonlocal paragraph_index, table_index
        for child in list(container):
            if child.tag == WORD_PARAGRAPH:
                paragraph_index += 1
                add_paragraph(child, f"paragraph:{paragraph_index}")
                continue
            if child.tag == WORD_TABLE:
                table_index += 1
                for row_index, row in enumerate(
                    child.findall(f"./{WORD_ROW}"), start=1
                ):
                    for cell_index, cell in enumerate(
                        row.findall(f"./{WORD_CELL}"), start=1
                    ):
                        for cell_paragraph_index, paragraph in enumerate(
                            cell.findall(f"./{WORD_PARAGRAPH}"), start=1
                        ):
                            add_paragraph(
                                paragraph,
                                f"table:{table_index}/row:{row_index}/cell:{cell_index}/"
                                f"paragraph:{cell_paragraph_index}",
                            )
                continue
            walk(child)

    walk(root)
    return units


def _docx_text_without_textboxes(paragraph: ElementTree.Element) -> str:
    """Collect text nodes while excluding nested textbox containers."""
    fragments: list[str] = []

    def visit(node: ElementTree.Element) -> None:
        if node.tag == WORD_TEXTBOX:
            return
        if node.tag == WORD_TEXT and node.text:
            fragments.append(node.text)
        for child in list(node):
            visit(child)

    visit(paragraph)
    return "".join(fragments).strip()


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
        _validate_archive_limits(infos)
        try:
            member = archive.getinfo(member_name)
        except KeyError:
            raise ExtractionFailure("missing_document_xml") from None
        if member.file_size > MAX_ARCHIVE_MEMBER_BYTES:
            raise ExtractionFailure("archive_member_too_large")
        return archive.read(member)


def _validate_archive_limits(infos: list[zipfile.ZipInfo]) -> None:
    if (
        len(infos) > 10_000
        or sum(info.file_size for info in infos) > MAX_ARCHIVE_UNCOMPRESSED_BYTES
    ):
        raise ExtractionFailure("archive_too_large")


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


def _extract_pdf(source_path: Path, scratch_dir: Path | None = None) -> list[RawUnit]:
    """Extract PDF pages with local Poppler, suppressing parser diagnostics and bounding runtime."""
    pdftotext = shutil.which("pdftotext")
    if pdftotext is None:
        raise ExtractionFailure("pdf_dependency_unavailable")
    try:
        completed = subprocess.run(
            [pdftotext, "-layout", "-enc", "UTF-8", str(source_path), "-"],
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
    text_units = [
        (f"page:{index}", page)
        for index, page in enumerate(extracted_text.split("\f"), start=1)
        if page.strip()
    ]
    if text_units:
        return text_units
    if scratch_dir is None:
        raise ExtractionFailure("ocr_scratch_unavailable")
    return _extract_pdf_with_local_ocr(source_path, scratch_dir)


def _extract_pdf_with_local_ocr(source_path: Path, scratch_dir: Path) -> list[RawUnit]:
    """OCR a textless PDF locally, bounded by page, image-size, and subprocess time limits."""
    pdftoppm = shutil.which("pdftoppm")
    tesseract = shutil.which("tesseract")
    if pdftoppm is None or tesseract is None:
        raise ExtractionFailure("ocr_dependency_unavailable")
    page_count = _pdf_page_count(source_path)
    if page_count > OCR_MAX_PAGES:
        raise ExtractionFailure("ocr_page_limit")
    language = _local_ocr_language(tesseract)
    if language is None:
        raise ExtractionFailure("ocr_language_unavailable")

    with tempfile.TemporaryDirectory(prefix=".ocr-", dir=scratch_dir) as temporary_dir:
        temporary_path = Path(temporary_dir)
        prefix = temporary_path / "page"
        try:
            completed = subprocess.run(
                [
                    pdftoppm,
                    "-png",
                    "-r",
                    "150",
                    "-scale-to",
                    "2000",
                    "-f",
                    "1",
                    "-l",
                    str(page_count),
                    str(source_path),
                    str(prefix),
                ],
                check=False,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=OCR_RENDER_TIMEOUT_SECONDS,
            )
        except subprocess.TimeoutExpired:
            raise ExtractionFailure("ocr_render_timeout") from None
        if completed.returncode != 0:
            raise ExtractionFailure("ocr_render_failure")

        images = sorted(temporary_path.glob("page-*.png"))
        if len(images) != page_count:
            raise ExtractionFailure("ocr_render_failure")
        if sum(image.stat().st_size for image in images) > OCR_MAX_RENDERED_BYTES:
            raise ExtractionFailure("ocr_render_limit")
        return _ocr_rendered_pages(tesseract, language, images)


def _pdf_page_count(source_path: Path) -> int:
    """Read PDF page count locally without emitting parser output."""
    pdfinfo = shutil.which("pdfinfo")
    if pdfinfo is None:
        raise ExtractionFailure("ocr_dependency_unavailable")
    try:
        completed = subprocess.run(
            [pdfinfo, str(source_path)],
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            timeout=OCR_RENDER_TIMEOUT_SECONDS,
        )
    except subprocess.TimeoutExpired:
        raise ExtractionFailure("ocr_page_count_timeout") from None
    if completed.returncode != 0:
        raise ExtractionFailure("ocr_page_count_failure")
    match = re.search(rb"(?m)^Pages:\s*(\d+)\s*$", completed.stdout)
    if match is None:
        raise ExtractionFailure("ocr_page_count_failure")
    return int(match.group(1))


def _local_ocr_language(tesseract: str) -> str | None:
    """Select an installed local OCR language without reaching a package registry or network."""
    try:
        completed = subprocess.run(
            [tesseract, "--list-langs"],
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            timeout=OCR_RENDER_TIMEOUT_SECONDS,
        )
    except subprocess.TimeoutExpired:
        return None
    if completed.returncode != 0:
        return None
    languages = set(completed.stdout.decode("utf-8", errors="ignore").splitlines())
    if "por" in languages:
        return "por"
    if "eng" in languages:
        return "eng"
    return None


def _ocr_rendered_pages(
    tesseract: str, language: str, images: list[Path]
) -> list[RawUnit]:
    """Extract each rendered page separately so the persisted locator stays page-specific."""
    units: list[RawUnit] = []
    for index, image in enumerate(images, start=1):
        try:
            completed = subprocess.run(
                [tesseract, str(image), "stdout", "-l", language],
                check=False,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                timeout=OCR_PAGE_TIMEOUT_SECONDS,
            )
        except subprocess.TimeoutExpired:
            raise ExtractionFailure("ocr_page_timeout") from None
        if completed.returncode != 0:
            raise ExtractionFailure("ocr_page_failure")
        try:
            page_text = completed.stdout.decode("utf-8", errors="strict").strip()
        except UnicodeDecodeError:
            raise ExtractionFailure("ocr_decode_failure") from None
        if page_text:
            units.append((f"page:{index}", page_text, True))
    return units


def _sanitize_units(
    source_id: str, raw_units: list[RawUnit]
) -> tuple[list[dict[str, object]], Counter[str]]:
    """Redact local text before it becomes any persisted derivative."""
    pii_counts: Counter[str] = Counter()
    sanitized_units: list[dict[str, object]] = []
    for raw_unit in raw_units:
        locator, raw_text = raw_unit[:2]
        is_ocr = len(raw_unit) == 3 and raw_unit[2]
        sanitized_text, unit_counts = _sanitize_text(raw_text)
        pii_counts.update(unit_counts)
        for chunk_locator, chunk_text in _chunk_unit(locator, sanitized_text):
            unit: dict[str, object] = {
                "source_id": source_id,
                "locator": chunk_locator,
                "unit_id": _sha256_text(f"{source_id}:{chunk_locator}"),
                "sanitized_text_sha256": _sha256_text(chunk_text),
                "text": chunk_text,
            }
            if is_ocr:
                unit["ocr"] = True
                unit["ocr_confidence"] = "unavailable"
                unit["requires_human_review"] = True
            sanitized_units.append(unit)
    return sanitized_units, pii_counts


def _sanitize_text(raw_text: str) -> tuple[str, Counter[str]]:
    """Apply the corpus masks and then the canonical backend PII scrubber."""
    pii_counts: Counter[str] = Counter()
    sanitized_text = raw_text
    for spec in PII_PATTERNS:
        sanitized_text, replacements = spec.pattern.subn(
            f"[REDACTED:{spec.kind.upper()}]", sanitized_text
        )
        if replacements:
            pii_counts[spec.kind] += replacements
    sanitized_text = URL_PATTERN.sub("[LINK_REMOVED]", sanitized_text)
    canonical_result = scrub_pii_canonico(sanitized_text)
    sanitized_text = canonical_result.text
    pii_counts.update(canonical_result.findings)
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
    units: list[dict[str, object]],
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
    """Atomically write a derivative that is never broader than owner-only."""
    temporary = target.with_name(f".{target.name}.tmp")
    descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        temporary.replace(target)
        target.chmod(0o600)
    except BaseException:
        temporary.unlink(missing_ok=True)
        raise


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
