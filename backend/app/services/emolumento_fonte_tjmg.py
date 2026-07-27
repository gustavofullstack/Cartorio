"""Coletor da fonte primária de emolumentos (Portaria CGJ/TJMG 8.664/2025).

Fluxo: download do PDF oficial → SHA-256 → extração da Tabela 1 (Atos do
Tabelião de Notas) → diff contra o catálogo publicado
(``app.services.emolumento_real_djalma``). Qualquer divergência bloqueia a
publicação e vai para revisão humana (docs/DADOS_PRECOS_E_PAINEL_AGENT_AI.md).

Uso operacional: ``scripts/coletar_tabela_tjmg.py``.
"""

from __future__ import annotations

import hashlib
import io
import re
from dataclasses import dataclass, field
from decimal import Decimal

import httpx
import pdfplumber

from app.services.emolumento_real_djalma import (
    ATOS_PUBLICADOS_2026,
    FAIXAS_ESCRITURA_COM_VALOR,
    FONTE_URL,
)

_TIMEOUT_DOWNLOAD = 90.0
_VALOR = r"(\d{1,3}(?:\.\d{3})*,\d{2})"

# Regex por slug do catálogo, ancorada no texto normalizado da Tabela 1.
_PADROES_ITENS: dict[str, str] = {
    "aprovacao_testamento_cerrado": rf"Aprovação de testamento cerrado {_VALOR} {_VALOR} {_VALOR}",
    "ata_notarial_ate_2_folhas": rf"2\.1 – Até duas folhas {_VALOR} {_VALOR} {_VALOR}",
    "ata_notarial_folha_acrescida": rf"Por folha acrescida {_VALOR} {_VALOR} {_VALOR}",
    "autenticacao_copia_folha": rf"Autenticação de cópia, por folha {_VALOR} {_VALOR} {_VALOR}",
    "autenticacao_documento_eletronico": rf"Autenticação de documento eletrônico {_VALOR} {_VALOR} {_VALOR}",
    "autenticacao_digital": rf"Autenticação digital {_VALOR} {_VALOR} {_VALOR}",
    "escritura_sem_conteudo_financeiro": rf"a\) Relativa a situação jurídica sem conteúdo {_VALOR} {_VALOR} {_VALOR} financeiro",
    "escritura_aditamento_sem_valor": rf"alteração contratual sem conteúdo {_VALOR} {_VALOR} {_VALOR} financeiro",
    "escritura_convencao_condominio": rf"e\) De convenção de condomínio {_VALOR} {_VALOR} {_VALOR}",
    "procuracao_geral": rf"Genérica, por outorgante, independentemente dos poderes conferidos e do número de {_VALOR} {_VALOR} {_VALOR} outorgados",
    "procuracao_previdenciaria": rf"independentemente dos poderes conferidos e do {_VALOR} {_VALOR} {_VALOR} número de outorgantes e outorgados",
    "procuracao_com_conteudo_financeiro": rf"f\.4\) Procuração relativa a situação jurídica com {_VALOR} {_VALOR} {_VALOR} conteúdo financeiro",
    "substabelecimento_procuracao": rf"g\) De substabelecimento de procuração {_VALOR} {_VALOR} {_VALOR}",
    "testamento": rf"h\.1\) Testamento {_VALOR} {_VALOR} {_VALOR}",
    "testamento_cerrado_a_rogo": rf"h\.2\) Testamento cerrado escrito pelo tabelião a {_VALOR} {_VALOR} {_VALOR} rogo do testador",
    "revogacao_testamento": rf"h\.3\) Revogação de testamento {_VALOR} {_VALOR} {_VALOR}",
    "inventario_sem_conteudo_financeiro": rf"i\.1\) Inventário sem conteúdo financeiro {_VALOR} {_VALOR} {_VALOR}",
    "escritura_pacto_divorcio_uniao_estavel": rf"j\) Pacto antenupcial.*?união estável e sua {_VALOR} {_VALOR} {_VALOR}",
    "reconhecimento_firma_assinatura": rf"a\) Por assinatura {_VALOR} {_VALOR} {_VALOR}",
    "reconhecimento_firma_cartao": rf"b\) Pela confecção e guarda do cartão ou ficha de {_VALOR} {_VALOR} {_VALOR} assinatura",
}


@dataclass(frozen=True)
class ItemExtraido:
    emolumentos: Decimal
    tfj: Decimal
    valor_final: Decimal


@dataclass(frozen=True)
class FaixaExtraida:
    de: Decimal
    ate: Decimal
    valores: ItemExtraido


@dataclass
class ExtracaoFonte:
    itens: dict[str, ItemExtraido] = field(default_factory=dict)
    itens_nao_localizados: list[str] = field(default_factory=list)
    faixas: list[FaixaExtraida] = field(default_factory=list)


@dataclass(frozen=True)
class Divergencia:
    slug: str
    campo: str
    catalogo: str
    fonte: str


def baixar_fonte(url: str = FONTE_URL) -> bytes:
    """Baixa o PDF oficial da fonte primária."""
    resposta = httpx.get(url, timeout=_TIMEOUT_DOWNLOAD, follow_redirects=True)
    resposta.raise_for_status()
    return resposta.content


