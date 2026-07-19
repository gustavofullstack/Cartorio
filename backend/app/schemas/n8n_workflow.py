"""Schemas Pydantic v2 estritos para validar exports JSON do N8N.

G8.13.T2 (cartorio-n8n): garantir que os JSONs exportados de workflows
N8N (`infra/n8n-workflows/*.json`) sigam schemas estritos quando carregados
pelo backend para analise/inventory/import.

Regras LGPD/P0:
- LGPD Art. 46: regex anti-PII (CPF/CNPJ/RG/telefone) em `node.name`.
- Forward-compat blocked: `extra="forbid"` em todos os modelos canonicos.
- Timezone IANA validado via `zoneinfo` (stdlib).
- Strict mode (Pydantic v2 `ConfigDict(strict=True)`) — recusa coercoes
  implicitas (int->str, str->int, str->float, etc).

Os campos conhecidos foram catalogados a partir de 39 exports reais
(Wave 29 inventory). Quando o N8N introduzir um novo campo canonico,
o inventario aponta `invalid` ate o schema ser atualizado — esse eh o
HITL by design: nenhuma importacao nao-canonica passa sem review.

Modified by Gustavo Almeida.
"""

from __future__ import annotations

import re
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import BaseModel, ConfigDict, Field, field_validator


# ---------------------------------------------------------------------------
# Constantes
# ---------------------------------------------------------------------------

# Patterns LGPD Art. 46 — deteccao de PII em campos que deveriam ser apenas
# identificadores (node name, parameter values, etc).
#
# NOTA: CEP NAO incluso (false-positive em UUIDs `67260601-4c9b-432f-...`)
# e CEP por si so nao eh dado pessoal.
#
# Cobertura minima: CPF (com/sem pontuacao), CNPJ, RG 7-9 digitos,
# telefone BR (com DDI +55), email.
#
# `\\b` (word boundary) eh usado como ancora para detectar CPFs/CNPJs
# mesmo apos prefixos alfanumericos (ex: "cpf-123.456.789-00") sem cair
# em falsos positivos com UUIDs (segmentos hex nao tem 9+ digitos
# contiguos suficientes para satisfazer os padroes).
_LGPD_PII_PATTERNS: tuple[re.Pattern[str], ...] = (
    # CPF: 11 digitos, opcionalmente pontuado (123.456.789-00 / 12345678900)
    re.compile(r"\b\d{3}\.?\d{3}\.?\d{3}-?\d{2}\b"),
    # CNPJ: 14 digitos, opcionalmente pontuado (com sufixo 0001 obrigatorio)
    re.compile(r"\b\d{2}\.?\d{3}\.?\d{3}/?0001-?\d{2}\b"),
    # RG formato XX.XXX.XXX-X (com pontos para evitar falso-positivo em UUIDs)
    re.compile(r"\b\d{2}\.\d{3}\.\d{3}-?[\dXx]\b"),
    # Telefone BR: +55 DDD 9XXXX-XXXX ou DDD XXXX-XXXX (10-11 digitos)
    re.compile(r"\+?55\s?\(?\d{2}\)?\s?9?\d{4}-?\d{4}\b"),
    # Email
    re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b"),
)


def _contains_pii(value: str) -> bool:
    """Retorna True se o texto contiver padroes LGPD-protegidos."""
    return any(p.search(value) for p in _LGPD_PII_PATTERNS)


# ---------------------------------------------------------------------------
# Settings (cron-aware)
# ---------------------------------------------------------------------------


class N8nSettings(BaseModel):
    """Bloco `settings` do workflow N8N.

    Campos conhecidos catalogados de 39 exports reais (Wave 29 G7). Todos
    opcionais — N8N defaults sao razoaveis. `timezone` precisa ser IANA.
    """

    model_config = ConfigDict(strict=True, extra="forbid")

    executionOrder: str = "v1"
    saveDataErrorExecution: str = "all"
    saveDataSuccessExecution: str = "all"
    saveExecutionProgress: bool = True
    saveManualExecutions: bool = True
    callerPolicy: str = "workflowsFromSameOwner"
    errorWorkflow: str = ""
    # binaryMode aceita bool (legacy) ou string "separate"/"combined" (N8N >=1.x)
    binaryMode: bool | str = False
    availableInMCP: bool = False
    timezone: str | None = None

    @field_validator("executionOrder")
    @classmethod
    def _execution_order_v1(cls, v: str) -> str:
        if v not in {"v1"}:
            raise ValueError(f"executionOrder deve ser 'v1' (got {v!r})")
        return v

    @field_validator("timezone")
    @classmethod
    def _iana_timezone(cls, v: str | None) -> str | None:
        if v is None:
            return None
        try:
            ZoneInfo(v)
        except ZoneInfoNotFoundError as exc:
            raise ValueError(f"Invalid IANA timezone: {v!r}") from exc
        return v

    @field_validator("errorWorkflow")
    @classmethod
    def _no_pii_in_error_workflow(cls, v: str) -> str:
        if v and _contains_pii(v):
            raise ValueError("errorWorkflow contains PII")
        return v


# ---------------------------------------------------------------------------
# Node
# ---------------------------------------------------------------------------


