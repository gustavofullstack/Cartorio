"""API router v1."""

from fastapi import APIRouter

api_router = APIRouter()


@api_router.get("/emolumento/calcular")
async def calcular_emolumento(
    tipo: str,
    folhas: int = 1,
    urgencia: bool = False,
) -> dict:
    """Calcula emolumento. Publico - sem PII envolvida."""
    from app.services.emolumento import calcular

    try:
        resultado = calcular(tipo, folhas=folhas, urgencia=urgencia)
    except ValueError as e:
        return {"erro": str(e)}
    return {
        "tipo": resultado.tipo,
        "folhas": resultado.folhas,
        "urgencia": resultado.urgencia,
        "base": str(resultado.base),
        "adicional_folhas": str(resultado.adicional_folhas),
        "adicional_urgencia": str(resultado.adicional_urgencia),
        "total": str(resultado.total),
        "tabela_referencia": resultado.tabela_referencia,
        "valido_ate": resultado.valido_ate,
    }


@api_router.post("/webhook/evolution")
async def webhook_evolution(payload: dict) -> dict:
    """Webhook do Evolution API (WhatsApp).

    Recebe mensagem, aplica PII scrubbing, detecta intencao via LLM,
    retorna resposta. Audit log de TUDO.
    """
    from app.services.audit import AuditService
    from app.services.pii import scrub
    from app.db import session_scope

    raw_text = payload.get("message", {}).get("text", "") or ""
    sender = payload.get("sender", "unknown")
    instance = payload.get("instance", "")

    scrub_result = scrub(raw_text)
    with session_scope() as db:
        AuditService.log(
            db,
            actor_id=sender,
            actor_type="bot",
            action="conversa.received",
            resource=f"whatsapp:{instance}",
            payload={
                "scrubbed": scrub_result.text,
                "findings": scrub_result.findings,
                "redaction_count": scrub_result.redaction_count,
            },
        )

    # TODO: chamar LLM (LiteLLM), detectar intent, gerar resposta
    # Por enquanto: echo + handoff se contem PII (defesa em profundidade)
    if scrub_result.redaction_count > 0:
        response_text = (
            "Recebi sua mensagem com dados sensiveis. "
            "Por seguranca, vou transferir para um atendente humano. "
            "Aguarde um instante."
        )
    else:
        response_text = "Recebi sua mensagem. Em breve um atendente ira responder."

    return {"status": "ok", "response": response_text, "scrubbed": scrub_result.text[:200]}


@api_router.post("/audit/verify")
async def audit_verify() -> dict:
    """Verifica integridade da cadeia de audit log."""
    from app.db import session_scope
    from app.services.audit import AuditService

    with session_scope() as db:
        ok, last_valid = AuditService.verify_chain(db)
    return {"chain_ok": ok, "last_valid_position": last_valid}
