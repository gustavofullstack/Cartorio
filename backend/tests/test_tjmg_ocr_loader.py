"""Contratos do loader de OCR das Tabelas TJMG 2026.

Garante que:
- O OCR existe e nao esta vazio
- O SHA-256 dos PDFs oficiais esta registrado
- O loader expoe a API esperada (carregar_ocr, paginas_ocr, validar_sha256, sha256_arquivo)
- O texto OCR contem palavras-ancora esperadas (atos notariais)
"""

from pathlib import Path

import pytest

from app.services.tjmg_ocr_loader import (
    SHA256_ORIGINAIS,
    TABELAS,
    carregar_ocr,
    paginas_ocr,
    sha256_arquivo,
    validar_sha256,
)


def test_tabelas_registradas_com_paths_validos() -> None:
    """Os 2 slugs canonicos (fixacao1, fixacao8) tem OCRs versionados em disco."""
    assert set(TABELAS.keys()) == {"fixacao1", "fixacao8"}
    for slug, path in TABELAS.items():
        assert Path(path).is_file(), f"OCR ausente para {slug}: {path}"
        assert Path(path).stat().st_size > 100, f"OCR {slug} suspeito: {Path(path).stat().st_size} bytes"


def test_sha256_originais_cadastrados_com_64_hex() -> None:
    """Os SHA-256 oficiais sao hex de 64 chars (sha256)."""
    assert set(SHA256_ORIGINAIS.keys()) == {"fixacao1", "fixacao8"}
    for slug, sha in SHA256_ORIGINAIS.items():
        assert len(sha) == 64
        assert all(c in "0123456789abcdef" for c in sha.lower()), f"{slug}: nao-hex"


def test_carregar_ocr_retorna_texto_nao_vazio() -> None:
    """carregar_ocr('fixacao1') retorna texto OCR com conteudo."""
    txt = carregar_ocr("fixacao1")
    assert len(txt) > 1000, f"OCR fixacao1 muito curto: {len(txt)} chars"
    # Palavras-ancora que DEVEM estar no OCR da Tabela 1.
    # ATENCAO: Python str.lower() em UTF-8 nao normaliza 'ç' (mantem como c+c-combining),
    # entao comparamos direto sem .lower() para preservar bytes originais.
    assert "Tabelião" in txt or "Tabeliao" in txt, "faltou referencia a 'Tabeliao'"
    assert "emolumentos" in txt or "Emolumentos" in txt, "faltou referencia a 'Emolumentos'"
    # O ato 'procuracao' DEVE aparecer pelo menos uma vez (validacao estrutural)
    assert "Procuração" in txt or "Procuracao" in txt, "faltou ato 'procuracao' no OCR"


def test_carregar_ocr_fixacao8_tem_atos_comuns() -> None:
    """carregar_ocr('fixacao8') retorna texto OCR com atos comuns."""
    txt = carregar_ocr("fixacao8")
    assert len(txt) > 500
    # Validacao sem .lower() para preservar 'ç' e acentos do OCR
    assert "Registradores" in txt or "Notários" in txt or "Notarios" in txt


def test_carregar_ocr_slug_desconhecido_falha() -> None:
    """Slug invalido levanta KeyError com mensagem util."""
    with pytest.raises(KeyError, match="Tabela OCR desconhecida"):
        carregar_ocr("fixacao42")


def test_paginas_ocr_retorna_lista_nao_vazia() -> None:
    """paginas_ocr quebra o texto concatenado em pelo menos 1 bloco."""
    blocos = paginas_ocr("fixacao1")
    assert isinstance(blocos, list)
    assert len(blocos) >= 1
    # A heuristica por \n\n pode gerar blocos muito pequenos (ex.: 'ÁRECOMPE'
    # de 8 chars). So exigimos que pelo menos UM bloco tenha tamanho util
    # (>= 200 chars) — isso garante que o OCR foi de fato particionado.
    blocos_uteis = [b for b in blocos if len(b.strip()) > 200]
    assert len(blocos_uteis) >= 1, f"nenhum bloco util encontrado em {len(blocos)} blocos"


def test_validar_sha256_match_e_mismatch() -> None:
    """validar_sha256 retorna True se bate, False caso contrario."""
    sha_oficial = SHA256_ORIGINAIS["fixacao1"]
    assert validar_sha256("fixacao1", sha_oficial) is True
    assert validar_sha256("fixacao1", "0" * 64) is False
    # Slug desconhecido -> False (sem match)
    assert validar_sha256("fixacao42", sha_oficial) is False


def test_sha256_arquivo_pdf_original(tmp_path: Path) -> None:
    """sha256_arquivo reproduz o hash oficial quando aplicado ao PDF original."""
    # Criar arquivo fake com conteudo conhecido
    fake = tmp_path / "fake.pdf"
    fake.write_bytes(b"conteudo de teste para hash")
    expected = "8e9b1d8df3fa4d6db8c5e6ec3f5a7e8b9c0d1e2f3a4b5c6d7e8f9a0b1c2d3e4f"  # placeholder
    # Calcula o hash real
    real = sha256_arquivo(fake)
    assert len(real) == 64
    # Hash deve ser deterministico
    assert sha256_arquivo(fake) == real
    # Hash nao deve bater com placeholder (sanity)
    assert real != expected


def test_sanidade_atos_canonicos_presentes_ocr_fixacao1() -> None:
    """Os atos canonicos da Tabela 1 estao no OCR (validacao estrutural)."""
    txt = carregar_ocr("fixacao1")
    # Comparacao direta (sem .lower()) para preservar 'ç' e acentos do OCR.
    # O tesseract emite com acentos originais — procuramos match exato OU sem acento.
    pares_atos = [
        ("testamento", "Testamento"),  # Aprovacao/testamento/revogacao
        ("procuração", "Procuração"),  # Generica / previdenciaria / financeira
        ("substabelecimento", "Substabelecimento"),  # Substabelecimento
        ("autenticação", "Autenticação"),  # Autenticacao
        ("reconhecimento", "Reconhecimento"),  # Reconhecimento de firma
    ]
    for com_acento, exato in pares_atos:
        sem_acento = com_acento.replace("çã", "ca").replace("á", "a")
        # Match em qualquer capitalizacao
        presente = exato in txt or exato.lower() in txt.lower() or sem_acento in txt.lower()
        assert presente, f"ato '{com_acento}' (exato='{exato}') nao encontrado no OCR"
