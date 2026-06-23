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
    import hashlib
    import datetime
    import time
    import httpx
    from app.services.audit import AuditService
    from app.services.pii import scrub
    from app.db import session_scope
    from app.models.conversa import Conversa
    from app.config import settings

    raw_text = payload.get("message", {}).get("text", "") or ""
    sender = payload.get("sender", "unknown")
    instance = payload.get("instance", "")

    # Calculate raw message hash
    raw_message_hash = hashlib.sha256(raw_text.encode("utf-8")).hexdigest()

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

    handoff = False
    handoff_reason = None
    intent = "chat"
    bot_response = ""
    llm_tokens_in = None
    llm_tokens_out = None
    llm_latency_ms = None

    if settings.pii_scrub_enabled and settings.pii_block_on_detect and scrub_result.redaction_count > 0:
        bot_response = (
            "Recebi sua mensagem com dados sensiveis. "
            "Por seguranca, vou transferir para um atendente humano. "
            "Aguarde um instante."
        )
        handoff = True
        handoff_reason = "PII detectada"
    else:
        # Chamar LLM
        start_time = time.time()
        try:
            if settings.opencode_go_api_key and settings.opencode_go_api_key != "CHANGE_ME":
                headers = {
                    "Authorization": f"Bearer {settings.opencode_go_api_key}",
                    "Content-Type": "application/json",
                }
                payload_data = {
                    "model": settings.opencode_go_model,
                    "messages": [
                        {
                            "role": "system",
                            "content": (
                                "Você é a Pietra, assistente de IA do Cartório do 2º Ofício de Notas de Uberlândia. "
                                "Ajude os clientes de forma prestativa, clara e objetiva. Se o cliente solicitar "
                                "falar com um humano, ou se for necessário um especialista, inclua a palavra [HUMANO] "
                                "na sua resposta para fazermos o redirecionamento. Nunca cometa erros legais nem "
                                "invente regras; se não souber ou for complexo, encaminhe para o humano com [HUMANO]."
                            ),
                        },
                        {"role": "user", "content": scrub_result.text},
                    ],
                    "temperature": 0.2,
                }
                async with httpx.AsyncClient(timeout=30.0) as client:
                    response = await client.post(
                        f"{settings.opencode_go_base_url}/chat/completions",
                        json=payload_data,
                        headers=headers,
                    )
                    if response.status_code == 200:
                        resp_json = response.json()
                        bot_response = resp_json["choices"][0]["message"]["content"]
                        usage = resp_json.get("usage", {})
                        llm_tokens_in = usage.get("prompt_tokens")
                        llm_tokens_out = usage.get("completion_tokens")
                    else:
                        bot_response = (
                            "Desculpe, tive um problema de comunicacao com o meu cerebro de IA. "
                            "Vou chamar um atendente humano para te ajudar. [HUMANO]"
                        )
                        handoff = True
                        handoff_reason = f"LLM error status {response.status_code}"
            else:
                bot_response = "Recebi sua mensagem. Em breve um atendente ira responder."
        except Exception as e:
            bot_response = (
                "Desculpe, tive um problema de comunicacao com o meu cerebro de IA. "
                "Vou chamar um atendente humano para te ajudar. [HUMANO]"
            )
            handoff = True
            handoff_reason = f"LLM Exception: {str(e)}"

        llm_latency_ms = int((time.time() - start_time) * 1000)

        if "[HUMANO]" in bot_response:
            handoff = True
            handoff_reason = "Solicitado pelo bot/cliente"
            bot_response = bot_response.replace("[HUMANO]", "").strip()

    # Save to Supabase (conversas table)
    try:
        with session_scope() as db:
            conversa = Conversa(
                canal="whatsapp",
                external_id=sender,
                raw_message_hash=raw_message_hash,
                raw_message_scrubbed=scrub_result.text,
                intent_detected=intent,
                confidence_score=1.0 if not handoff else 0.0,
                bot_response=bot_response,
                handoff_to_human=handoff,
                handoff_at=datetime.datetime.now(datetime.timezone.utc) if handoff else None,
                handoff_reason=handoff_reason,
                llm_model=settings.opencode_go_model,
                llm_tokens_in=llm_tokens_in,
                llm_tokens_out=llm_tokens_out,
                llm_latency_ms=llm_latency_ms,
            )
            db.add(conversa)
    except Exception:
        pass

    return {
        "status": "ok",
        "response": bot_response,
        "scrubbed": scrub_result.text[:200],
    }


