"""Dados e preços reais do 2º Serviço Notarial de Uberlândia (Tabelionato Djalma).

Fonte primária: Portaria CGJ/TJMG nº 8.664/2025 (vigência a partir de 2026-01-01),
Tabela 1 — Atos do Tabelião de Notas.
PDF oficial: https://www8.tjmg.jus.br/institucional/at/pdf/cpo86642025.pdf
SHA-256 do PDF capturado em 2026-07-26 (hash público de documento oficial, não é secret):
84781a023d6d51d9cf68a4d2ecd0c78b7fa3b0c04ba800be4d7e085aa7173417  # noqa: ALLOW_KEY_FALLBACK

Regras de segurança do dado (docs/DADOS_PRECOS_E_PAINEL_AGENT_AI.md):
- O agente só publica itens de consulta direta da Tabela 1, sem composição.
- Escritura com conteúdo financeiro, urgência, folhas adicionais e qualquer
  parâmetro composto retornam ``HITL_REQUIRED`` — nunca um preço inferido.
- A portaria discrimina apenas Emolumentos + Taxa de Fiscalização Judiciária
  (TFJ). Não há ISSQN ou outros fundos nesta tabela; nada é adicionado.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Final, TypedDict

CARTORIO: Final[str] = "2º Serviço Notarial de Uberlândia"
TABELIAO: Final[str] = "Djalma de Oliveira"
FONTE_URL: Final[str] = "https://www8.tjmg.jus.br/institucional/at/pdf/cpo86642025.pdf"
FONTE_SHA256: Final[str] = "84781a023d6d51d9cf68a4d2ecd0c78b7fa3b0c04ba800be4d7e085aa7173417"  # noqa: ALLOW_KEY_FALLBACK

FONTE_CAPTURADA_EM: Final[str] = "2026-07-26"
VIGENCIA_INICIO: Final[str] = "2026-01-01"
TABELA_REFERENCIA: Final[str] = "PORTARIA_CGJ_TJMG_8664_2025_TABELA_1"

STATUS_PUBLISHED: Final[str] = "PUBLISHED"
STATUS_HITL: Final[str] = "HITL_REQUIRED"


class ItemTabela1(TypedDict):
    ato: str
    item_portaria: str
    emolumentos: Decimal
    tfj: Decimal
    valor_final: Decimal


# Tabela 1 — itens de consulta direta (sem composição), transcritos do PDF oficial.
ATOS_PUBLICADOS_2026: Final[dict[str, ItemTabela1]] = {
    "aprovacao_testamento_cerrado": {
        "ato": "Aprovação de testamento cerrado",
        "item_portaria": "Tabela 1, item 1",
        "emolumentos": Decimal("498.82"),
        "tfj": Decimal("156.88"),
        "valor_final": Decimal("655.70"),
    },
    "ata_notarial_ate_2_folhas": {
        "ato": "Ata notarial, até duas folhas",
        "item_portaria": "Tabela 1, item 2.1",
        "emolumentos": Decimal("166.18"),
        "tfj": Decimal("52.24"),
        "valor_final": Decimal("218.42"),
    },
    "ata_notarial_folha_acrescida": {
        "ato": "Ata notarial, por folha acrescida",
        "item_portaria": "Tabela 1, item 2.1.1",
        "emolumentos": Decimal("8.55"),
        "tfj": Decimal("2.66"),
        "valor_final": Decimal("11.21"),
    },
    "autenticacao_copia_folha": {
        "ato": "Autenticação de cópia, por folha",
        "item_portaria": "Tabela 1, item 3",
        "emolumentos": Decimal("8.55"),
        "tfj": Decimal("2.66"),
        "valor_final": Decimal("11.21"),
    },
    "autenticacao_documento_eletronico": {
        "ato": "Autenticação de documento eletrônico",
        "item_portaria": "Tabela 1, item 3.1",
        "emolumentos": Decimal("10.01"),
        "tfj": Decimal("2.98"),
        "valor_final": Decimal("12.99"),
    },
    "autenticacao_digital": {
        "ato": "Autenticação digital",
        "item_portaria": "Tabela 1, item 3.2",
        "emolumentos": Decimal("10.01"),
        "tfj": Decimal("2.98"),
        "valor_final": Decimal("12.99"),
    },
    "escritura_sem_conteudo_financeiro": {
        "ato": "Escritura pública relativa a situação jurídica sem conteúdo financeiro",
        "item_portaria": "Tabela 1, item 4.a",
        "emolumentos": Decimal("55.45"),
        "tfj": Decimal("17.45"),
        "valor_final": Decimal("72.90"),
    },
    "escritura_aditamento_sem_valor": {
        "ato": "Escritura de aditamento, retificação ou ratificação sem conteúdo financeiro",
        "item_portaria": "Tabela 1, item 4.c",
        "emolumentos": Decimal("32.98"),
        "tfj": Decimal("10.37"),
        "valor_final": Decimal("43.35"),
    },
    "escritura_convencao_condominio": {
        "ato": "Escritura de convenção de condomínio",
        "item_portaria": "Tabela 1, item 4.e",
        "emolumentos": Decimal("132.88"),
        "tfj": Decimal("41.80"),
        "valor_final": Decimal("174.68"),
    },
    "procuracao_geral": {
        "ato": "Procuração genérica, por outorgante",
        "item_portaria": "Tabela 1, item 4.f.1",
        "emolumentos": Decimal("52.43"),
        "tfj": Decimal("16.51"),
        "valor_final": Decimal("68.94"),
    },
    "procuracao_previdenciaria": {
        "ato": "Procuração para fins de previdência e assistência social",
        "item_portaria": "Tabela 1, item 4.f.2",
        "emolumentos": Decimal("27.86"),
        "tfj": Decimal("8.75"),
        "valor_final": Decimal("36.61"),
    },
    "procuracao_com_conteudo_financeiro": {
        "ato": "Procuração relativa a situação jurídica com conteúdo financeiro",
        "item_portaria": "Tabela 1, item 4.f.4",
        "emolumentos": Decimal("166.18"),
        "tfj": Decimal("52.23"),
        "valor_final": Decimal("218.41"),
    },
    "substabelecimento_procuracao": {
        "ato": "Substabelecimento de procuração",
        "item_portaria": "Tabela 1, item 4.g",
        "emolumentos": Decimal("34.96"),
        "tfj": Decimal("11.00"),
        "valor_final": Decimal("45.96"),
    },
    "testamento": {
        "ato": "Testamento",
        "item_portaria": "Tabela 1, item 4.h.1",
        "emolumentos": Decimal("332.64"),
        "tfj": Decimal("104.60"),
        "valor_final": Decimal("437.24"),
    },
    "testamento_cerrado_a_rogo": {
        "ato": "Testamento cerrado escrito pelo tabelião a rogo do testador",
        "item_portaria": "Tabela 1, item 4.h.2",
        "emolumentos": Decimal("665.27"),
        "tfj": Decimal("209.22"),
        "valor_final": Decimal("874.49"),
    },
    "revogacao_testamento": {
        "ato": "Revogação de testamento",
        "item_portaria": "Tabela 1, item 4.h.3",
        "emolumentos": Decimal("166.29"),
        "tfj": Decimal("52.34"),
        "valor_final": Decimal("218.63"),
    },
    "inventario_sem_conteudo_financeiro": {
        "ato": "Inventário sem conteúdo financeiro",
        "item_portaria": "Tabela 1, item 4.i.1",
        "emolumentos": Decimal("166.18"),
        "tfj": Decimal("52.23"),
        "valor_final": Decimal("218.41"),
    },
    "escritura_pacto_divorcio_uniao_estavel": {
        "ato": (
            "Pacto antenupcial, emancipação, separação, divórcio, união estável "
            "e atos afins sem excedente de meação"
        ),
        "item_portaria": "Tabela 1, item 4.j",
        "emolumentos": Decimal("498.82"),
        "tfj": Decimal("156.86"),
        "valor_final": Decimal("655.68"),
    },
    "reconhecimento_firma_assinatura": {
        "ato": "Reconhecimento de firma por assinatura",
        "item_portaria": "Tabela 1, item 5.a",
        "emolumentos": Decimal("8.55"),
        "tfj": Decimal("2.66"),
        "valor_final": Decimal("11.21"),
    },
    "reconhecimento_firma_cartao": {
        "ato": "Reconhecimento de firma pela confecção e guarda do cartão de assinatura",
        "item_portaria": "Tabela 1, item 5.b",
        "emolumentos": Decimal("8.55"),
        "tfj": Decimal("2.66"),
        "valor_final": Decimal("11.21"),
    },
}

# Aliases de slugs legados (extração por palavras-chave) para o catálogo oficial.
# Slugs sem equivalente direto na Tabela 1 caem em HITL_REQUIRED.
ALIASES_SLUG: Final[dict[str, str]] = {
    "autenticacao_pagina": "autenticacao_copia_folha",
    "testamento_publico": "testamento",
    "ata_notarial_primeira_folha": "ata_notarial_ate_2_folhas",
    "escritura_sem_valor": "escritura_sem_conteudo_financeiro",
}


class FaixaEscritura(TypedDict):
    de: Decimal
    ate: Decimal | None  # None = "acima de" (ver NOTA XXV)
    emolumentos: Decimal
    tfj: Decimal
    valor_final: Decimal


# Tabela 1, item 4.b — escritura com conteúdo financeiro (23 faixas).
# Referência validada para o escrevente; NÃO é preço publicado pelo agente
# (ato composto → HITL_REQUIRED). Acima de R$ 3.200.000,00 aplica-se a NOTA XXV.
FAIXAS_ESCRITURA_COM_VALOR: Final[list[FaixaEscritura]] = [
    {
        "de": Decimal("0.00"),
        "ate": Decimal("1400.00"),
        "emolumentos": Decimal("159.20"),
        "tfj": Decimal("61.35"),
        "valor_final": Decimal("220.55"),
    },
    {
        "de": Decimal("1400.01"),
        "ate": Decimal("2720.00"),
        "emolumentos": Decimal("259.68"),
        "tfj": Decimal("100.08"),
        "valor_final": Decimal("359.76"),
    },
    {
        "de": Decimal("2720.01"),
        "ate": Decimal("5440.00"),
        "emolumentos": Decimal("376.34"),
        "tfj": Decimal("145.01"),
        "valor_final": Decimal("521.35"),
    },
    {
        "de": Decimal("5440.01"),
        "ate": Decimal("7000.00"),
        "emolumentos": Decimal("520.99"),
        "tfj": Decimal("200.76"),
        "valor_final": Decimal("721.75"),
    },
    {
        "de": Decimal("7000.01"),
        "ate": Decimal("14000.00"),
        "emolumentos": Decimal("694.78"),
        "tfj": Decimal("267.69"),
        "valor_final": Decimal("962.47"),
    },
    {
        "de": Decimal("14000.01"),
        "ate": Decimal("28000.00"),
        "emolumentos": Decimal("897.58"),
        "tfj": Decimal("345.89"),
        "valor_final": Decimal("1243.47"),
    },
    {
        "de": Decimal("28000.01"),
        "ate": Decimal("42000.00"),
        "emolumentos": Decimal("1129.02"),
        "tfj": Decimal("435.05"),
        "valor_final": Decimal("1564.07"),
    },
    {
        "de": Decimal("42000.01"),
        "ate": Decimal("56000.00"),
        "emolumentos": Decimal("1389.81"),
        "tfj": Decimal("535.50"),
        "valor_final": Decimal("1925.31"),
    },
    {
        "de": Decimal("56000.01"),
        "ate": Decimal("70000.00"),
        "emolumentos": Decimal("1679.40"),
        "tfj": Decimal("647.11"),
        "valor_final": Decimal("2326.51"),
    },
    {
        "de": Decimal("70000.01"),
        "ate": Decimal("105000.00"),
        "emolumentos": Decimal("2113.64"),
        "tfj": Decimal("814.42"),
        "valor_final": Decimal("2928.06"),
    },
    {
        "de": Decimal("105000.01"),
        "ate": Decimal("140000.00"),
        "emolumentos": Decimal("2540.87"),
        "tfj": Decimal("1180.65"),
        "valor_final": Decimal("3721.52"),
    },
    {
        "de": Decimal("140000.01"),
        "ate": Decimal("175000.00"),
        "emolumentos": Decimal("2717.08"),
        "tfj": Decimal("1262.61"),
        "valor_final": Decimal("3979.69"),
    },
    {
        "de": Decimal("175000.01"),
        "ate": Decimal("210000.00"),
        "emolumentos": Decimal("2893.66"),
        "tfj": Decimal("1344.66"),
        "valor_final": Decimal("4238.32"),
    },
    {
        "de": Decimal("210000.01"),
        "ate": Decimal("280000.00"),
        "emolumentos": Decimal("3070.72"),
        "tfj": Decimal("1701.35"),
        "valor_final": Decimal("4772.07"),
    },
    {
        "de": Decimal("280000.01"),
        "ate": Decimal("350000.00"),
        "emolumentos": Decimal("3155.22"),
        "tfj": Decimal("1748.31"),
        "valor_final": Decimal("4903.53"),
    },
    {
        "de": Decimal("350000.01"),
        "ate": Decimal("420000.00"),
        "emolumentos": Decimal("3240.20"),
        "tfj": Decimal("1795.39"),
        "valor_final": Decimal("5035.59"),
    },
    {
        "de": Decimal("420000.01"),
        "ate": Decimal("560000.00"),
        "emolumentos": Decimal("3325.70"),
        "tfj": Decimal("2197.44"),
        "valor_final": Decimal("5523.14"),
    },
    {
        "de": Decimal("560000.01"),
        "ate": Decimal("700000.00"),
        "emolumentos": Decimal("3508.36"),
        "tfj": Decimal("2318.34"),
        "valor_final": Decimal("5826.70"),
    },
    {
        "de": Decimal("700000.01"),
        "ate": Decimal("840000.00"),
        "emolumentos": Decimal("3691.51"),
        "tfj": Decimal("2439.36"),
        "valor_final": Decimal("6130.87"),
    },
    {
        "de": Decimal("840000.01"),
        "ate": Decimal("1120000.00"),
        "emolumentos": Decimal("3875.31"),
        "tfj": Decimal("2991.22"),
        "valor_final": Decimal("6866.53"),
    },
    {
        "de": Decimal("1120000.01"),
        "ate": Decimal("1400000.00"),
        "emolumentos": Decimal("4197.56"),
        "tfj": Decimal("3240.08"),
        "valor_final": Decimal("7437.64"),
    },
    {
        "de": Decimal("1400000.01"),
        "ate": Decimal("1680000.00"),
        "emolumentos": Decimal("4520.42"),
        "tfj": Decimal("3489.30"),
        "valor_final": Decimal("8009.72"),
    },
    {
        "de": Decimal("1680000.01"),
        "ate": Decimal("3200000.00"),
        "emolumentos": Decimal("4844.02"),
        "tfj": Decimal("3738.95"),
        "valor_final": Decimal("8582.97"),
    },
]

# NOTA XXV — acréscimos sobre emolumentos brutos acima de R$ 3.200.000,00:
# a cada faixa de R$ 500.000,00 ou fração (limite de 100 faixas):
NOTA_XXV_TETO_FAIXAS: Final[Decimal] = Decimal("3200000.00")
NOTA_XXV_PASSO_FAIXA: Final[Decimal] = Decimal("500000.00")
NOTA_XXV_ACRESCIMO_PRIMEIRA: Final[Decimal] = Decimal("3289.90")
NOTA_XXV_ACRESCIMO_SUBSEQUENTE: Final[Decimal] = Decimal("2193.27")
NOTA_XXV_TFJ_FIXA: Final[Decimal] = Decimal("4673.83")
NOTA_XXV_LIMITE_FAIXAS: Final[int] = 100


@dataclass(frozen=True)
class EmolumentoDetalhados:
    cartorio: str
    tabeliao: str
    tipo_ato: str
    valor_declarado: Decimal | None
    folhas: int
    status: str  # PUBLISHED | HITL_REQUIRED
    emolumento_base: Decimal | None
    tfj: Decimal | None
    total: Decimal | None
    item_portaria: str | None
    motivo_hitl: str | None
    tabela_referencia: str

    def to_dict(self) -> dict[str, str | int | float | None]:
        return {
            "cartorio": self.cartorio,
            "tabeliao": self.tabeliao,
            "tipo_ato": self.tipo_ato,
            "valor_declarado": float(self.valor_declarado)
            if self.valor_declarado is not None
            else None,
            "folhas": self.folhas,
            "status": self.status,
            "emolumento_base": f"{self.emolumento_base:.2f}"
            if self.emolumento_base is not None
            else None,
            "tfj": f"{self.tfj:.2f}" if self.tfj is not None else None,
            "total": f"{self.total:.2f}" if self.total is not None else None,
            "item_portaria": self.item_portaria,
            "motivo_hitl": self.motivo_hitl,
            "tabela_referencia": self.tabela_referencia,
        }


def _hitl(
    tipo_ato: str,
    motivo: str,
    *,
    valor_declarado: Decimal | None = None,
    folhas: int = 1,
) -> EmolumentoDetalhados:
    return EmolumentoDetalhados(
        cartorio=CARTORIO,
        tabeliao=TABELIAO,
        tipo_ato=tipo_ato,
        valor_declarado=valor_declarado,
        folhas=folhas,
        status=STATUS_HITL,
        emolumento_base=None,
        tfj=None,
        total=None,
        item_portaria=None,
        motivo_hitl=motivo,
        tabela_referencia=TABELA_REFERENCIA,
    )


def calcular_emolumento_real_djalma(
    tipo_ato: str,
    *,
    valor_declarado: Decimal | float | int | None = None,
    folhas: int = 1,
    urgencia: bool = False,
) -> EmolumentoDetalhados:
    """Consulta item publicado da Portaria CGJ/TJMG 8.664/2025 (Tabela 1).

    Retorna ``PUBLISHED`` somente para ato de consulta direta, sem parâmetros
    adicionais (1 folha, sem urgência, sem valor declarado). Qualquer composição
    retorna ``HITL_REQUIRED`` — o agente nunca infere tributo ou preço.
    """
    folhas = max(1, folhas)
    val_dec: Decimal | None = None
    if valor_declarado is not None:
        val_dec = Decimal(str(valor_declarado))

    slug = ALIASES_SLUG.get(tipo_ato, tipo_ato)

    if urgencia:
        return _hitl(
            slug,
            "Urgência não possui acréscimo publicado na Portaria 8.664/2025; "
            "orçamento exige conferência do escrevente.",
            valor_declarado=val_dec,
            folhas=folhas,
        )
    if val_dec is not None:
        return _hitl(
            slug,
            "Ato com conteúdo financeiro depende de composição (Tabela 1, item 4.b "
            "e notas); orçamento exige conferência do escrevente.",
            valor_declarado=val_dec,
            folhas=folhas,
        )
    if folhas > 1:
        return _hitl(
            slug,
            "Quantidade de folhas adicional não compõe preço publicado; "
            "orçamento exige conferência do escrevente.",
            folhas=folhas,
        )

    item = ATOS_PUBLICADOS_2026.get(slug)
    if item is None:
        return _hitl(
            slug,
            "Ato não localizado entre os itens de consulta direta da Tabela 1; "
            "encaminhado ao escrevente.",
            folhas=folhas,
        )

    return EmolumentoDetalhados(
        cartorio=CARTORIO,
        tabeliao=TABELIAO,
        tipo_ato=slug,
        valor_declarado=None,
        folhas=1,
        status=STATUS_PUBLISHED,
        emolumento_base=item["emolumentos"],
        tfj=item["tfj"],
        total=item["valor_final"],
        item_portaria=item["item_portaria"],
        motivo_hitl=None,
        tabela_referencia=TABELA_REFERENCIA,
    )


def catalogo_publico() -> dict[str, object]:
    """Catálogo público versionado com proveniência (fonte, hash, vigência).

    Consumido pelo endpoint ``/api/v1/emolumentos/real/djalma`` e pelo painel
    do Agent AI. As faixas de escritura com conteúdo financeiro aparecem como
    referência do escrevente, marcadas ``HITL_REQUIRED``.
    """
    itens = [
        {
            "tipo_ato": slug,
            "ato": item["ato"],
            "item_portaria": item["item_portaria"],
            "emolumentos": f"{item['emolumentos']:.2f}",
            "tfj": f"{item['tfj']:.2f}",
            "valor_final": f"{item['valor_final']:.2f}",
            "status": STATUS_PUBLISHED,
            "escopo": "consulta direta; sem folhas adicionais, urgência ou composição",
        }
        for slug, item in ATOS_PUBLICADOS_2026.items()
    ]
    faixas = [
        {
            "tipo_ato": "escritura_com_conteudo_financeiro",
            "item_portaria": "Tabela 1, item 4.b",
            "de": f"{faixa['de']:.2f}",
            "ate": f"{faixa['ate']:.2f}" if faixa["ate"] is not None else None,
            "emolumentos": f"{faixa['emolumentos']:.2f}",
            "tfj": f"{faixa['tfj']:.2f}",
            "valor_final": f"{faixa['valor_final']:.2f}",
            "status": STATUS_HITL,
            "escopo": "referência do escrevente; não publicado pelo agente",
        }
        for faixa in FAIXAS_ESCRITURA_COM_VALOR
    ]
    return {
        "cartorio": CARTORIO,
        "tabeliao": TABELIAO,
        "fonte": {
            "nome": "Portaria CGJ/TJMG nº 8.664/2025 — Tabela 1 (Atos do Tabelião de Notas)",
            "url": FONTE_URL,
            "sha256": FONTE_SHA256,  # noqa: ALLOW_KEY_FALLBACK
            "capturado_em": FONTE_CAPTURADA_EM,
            "vigencia_inicio": VIGENCIA_INICIO,
            "vigencia_fim": None,
            "estado": STATUS_PUBLISHED,
            "revisao_humana": "pendente de validação do escrevente responsável",
        },
        "itens": itens,
        "referencia_escrevente": {
            "escritura_com_conteudo_financeiro": faixas,
            "nota_xxv": {
                "teto_faixas_tabela": f"{NOTA_XXV_TETO_FAIXAS:.2f}",
                "passo_faixa": f"{NOTA_XXV_PASSO_FAIXA:.2f}",
                "acrescimo_primeira_faixa": f"{NOTA_XXV_ACRESCIMO_PRIMEIRA:.2f}",
                "acrescimo_faixa_subsequente": f"{NOTA_XXV_ACRESCIMO_SUBSEQUENTE:.2f}",
                "tfj_fixa": f"{NOTA_XXV_TFJ_FIXA:.2f}",
                "limite_faixas": NOTA_XXV_LIMITE_FAIXAS,
            },
        },
    }
