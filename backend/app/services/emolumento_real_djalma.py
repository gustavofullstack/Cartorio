"""Catálogo oficial versionado de emolumentos do Agent AI.

Esta camada somente expõe valores diretamente verificáveis na Portaria
CGJ/TJMG nº 8.664/2025 (Tabela 1), vigente desde 2026-01-01. Não infere
ISSQN, RECOMPE, urgência, arquivamentos, diligências ou outros componentes
que não estejam no item consultado. Atos compostos falham de modo seguro:
o agente informa a referência e encaminha ao escrevente.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Final, Literal


FONTE_URL: Final = "https://www8.tjmg.jus.br/institucional/at/pdf/cpo86642025.pdf"
FONTE_SHA256: Final = "84781a023d6d51d9cf68a4d2ecd0c78b7fa3b0c04ba800be4d7e085aa7173417"
FONTE_REFERENCIA: Final = "Portaria CGJ/TJMG nº 8.664/2025 — Tabela 1"
VIGENCIA_INICIO: Final = "2026-01-01"


@dataclass(frozen=True)
class ItemTabela:
    """Linha verificável da tabela oficial, incluindo o valor final ao usuário."""

    tipo_ato: str
    descricao: str
    referencia: str
    emolumentos: Decimal
    tfj: Decimal
    valor_final: Decimal
    hitl_obrigatorio: bool


ITENS_PUBLICAVEIS: Final[dict[str, ItemTabela]] = {
    "reconhecimento_firma_semelhanca": ItemTabela(
        "reconhecimento_firma_semelhanca", "Reconhecimento de firma por assinatura",
        "Tabela 1, item 5.a", Decimal("8.55"), Decimal("2.66"), Decimal("11.21"), False,
    ),
    "reconhecimento_firma_autenticidade": ItemTabela(
        "reconhecimento_firma_autenticidade", "Reconhecimento de firma por assinatura",
        "Tabela 1, item 5.a", Decimal("8.55"), Decimal("2.66"), Decimal("11.21"), False,
    ),
    "autenticacao_pagina": ItemTabela(
        "autenticacao_pagina", "Autenticação de cópia por folha", "Tabela 1, item 3",
        Decimal("8.55"), Decimal("2.66"), Decimal("11.21"), False,
    ),
    "procuracao_geral": ItemTabela(
        "procuracao_geral", "Procuração genérica por outorgante", "Tabela 1, item 4.f.1",
        Decimal("52.43"), Decimal("16.51"), Decimal("68.94"), False,
    ),
    "procuracao_previdenciaria": ItemTabela(
        "procuracao_previdenciaria", "Procuração para previdência e assistência social",
        "Tabela 1, item 4.f.2", Decimal("27.86"), Decimal("8.75"), Decimal("36.61"), False,
    ),
    "ata_notarial_primeira_folha": ItemTabela(
        "ata_notarial_primeira_folha", "Ata notarial até duas folhas", "Tabela 1, item 2.1",
        Decimal("166.18"), Decimal("52.24"), Decimal("218.42"), True,
    ),
    "testamento_publico": ItemTabela(
        "testamento_publico", "Testamento", "Tabela 1, item 4.h.1",
        Decimal("332.64"), Decimal("104.60"), Decimal("437.24"), True,
    ),
}

# Compatibilidade de leitura para consumidores anteriores: são valores finais,
# não bases tributáveis. A API nova identifica isso explicitamente.
ATOS_FIXOS_2026: Final[dict[str, Decimal]] = {
    key: item.valor_final for key, item in ITENS_PUBLICAVEIS.items()
}
FAIXAS_ESCRITURA_DECLARADO: Final[list[dict[str, Decimal]]] = []


@dataclass(frozen=True)
class EmolumentoDetalhados:
    """Resposta segura de consulta ou pré-triagem de emolumento."""

    cartorio: str
    tipo_ato: str
    status: Literal["PUBLISHED", "HITL_REQUIRED"]
    emolumento_base: Decimal | None
    tfj: Decimal | None
    total: Decimal | None
    tabela_referencia: str
    fonte_url: str
    vigencia_inicio: str
    observacao: str

    def to_dict(self) -> dict[str, str | None]:
        return {
            "cartorio": self.cartorio,
            "tipo_ato": self.tipo_ato,
            "status": self.status,
            "emolumento_base": _money(self.emolumento_base),
            "tfj": _money(self.tfj),
            "total": _money(self.total),
            "tabela_referencia": self.tabela_referencia,
            "fonte_url": self.fonte_url,
            "vigencia_inicio": self.vigencia_inicio,
            "observacao": self.observacao,
        }


def _money(value: Decimal | None) -> str | None:
    return f"{value:.2f}" if value is not None else None


def catalogo_publico() -> dict[str, object]:
    """Retorna somente dados de preço publicados e sua proveniência."""
    return {
        "cartorio": "2º Serviço Notarial de Uberlândia",
        "jurisdicao": "Uberlândia - MG",
        "fonte": {
            "referencia": FONTE_REFERENCIA,
            "url": FONTE_URL,
            "sha256": FONTE_SHA256,
            "vigencia_inicio": VIGENCIA_INICIO,
        },
        "itens": [
            {
                "tipo_ato": item.tipo_ato,
                "descricao": item.descricao,
                "referencia": item.referencia,
                "emolumentos": _money(item.emolumentos),
                "tfj": _money(item.tfj),
                "valor_final": _money(item.valor_final),
                "hitl_obrigatorio": item.hitl_obrigatorio,
            }
            for item in ITENS_PUBLICAVEIS.values()
        ],
        "regra": "Atos ausentes ou compostos exigem conferência humana; nenhum total é inferido.",
    }


def calcular_emolumento_real_djalma(
    tipo_ato: str,
    *,
    valor_declarado: Decimal | float | int | None = None,
    folhas: int = 1,
    urgencia: bool = False,
) -> EmolumentoDetalhados:
    """Consulta um item publicado ou retorna encaminhamento humano seguro."""
    item = ITENS_PUBLICAVEIS.get(tipo_ato)
    requires_review = (
        item is None or item.hitl_obrigatorio or valor_declarado is not None or folhas != 1 or urgencia
    )
    if requires_review:
        return EmolumentoDetalhados(
            cartorio="2º Serviço Notarial de Uberlândia",
            tipo_ato=tipo_ato,
            status="HITL_REQUIRED",
            emolumento_base=item.emolumentos if item else None,
            tfj=item.tfj if item else None,
            total=None,
            tabela_referencia=item.referencia if item else FONTE_REFERENCIA,
            fonte_url=FONTE_URL,
            vigencia_inicio=VIGENCIA_INICIO,
            observacao=(
                "Ato composto, não publicado ou com parâmetro adicional: "
                "conferência do escrevente obrigatória antes de informar total."
            ),
        )
    return EmolumentoDetalhados(
        cartorio="2º Serviço Notarial de Uberlândia",
        tipo_ato=tipo_ato,
        status="PUBLISHED",
        emolumento_base=item.emolumentos,
        tfj=item.tfj,
        total=item.valor_final,
        tabela_referencia=item.referencia,
        fonte_url=FONTE_URL,
        vigencia_inicio=VIGENCIA_INICIO,
        observacao="Valor final ao usuário da tabela estadual, para o escopo indicado.",
    )
