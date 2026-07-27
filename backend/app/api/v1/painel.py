"""Painel de dados do Agent AI (Fase 4) — 4 blocos agregados, sem PII.

Spec: docs/DADOS_PRECOS_E_PAINEL_AGENT_AI.md.

Endpoints (todos GET, sob ``/api/v1/painel``):
- ``/fonte``     — bloco 1: qualidade da fonte (proveniencia, idade, aprovacao).
- ``/catalogo``  — bloco 2: itens PUBLISHED vigentes do catalogo.
- ``/extracao``  — bloco 3: contadores de extracao por IA (outcome/reason).
- ``/operacao``  — bloco 4: consultas de preco, handoffs e taxa de handoff.
- ``/ia-usage``  — telemetria LiteLLM (Fase 3) exposta ao painel.

Regras P0:
- NUNCA texto de cliente, CPF, telefone, documento ou identificador de
  conversa. Somente dados de catalogo e contadores com rotulos categoricos.
- Fail-open como o extrator: DB vazio/indisponivel cai no fallback das
  constantes versionadas de ``emolumento_real_djalma`` — o painel nunca
  quebra por falta de banco.
- Nunca retornar ORM direto: respostas via Pydantic v2.
"""

from __future__ import annotations

import datetime
from typing import Annotated, Any, cast

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models.emolumento_catalogo import EmolumentoItem, EstadoEmolumento, FonteCaptura
from app.services import emolumento_real_djalma, ia_usage
from app.services.metrics import store

painel_router = APIRouter(prefix="/painel", tags=["painel"])

ESCOPO_CONSULTA_DIRETA = "consulta direta; sem folhas adicionais, urgência ou composição"


# ============================================================================
# Schemas de resposta (Pydantic v2 — nunca ORM direto)
# ============================================================================


class AprovacaoHumana(BaseModel):
    """Revisao humana da captura vigente (bloco 1)."""

    revisado_por: str | None = Field(description="Identificador funcional do revisor, se houve.")
    revisado_em: str | None = Field(description="Instante ISO da revisao, se houve.")
    mensagem: str = Field(description="Estado da aprovacao humana em linguagem operacional.")


class FontePainelResponse(BaseModel):
    """Bloco 1 — qualidade da fonte oficial de precos."""

    nome: str
    url: str
    sha256: str
    capturado_em: str
    idade_dias: int = Field(description="Dias entre a captura e hoje (calculado no servidor).")
    vigencia_inicio: str
    vigencia_fim: str | None
    estado: str
    aprovacao_humana: AprovacaoHumana
    origem: str = Field(description="'banco' quando ha captura PUBLISHED; 'constantes' no fallback.")


class CatalogoItemResponse(BaseModel):
    """Item publicado do catalogo (bloco 2)."""

    tipo_ato: str
    ato: str
    item_portaria: str
    emolumentos: str
    tfj: str
    valor_final: str
    status: str
    escopo: str | None


class CatalogoPainelResponse(BaseModel):
    """Bloco 2 — catalogo publicado vigente."""

    total: int
    escopo: str
    itens: list[CatalogoItemResponse]
    origem: str = Field(description="'banco' quando ha itens PUBLISHED; 'constantes' no fallback.")


class ExtracaoPainelResponse(BaseModel):
    """Bloco 3 — extracao por IA, agregada por rotulo categorico (sem PII)."""

    extracoes_por_outcome: dict[str, int]
    extracoes_total: int
    handoffs_por_reason: dict[str, int]
    handoffs_total: int
    llm_fallback_por_reason: dict[str, int]
    llm_fallback_total: int
    retencao: str
    rotulos: str


class OperacaoPainelResponse(BaseModel):
    """Bloco 4 — operacao de consulta de precos."""

    consultas_por_outcome: dict[str, int]
    consultas_total: int
    handoffs_total: int
    taxa_handoff: float = Field(description="handoffs/consultas; 0.0 quando nao ha consultas.")


# ============================================================================
# Helpers (fail-open: qualquer falha de DB cai no fallback das constantes)
# ============================================================================


def _parse_labels_key(key: str) -> dict[str, str]:
    """Decodifica a chave de labels do MetricsStore ("k=v|k2=v2")."""
    if not key:
        return {}
    return dict(item.split("=", 1) for item in key.split("|") if "=" in item)


def _agregar_contador(nome: str, rotulo: str) -> dict[str, int]:
    """Agrega um counter do store por um rotulo categorico (ex.: outcome)."""
    agregado: dict[str, int] = {}
    for key, valor in store.counters.get(nome, {}).items():
        valor_rotulo = _parse_labels_key(key).get(rotulo, "sem_rotulo")
        agregado[valor_rotulo] = agregado.get(valor_rotulo, 0) + valor
    return agregado


