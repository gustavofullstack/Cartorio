"""LGPD RIPD — Relatorio de Impacto a Protecao de Dados (D21).

Endpoint publico que retorna o RIPD (Relatorio de Impacto a Protecao de Dados
Pessoais) do 2o Servico Notarial de Uberlandia, exigido pela LGPD art. 38 e
recomendado pela ANPD para agentes de tratamento que realizam tratamento de
alto risco (notas e escrituras publicas).

Conteudo:
1. Identificacao do agente de tratamento
2. Descricao dos tratamentos e finalidades
3. Categorias de dados pessoais tratados
4. Bases legais (LGPD art. 6o e 7o)
5. Riscos identificados (probabilidade x impacto)
6. Medidas de mitigacao
7. Plano de retencao por categoria
8. Direitos dos titulares (LGPD art. 18)

LGPD-by-design: o RIPD nao expoe PII individual. Apenas informacoes agregadas
sobre categorias de dados e finalidades. Auth minima via X-API-Key.

Usage:
    GET /api/v1/lgpd/ripd[?format=json|markdown]

References:
    - LGPD Lei 13.709/2018 art. 38 (relatorio de impacto)
    - Recomendacao ANPD/CDIR/01/2023 (RIPD)
    - Provimento CNJ 74/2018 (notarios)
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.api.deps import require_cartorio_api_key
from app.db import get_db

ripd_router = APIRouter(tags=["lgpd-ripd"])


# ============================================================================
# Conteudo estruturado do RIPD (LGPD art. 38 + ANPD Recomendacao 01/2023)
# ============================================================================

_RIPD_METADATA: dict[str, Any] = {
    "documento": "RIPD — Relatorio de Impacto a Protecao de Dados Pessoais",
    "versao": "1.0",
    "base_legal_geral": "LGPD Lei 13.709/2018",
    "agente_tratamento": {
        "nome": "2o Servico Notarial de Uberlandia",
        "cnpj": "PLACEHOLDER_CNPJ",
        "endereco": "Uberlandia, MG, Brasil",
        "representante_legal": "Tabeliao(a) titular do servico",
        "encarregado_dpo": {
            "nome": "Gustavo Almeida",
            "email": "dpo@2notasudi.com.br",
            "telefone": "+55 34 99999-9999",
            "papel": "Encarregado de Dados (LGPD art. 41)",
            "telegram_chat_id": "6682284055",
        },
    },
}

_RIPD_CATEGORIAS_DADOS: list[dict[str, str]] = [
    {
        "categoria": "dados_identificacao",
        "descricao": "Nome completo, CPF/CNPJ (apenas hash SHA-256), RG, data de nascimento.",
        "tipo_lgpd": "pessoal",
        "exemplos_campos": "clientes.nome, clientes.cpf_hash, clientes.telefone_hash",
    },
    {
        "categoria": "dados_contato",
        "descricao": "Telefone (hash), e-mail, endereco, WhatsApp ID, Telegram chat_id.",
        "tipo_lgpd": "pessoal",
        "exemplos_campos": "clientes.email, clientes.whatsapp_number, clientes.telegram_chat_id",
    },
    {
        "categoria": "dados_ato_juridico",
        "descricao": "Tipo do ato, valor, partes envolvidas, data do ato, numero da escritura/protocolo.",
        "tipo_lgpd": "pessoal",
        "exemplos_campos": "protocolos.tipo, protocolos.valor_total, protocolos.numero",
    },
    {
        "categoria": "dados_documento",
        "descricao": "PDFs, imagens de documentos, hash SHA-256 de integridade.",
        "tipo_lgpd": "pessoal_documental",
        "exemplos_campos": "documentos.filename, documentos.hash_sha256",
    },
    {
        "categoria": "dados_audit",
        "descricao": "request_id, IP truncado /24 (LGPD D5), user_agent, canal de origem.",
        "tipo_lgpd": "pessoal_logs",
        "exemplos_campos": "audit_log.ip_truncated, audit_log.user_agent, audit_log.canal",
    },
    {
        "categoria": "dados_lgpd",
        "descricao": "Consentimento, finalidades aceitas/revogadas, motivo de encerramento, retencao.",
        "tipo_lgpd": "pessoal_metadados",
        "exemplos_campos": "clientes.consentimento_lgpd, lgpd_consents.finalidades",
    },
]

_RIPD_FINALIDADES: list[dict[str, str]] = [
    {
        "finalidade": "Atendimento Notarial",
        "descricao": "Prestacao dos servicos notariais (escrituras, procurações, certidoes, reconhecimentos de firma).",
        "base_legal": "LGPD art. 6o II (execucao de contrato) + art. 7o II (obrigacao legal - Lei 8.935/94)",
    },
    {
        "finalidade": "Calculo de Emolumentos",
        "descricao": "Calculo e cobranca dos emolumentos devidos pelos atos praticados (tabela MG 2026).",
        "base_legal": "LGPD art. 7o II (obrigacao legal - Provimento CGJ/MG)",
    },
    {
        "finalidade": "Auditoria e Compliance",
        "descricao": "Registro imutavel de todas as operacoes de tratamento (audit chain SHA256+HMAC).",
        "base_legal": "LGPD art. 7o II (cumprimento de obrigacao legal - LGPD art. 37)",
    },
    {
        "finalidade": "Cumprimento de Obrigacao Legal/Regulatoria",
        "descricao": "Atendimento a fiscalizacao CGJ/MG, CNJ, Receita Federal, ANPD.",
        "base_legal": "LGPD art. 7o II (obrigacao legal) + art. 6o III (interesse publico)",
    },
    {
        "finalidade": "Atendimento via WhatsApp/Telegram/Web",
        "descricao": "Bot multi-canal para orientacao inicial, agendamento e consulta de protocolos.",
        "base_legal": "LGPD art. 7o I (consentimento especifico do titular)",
    },
    {
        "finalidade": "LGPD Compliance (Direitos do Titular)",
        "descricao": "Atendimento aos 6 direitos do art. 18 (acesso, correcao, anonimizacao, portabilidade, etc).",
        "base_legal": "LGPD art. 7o VI (exercicio regular de direitos)",
    },
]

_RIPD_BASES_LEGAIS: list[dict[str, str]] = [
    {
        "artigo_lgpd": "art. 6o II",
        "principio": "necessidade",
        "aplicacao": "Apenas dados estritamente necessarios para o ato notarial sao coletados.",
    },
    {
        "artigo_lgpd": "art. 6o III",
        "principio": "transparencia",
        "aplicacao": "Banner de consentimento + Privacy Policy acessivel via bot (D19) e endpoint publico.",
    },
    {
        "artigo_lgpd": "art. 6o VIII",
        "principio": "prevencao",
        "aplicacao": "Audit chain SHA256+HMAC + PII scrubbing 3 camadas antes de LLM publica.",
    },
    {
        "artigo_lgpd": "art. 7o I",
        "hipotese": "consentimento",
        "aplicacao": "Para canais de marketing e prospeccao (consentimento opt-in granulhar).",
    },
    {
        "artigo_lgpd": "art. 7o II",
        "hipotese": "obrigacao legal",
        "aplicacao": "Para cumprimento da Lei 8.935/94 (servicos notariais) e Provimento CNJ 74/2018.",
    },
    {
        "artigo_lgpd": "art. 7o VI",
        "hipotese": "exercicio regular de direitos",
        "aplicacao": "Para execucao dos direitos do titular (art. 18 — anonimizacao, acesso, portabilidade).",
    },
]

_RIPD_RISCOS: list[dict[str, Any]] = [
    {
        "id": "R1",
        "descricao": "Acesso nao autorizado via X-API-Key comprometida.",
        "probabilidade": "baixa",
        "impacto": "alto",
        "mitigacao": "Rotacao periodica de chaves + MFA via Tailscale + audit log de tentativas falhas (LGPD D5).",
    },
    {
        "id": "R2",
        "descricao": "Vazamento de PII por LLM publica (OpenAI/Anthropic).",
        "probabilidade": "media",
        "impacto": "alto",
        "mitigacao": (
            "PII scrubbing 3 camadas (Pydantic validators + Sentry before_send + log MaskingFilter) "
            "ANTES de qualquer chamada LLM. Provider primario opencode_go (self-hosted)."
        ),
    },
    {
        "id": "R3",
        "descricao": "Retencao excessiva de dados alem do prazo legal.",
        "probabilidade": "media",
        "impacto": "medio",
        "mitigacao": (
            "Scheduler diario retencao (03:00 BRT) apaga conversas >90 dias; clientes sem protocolo >5 anos "
            "sao anonimizados."
        ),
    },
    {
        "id": "R4",
        "descricao": "Modificacao retroativa do audit log (tampering).",
        "probabilidade": "muito_baixa",
        "impacto": "critico",
        "mitigacao": (
            "Hash chain SHA256 + HMAC por entrada + dead-man's switch a cada 15min + verificacao "
            "automatica GET /admin/audit/health."
        ),
    },
    {
        "id": "R5",
        "descricao": "Exposicao de PII raw via logs de aplicacao ou APIs publicas.",
        "probabilidade": "baixa",
        "impacto": "alto",
        "mitigacao": "MaskingFilter em TODO log (CPF/CNPJ/RG/email/phone padronizados) + IP truncado /24.",
    },
]

_RIPD_MITIGACOES: list[dict[str, str]] = [
    {
        "controle": "Audit Chain SHA256+HMAC",
        "descricao": "Cada entrada do audit log eh encadeada via hash da anterior + assinatura HMAC. Tamper-evident.",
        "referencia": "app/services/audit.py + tests/test_audit.py (regressao t024, t025)",
    },
    {
        "controle": "PII Scrubbing 3 Camadas",
        "descricao": "Pydantic field validators + Sentry before_send + log MaskingFilter. CPF/RG/telefone nunca raw.",
        "referencia": "app/services/pii.py + app/services/log_masker.py",
    },
    {
        "controle": "Soft Delete + Anonimizacao",
        "descricao": "Cliente anon. (LGPD art. 18 IV/V) preserva PK mas zera PII. Janela de reversibilidade 30 dias.",
        "referencia": "app/services/lgpd_direito_esquecimento.py (D14)",
    },
    {
        "controle": "Retencao Configuravel",
        "descricao": "Conversas 90d, clientes COM protocolo 5y, audit log 7y (obrigacao legal).",
        "referencia": "app/jobs/retencao.py (scheduler diario 03:00 BRT)",
    },
    {
        "controle": "HITL obrigatorio",
        "descricao": "Protocolo nasce DRAFT; escrevente valida antes de processar. Bot nunca decide sozinho.",
        "referencia": "PRD cartorio + ADR 015 + tests/test_protocolo.py",
    },
    {
        "controle": "Rate Limit 3-tier",
        "descricao": "N8N 600/min, DPO 60/min, default 30/min. Sliding window + fail-open se Redis cair.",
        "referencia": "app/services/rate_limit.py + app/services/rate_limit_by_key.py",
    },
]

_RIPD_RETENCAO: dict[str, Any] = {
    "regra_geral": (
        "Retencao minima para cumprimento de obrigacao legal (Provimento CNJ 74/2018, "
        "Lei 8.935/94 art. 25). Pos-retencao: anonimizacao irreversivel ou hard delete."
    ),
    "categorias": [
        {
            "categoria": "clientes (com protocolo ativo)",
            "prazo": "5 anos pos-ultimo atendimento",
            "acao_pos_prazo": "Anonimizacao (nome + email + telefone zerados, PK preservado)",
            "base_legal": "Provimento CNJ 74/2018 art. 14",
        },
        {
            "categoria": "clientes (sem protocolo)",
            "prazo": "5 anos pos-cadastro",
            "acao_pos_prazo": "Anonimizacao",
            "base_legal": "LGPD art. 18 V (minimizacao)",
        },
        {
            "categoria": "conversas (WhatsApp/Telegram/Web)",
            "prazo": "90 dias",
            "acao_pos_prazo": "Hard delete",
            "base_legal": "LGPD art. 6o II (necessidade) — conteudo ja eh PII-scrubbed",
        },
        {
            "categoria": "audit_log",
            "prazo": "7 anos",
            "acao_pos_prazo": "Manter (obrigacao legal — LGPD art. 37 + integridade forense)",
            "base_legal": "LGPD art. 37 + CPC art. 405",
        },
        {
            "categoria": "documentos (PDFs/imagens)",
            "prazo": "5 anos pos-ato",
            "acao_pos_prazo": "Mover para archive cold storage",
            "base_legal": "Provimento CNJ 74/2018 art. 23",
        },
        {
            "categoria": "protocolos (DRAFT abandonados)",
            "prazo": "180 dias",
            "acao_pos_prazo": "Hard delete",
            "base_legal": "LGPD art. 6o II",
        },
    ],
}

_RIPD_DIREITOS_TITULAR: list[dict[str, str]] = [
    {
        "direito": "Confirmacao de existencia + Acesso (art. 18 I+II)",
        "como_exercer": "POST /api/v1/lgpd/consent/cliente/{id} ou GET /cliente/{id}/lgpd/acesso",
        "prazo_resposta": "15 dias (LGPD art. 18 §5)",
    },
    {
        "direito": "Correcao (art. 18 III)",
        "como_exercer": "POST /cliente/{id}/lgpd/corrigir",
        "prazo_resposta": "15 dias",
    },
    {
        "direito": "Anonimizacao, Bloqueio ou Eliminacao (art. 18 IV)",
        "como_exercer": "POST /cliente/{id}/lgpd/anonimizar (reversivel por 30 dias)",
        "prazo_resposta": "Imediato (soft delete)",
    },
    {
        "direito": "Portabilidade (art. 18 V)",
        "como_exercer": "GET /api/v1/lgpd/export/{cliente_id} ou POST /cliente/{id}/lgpd/portabilidade",
        "prazo_resposta": "15 dias",
    },
    {
        "direito": "Revogacao do consentimento (art. 18 VI)",
        "como_exercer": "POST /cliente/{id}/lgpd/revogar_consentimento",
        "prazo_resposta": "Imediato",
    },
    {
        "direito": "Oposicao (art. 18 IX)",
        "como_exercer": "POST /cliente/{id}/lgpd/oposicao ou /optout",
        "prazo_resposta": "15 dias",
    },
]


def _build_ripd() -> dict[str, Any]:
    """Constroi o documento RIPD completo (estrutura in-memory, sem PII).

    Returns:
        dict estruturado com todas as 8 secoes do RIPD + timestamp + version.
    """
    return {
        "metadata": {
            **_RIPD_METADATA,
            "gerado_em": datetime.now(tz=timezone.utc).isoformat(),
            "gerado_por": "system:cartorio-dpo",
        },
        "categorias_dados_pessoais": _RIPD_CATEGORIAS_DADOS,
        "finalidades": _RIPD_FINALIDADES,
        "bases_legais": _RIPD_BASES_LEGAIS,
        "riscos_identificados": _RIPD_RISCOS,
        "medidas_mitigacao": _RIPD_MITIGACOES,
        "politica_retencao": _RIPD_RETENCAO,
        "direitos_titular_art_18": _RIPD_DIREITOS_TITULAR,
    }


def _render_ripd_markdown(ripd: dict[str, Any]) -> str:
    """Renderiza o RIPD em Markdown (RFC P1-2026 — D21).

    Estrutura: titulo + metadata + 7 secoes principais. Otimizado para envio
    via Telegram/WhatsApp (suporta subset de Markdown: bold, listas, headers).
    """
    meta = ripd["metadata"]
    lines: list[str] = [
        f"# {meta['documento']}",
        "",
        f"**Versao**: {meta['versao']}  ",
        f"**Gerado em**: {meta['gerado_em']}  ",
        f"**Base legal geral**: {meta['base_legal_geral']}",
        "",
        "## 1. Identificacao do Agente de Tratamento",
        "",
        f"- **Nome**: {meta['agente_tratamento']['nome']}",
        f"- **CNPJ**: {meta['agente_tratamento']['cnpj']}",
        f"- **Endereco**: {meta['agente_tratamento']['endereco']}",
        f"- **Representante legal**: {meta['agente_tratamento']['representante_legal']}",
        "",
        "### Encarregado/DPO (LGPD art. 41)",
        "",
        f"- **Nome**: {meta['agente_tratamento']['encarregado_dpo']['nome']}",
        f"- **E-mail**: {meta['agente_tratamento']['encarregado_dpo']['email']}",
        f"- **Telefone**: {meta['agente_tratamento']['encarregado_dpo']['telefone']}",
        f"- **Telegram (DPO direto)**: `{meta['agente_tratamento']['encarregado_dpo']['telegram_chat_id']}`",
        "",
        "## 2. Categorias de Dados Pessoais Tratados",
        "",
    ]

    for cat in ripd["categorias_dados_pessoais"]:
        lines.extend(
            [
                f"### {cat['categoria']} ({cat['tipo_lgpd']})",
                f"- {cat['descricao']}",
                f"- **Campos no schema**: `{cat['exemplos_campos']}`",
                "",
            ]
        )

    lines.append("## 3. Finalidades de Tratamento")
    lines.append("")
    for f in ripd["finalidades"]:
        lines.extend(
            [
                f"### {f['finalidade']}",
                f"- {f['descricao']}",
                f"- **Base legal**: {f['base_legal']}",
                "",
            ]
        )

    lines.append("## 4. Bases Legais (LGPD art. 6o e 7o)")
    lines.append("")
    for bl in ripd["bases_legais"]:
        key = bl.get("principio") or bl.get("hipotese") or "—"
        article = bl["artigo_lgpd"]
        lines.extend(
            [
                f"- **{article}** ({key}): {bl['aplicacao']}",
            ]
        )
    lines.append("")

    lines.append("## 5. Riscos Identificados")
    lines.append("")
    for r in ripd["riscos_identificados"]:
        lines.extend(
            [
                f"### {r['id']} — {r['descricao']}",
                f"- **Probabilidade**: {r['probabilidade']}",
                f"- **Impacto**: {r['impacto']}",
                f"- **Mitigacao**: {r['mitigacao']}",
                "",
            ]
        )

    lines.append("## 6. Medidas de Mitigacao")
    lines.append("")
    for m in ripd["medidas_mitigacao"]:
        lines.extend(
            [
                f"### {m['controle']}",
                f"- {m['descricao']}",
                f"- **Referencia**: `{m['referencia']}`",
                "",
            ]
        )

    lines.append("## 7. Politica de Retencao por Categoria")
    lines.append("")
    lines.append(f"> {ripd['politica_retencao']['regra_geral']}")
    lines.append("")
    for c in ripd["politica_retencao"]["categorias"]:
        lines.extend(
            [
                f"### {c['categoria']}",
                f"- **Prazo**: {c['prazo']}",
                f"- **Acao pos-prazo**: {c['acao_pos_prazo']}",
                f"- **Base legal**: {c['base_legal']}",
                "",
            ]
        )

    lines.append("## 8. Direitos dos Titulares (LGPD art. 18)")
    lines.append("")
    for d in ripd["direitos_titular_art_18"]:
        lines.extend(
            [
                f"### {d['direito']}",
                f"- **Como exercer**: `{d['como_exercer']}`",
                f"- **Prazo de resposta**: {d['prazo_resposta']}",
                "",
            ]
        )

    return "\n".join(lines)


# ============================================================================
# Endpoint publico
# ============================================================================


@ripd_router.get(
    "/lgpd/ripd",
    summary="RIPD — Relatorio de Impacto a Protecao de Dados",
    description=(
        "Retorna o RIPD (LGPD art. 38) do 2o Servico Notarial de Uberlandia.\n\n"
        "Inclui 8 secoes: identificacao do agente, categorias de dados, finalidades, "
        "bases legais, riscos + mitigacao, politica de retencao, e direitos do titular (art. 18).\n\n"
        "NAO expoe PII individual — apenas informacoes agregadas sobre categorias e finalidades.\n\n"
        "Auth: X-API-Key (gate padrao LGPD D21). Formato: `json` (default) ou `markdown`."
    ),
)
def get_ripd(
    request: Request,
    _api_key: Annotated[str, Depends(require_cartorio_api_key)] = "",
    format: str = Query("json", pattern="^(json|markdown)$"),
    db: Annotated[Session, Depends(get_db)] = None,  # type: ignore[assignment]
) -> JSONResponse:
    """Retorna o RIPD estruturado (json) ou renderizado (markdown)."""
    ripd = _build_ripd()
    if format == "markdown":
        md = _render_ripd_markdown(ripd)
        return JSONResponse(
            status_code=200,
            content={
                "ripd_markdown": md,
                "gerado_em": ripd["metadata"]["gerado_em"],
            },
        )
    return JSONResponse(status_code=200, content=ripd)


__all__ = ["ripd_router", "_build_ripd", "_render_ripd_markdown"]
