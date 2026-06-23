"""Schemas Pydantic v2 do recurso Protocolo.

Cobre:
- Entrada de criacao (POST /api/v1/protocolo) com consentimento LGPD obrigatorio.
- Saida de consulta (GET /api/v1/protocolo/{numero}) com historico + proxima acao.
- Erros estruturados (404, LGPD_BLOCKED, 422).

Convencoes:
- Campos PII (cpf) entram crus pelo cliente, sao scrubbed no service layer,
  e persistidos apenas como hash no banco. Schema NAO persiste PII puro.
- Status segue o enum do modelo: DRAFT, aberto, em_andamento, aguardando_doc,
  concluido, cancelado, expirado.
- numero_protocolo segue formato ANO-SEQUENCIAL (YYYY-NNNNN).
"""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


# ============================================================================
# Enums e constantes de dominio
# ============================================================================

class StatusProtocolo(str, Enum):
    """Ciclo de vida do protocolo. DRAFT = criado pelo bot, aguardando HITL."""

    DRAFT = "DRAFT"
    ABERTO = "aberto"
    EM_ANDAMENTO = "em_andamento"
    AGUARDANDO_DOC = "aguardando_doc"
    CONCLUIDO = "concluido"
    CANCELADO = "cancelado"
    EXPIRADO = "expirado"


class CanalOrigem(str, Enum):
    """Canal pelo qual o cliente iniciou o atendimento."""

    WHATSAPP = "whatsapp"
    TELEGRAM = "telegram"
    WEB = "web"
    BALCAO = "balcao"
    EMAIL = "email"


class EtapaHistorico(str, Enum):
    """Etapas que aparecem no historico do protocolo."""

    CRIADO = "criado"
    PII_SCRUBBED = "pii_scrubbed"
    AGUARDANDO_DOC = "aguardando_documento"
    AGUARDANDO_APROVACAO = "aguardando_aprovacao_escrevente"
    EM_ANALISE = "em_analise_juridica"
    EMOLUMENTO_CALCULADO = "emolumento_calculado"
    CONCLUIDO = "concluido"
    CANCELADO = "cancelado"


# ============================================================================
# Erros estruturados
# ============================================================================

class ErrorResponse(BaseModel):
    """Envelope padrao de erro 4xx/5xx para a API."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "erro": "LGPD_BLOCKED",
                "mensagem": "Consentimento obrigatorio. Cliente precisa aceitar LGPD.",
            }
        }
    )

    erro: str = Field(..., description="Codigo curto do erro (LGPD_BLOCKED, NOT_FOUND, ...).")
    mensagem: str = Field(..., description="Mensagem humana em PT-BR explicando o erro.")
    detalhes: dict | None = Field(default=None, description="Detalhes adicionais opcionais.")


class LGPDBlockedResponse(ErrorResponse):
    """Erro especifico quando o cliente recusa consentimento LGPD."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "erro": "LGPD_BLOCKED",
                "mensagem": (
                    "Consentimento obrigatorio. Conforme Lei 13.709/2018 (LGPD), "
                    "o tratamento de dados pessoais exige consentimento explicito."
                ),
                "detalhes": {"consentimento_lgpd_aceito": False},
            }
        }
    )


