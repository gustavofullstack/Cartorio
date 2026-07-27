"""Seed do catalogo versionado de emolumentos (Fase 1 — task E0.S0.5.T4).

Cria UMA FonteCaptura PUBLISHED com a proveniencia do PDF oficial da Portaria
CGJ/TJMG 8.664/2025 (validada em ``app.services.emolumento_real_djalma``) e:
- 20 EmolumentoItems PUBLISHED (consulta direta da Tabela 1);
- 23 itens de referencia das faixas de escritura com conteudo financeiro
  (item 4.b) em HUMAN_REVIEWED — referencia do escrevente, NAO publicados.

Idempotente: se ja existir captura com FONTE_SHA256, retorna a existente.
"""

from __future__ import annotations

from datetime import UTC, date, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.emolumento_catalogo import EmolumentoItem, EstadoEmolumento, FonteCaptura
from app.services.emolumento_real_djalma import (
    ATOS_PUBLICADOS_2026,
    FAIXAS_ESCRITURA_COM_VALOR,
    FONTE_CAPTURADA_EM,
    FONTE_SHA256,
    FONTE_URL,
    VIGENCIA_INICIO,
)

ESCOPO_CONSULTA_DIRETA = "consulta direta; sem folhas adicionais, urgência ou composição"
ESCOPO_REFERENCIA_ESCREVENTE = "referência do escrevente; não publicado pelo agente"
TIPO_ATO_ESCRITURA_COM_VALOR = "escritura_com_conteudo_financeiro"


def seed_catalogo(db: Session) -> FonteCaptura:
    """Semeia a captura inicial PUBLISHED; idempotente por FONTE_SHA256."""
    existente = (
        db.execute(select(FonteCaptura).where(FonteCaptura.sha256 == FONTE_SHA256))
        .scalars()
        .first()
    )
    if existente is not None:
        return existente

    vigencia_inicio = date.fromisoformat(VIGENCIA_INICIO)
    captura = FonteCaptura(
        url=FONTE_URL,
        sha256=FONTE_SHA256,
        capturado_em=date.fromisoformat(FONTE_CAPTURADA_EM),
        vigencia_inicio=vigencia_inicio,
        vigencia_fim=None,
        estado=EstadoEmolumento.PUBLISHED,
        revisado_por="seed-validacao-pdf",
        revisado_em=datetime.now(UTC).replace(tzinfo=None),
    )
    db.add(captura)
    db.flush()

    for slug, item in ATOS_PUBLICADOS_2026.items():
        db.add(
            EmolumentoItem(
                captura_id=captura.id,
                tipo_ato=slug,
                item_portaria=item["item_portaria"],
                ato=item["ato"],
                emolumentos=item["emolumentos"],
                tfj=item["tfj"],
                valor_final=item["valor_final"],
                componentes=None,
                escopo=ESCOPO_CONSULTA_DIRETA,
                estado=EstadoEmolumento.PUBLISHED,
                vigencia_inicio=vigencia_inicio,
                vigencia_fim=None,
            )
        )

    for i, faixa in enumerate(FAIXAS_ESCRITURA_COM_VALOR, start=1):
        db.add(
            EmolumentoItem(
                captura_id=captura.id,
                tipo_ato=TIPO_ATO_ESCRITURA_COM_VALOR,
                item_portaria=f"Tabela 1, item 4.b — faixa {i:02d}",
                ato="Escritura pública com conteúdo financeiro (faixa de valores)",
                emolumentos=faixa["emolumentos"],
                tfj=faixa["tfj"],
                valor_final=faixa["valor_final"],
                componentes={
                    "de": f"{faixa['de']:.2f}",
                    "ate": f"{faixa['ate']:.2f}" if faixa["ate"] is not None else None,
                },
                escopo=ESCOPO_REFERENCIA_ESCREVENTE,
                estado=EstadoEmolumento.HUMAN_REVIEWED,
                vigencia_inicio=vigencia_inicio,
                vigencia_fim=None,
            )
        )

    db.commit()
    db.refresh(captura)
    return captura


__all__ = ["seed_catalogo"]