def sha256_pdf(conteudo: bytes) -> str:
    """SHA-256 hex do PDF capturado (registrado no doc de proveniência)."""
    return hashlib.sha256(conteudo).hexdigest()


def _texto_tabela1(conteudo: bytes) -> str:
    """Texto da Tabela 1 (entre 'TABELA 1' e 'TABELA 2'), whitespace normalizado."""
    trechos: list[str] = []
    with pdfplumber.open(io.BytesIO(conteudo)) as pdf:
        for page in pdf.pages:
            trechos.append(page.extract_text() or "")
    texto = re.sub(r"\s+", " ", " ".join(trechos))
    inicio = texto.find("TABELA 1")
    fim = texto.find("TABELA 2")
    if inicio == -1 or fim == -1 or fim <= inicio:
        msg = "Tabela 1 não localizada no PDF (marcadores TABELA 1/TABELA 2 ausentes)."
        raise ValueError(msg)
    return texto[inicio:fim]


def _para_decimal(valor: str) -> Decimal:
    return Decimal(valor.replace(".", "").replace(",", "."))


def extrair_tabela1(conteudo: bytes) -> ExtracaoFonte:
    """Extrai os itens de consulta direta e as faixas do item 4.b da Tabela 1."""
    texto = _texto_tabela1(conteudo)
    resultado = ExtracaoFonte()

    for slug, padrao in _PADROES_ITENS.items():
        match = re.search(padrao, texto)
        if match is None:
            resultado.itens_nao_localizados.append(slug)
            continue
        resultado.itens[slug] = ItemExtraido(
            emolumentos=_para_decimal(match.group(1)),
            tfj=_para_decimal(match.group(2)),
            valor_final=_para_decimal(match.group(3)),
        )

    secao = re.search(r"com conteúdo financeiro: (.*?) acima de 3\.200\.000,00", texto)
    if secao is None:
        msg = "Seção de faixas do item 4.b não localizada na Tabela 1."
        raise ValueError(msg)
    trecho = secao.group(1)
    primeira = re.search(rf"^até {_VALOR} {_VALOR} {_VALOR} {_VALOR}", trecho)
    if primeira is not None:
        resultado.faixas.append(
            FaixaExtraida(
                de=Decimal("0.00"),
                ate=_para_decimal(primeira.group(1)),
                valores=ItemExtraido(
                    emolumentos=_para_decimal(primeira.group(2)),
                    tfj=_para_decimal(primeira.group(3)),
                    valor_final=_para_decimal(primeira.group(4)),
                ),
            )
        )
    for match in re.finditer(rf"de {_VALOR} até {_VALOR} {_VALOR} {_VALOR} {_VALOR}", trecho):
        resultado.faixas.append(
            FaixaExtraida(
                de=_para_decimal(match.group(1)),
                ate=_para_decimal(match.group(2)),
                valores=ItemExtraido(
                    emolumentos=_para_decimal(match.group(3)),
                    tfj=_para_decimal(match.group(4)),
                    valor_final=_para_decimal(match.group(5)),
                ),
            )
        )
    return resultado


def diff_com_catalogo(extracao: ExtracaoFonte) -> list[Divergencia]:
    """Compara a extração da fonte com o catálogo publicado.

    Lista vazia = zero divergências (critério de aceite para publicação).
    """
    divergencias: list[Divergencia] = []

    for slug in extracao.itens_nao_localizados:
        if slug in ATOS_PUBLICADOS_2026:
            divergencias.append(
                Divergencia(slug=slug, campo="ato", catalogo="presente", fonte="nao_extraido")
            )

    for slug, extraido in extracao.itens.items():
        item = ATOS_PUBLICADOS_2026.get(slug)
        if item is None:
            continue
        for campo in ("emolumentos", "tfj", "valor_final"):
            if getattr(extraido, campo) != item[campo]:
                divergencias.append(
                    Divergencia(
                        slug=slug,
                        campo=campo,
                        catalogo=f"{item[campo]:.2f}",
                        fonte=f"{getattr(extraido, campo):.2f}",
                    )
                )

    if len(extracao.faixas) != len(FAIXAS_ESCRITURA_COM_VALOR):
        divergencias.append(
            Divergencia(
                slug="escritura_com_conteudo_financeiro",
                campo="quantidade_faixas",
                catalogo=str(len(FAIXAS_ESCRITURA_COM_VALOR)),
                fonte=str(len(extracao.faixas)),
            )
        )
    for indice, (faixa, referencia) in enumerate(zip(extracao.faixas, FAIXAS_ESCRITURA_COM_VALOR)):
        slug = f"escritura_com_conteudo_financeiro[{indice}]"
        pares = (
            ("de", faixa.de, referencia["de"]),
            ("ate", faixa.ate, referencia["ate"]),
            ("emolumentos", faixa.valores.emolumentos, referencia["emolumentos"]),
            ("tfj", faixa.valores.tfj, referencia["tfj"]),
            ("valor_final", faixa.valores.valor_final, referencia["valor_final"]),
        )
        for campo, valor_fonte, valor_catalogo in pares:
            if valor_fonte != valor_catalogo:
                divergencias.append(
                    Divergencia(
                        slug=slug,
                        campo=campo,
                        catalogo=f"{valor_catalogo:.2f}",
                        fonte=f"{valor_fonte:.2f}",
                    )
                )
    return divergencias
