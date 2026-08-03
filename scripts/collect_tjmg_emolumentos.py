#!/usr/bin/env python3
"""Coleta metadados verificáveis da tabela de emolumentos do TJMG.

O script não publica preços nem persiste o PDF. Ele baixa a fonte em arquivo
temporário, calcula o hash, confirma a identificação da portaria por
``pdftotext`` e grava um manifesto que precisa passar por revisão humana antes
de qualquer promoção para o catálogo do Agent AI.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen


DEFAULT_URL = "https://www8.tjmg.jus.br/institucional/at/pdf/cpo86642025.pdf"
EXPECTED_MARKER = "PORTARIA Nº 8.664/CGJ/2025"


def download_pdf(url: str) -> bytes:
    """Baixa somente o documento oficial solicitado, com agente identificável."""
    request = Request(
        url, headers={"User-Agent": "Cartorio-AgentAI-SourceCollector/1.0"}
    )
    with urlopen(request, timeout=30) as response:  # noqa: S310 - URL supplied by operator
        return response.read()


def extract_text(pdf_bytes: bytes) -> str:
    """Extrai texto localmente sem enviar o documento a serviços externos."""
    with tempfile.TemporaryDirectory(prefix="tjmg-emolumentos-") as temp_dir:
        pdf_path = Path(temp_dir) / "source.pdf"
        pdf_path.write_bytes(pdf_bytes)
        result = subprocess.run(
            ["pdftotext", "-layout", str(pdf_path), "-"],
            check=True,
            capture_output=True,
            text=True,
            timeout=30,
        )
    return result.stdout


def build_manifest(
    url: str, pdf_bytes: bytes, extracted_text: str
) -> dict[str, object]:
    """Monta manifesto auditável sem armazenar conteúdo ou dados de titulares."""
    marker_found = EXPECTED_MARKER in extracted_text
    return {
        "source_url": url,
        "sha256": hashlib.sha256(pdf_bytes).hexdigest(),
        "captured_at": datetime.now(timezone.utc).isoformat(),
        "expected_marker": EXPECTED_MARKER,
        "marker_found": marker_found,
        "publication_state": "CAPTURED" if marker_found else "REJECTED",
        "review_required": True,
        "publication_blocked": True,
        "note": "Manifesto não publica preços. Comparar e aprovar itens antes de promover PUBLISHED.",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default=DEFAULT_URL, help="URL do PDF oficial do TJMG")
    parser.add_argument(
        "--output", type=Path, required=True, help="Arquivo JSON do manifesto"
    )
    args = parser.parse_args()

    pdf_bytes = download_pdf(args.url)
    manifest = build_manifest(args.url, pdf_bytes, extract_text(pdf_bytes))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "publication_state": manifest["publication_state"],
                "output": str(args.output),
            }
        )
    )
    return 0 if manifest["publication_state"] == "CAPTURED" else 2


if __name__ == "__main__":
    raise SystemExit(main())
