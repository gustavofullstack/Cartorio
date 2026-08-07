"""Contract tests for the offline, private BRAIN corpus ingestion boundary."""

from __future__ import annotations

import hashlib
import json
import stat
import sys
import zipfile
from pathlib import Path
from unittest.mock import patch

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.brain_corpus_ingest import _extract_pdf, run_ingestion  # noqa: E402


def _write_docx(path: Path, text: str) -> None:
    """Create the smallest DOCX fixture needed to exercise local extraction."""
    document_xml = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
        f"<w:body><w:p><w:r><w:t>{text}</w:t></w:r></w:p></w:body></w:document>"
    )
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("word/document.xml", document_xml)


def _write_odt(path: Path, text: str) -> None:
    """Create the smallest ODT fixture needed to exercise local extraction."""
    content_xml = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        "<office:document-content "
        'xmlns:office="urn:oasis:names:tc:opendocument:xmlns:office:1.0" '
        'xmlns:text="urn:oasis:names:tc:opendocument:xmlns:text:1.0">'
        f"<office:body><office:text><text:p>{text}</text:p></office:text></office:body>"
        "</office:document-content>"
    )
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("content.xml", content_xml)


def test_ingestion_writes_only_sanitized_derivatives_and_blocks_partial_errors(
    tmp_path: Path,
) -> None:
    """Output has no source names or PII values, while failures remain blocking."""
    source_dir = tmp_path / "quarantine"
    source_dir.mkdir()
    raw_text = (
        "Contato pessoa@example.invalid CPF 529.982.247-25 telefone (34) 99999-0000 "
        "link https://example.invalid/documento"
    )
    source_file = source_dir / "sensitive.txt"
    source_file.write_text(raw_text, encoding="utf-8")
    (source_dir / "unsupported.bin").write_bytes(b"not a permitted corpus document")
    original_sha256 = hashlib.sha256(source_file.read_bytes()).hexdigest()

    result = run_ingestion(source_dir, source_dir / "derived")

    assert result.is_blocked is True
    assert result.sources_discovered == 2
    assert result.sources_extracted == 1
    assert source_file.read_text(encoding="utf-8") == raw_text
    assert hashlib.sha256(source_file.read_bytes()).hexdigest() == original_sha256

    manifest_text = (source_dir / "derived" / "manifest.sanitized.json").read_text(encoding="utf-8")
    units_text = (source_dir / "derived" / "units.sanitized.jsonl").read_text(encoding="utf-8")
    errors_text = (source_dir / "derived" / "errors.blocking.json").read_text(encoding="utf-8")
    for forbidden in (
        "sensitive.txt",
        "unsupported.bin",
        "pessoa@example.invalid",
        "529.982.247-25",
        "https://example.invalid/documento",
    ):
        assert forbidden not in manifest_text
        assert forbidden not in units_text
        assert forbidden not in errors_text

    manifest = json.loads(manifest_text)
    unit = json.loads(units_text)
    errors = json.loads(errors_text)
    assert manifest["is_blocked"] is True
    assert manifest["sources"][0]["pii_counts"] == {"cpf": 1, "email": 1, "phone": 1}
    assert unit["locator"] == "line:1"
    assert unit["sanitized_text_sha256"]
    assert "[REDACTED:EMAIL]" in unit["text"]
    assert "[LINK_REMOVED]" in unit["text"]
    assert errors["errors"][0]["code"] == "unsupported_extension"
    assert "source_id" in errors["errors"][0]
    assert "path" not in errors["errors"][0]


