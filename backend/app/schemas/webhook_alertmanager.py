"""Pydantic schemas para AlertManager v4 webhook payload (G8.15.T2 + G8.17.T2).

LGPD: ``extra="forbid"`` + whitelist de campos (LGPD Art. 46 - seguranca por
design). Qualquer campo nao documentado eh rejeitado (forward-compat).

G8.17.T2: cada campo com `Field(description=...)` + marker `**LGPD PII**` em
campos sensiveis (summary/description/runbook).

Ref: https://prometheus.io/docs/alerting/latest/configuration/#webhook_config
"""

from __future__ import annotations

from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field

from app.services.pii_marker import PIIField

_AM_CONFIG = ConfigDict(strict=True, extra="forbid")


class AlertLabel(BaseModel):
    """Labels canonicos aceitos (whitelist LGPD). Outros campos rejeitados."""

    model_config = _AM_CONFIG

    alertname: Annotated[
        str,
        Field(
            description="Nome canonico do alerta Prometheus (obrigatorio).",
            min_length=1,
            max_length=200,
            examples=["HighErrorRate", "API5xxSpike"],
        ),
    ]
    severity: Annotated[
        str,
        Field(
            default="warning",
            description="Severidade: 'critical' (P0), 'warning' (P1), 'info' (P2).",
            pattern="^(critical|warning|info)$",
            examples=["critical", "warning"],
        ),
    ]
    instance: Annotated[
        str,
        Field(
            default="unknown",
            description="Host:port do servico afetado (truncado em 300 chars).",
            max_length=300,
            examples=["cartorio-api-1:8000"],
        ),
    ]
    squad: Annotated[
        str,
        Field(
            default="cartorio-sre",
            description="Squad responsavel pelo alerta (rota Telegram).",
            max_length=100,
            examples=["cartorio-sre", "cartorio-lgpd", "cartorio-n8n"],
        ),
    ]
    job: Annotated[
        str | None,
        Field(
            default=None,
            description="Job Prometheus que originou o alerta.",
            max_length=100,
            examples=["cartorio-api"],
        ),
    ] = None


class AlertAnnotation(BaseModel):
    """Annotations - summary/description/runbook opcionais.

    LGPD: summary/description podem conter CPF/RG/email injetados por engano.
    Backend aplica scrubber regex antes de enviar ao Telegram.
    """

    model_config = _AM_CONFIG

    summary: Annotated[
        str | None,
        PIIField(
            default=None,
            description="Resumo curto do alerta (LGPD: passa por scrubber antes de exibir).",
            max_length=2000,
            examples=["API latency p99 > 2s for 5m"],
        ),
    ] = None
    description: Annotated[
        str | None,
        PIIField(
            default=None,
            description="Descricao detalhada (LGPD: scrubbed antes do Telegram).",
            max_length=4000,
            examples=["Endpoint /api/v1/protocolo p99=2.3s, threshold=2s"],
        ),
    ] = None
    runbook_url: Annotated[
        str | None,
        Field(
            default=None,
            description="URL do runbook (max 500 chars).",
            max_length=500,
            examples=["https://runbooks.2notasudi.com.br/high-latency"],
        ),
    ] = None
    runbook: Annotated[
        str | None,
        Field(
            default=None,
            description="Alias de runbook_url (AlertManager legacy).",
            max_length=500,
        ),
    ] = None


class AlertEntry(BaseModel):
    """Um alerta individual dentro do payload AlertManager v4."""

    model_config = _AM_CONFIG

    status: Annotated[
        str,
        Field(
            description="Estado do alerta: 'firing' (ativo) ou 'resolved' (resolvido).",
            pattern="^(firing|resolved)$",
            examples=["firing", "resolved"],
        ),
    ]
    labels: Annotated[
        AlertLabel,
        Field(description="Labels canonicos (alertname, severity, instance, squad)."),
    ]
    annotations: Annotated[
        AlertAnnotation,
        Field(default_factory=AlertAnnotation, description="Anotacoes (summary/description)."),
    ]
    starts_at: Annotated[
        str | None,
        Field(
            default=None,
            alias="startsAt",
            description="ISO 8601 do momento que o alerta comecou a firing.",
            max_length=64,
        ),
    ] = None
    ends_at: Annotated[
        str | None,
        Field(
            default=None,
            alias="endsAt",
            description="ISO 8601 do momento que o alerta foi resolvido.",
            max_length=64,
        ),
    ] = None
    generator_url: Annotated[
        str | None,
        Field(
            default=None,
            alias="generatorURL",
            description="URL do Prometheus que originou o alerta.",
            max_length=500,
        ),
    ] = None
    fingerprint: Annotated[
        str | None,
        Field(
            default=None,
            description="Hash unico do alerta (16 chars hex).",
            max_length=64,
        ),
    ] = None


class AlertManagerPayload(BaseModel):
    """Payload completo de webhook AlertManager v4.

    LGPD Art. 46: processado em memoria, nao persistido, AUTO-PURGE ao final.
    Documentado em https://prometheus.io/docs/alerting/latest/configuration/#webhook_config
    """

    model_config = _AM_CONFIG

    version: Annotated[
        str,
        Field(
            default="4",
            description="Versao do schema AlertManager.",
            pattern=r"^[1-9][0-9]*$",
            examples=["4"],
        ),
    ]
    group_key: Annotated[
        str,
        Field(
            alias="groupKey",
            description="Chave do grupo de alertas (concat de labels).",
            max_length=500,
        ),
    ]
    status: Annotated[
        str,
        Field(
            description="Status agregado do grupo: 'firing' ou 'resolved'.",
            pattern="^(firing|resolved)$",
        ),
    ]
    receiver: Annotated[
        str,
        Field(
            description="Nome do receiver configurado no AlertManager.",
            max_length=200,
            examples=["cartorio-telegram-default"],
        ),
    ]
    group_labels: Annotated[
        dict[str, str],
        Field(
            default_factory=dict,
            alias="groupLabels",
            description="Labels comuns do grupo (chave=valor).",
        ),
    ]
    common_labels: Annotated[
        dict[str, str],
        Field(
            default_factory=dict,
            alias="commonLabels",
            description="Labels compartilhados entre todos os alerts do grupo.",
        ),
    ]
    common_annotations: Annotated[
        dict[str, str],
        Field(
            default_factory=dict,
            alias="commonAnnotations",
            description="Anotacoes compartilhadas entre todos os alerts.",
        ),
    ]
    alerts: Annotated[
        list[AlertEntry],
        Field(
            description="Lista de alertas individuais (1..100).",
            min_length=1,
            max_length=100,
        ),
    ]


__all__ = [
    "AlertLabel",
    "AlertAnnotation",
    "AlertEntry",
    "AlertManagerPayload",
]