@api_router.post("/audit/verify")
async def audit_verify() -> dict:
    """Verifica integridade da cadeia de audit log."""
    from app.db import session_scope
    from app.services.audit import AuditService

    with session_scope() as db:
        ok, last_valid = AuditService.verify_chain(db)
    return {"chain_ok": ok, "last_valid_position": last_valid}


@api_router.get("/health/radar")
async def health_radar() -> dict:
    """Verifica conexoes de todos os servicos da suite."""
    import redis
    import httpx
    from app.db import engine
    from sqlalchemy import text
    from app.config import settings

    # 1. DB (PostgreSQL via SQLAlchemy)
    db_ok = False
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
            db_ok = True
    except Exception:
        pass

    # 2. Redis
    redis_ok = False
    try:
        r = redis.from_url(settings.redis_url, socket_timeout=2.0)
        r.ping()
        redis_ok = True
    except Exception:
        pass

    # 3. n8n, OpenClaw, Evolution API (via httpx)
    n8n_ok = False
    openclaw_ok = False
    evolution_ok = False

    async with httpx.AsyncClient(timeout=3.0) as client:
        # Check n8n
        try:
            resp = await client.get(f"{settings.n8n_base_url}/healthz")
            if resp.status_code == 200:
                n8n_ok = True
        except Exception:
            pass

        # Check openclaw
        try:
            resp = await client.get(f"{settings.openclaw_base_url}/health")
            if resp.status_code == 200:
                openclaw_ok = True
        except Exception:
            pass

        # Check evolution
        try:
            resp = await client.get(f"{settings.evolution_base_url}/")
            if resp.status_code == 200:
                evolution_ok = True
        except Exception:
            pass

    overall_status = "green" if (db_ok and redis_ok and n8n_ok and openclaw_ok and evolution_ok) else "red"

    return {
        "status": overall_status,
        "services": {
            "database": "online" if db_ok else "offline",
            "redis": "online" if redis_ok else "offline",
            "n8n": "online" if n8n_ok else "offline",
            "openclaw": "online" if openclaw_ok else "offline",
            "evolution": "online" if evolution_ok else "offline",
        }
    }


@api_router.get("/postman")
async def postman_collection() -> dict:
    """Retorna a colecao do Postman v2.1.0."""
    return {
        "info": {
            "name": "Cartorio API",
            "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json"
        },
        "item": [
            {
                "name": "Calcular Emolumento",
                "request": {
                    "method": "GET",
                    "header": [],
                    "url": {
                        "raw": "{{base_url}}/api/v1/emolumento/calcular?tipo=escritura_compra_venda&folhas=3&urgencia=true",
                        "host": ["{{base_url}}"],
                        "path": ["api", "v1", "emolumento", "calcular"],
                        "query": [
                            {"key": "tipo", "value": "escritura_compra_venda"},
                            {"key": "folhas", "value": "3"},
                            {"key": "urgencia", "value": "true"}
                        ]
                    }
                }
            },
            {
                "name": "Webhook Evolution",
                "request": {
                    "method": "POST",
                    "header": [
                        {"key": "Content-Type", "value": "application/json"}
                    ],
                    "body": {
                        "mode": "raw",
                        "raw": "{\n  \"message\": {\n    \"text\": \"Olá, preciso de uma certidão\"\n  },\n  \"sender\": \"user123\",\n  \"instance\": \"inst1\"\n}"
                    },
                    "url": {
                        "raw": "{{base_url}}/api/v1/webhook/evolution",
                        "host": ["{{base_url}}"],
                        "path": ["api", "v1", "webhook", "evolution"]
                    }
                }
            },
            {
                "name": "Audit Verify",
                "request": {
                    "method": "POST",
                    "header": [],
                    "url": {
                        "raw": "{{base_url}}/api/v1/audit/verify",
                        "host": ["{{base_url}}"],
                        "path": ["api", "v1", "audit", "verify"]
                    }
                }
            },
            {
                "name": "Health Radar",
                "request": {
                    "method": "GET",
                    "header": [],
                    "url": {
                        "raw": "{{base_url}}/api/v1/health/radar",
                        "host": ["{{base_url}}"],
                        "path": ["api", "v1", "health", "radar"]
                    }
                }
            },
            {
                "name": "Postman Export",
                "request": {
                    "method": "GET",
                    "header": [],
                    "url": {
                        "raw": "{{base_url}}/api/v1/postman",
                        "host": ["{{base_url}}"],
                        "path": ["api", "v1", "postman"]
                    }
                }
            }
        ],
        "variable": [
            {
                "key": "base_url",
                "value": "https://api.2notasudi.com.br",
                "type": "string"
            }
        ]
    }