def _captura_published_recente(db: Session | None) -> FonteCaptura | None:
    """Captura PUBLISHED mais recente no banco; None se vazio/indisponivel."""
    if db is None:
        return None
    try:
        stmt = (
            select(FonteCaptura)
            .where(FonteCaptura.estado == EstadoEmolumento.PUBLISHED)
            .order_by(FonteCaptura.vigencia_inicio.desc(), FonteCaptura.id.desc())
            .limit(1)
        )
        return db.execute(stmt).scalars().first()
    except Exception:
        return None


def _itens_published_vigentes(db: Session | None) -> list[EmolumentoItem]:
    """Itens PUBLISHED cuja vigencia contem hoje; [] se vazio/indisponivel."""
    if db is None:
        return []
    hoje = datetime.date.today()
    try:
        stmt = (
            select(EmolumentoItem)
            .where(
                EmolumentoItem.estado == EstadoEmolumento.PUBLISHED,
                EmolumentoItem.vigencia_inicio <= hoje,
                or_(
                    EmolumentoItem.vigencia_fim.is_(None),
                    EmolumentoItem.vigencia_fim >= hoje,
                ),
            )
            .order_by(EmolumentoItem.item_portaria, EmolumentoItem.tipo_ato)
        )
        return list(db.execute(stmt).scalars().all())
    except Exception:
        return []


# ============================================================================
# Bloco 1 — qualidade da fonte
# ============================================================================


@painel_router.get(
    "/fonte",
    summary="Qualidade da fonte oficial de preços",
    description=(
        "Proveniencia, integridade (SHA-256), vigencia, idade da captura e "
        "aprovacao humana. Usa a captura PUBLISHED mais recente do banco; "
        "sem banco, cai nas constantes versionadas da Portaria CGJ/TJMG 8.664/2025."
    ),
    response_model=FontePainelResponse,
)
async def painel_fonte(db: Session = Depends(get_db)) -> FontePainelResponse:  # noqa: B008
    """Bloco 1 do painel: qualidade da fonte (fail-open para as constantes)."""
    fonte_const = cast(dict[str, Any], emolumento_real_djalma.catalogo_publico()["fonte"])
    captura = _captura_published_recente(db)

    if captura is not None:
        capturado_em = captura.capturado_em.isoformat()
        idade_dias = (datetime.date.today() - captura.capturado_em).days
        revisado = captura.revisado_por is not None
        return FontePainelResponse(
            nome=str(fonte_const["nome"]),
            url=captura.url,
            sha256=captura.sha256,
            capturado_em=capturado_em,
            idade_dias=idade_dias,
            vigencia_inicio=captura.vigencia_inicio.isoformat(),
            vigencia_fim=captura.vigencia_fim.isoformat() if captura.vigencia_fim else None,
            estado=captura.estado,
            aprovacao_humana=AprovacaoHumana(
                revisado_por=captura.revisado_por,
                revisado_em=captura.revisado_em.isoformat() if captura.revisado_em else None,
                mensagem=(
                    "captura revisada e publicada pelo escrevente"
                    if revisado
                    else "captura publicada sem revisor registrado"
                ),
            ),
            origem="banco",
        )

    capturado_em = str(fonte_const["capturado_em"])
    idade_dias = (datetime.date.today() - datetime.date.fromisoformat(capturado_em)).days
    return FontePainelResponse(
        nome=str(fonte_const["nome"]),
        url=str(fonte_const["url"]),
        sha256=str(fonte_const["sha256"]),
        capturado_em=capturado_em,
        idade_dias=idade_dias,
        vigencia_inicio=str(fonte_const["vigencia_inicio"]),
        vigencia_fim=cast(str | None, fonte_const["vigencia_fim"]),
        estado=str(fonte_const["estado"]),
        aprovacao_humana=AprovacaoHumana(
            revisado_por=None,
            revisado_em=None,
            mensagem=str(fonte_const["revisao_humana"]),
        ),
        origem="constantes",
    )


# ============================================================================
# Bloco 2 — catalogo publicado
# ============================================================================


