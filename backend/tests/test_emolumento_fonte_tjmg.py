"""Testes do coletor da fonte primária TJMG (Portaria CGJ/TJMG 8.664/2025).

Usa o PDF oficial capturado como fixture local (sem rede):
``backend/data/fontes/cpo86642025.pdf``. O teste de diff com divergência zero
é o critério de aceite da coleta — falha se o catálogo publicado regredir.
"""

from decimal import Decimal
from pathlib import Path

import pytest

from app.services.emolumento_real_djalma import FONTE_SHA256
from app.services.emolumento_fonte_tjmg import (
    ExtracaoFonte,
    ItemExtraido,
    diff_com_catalogo,
    extrair_tabela1,
    sha256_pdf,
)

PDF_FIXTURE = Path(__file__).resolve().parents[1] / "data" / "fontes" / "cpo86642025.pdf"


@pytest.fixture(scope="module")
def pdf_bytes() -> bytes:
    return PDF_FIXTURE.read_bytes()


def test_sha256_do_pdf_confere_com_proveniencia(pdf_bytes: bytes):
    assert sha256_pdf(pdf_bytes) == FONTE_SHA256


def test_extracao_localiza_todos_os_itens_publicados(pdf_bytes: bytes):
    extracao = extrair_tabela1(pdf_bytes)
    assert extracao.itens_nao_localizados == []
    assert len(extracao.itens) == 20
    assert len(extracao.faixas) == 23


def test_criterio_aceite_zero_divergencias(pdf_bytes: bytes):
    """Critério de aceite da coleta: catálogo publicado == fonte oficial."""
    divergencias = diff_com_catalogo(extrair_tabela1(pdf_bytes))
    assert divergencias == []


def test_extracao_valores_nominais(pdf_bytes: bytes):
    extracao = extrair_tabela1(pdf_bytes)
    procuracao = extracao.itens["procuracao_geral"]
    assert f"{procuracao.emolumentos:.2f}" == "52.43"
    assert f"{procuracao.tfj:.2f}" == "16.51"
    assert f"{procuracao.valor_final:.2f}" == "68.94"
    primeira_faixa = extracao.faixas[0]
    assert f"{primeira_faixa.de:.2f}" == "0.00"
    assert f"{primeira_faixa.ate:.2f}" == "1400.00"
    ultima_faixa = extracao.faixas[-1]
    assert f"{ultima_faixa.ate:.2f}" == "3200000.00"
    assert f"{ultima_faixa.valores.valor_final:.2f}" == "8582.97"


def test_diff_detecta_divergencia_plantada():
    extracao = ExtracaoFonte(
        itens={
            "procuracao_geral": ItemExtraido(
                emolumentos=Decimal("99.99"),
                tfj=Decimal("16.51"),
                valor_final=Decimal("68.94"),
            )
        }
    )
    divergencias = diff_com_catalogo(extracao)
    assert any(d.slug == "procuracao_geral" and d.campo == "emolumentos" for d in divergencias)


def test_diff_detecta_item_nao_extraido():
    extracao = ExtracaoFonte(itens_nao_localizados=["testamento"])
    divergencias = diff_com_catalogo(extracao)
    assert any(d.slug == "testamento" and d.fonte == "nao_extraido" for d in divergencias)