def test_ingestion_extracts_local_docx_and_odt_with_stable_locators(tmp_path: Path) -> None:
    """Office formats are extracted through archive XML, without network or office automation."""
    source_dir = tmp_path / "quarantine"
    source_dir.mkdir()
    _write_docx(source_dir / "document.docx", "Primeiro bloco")
    _write_odt(source_dir / "document.odt", "Segundo bloco")

    result = run_ingestion(source_dir, source_dir / "derived")

    assert result.is_blocked is False
    units = [
        json.loads(line)
        for line in (source_dir / "derived" / "units.sanitized.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()
    ]
    assert {unit["locator"] for unit in units} == {"paragraph:1"}
    assert all(len(unit["source_id"]) == 64 for unit in units)
    assert all(len(unit["sanitized_text_sha256"]) == 64 for unit in units)


def test_docx_preserves_tables_textboxes_and_auxiliary_parts_without_duplication(
    tmp_path: Path,
) -> None:
    source_dir = tmp_path / "quarantine"
    source_dir.mkdir()
    path = source_dir / "structured.docx"
    document_xml = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
        "<w:body>"
        "<w:p><w:r><w:t>Corpo</w:t></w:r>"
        "<w:r><w:txbxContent><w:p><w:r><w:t>Caixa</w:t></w:r></w:p>"
        "</w:txbxContent></w:r></w:p>"
        "<w:tbl><w:tr><w:tc><w:p><w:r><w:t>Célula</w:t></w:r></w:p>"
        "</w:tc></w:tr></w:tbl>"
        "</w:body></w:document>"
    )
    header_xml = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<w:hdr xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
        "<w:p><w:r><w:t>Cabeçalho</w:t></w:r></w:p></w:hdr>"
    )
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("word/document.xml", document_xml)
        archive.writestr("word/header1.xml", header_xml)

    result = run_ingestion(source_dir, source_dir / "derived")

    assert result.is_blocked is False
    units = [
        json.loads(line)
        for line in (source_dir / "derived" / "units.sanitized.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()
    ]
    by_locator = {unit["locator"]: unit["text"] for unit in units}
    assert by_locator == {
        "paragraph:1": "Corpo",
        "textbox:1/paragraph:1": "Caixa",
        "table:1/row:1/cell:1/paragraph:1": "Célula",
        "header:1/paragraph:1": "Cabeçalho",
    }
    assert sum(unit["text"] == "Caixa" for unit in units) == 1


def test_ingestion_applies_canonical_scrubber_and_owner_only_permissions(tmp_path: Path) -> None:
    source_dir = tmp_path / "quarantine"
    source_dir.mkdir(mode=0o700)
    (source_dir / "document.txt").write_text(
        "Data 31/07/2026 e contato (34) 99999-0000",
        encoding="utf-8",
    )

    result = run_ingestion(source_dir, source_dir / "derived")

    assert result.is_blocked is False
    derived = source_dir / "derived"
    unit = json.loads((derived / "units.sanitized.jsonl").read_text(encoding="utf-8"))
    assert "31/07/2026" not in unit["text"]
    assert "99999-0000" not in unit["text"]
    assert stat.S_IMODE(derived.stat().st_mode) == 0o700
    for output in derived.iterdir():
        assert stat.S_IMODE(output.stat().st_mode) == 0o600


def test_ingestion_refuses_to_write_outside_the_quarantine_subdirectory(tmp_path: Path) -> None:
    """Derived data cannot be directed to an arbitrary location."""
    source_dir = tmp_path / "quarantine"
    source_dir.mkdir()
    (source_dir / "document.txt").write_text("conteudo", encoding="utf-8")

    with pytest.raises(ValueError, match="inside the source quarantine"):
        run_ingestion(source_dir, tmp_path / "outside")


def test_ingestion_skips_the_private_control_manifest_not_part_of_the_corpus(
    tmp_path: Path,
) -> None:
    """The pre-existing private manifest is control metadata, not an unsupported source."""
    source_dir = tmp_path / "quarantine"
    source_dir.mkdir()
    (source_dir / "MANIFEST.private.json").write_text("{}", encoding="utf-8")
    (source_dir / "document.txt").write_text("conteudo", encoding="utf-8")

    result = run_ingestion(source_dir, source_dir / "derived")

    assert result.is_blocked is False
    assert result.sources_discovered == 1
    assert result.sources_extracted == 1


def test_ingestion_rejects_symlinks_before_any_source_read(tmp_path: Path) -> None:
    """A symlink cannot make the private reader traverse outside its quarantine."""
    source_dir = tmp_path / "quarantine"
    source_dir.mkdir()
    external_source = tmp_path / "external.txt"
    external_source.write_text("external", encoding="utf-8")
    (source_dir / "linked.txt").symlink_to(external_source)

    with patch("scripts.brain_corpus_ingest._sha256_file", side_effect=AssertionError):
        result = run_ingestion(source_dir, source_dir / "derived")

    report = json.loads(
        (source_dir / "derived" / "errors.blocking.json").read_text(encoding="utf-8")
    )
    assert result.is_blocked is True
    assert report["errors"][0]["code"] == "symlink_rejected"


def test_pdf_extraction_uses_local_pdftotext_with_a_hard_timeout(tmp_path: Path) -> None:
    """The PDF adapter uses a bounded local binary and never emits parser diagnostics."""
    source_file = tmp_path / "document.pdf"
    source_file.write_bytes(b"fixture")

    class CompletedProcess:
        returncode = 0
        stdout = b"primeira pagina\fsegunda pagina"

    with patch(
        "scripts.brain_corpus_ingest.subprocess.run", return_value=CompletedProcess()
    ) as run:
        with patch("scripts.brain_corpus_ingest.shutil.which", return_value="/usr/bin/pdftotext"):
            units = _extract_pdf(source_file)

    assert units == [("page:1", "primeira pagina"), ("page:2", "segunda pagina")]
    assert run.call_args.kwargs["timeout"] < 30
    assert run.call_args.kwargs["stderr"] is not None


def test_textless_pdf_delegates_to_local_ocr_with_private_scratch(tmp_path: Path) -> None:
    """An empty text layer uses the bounded OCR fallback, preserving page locators."""
    source_file = tmp_path / "document.pdf"
    source_file.write_bytes(b"fixture")
    scratch_dir = tmp_path / "derived"
    scratch_dir.mkdir()

    class CompletedProcess:
        returncode = 0
        stdout = b""

    with (
        patch("scripts.brain_corpus_ingest.subprocess.run", return_value=CompletedProcess()),
        patch(
            "scripts.brain_corpus_ingest._extract_pdf_with_local_ocr",
            return_value=[("page:1", "texto reconhecido")],
        ) as ocr,
        patch("scripts.brain_corpus_ingest.shutil.which", return_value="/usr/bin/pdftotext"),
    ):
        units = _extract_pdf(source_file, scratch_dir)

    assert units == [("page:1", "texto reconhecido")]
    ocr.assert_called_once_with(source_file, scratch_dir)
