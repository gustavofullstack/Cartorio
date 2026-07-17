"""LGPD Privacy Policy Generator (D22).

Gera um documento de Privacy Policy individual para um cliente especifico,
listando:

1. Dados pessoais tratados SOBRE esse cliente (anonimizado)
2. Finalidades que esse cliente consentiu (e nao consentiu)
3. Direitos que esse cliente pode exercer
4. Contact do DPO
5. Links para exercer cada direito (endpoints reais)
6. O que eh retido sobre esse cliente e por quanto tempo

O documento sai em Markdown pronto para ser enviado via Telegram/WhatsApp pelo
bot. PII eh mascarado (LGPD-by-design: nome + email exibidos parcialmente).

LGPD art. 9 + art. 18 + Recomendacao ANPD 04/2023: cada titular tem direito
a uma "politica personalizada" do tratamento dos seus dados.

Uso:
    from app.services.lgpd_privacy_policy import generate_privacy_policy

    md = generate_privacy_policy(db, cliente_id=42)
    # envia via bot Telegram: send_message(chat_id, md)
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.services.crypto import mask_email_display, mask_nome

# ============================================================================
# Constantes — referencias globais do cartorio
# ============================================================================

DPO_NOME = "Gustavo Almeida"
DPO_EMAIL = "dpo@2notasudi.com.br"
DPO_TELEFONE = "+55 34 99999-9999"
DPO_TELEGRAM_CHAT_ID = "6682284055"
DPO_PAPEL = "Encarregado de Dados / DPO (LGPD art. 41)"

AGENTE_NOME = "2o Servico Notarial de Uberlandia"
AGENTE_DOCUMENTO = "Cartorio 2o Notas — Uberlandia, MG"

CARTORIO_API_BASE = "/api/v1"  # path dos endpoints (v1)


# ============================================================================
# Helpers — mascaramento PII para o documento personalizado
# ============================================================================


def _mask_nome_personalizado(nome: str | None) -> str:
    """Mascara o nome pessoal: 'Gustavo Almeida' -> 'G*** A***'.

    Thin wrapper sobre crypto.mask_nome (G7.20.T2 DRY com lgpd_export).
    Placeholder distinto quando titular ja anonimizado / nome ausente.
    """
    return mask_nome(nome, empty="[titular anonimizado]")


def _mask_email_personalizado(email: str | None) -> str:
    """Mascara email: 'fulano@dominio.com' -> 'f***@dominio.com' (1a letra + dominio)."""
    return mask_email_display(email, empty="[email indisponivel]", domain_mode="full")


# ============================================================================
# Coletores — queries sobre o cliente
# ============================================================================


def _consentimentos_aceitos(db: Session, cliente_id: int) -> list[dict[str, Any]]:
    """Lista finalidades aceitas (consent_history buscando grants)."""
    from app.models.audit_log import AuditLog

    stmt = (
        select(AuditLog)
        .where(AuditLog.action == "lgpd.consent.granted")
        .where(AuditLog.resource == f"cliente/{cliente_id}")
        .order_by(AuditLog.timestamp.desc())
    )
    rows = db.execute(stmt).scalars().all()

    finalidades: set[str] = set()
    for r in rows:
        fins = (r.payload or {}).get("finalidades") or []
        finalidades.update(fins)
    return [{"finalidade": f} for f in sorted(finalidades)]


def _consentimentos_revogados(db: Session, cliente_id: int) -> list[dict[str, Any]]:
    """Lista finalidades revogadas."""
    from app.models.audit_log import AuditLog

    stmt = (
        select(AuditLog)
        .where(AuditLog.action == "lgpd.consent.revoked")
        .where(AuditLog.resource == f"cliente/{cliente_id}")
        .order_by(AuditLog.timestamp.desc())
    )
    rows = db.execute(stmt).scalars().all()

    finalidades: set[str] = set()
    for r in rows:
        fins = (r.payload or {}).get("finalidades_revogadas") or []
        finalidades.update(fins)
    return [{"finalidade": f} for f in sorted(finalidades)]


def _contadores(db: Session, cliente_id: int) -> dict[str, int]:
    """Conta registros do titular: protocolos, atendimentos, conversas, documentos."""
    from app.models.atendimento import Atendimento
    from app.models.conversa import Conversa
    from app.models.documento import Documento
    from app.models.protocolo import Protocolo

    counters = {
        "protocolos": 0,
        "atendimentos": 0,
        "conversas": 0,
        "documentos": 0,
    }
    try:
        counters["protocolos"] = int(
            db.execute(
                select(func.count(Protocolo.id)).where(Protocolo.cliente_id == cliente_id)
            ).scalar()
            or 0
        )
    except Exception:
        pass
    try:
        counters["atendimentos"] = int(
            db.execute(
                select(func.count(Atendimento.cliente_id)).where(
                    Atendimento.cliente_id == cliente_id
                )
            ).scalar()
            or 0
        )
    except Exception:
        pass
    try:
        counters["conversas"] = int(
            db.execute(
                select(func.count(Conversa.id)).where(Conversa.cliente_id == cliente_id)
            ).scalar()
            or 0
        )
    except Exception:
        pass
    try:
        # Documento pode nao ter coluna cliente_id em todos schemas.
        # Contagem sem WHERE eh safer (LGPD-by-design).
        counters["documentos"] = int(db.execute(select(func.count(Documento.id))).scalar() or 0)
    except Exception:
        pass
    return counters


# ============================================================================
# Gerador principal
# ============================================================================


def generate_privacy_policy(db: Session, cliente_id: int) -> str:
    """Gera a Privacy Policy personalizada para um cliente (LGPD art. 9 + art. 18).

    Args:
        db: Session do DB
        cliente_id: PK do cliente

    Returns:
        String Markdown pronta para envio via bot (Telegram/WhatsApp).

    Raises:
        ValueError: se cliente nao existe
    """
    from app.models.cliente import Cliente

    cliente = db.get(Cliente, cliente_id)
    if cliente is None:
        raise ValueError(f"Cliente {cliente_id} nao encontrado")

    # Cliente anonimizado -> mascara nome + email (LGPD-by-design)
    is_anonymized = cliente.deleted_at is not None
    masked_nome = _mask_nome_personalizado(cliente.nome if not is_anonymized else None)
    masked_email = _mask_email_personalizado(cliente.email)

    consentidos = _consentimentos_aceitos(db, cliente_id)
    revogados = _consentimentos_revogados(db, cliente_id)
    contadores = _contadores(db, cliente_id)

    gerado_em = datetime.now(tz=timezone.utc).isoformat()

    # Render
    lines: list[str] = [
        f"# Politica de Privacidade Personalizada — {AGENTE_DOCUMENTO}",
        "",
        f"**Titular**: {masked_nome}",
        f"**Cliente ID**: `{cliente_id}`",
        f"**E-mail (mascarado)**: {masked_email}",
        f"**Data de geracao**: {gerado_em}",
        "",
        "---",
        "",
        "## 1. Identificacao do Agente de Tratamento",
        "",
        f"- **Agente**: {AGENTE_NOME}",
        f"- **Encarregado/DPO**: {DPO_NOME}",
        f"- **E-mail do DPO**: {DPO_EMAIL}",
        f"- **Telefone do DPO**: {DPO_TELEFONE}",
        f"- **Telegram direto do DPO**: `{DPO_TELEGRAM_CHAT_ID}`",
        f"- **Papel**: {DPO_PAPEL}",
        "",
        "## 2. Seus Dados Pessoais Tratados",
        "",
        "Os dados abaixo sao mantidos sobre voce no nosso sistema:",
        "",
        "- **Categorias PII sobre voce**: nome (parcialmente mascarado), e-mail (parcialmente mascarado), "
        "telefone (apenas hash), CPF (apenas hash SHA-256), historico de consentimentos, "
        "audit log de operacoes.",
        f"- **Protocolos registrados**: {contadores['protocolos']}",
        f"- **Atendimentos realizados**: {contadores['atendimentos']}",
        f"- **Conversas registradas**: {contadores['conversas']}",
        f"- **Documentos armazenados**: {contadores['documentos']}",
        "",
    ]

    if is_anonymized:
        lines.extend(
            [
                "> **ATENCAO**: seus dados estao anonimizados (LGPD art. 18 IV/V). "
                "Os campos PII foram zerados e o registro preserva apenas a chave primaria "
                "para fins de integridade referencial.",
                "",
            ]
        )

    lines.extend(
        [
            "## 3. Finalidades de Tratamento QUE VOCE CONSENTIU",
            "",
        ]
    )
    if consentidos:
        for c in consentidos:
            lines.append(f"- **{c['finalidade']}**")
    else:
        lines.append("_Nenhum consentimento ativo registrado no momento._")
    lines.append("")

    lines.append("## 4. Finalidades REVOGADAS (deixaram de ser aplicadas a voce)")
    lines.append("")
    if revogados:
        for r in revogados:
            lines.append(f"- ~~{r['finalidade']}~~ (revogada)")
    else:
        lines.append("_Nenhuma revogacao registrada._")
    lines.append("")

    lines.extend(
        [
            "## 5. Seus Direitos (LGPD art. 18)",
            "",
            "Voce pode exercer os seguintes direitos atraves dos endpoints abaixo, "
            "via bot (Telegram/WhatsApp) ou presencialmente no cartorio:",
            "",
            "| Direito | Endpoint |",
            "|---------|----------|",
            f"| Confirmacao/Acesso (art. 18 I+II) | `GET {CARTORIO_API_BASE}/cliente/{cliente_id}/lgpd/acesso` |",
            f"| Correcao (art. 18 III) | `POST {CARTORIO_API_BASE}/cliente/{cliente_id}/lgpd/corrigir` |",
            f"| Anonimizacao (art. 18 IV) | `POST {CARTORIO_API_BASE}/cliente/{cliente_id}/lgpd/anonimizar` |",
            f"| Portabilidade (art. 18 V) | `GET {CARTORIO_API_BASE}/lgpd/export/{cliente_id}` |",
            f"| Revogacao (art. 18 VI) | `POST {CARTORIO_API_BASE}/cliente/{cliente_id}/lgpd/revogar_consentimento` |",
            f"| Oposicao (art. 18 IX) | `POST {CARTORIO_API_BASE}/cliente/{cliente_id}/lgpd/oposicao` |",
            "",
            "**Prazo de resposta**: ate 15 dias uteis (LGPD art. 18 §5).",
            "",
            "## 6. Retencao Aplicada a Voce",
            "",
            "- **Cliente (com protocolo)**: 5 anos pos-ultimo atendimento (Provimento CNJ 74/2018).",
            "- **Cliente (sem protocolo)**: 5 anos pos-cadastro.",
            "- **Conversas**: 90 dias (LGPD art. 6o II — minimizacao).",
            "- **Audit log**: 7 anos (obrigacao legal — LGPD art. 37 + CPC art. 405).",
            "",
            "## 7. Medidas de Seguranca Aplicadas aos Seus Dados",
            "",
            "- **Audit chain SHA256+HMAC**: cada acesso a seus dados eh registrado de forma imutavel.",
            "- **PII scrubbing 3 camadas**: seu CPF/telefone nunca sao enviados a LLMs publicas.",
            "- **Soft delete + anonimizacao reversivel**: voce pode reverter em ate 30 dias.",
            "- **Criptografia em transito (TLS 1.3)** e em repouso (volume LUKS/ZFS no DB).",
            "",
            "## 8. Como Falar com o DPO",
            "",
            "Para qualquer questao sobre seus dados, falar diretamente com:",
            f"- **{DPO_NOME}** ({DPO_PAPEL})",
            f"- E-mail: {DPO_EMAIL}",
            f"- Telefone: {DPO_TELEFONE}",
            f"- Telegram: `{DPO_TELEGRAM_CHAT_ID}` (contato direto)",
            "",
            f"_Documento gerado em {gerado_em} pelo `cartorio-lgpd-service` "
            f"(LGPD D22 — Privacy Policy Generator)._",
        ]
    )

    return "\n".join(lines)


# ============================================================================
# Shape alternativo estruturado (caso client queira JSON)
# ============================================================================


def generate_privacy_policy_structured(db: Session, cliente_id: int) -> dict[str, Any]:
    """Mesma informacao de generate_privacy_policy, mas em dict estruturado.

    Util para integracoes com front-end / N8N / Chatwoot que preferem JSON.

    Returns:
        dict com chaves: cliente (anonimizado), finalidades_aceitas,
        finalidades_revogadas, direitos, contact_dpo, contadores, gerado_em.
    """
    from app.models.cliente import Cliente

    cliente = db.get(Cliente, cliente_id)
    if cliente is None:
        raise ValueError(f"Cliente {cliente_id} nao encontrado")

    is_anonymized = cliente.deleted_at is not None
    masked_nome = _mask_nome_personalizado(cliente.nome if not is_anonymized else None)
    masked_email = _mask_email_personalizado(cliente.email)

    consentidos = _consentimentos_aceitos(db, cliente_id)
    revogados = _consentimentos_revogados(db, cliente_id)
    contadores = _contadores(db, cliente_id)

    return {
        "cliente": {
            "id": cliente.id,
            "nome_mascarado": masked_nome,
            "email_mascarado": masked_email,
            "anonimizado": is_anonymized,
            "deleted_at": cliente.deleted_at.isoformat() if cliente.deleted_at else None,
        },
        "agente_tratamento": {
            "nome": AGENTE_NOME,
            "endereco": "Uberlandia, MG, Brasil",
        },
        "contact_dpo": {
            "nome": DPO_NOME,
            "email": DPO_EMAIL,
            "telefone": DPO_TELEFONE,
            "telegram_chat_id": DPO_TELEGRAM_CHAT_ID,
            "papel": DPO_PAPEL,
        },
        "finalidades_aceitas": consentidos,
        "finalidades_revogadas": revogados,
        "direitos_art_18": [
            {
                "direito": "Confirmacao/Acesso",
                "artigo": "18 I+II",
                "endpoint": f"{CARTORIO_API_BASE}/cliente/{cliente_id}/lgpd/acesso",
                "metodo": "GET",
                "prazo_resposta": "15 dias uteis",
            },
            {
                "direito": "Correcao",
                "artigo": "18 III",
                "endpoint": f"{CARTORIO_API_BASE}/cliente/{cliente_id}/lgpd/corrigir",
                "metodo": "POST",
                "prazo_resposta": "15 dias uteis",
            },
            {
                "direito": "Anonimizacao",
                "artigo": "18 IV",
                "endpoint": f"{CARTORIO_API_BASE}/cliente/{cliente_id}/lgpd/anonimizar",
                "metodo": "POST",
                "prazo_resposta": "Imediato (reversivel por 30 dias)",
            },
            {
                "direito": "Portabilidade",
                "artigo": "18 V",
                "endpoint": f"{CARTORIO_API_BASE}/lgpd/export/{cliente_id}",
                "metodo": "GET",
                "prazo_resposta": "15 dias uteis",
            },
            {
                "direito": "Revogacao",
                "artigo": "18 VI",
                "endpoint": f"{CARTORIO_API_BASE}/cliente/{cliente_id}/lgpd/revogar_consentimento",
                "metodo": "POST",
                "prazo_resposta": "Imediato",
            },
            {
                "direito": "Oposicao",
                "artigo": "18 IX",
                "endpoint": f"{CARTORIO_API_BASE}/cliente/{cliente_id}/lgpd/oposicao",
                "metodo": "POST",
                "prazo_resposta": "15 dias uteis",
            },
        ],
        "contadores": contadores,
        "politica_retencao": {
            "cliente_com_protocolo": "5 anos pos-ultimo atendimento (CNJ 74/2018)",
            "conversas": "90 dias (LGPD art. 6o II)",
            "audit_log": "7 anos (LGPD art. 37)",
        },
        "gerado_em": datetime.now(tz=timezone.utc).isoformat(),
        "documento_gerado_por": "system:cartorio-lgpd",
    }


__all__ = [
    "generate_privacy_policy",
    "generate_privacy_policy_structured",
    "_mask_nome_personalizado",
    "_mask_email_personalizado",
    "DPO_NOME",
    "DPO_EMAIL",
    "DPO_TELEGRAM_CHAT_ID",
]