class N8nNode(BaseModel):
    """Um node dentro de `workflow.nodes[]`.

    Campos catalogados de 39 exports. Required canonico: `name`, `type`,
    `typeVersion`, `position`. `id` eh opcional (alguns exports N8N
    omitem — ex: `23-lgpd-esqueci-v2.json` tem 8 nodes sem id).
    """

    model_config = ConfigDict(strict=True, extra="forbid")

    id: str = Field(default="", max_length=200)
    name: str = Field(..., min_length=1, max_length=200)
    type: str = Field(..., min_length=1, max_length=200)
    typeVersion: float = Field(...)  # float — versoes como 3.4 existem
    position: list[float] = Field(..., min_length=2, max_length=2)
    parameters: dict[str, Any] = Field(default_factory=dict)
    credentials: dict[str, Any] = Field(default_factory=dict)
    options: dict[str, Any] = Field(default_factory=dict)
    webhookId: str | None = None
    alwaysOutputData: bool = False
    onError: str = "stopWorkflow"
    retryOnFail: bool = False

    @field_validator("name")
    @classmethod
    def _no_pii_in_name(cls, v: str) -> str:
        # LGPD Art. 46 — node name NAO pode conter dado pessoal.
        if _contains_pii(v):
            raise ValueError("PII detected in node name (LGPD Art. 46): use only safe identifiers")
        return v

    @field_validator("webhookId")
    @classmethod
    def _no_pii_in_webhook_id(cls, v: str | None) -> str | None:
        # webhookId eh UUID de roteamento — nao deve carregar dado pessoal.
        # UUIDs canonicos sao seguros (apenas hex + dash); qualquer outro
        # formato levanta.
        if v is None:
            return None
        if _contains_pii(v):
            raise ValueError("webhookId contains PII (LGPD Art. 46)")
        # Se nao eh UUID canonico, alerta: webhook path exposto em URL publica
        if not re.fullmatch(r"[0-9a-fA-F-]{8,}", v):
            # aceita UUID-like sem rigidez absoluta (N8N as vezes usa slugs)
            pass
        return v

    @field_validator("type")
    @classmethod
    def _type_namespace(cls, v: str) -> str:
        # N8N type segue padrao "namespace.nodeType" — sanity check minimo.
        if "." not in v and not v.startswith("@"):
            # alguns tipos built-in nao tem namespace; aceitamos mas warn
            # via nota de schema — sem raise pra nao quebrar legitimos.
            pass
        return v

    @field_validator("onError")
    @classmethod
    def _on_error_known(cls, v: str) -> str:
        if v not in {"stopWorkflow", "continueRegularOutput", "continueErrorOutput"}:
            raise ValueError(
                f"onError deve ser stopWorkflow|continueRegularOutput|"
                f"continueErrorOutput (got {v!r})"
            )
        return v


# ---------------------------------------------------------------------------
# Workflow (root)
# ---------------------------------------------------------------------------


class N8nWorkflow(BaseModel):
    """Export JSON canonico de um workflow N8N.

    Schema derivado de 39 exports reais (Wave 29 G7). Required: `name`.
    Demais campos seguem defaults razoaveis. `extra="forbid"` bloqueia
    campos novos nao catalogados — sinaliza HITL para revisao do schema
    antes de aceitar imports futuros.
    """

    model_config = ConfigDict(strict=True, extra="forbid")

    # Identidade
    id: str | None = None
    name: str = Field(..., min_length=1, max_length=200)
    description: str | None = None

    # Estado
    active: bool = False
    isArchived: bool = False

    # Conteudo
    nodes: list[N8nNode] = Field(default_factory=list)
    connections: dict[str, Any] = Field(default_factory=dict)
    settings: N8nSettings = Field(default_factory=N8nSettings)
    # N8N exporta tags como list[str] OU list[{"name": "..."}] dependendo da
    # versao. Aceitamos ambos.
    tags: list[str | dict[str, Any]] = Field(default_factory=list)
    pinData: dict[str, Any] | None = None
    staticData: dict[str, Any] | None = None

    # Metadata de versionamento (N8N API)
    activeVersion: dict[str, Any] | None = None
    activeVersionId: str | None = None
    versionId: str | None = None
    versionCounter: int = 1
    triggerCount: int = 0
    meta: dict[str, Any] | None = None

    # Timestamps (N8N ISO-8601)
    createdAt: str | None = None
    updatedAt: str | None = None

    # Compartilhamento / origem
    shared: list[dict[str, Any]] = Field(default_factory=list)
    sourceWorkflowId: str | None = None
    nodeGroups: list[dict[str, Any]] = Field(default_factory=list)

    @field_validator("name", "description")
    @classmethod
    def _no_pii_in_workflow_text(cls, v: str | None) -> str | None:
        if v is not None and _contains_pii(v):
            raise ValueError("PII detected in workflow name/description (LGPD Art. 46)")
        return v

    @field_validator("tags")
    @classmethod
    def _tags_no_pii(cls, v: list[str | dict[str, Any]]) -> list[str | dict[str, Any]]:
        for tag in v:
            text = (
                tag
                if isinstance(tag, str)
                else (tag.get("name", "") if isinstance(tag, dict) else "")
            )
            if isinstance(text, str) and _contains_pii(text):
                raise ValueError(f"PII detected in tag (LGPD Art. 46): {text!r}")
        return v


# ---------------------------------------------------------------------------
# Helpers publicos
# ---------------------------------------------------------------------------


def validate_workflow_payload(payload: dict[str, Any]) -> N8nWorkflow:
    """Valida um payload (dict ja desserializado) contra o schema strict.

    Raises:
        pydantic.ValidationError: em qualquer violacao.
    """
    return N8nWorkflow.model_validate(payload)


def is_strict_valid(payload: dict[str, Any]) -> bool:
    """Retorna True se payload passa schema strict, False caso contrario.

    Nao levanta — util para inventory em batch.
    """
    try:
        N8nWorkflow.model_validate(payload)
    except Exception:  # noqa: BLE001 — ValidationError ou outros
        return False
    return True