@painel_router.get(
    "/catalogo",
    summary="Catálogo publicado vigente",
    description=(
        "Itens PUBLISHED cuja vigencia contem a data da consulta. "
        "Sem banco, cai no catalogo publico versionado (constantes)."
    ),
    response_model=CatalogoPainelResponse,
)
async def painel_catalogo(db: Session = Depends(get_db)) -> CatalogoPainelResponse:  # noqa: B008
    """Bloco 2 do painel: itens publicados vigentes (fail-open)."""
    itens_db = _itens_published_vigentes(db)
    if itens_db:
        return CatalogoPainelResponse(
            total=len(itens_db),
            escopo=ESCOPO_CONSULTA_DIRETA,
            itens=[
                CatalogoItemResponse(
                    tipo_ato=item.tipo_ato,
                    ato=item.ato,
                    item_portaria=item.item_portaria,
                    emolumentos=f"{item.emolumentos:.2f}",
                    tfj=f"{item.tfj:.2f}",
                    valor_final=f"{item.valor_final:.2f}",
                    status=item.estado,
                    escopo=item.escopo,
                )
                for item in itens_db
            ],
            origem="banco",
        )

    itens_const = cast(list[dict[str, Any]], emolumento_real_djalma.catalogo_publico()["itens"])
    return CatalogoPainelResponse(
        total=len(itens_const),
        escopo=ESCOPO_CONSULTA_DIRETA,
        itens=[CatalogoItemResponse(**item) for item in itens_const],
        origem="constantes",
    )


# ============================================================================
# Bloco 3 — extracao por IA (sem texto/ids)
# ============================================================================


@painel_router.get(
    "/extracao",
    summary="Extração por IA agregada (sem PII)",
    description=(
        "Contadores em memoria por rotulo categorico: extracoes por outcome, "
        "handoffs por reason e fallbacks de LLM por reason. "
        "Nunca texto, CPF, telefone ou identificador de conversa."
    ),
    response_model=ExtracaoPainelResponse,
)
async def painel_extracao() -> ExtracaoPainelResponse:
    """Bloco 3 do painel: agregado dos contadores do MetricsStore."""
    extracoes = _agregar_contador("cartorio_agent_ai_extracoes_total", "outcome")
    handoffs = _agregar_contador("cartorio_agent_ai_handoffs_total", "reason")
    fallbacks = _agregar_contador("cartorio_agent_ai_llm_fallback_total", "reason")
    return ExtracaoPainelResponse(
        extracoes_por_outcome=extracoes,
        extracoes_total=sum(extracoes.values()),
        handoffs_por_reason=handoffs,
        handoffs_total=sum(handoffs.values()),
        llm_fallback_por_reason=fallbacks,
        llm_fallback_total=sum(fallbacks.values()),
        retencao="em memória do processo; usar Prometheus para série histórica",
        rotulos="somente outcome categórico; sem texto, identificador ou dado pessoal",
    )


# ============================================================================
# Bloco 4 — operacao
# ============================================================================


@painel_router.get(
    "/operacao",
    summary="Operação de consulta de preços",
    description=(
        "Consultas ao endpoint /emolumentos/real/calcular por outcome, "
        "handoffs ao escrevente e taxa de handoff (divisao por zero tratada)."
    ),
    response_model=OperacaoPainelResponse,
)
async def painel_operacao() -> OperacaoPainelResponse:
    """Bloco 4 do painel: consultas, handoffs e taxa de handoff."""
    consultas = _agregar_contador("cartorio_agent_ai_consultas_total", "outcome")
    consultas_total = sum(consultas.values())
    handoffs_total = sum(store.counters.get("cartorio_agent_ai_handoffs_total", {}).values())
    taxa_handoff = (handoffs_total / consultas_total) if consultas_total > 0 else 0.0
    return OperacaoPainelResponse(
        consultas_por_outcome=consultas,
        consultas_total=consultas_total,
        handoffs_total=handoffs_total,
        taxa_handoff=taxa_handoff,
    )


# ============================================================================
# Telemetria LiteLLM (Fase 3) exposta ao painel
# ============================================================================


@painel_router.get(
    "/ia-usage",
    summary="Uso agregado da IA (LiteLLM spend)",
    description=(
        "Proxy de ia_usage.uso_agregado: custo, chamadas e tokens por modelo "
        "e por dia. Retorna {'disponivel': False, 'motivo': ...} quando a "
        "telemetria nao esta configurada — nunca vaza exception."
    ),
)
async def painel_ia_usage(
    dias: Annotated[int, Query(ge=1, le=365, description="Janela de agregação em dias.")] = 30,
) -> dict[str, Any]:
    """Telemetria de uso da IA (somente colunas agregadas, sem PII)."""
    return ia_usage.uso_agregado(dias)


__all__ = ["painel_router"]
