"""Loader dos OCRs versionados das Tabelas TJMG 2026 (Portaria CGJ/TJMG 8.664/2025).

Os PDFs oficiais da RECOMPE sao ESCANEADOS (imagem pura, 0 chars via
``pdfplumber``). Para que ``emolumento_fonte_tjmg`` funcione offline e de forma
reprodutivel, mantemos os OCRs versionados em ``docs/tjmg-ocr/``.

SHA-256 dos PDFs originais + caminhos OCR vivem em ``docs/tjmg-ocr/INDEX.md``.
Este modulo expoe:

- ``TABELAS``: dict slug -> path do OCR local
- ``SHA256_ORIGINAIS``: dict slug -> SHA-256 do PDF original
- ``carregar_ocr(slug)``: retorna o texto OCR concatenado
- ``paginas_ocr(slug)``: retorna lista de textos por pagina (separa por ``--- PAGE N ---`` marker)
- ``validar_sha256(slug, sha)``: True se bate com o oficial

NUNCA modificar os OCRs sem regenerar via tesseract — qualquer divergencia
entre o texto OCR e o PDF oficial quebra a rastreabilidade legal (LGPD Art. 37
+ CNJ Provimento 74).

Modified by Gustavo Almeida · 2026-07-27
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Final

_BASE = Path(__file__).resolve().parents[3] / "docs" / "tjmg-ocr"

TABELAS: Final[dict[str, str]] = {
    "fixacao1": str(_BASE / "fixacao1_ocr.txt"),
    "fixacao8": str(_BASE / "fixacao8_ocr.txt"),
}

# SHA-256 dos PDFs oficiais (calculados 2026-07-27 via shasum -a 256).
# NAO sao chaves secretas — sao fingerprints publicos de PDFs publicos (RECOMPE)
# para detectar tampering do arquivo original. Marcar como allow porque o
# secret scanner confunde hex64 com API keys.
SHA256_ORIGINAIS: Final[dict[str, str]] = {
    "fixacao1": "202db21576f76d9a5f1ab45264a4e07ee6f25dd48391f7f7940f0353637a9d64",  # noqa: F401, F841
    "fixacao8": "2b6c862be0daf9bcb641641d638a6d3cd8805d829a9806fdd01d8eaec2a4b06e",  # noqa: F401, F841
}

# Headers emitidos pelo tesseract quando rodado por pagina individual. Usamos
# o pattern "--- PAGE N ---" quando concatenamos manualmente, mas o OCR nao
# emite isso. Em vez disso, separamos por linhas em branco duplas.
_PAGE_SEPARATOR: Final[str] = "\n\n"


def carregar_ocr(slug: str) -> str:
    """Retorna o texto OCR completo de uma tabela."""
    path = TABELAS.get(slug)
    if not path:
        raise KeyError(f"Tabela OCR desconhecida: {slug}. Conhecidas: {list(TABELAS)}")
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"OCR nao encontrado: {path}")
    return p.read_text(encoding="utf-8")


def paginas_ocr(slug: str) -> list[str]:
    """Divide o OCR concatenado em paginas aproximadas (heuristica por paragrafos).

    Os arquivos ``fixacao{1,8}_ocr.txt`` foram gerados concatenando
    ``pNN-NN.txt`` sem marcador. Esta heuristica quebra por paragrafos de >=2
    linhas em branco consecutivos (que o tesseract emite entre secoes / final
    de pagina) e retorna a lista de blocos. **Nao e canonica** — para
    associacao pagina-oficial <-> texto, use o PDF original e rode
    ``pdftoppm + tesseract`` por pagina.
    """
    texto = carregar_ocr(slug)
    blocos = [b.strip() for b in texto.split(_PAGE_SEPARATOR) if b.strip()]
    return blocos


def validar_sha256(slug: str, sha: str) -> bool:
    """Compara o SHA-256 fornecido com o oficial registrado."""
    return SHA256_ORIGINAIS.get(slug, "").lower() == sha.lower()


def sha256_arquivo(path: str | Path) -> str:
    """Calcula SHA-256 de um arquivo local (PDF original, por exemplo)."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(64 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()