class ProtocoloNotFoundResponse(ErrorResponse):
    """Erro 404 especifico para GET /api/v1/protocolo/{numero}."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "erro": "PROTOCOLO_NOT_FOUND",
                "mensagem": "Protocolo 2026-99999 nao encontrado.",
                "detalhes": {"numero_consultado": "2026-99999"},
            }
        }
    )


# ============================================================================
# Request: criacao de protocolo
# ============================================================================

class ProtocoloCreateRequest(BaseModel):
    """Payload de entrada para POST /api/v1/protocolo.

    LGPD: o campo `consentimento_lgpd` DEVE ser True. Sem isso, o endpoint
    retorna 422 com codigo LGPD_BLOCKED (gate regulatorio, nao erro de
    validacao tecnica - optamos por 422 para o cliente ver o motivo).

    O `cliente_cpf` e recebido em texto puro do cliente, mas e scrubbed antes
    de qualquer saida para LLM e hasheado antes de persistir.
    """

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "cliente_cpf": "123.456.789-09",
                "cliente_nome": "Joao da Silva",
                "tipo": "certidao_negativa",
                "canal_origem": "web",
                "consentimento_lgpd": True,
            }
        }
    )

    cliente_cpf: Annotated[
        str,
        Field(
            min_length=11,
            max_length=14,
            description="CPF do cliente (com ou sem pontuacao). Scrubbed e hasheado antes de persistir.",
            examples=["123.456.789-09"],
        ),
    ]
    cliente_nome: Annotated[
        str,
        Field(
            min_length=3,
            max_length=255,
            description="Nome completo do cliente. NUNCA persistido em texto puro se contiver dado sensivel.",
            examples=["Joao da Silva"],
        ),
    ]
    tipo: Annotated[
        str,
        Field(
            min_length=3,
            max_length=64,
            description=(
                "Tipo do ato cartorario. Valores validos: certidao_negativa, "
                "certidao_positiva, certidao_casamento, escritura_compra_venda, "
                "escritura_doacao, procuracao, autenticacao, reconhecimento_firma, "
                "registro_nascimento, registro_obito."
            ),
            examples=["certidao_negativa"],
        ),
    ]
    canal_origem: Annotated[
        CanalOrigem,
        Field(
            default=CanalOrigem.WEB,
            description="Canal pelo qual o cliente iniciou a solicitacao.",
        ),
    ]
    consentimento_lgpd: Annotated[
        bool,
        Field(
            description=(
                "OBRIGATORIO ser True. Conforme LGPD (Lei 13.709/2018, art. 7o, I), "
                "o tratamento de dados pessoais exige consentimento explicito. "
                "Se False, retorna 422 LGPD_BLOCKED."
            ),
        ),
    ]

    @field_validator("cliente_cpf")
    @classmethod
    def _strip_cpf(cls, v: str) -> str:
        """Aceita CPF com ou sem pontuacao - normaliza para 11 digitos."""
        digits = "".join(c for c in v if c.isdigit())
        if len(digits) != 11:
            raise ValueError(f"CPF deve conter 11 digitos, recebeu {len(digits)}")
        return digits

    @field_validator("tipo")
    @classmethod
    def _strip_tipo(cls, v: str) -> str:
        """Normaliza tipo pra lowercase, sem espacos."""
        return v.strip().lower()


# ============================================================================
# Response: saida do GET /api/v1/protocolo/{numero}
# ============================================================================

class HistoricoEtapa(BaseModel):
    """Uma entrada no historico de etapas do protocolo."""

    etapa: Annotated[
        EtapaHistorico,
        Field(description="Identificador da etapa."),
    ]
    timestamp: Annotated[
        datetime,
        Field(description="Quando a etapa foi registrada (UTC)."),
    ]
    descricao: Annotated[
        str,
        Field(
            description="Descricao humana em PT-BR do que aconteceu na etapa.",
            examples=["Protocolo criado em modo DRAFT aguardando validacao do escrevente."],
        ),
    ]
    autor: Annotated[
        str,
        Field(
            description="Quem executou a etapa (bot, escrevente, sistema, etc).",
            examples=["bot"],
        ),
    ]


class ProtocoloResponse(BaseModel):
    """Resposta completa do GET /api/v1/protocolo/{numero}.

    Inclui estado atual + historico + proxima acao esperada + prazo estimado.
    A coluna `valor_total` reflete snapshot da tabela de emolumentos na data
    de criacao (regra do projeto: nunca recalcular protocolo antigo).
    """

    model_config = ConfigDict(
        from_attributes=True,
        json_schema_extra={
            "example": {
                "numero": "2026-00001",
                "status": "DRAFT",
                "etapa_atual": "criado",
                "cliente": {"nome": "Joao da Silva", "cpf_hash": "a" * 64},
                "tipo": "certidao_negativa",
                "canal_origem": "web",
                "valor_base": "87.50",
                "valor_total": "87.50",
                "tabela_referencia": "TABELA_2026_MG",
                "prazo_estimado": "5 dias uteis",
                "proxima_acao": (
                    "Aguardando validacao do escrevente. "
                    "Acesse o painel admin ou aguarde contato via WhatsApp."
                ),
                "historico": [
                    {
                        "etapa": "pii_scrubbed",
                        "timestamp": "2026-06-23T10:00:00.000000",
                        "descricao": "CPF do cliente hasheado (SHA256+salt) e removido do payload.",
                        "autor": "bot",
                    },
                    {
                        "etapa": "criado",
                        "timestamp": "2026-06-23T10:00:00.500000",
                        "descricao": (
                            "Protocolo criado em modo DRAFT aguardando validacao humana."
                        ),
                        "autor": "bot",
                    },
                ],
                "created_at": "2026-06-23T10:00:00.500000",
                "updated_at": "2026-06-23T10:00:00.500000",
            }
        },
    )

    numero: Annotated[
        str,
        Field(
            pattern=r"^\d{4}-\d{5}$",
            description="Numero do protocolo no formato ANO-SEQUENCIAL (YYYY-NNNNN).",
            examples=["2026-00001"],
        ),
    ]
    status: Annotated[
        StatusProtocolo,
        Field(description="Status atual do protocolo no ciclo de vida."),
    ]
    etapa_atual: Annotated[
        EtapaHistorico,
        Field(description="Etapa atual (ultima do historico)."),
    ]
    cliente: Annotated[
        "ClienteResumo",
        Field(description="Dados do cliente (apenas nome + hash do CPF)."),
    ]
    tipo: Annotated[str, Field(description="Tipo do ato cartorario.")]
    canal_origem: Annotated[CanalOrigem, Field(description="Canal de origem.")]
    valor_base: Annotated[
        Decimal | None,
        Field(description="Valor base do emolumento (snapshot na data de criacao)."),
    ]
    valor_total: Annotated[
        Decimal | None,
        Field(description="Valor total do emolumento (base + adicionais)."),
    ]
    tabela_referencia: Annotated[
        str | None,
        Field(description="Identificador da tabela de emolumentos usada."),
    ]
    prazo_estimado: Annotated[
        str | None,
        Field(description="Prazo estimado em PT-BR (ex: '5 dias uteis')."),
    ]
    proxima_acao: Annotated[
        str,
        Field(description="Descricao da proxima acao esperada do fluxo."),
    ]
    historico: Annotated[
        list[HistoricoEtapa],
        Field(description="Linha do tempo completa das etapas do protocolo."),
    ]
    created_at: Annotated[datetime, Field(description="Data de criacao (UTC).")]
    updated_at: Annotated[datetime, Field(description="Data da ultima atualizacao (UTC).")]


class ClienteResumo(BaseModel):
    """Resumo publico do cliente (sem PII em texto puro)."""

    model_config = ConfigDict(from_attributes=True)

    nome: Annotated[
        str,
        Field(description="Nome do cliente (pode conter PII - cuidado ao logar)."),
    ]
    cpf_hash: Annotated[
        str,
        Field(description="Hash SHA256 do CPF (com salt). NAO permite reversao."),
    ]


# Resolver forward reference
ProtocoloResponse.model_rebuild()


# ============================================================================
# Response: saida do POST /api/v1/protocolo
# ============================================================================

class ProtocoloCreateResponse(BaseModel):
    """Resposta do POST /api/v1/protocolo.

    Em caso de LGPD_BLOCKED, retorna 422 + LGPDBlockedResponse.
    Em caso de sucesso, retorna 201 com o protocolo criado em modo DRAFT.
    """

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "status": "criado",
                "numero": "2026-00042",
                "protocolo_id": 42,
                "estado": "DRAFT",
                "proxima_acao": (
                    "Aguardando validacao humana do escrevente. "
                    "O protocolo NAO sera processado ate confirmacao no painel admin."
                ),
                "cliente_id": 7,
            }
        }
    )

    status: Annotated[Literal["criado"], Field(description="Sempre 'criado' em sucesso.")]
    numero: Annotated[
        str,
        Field(
            pattern=r"^\d{4}-\d{5}$",
            description="Numero do protocolo atribuido (ANO-SEQUENCIAL).",
            examples=["2026-00042"],
        ),
    ]
    protocolo_id: Annotated[
        int,
        Field(description="ID interno do protocolo no banco."),
    ]
    estado: Annotated[
        StatusProtocolo,
        Field(description="Estado inicial. SEMPRE DRAFT (HITL obrigatorio)."),
    ]
    proxima_acao: Annotated[
        str,
        Field(description="O que o cliente/escrevente deve fazer em seguida."),
    ]
    cliente_id: Annotated[
        int,
        Field(description="ID interno do cliente (reutilizado se CPF ja existir)."),
    ]


__all__ = [
    "CanalOrigem",
    "ClienteResumo",
    "ErrorResponse",
    "EtapaHistorico",
    "HistoricoEtapa",
    "LGPDBlockedResponse",
    "ProtocoloCreateRequest",
    "ProtocoloCreateResponse",
    "ProtocoloNotFoundResponse",
    "ProtocoloResponse",
    "StatusProtocolo",
]
