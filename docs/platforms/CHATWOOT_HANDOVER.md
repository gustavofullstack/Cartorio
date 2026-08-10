# Chatwoot Handover — Human-in-the-Loop (HITL)

> **Versão**: 3.0 (2026-07-09)
> **Status**: ✅ Telegram 100% · 🟡 WhatsApp em construção (T64)
> **Chatwoot**: `chatwoot.2notasudi.com.br`

## 🎯 Visão Geral

Quando o bot identifica que a solicitação requer intervenção humana, ele transfere a conversa para um escrevente via **Chatwoot** (CRM open-source). O fluxo mantém histórico, contexto e permite retorno automático para o bot.

## 🔄 Fluxo HITL End-to-End

```
┌──────────────────────────────────────────────────────────────────┐
│                  FLUXO HITL (CHATWOOT)                          │
└──────────────────────────────────────────────────────────────────┘
                                │
       ┌────────────────────────┼────────────────────────┐
       ▼                        ▼                        ▼
   Telegram bot            WhatsApp bot              Admin UI
   /humano                  /humano                   painel
       │                        │                        │
       └────────────────────────┼────────────────────────┘
                                ▼
              ┌──────────────────────────────────┐
              │ 1. Detectar intent               │
              │    - confidence < 0.7             │
              │    - keywords: humano, urgente,    │
              │      reclamação, advogado          │
              │    - LLM sugere HITL              │
              └──────────────┬───────────────────┘
                             ▼
              ┌──────────────────────────────────┐
              │ 2. Criar conversa Chatwoot        │
              │    POST /api/v1/accounts/:id/      │
              │         conversations             │
              │    - contact_id (chat_id)          │
              │    - inbox_id (bot_handover)       │
              │    - status: open                  │
              │    - assignee: null (fila geral)   │
              └──────────────┬───────────────────┘
                             ▼
              ┌──────────────────────────────────┐
              │ 3. Mensagem inicial ao escrevente │
              │    "Cliente transferido do bot"   │
              │    - chat_id                       │
              │    - últimas 5 mensagens           │
              │    - intent detectado              │
              │    - PII já scrubbed               │
              └──────────────┬───────────────────┘
                             ▼
              ┌──────────────────────────────────┐
              │ 4. Notificar escrevente           │
              │    - Email                        │
              │    - Push notification Chatwoot   │
              │    - Telegram GRUPO Pietra (opcional) │
              └──────────────┬───────────────────┘
                             ▼
              ┌──────────────────────────────────┐
              │ 5. Cliente recebe confirmação     │
              │    "Vou transferir para humano"   │
              │    "Tempo médio: 5 min"            │
              └──────────────┬───────────────────┘
                             ▼
              ┌──────────────────────────────────┐
              │ 6. Escrevente responde            │
              │    via Chatwoot                    │
              │    - Mensagem vai para cliente     │
              │      (Telegram ou WhatsApp)        │
              │    - Audit log HITL                │
              └──────────────┬───────────────────┘
                             ▼
              ┌──────────────────────────────────┐
              │ 7. Resolução                      │
              │    - Escrevente marca "resolved"  │
              │    - Bot volta a responder         │
              │      após 24h de inatividade       │
              │    - Canned responses disponíveis  │
              └──────────────────────────────────┘
```

## 🎯 Quando Acionar HITL

### Triggers Automáticos (LLM detecta)

1. **Confidence < 0.7** na intent detectada
2. **Keywords**: "humano", "atendente", "pessoa", "urgente", "reclamação", "advogado", "judicial"
3. **Ato jurídico**: "isenção", "validação", "certidão", "inventário"
4. **Erro LLM**: 3 falhas consecutivas no fallback chain
5. **PII detectada no output** (camada 3 falhou)

### Triggers Manuais (comando direto)

- `/humano` (Telegram + WhatsApp)
- Botão `[👤 Falar com humano]` (WhatsApp list message)

## 📦 Canned Responses (Macros)

**Arquivo**: `backend/app/services/chatwoot_canned_responses.py`

```python
CANNED_RESPONSES = {
    "saudacao_inicial": {
        "content": "Olá! Sou [nome] do Cartório 2º Notas. Como posso ajudar?",
        "shortcut": "/oi",
    },
    "pedir_documento": {
        "content": (
            "Para [serviço], preciso dos seguintes documentos:\n"
            "- RG e CPF\n"
            "- Comprovante de residência\n"
            "- [documento específico]\n\n"
            "Pode enviar foto ou PDF?"
        ),
        "shortcut": "/docs",
    },
    "agendar_presencial": {
        "content": (
            "Vou agendar atendimento presencial.\n"
            "Data: [data]\n"
            "Horário: [horário]\n"
            "Local: Rua XV de Novembro, 123 - Centro\n\n"
            "Confirma?"
        ),
        "shortcut": "/agendar",
    },
    "transferir_outro_setor": {
        "content": (
            "Vou transferir para [setor]. "
            "Retornaremos em até 24h úteis."
        ),
        "shortcut": "/transferir",
    },
    "resolver_duvida_juridica": {
        "content": (
            "Sobre [assunto]: [resposta técnica]. "
            "Mais alguma dúvida?"
        ),
        "shortcut": "/juridico",
    },
    "encerrar_atendimento": {
        "content": (
            "Atendimento encerrado. Obrigado por contatar o Cartório 2º Notas!\n"
            "Caso precise, é só chamar. 📞 (11) 1234-5678"
        ),
        "shortcut": /fim,
    },
}
```

## 🔌 Integração Chatwoot ↔ Backend

### Variáveis de Ambiente

```bash
CHATWOOT_BASE_URL=https://chatwoot.2notasudi.com.br
CHATWOOT_API_ACCESS_TOKEN=************************
CHATWOOT_ACCOUNT_ID=1
CHATWOOT_INBOX_BOT_ID=42
```

### Endpoints Usados

```
GET   /api/v1/accounts/:id/contacts/search?q=<chat_id>
POST  /api/v1/accounts/:id/contacts (criar se não existir)
POST  /api/v1/accounts/:id/conversations
POST  /api/v1/accounts/:id/conversations/:id/messages
POST  /api/v1/accounts/:id/conversations/:id/assignments
POST  /api/v1/accounts/:id/conversations/:id/status (resolve/snooze)
```

### Criar Conversa HITL

```python
# chatwoot_handoff.py
async def create_handover(
    channel: Channel,
    chat_id: str,
    sender_name: str,
    intent: str,
    last_messages: list[str],
) -> int:
    """Retorna conversation_id no Chatwoot."""

    # 1. Buscar/criar contact
    contact = await search_or_create_contact(chat_id, sender_name)

    # 2. Criar conversa
    conv = await httpx_post(
        f"{CHATWOOT_BASE_URL}/api/v1/accounts/{CHATWOOT_ACCOUNT_ID}/conversations",
        headers={"api_access_token": CHATWOOT_API_ACCESS_TOKEN},
        json={
            "contact_id": contact["id"],
            "inbox_id": CHATWOOT_INBOX_BOT_ID,
            "status": "open",
            "assignee_id": None,  # fila geral
            "custom_attributes": {
                "channel": channel.value,
                "chat_id_hash": hashlib.sha256(chat_id.encode()).hexdigest(),
                "intent": intent,
                "source": "bot_handover",
            },
        },
    )
    conversation_id = conv["id"]

    # 3. Mensagem inicial ao escrevente
    context_msg = (
        f"🤖 Cliente transferido do bot\n"
        f"Canal: {channel.value}\n"
        f"Intent: {intent}\n"
        f"Últimas mensagens:\n"
        + "\n".join(f"- {m[:200]}" for m in last_messages[-5:])
    )
    await httpx_post(
        f"{CHATWOOT_BASE_URL}/api/v1/accounts/{CHATWOOT_ACCOUNT_ID}/conversations/{conversation_id}/messages",
        headers={"api_access_token": CHATWOOT_API_ACCESS_TOKEN},
        json={"content": context_msg, "message_type": "incoming"},
    )

    # 4. Audit log
    await audit_log(
        channel=channel,
        chat_id=chat_id,
        sender_name=sender_name,
        content=f"HITL handover to Chatwoot conv={conversation_id}",
        intent="hitl",
        provider_used="chatwoot",
        latency_ms=0,
        consent_granted=True,
    )

    return conversation_id
```

### Webhook Chatwoot → Backend

Chatwoot envia webhooks quando escrevente responde. Backend repassa para Telegram/WhatsApp.

**Endpoint**: `POST /api/v1/webhook/chatwoot`

```python
# router.py
@router.post("/webhook/chatwoot")
async def chatwoot_webhook(request: Request):
    payload = await request.json()
    event = payload.get("event")

    if event == "message_created":
        msg = payload["message"]
        conv_id = msg["conversation_id"]

        # Buscar custom_attributes (channel + chat_id_hash)
        conv = await get_chatwoot_conversation(conv_id)
        channel = conv["custom_attributes"]["channel"]
        chat_id_hash = conv["custom_attributes"]["chat_id_hash"]

        # Resolver chat_id original (mapa reverso)
        chat_id = await reverse_chat_id_lookup(chat_id_hash)

        # Repassar para Telegram/WhatsApp
        if channel == "telegram":
            await telegram_send_message(chat_id, msg["content"])
        elif channel == "whatsapp":
            await whatsapp_send_message(chat_id, msg["content"])

        # Audit log
        await audit_log(...)

    return {"ok": True}
```

## 📊 Métricas HITL

```
# Counter
bot_hitl_total{channel="telegram",reason="confidence_low"} 23
bot_hitl_total{channel="telegram",reason="user_requested"} 12
bot_hitl_total{channel="whatsapp",reason="user_requested"} 5
bot_hitl_total{channel="telegram",reason="llm_error"} 2

# Histogram (tempo de espera até primeira resposta humana)
hitl_first_response_seconds{channel="telegram",quantile="0.5"} 180
hitl_first_response_seconds{channel="telegram",quantile="0.95"} 600

# Gauge
hitl_open_conversations{channel="telegram"} 3
hitl_open_conversations{channel="whatsapp"} 1
```

## 🚨 Alertas HITL

| Trigger | Threshold | Ação |
|---|---|---|
| Conversa HITL aberta | > 5 min sem resposta | Notificar Telegram GRUPO Pietra |
| Conversa HITL aberta | > 30 min sem resposta | Email Gustavo |
| Conversa HITL resolvida | > 24h sem follow-up | Auto-close + audit |
| Conversa HITL | > 3 escalonamentos | HITL escalation (gerente) |

## 🛡️ LGPD no HITL

- **Audit log** registra transição bot → humano
- **PII scrub** antes de enviar contexto ao Chatwoot (escrevente vê `[REDACTED:cpf]` em vez do CPF real se aplicável)
- **Consent verification**: se WhatsApp sem consent, escrevente é avisado e NÃO vê dados pessoais

```python
async def get_safe_context(messages: list[str]) -> list[str]:
    """Scrub PII antes de enviar para Chatwoot (escrevente vê contexto sem PII)."""
    return [scrub(m).text for m in messages]
```

**Escrevente pode pedir mais detalhes** via comando interno:
```
/ver-detalhes <message_id>
```
Que retorna o dado original (com audit trail adicional).

## 🛠️ Troubleshooting HITL

### Chatwoot offline

```bash
# 1. Verificar
curl -sS https://chatwoot.2notasudi.com.br/api/v1/accounts/1 \
  -H "api_access_token: $CHATWOOT_API_ACCESS_TOKEN"

# 2. Restart (se down)
docker service update --force cartorio_chatwoot-web
docker service update --force cartorio_chatwoot-sidekiq
```

### Escrevente não recebe notificação

```bash
# Verificar inbox_id correto
curl -sS https://chatwoot.2notasudi.com.br/api/v1/accounts/1/inboxes \
  -H "api_access_token: $CHATWOOT_API_ACCESS_TOKEN" | jq '.[] | {id, name}'

# Conferir env CHATWOOT_INBOX_BOT_ID
```

### Cliente não recebe resposta do Chatwoot

```bash
# Verificar webhook Chatwoot → Backend
docker logs cartorio_api --since 5m 2>&1 | grep "chatwoot_webhook"

# Testar
curl -X POST http://cartorio_api:8000/api/v1/webhook/chatwoot \
  -H "Content-Type: application/json" \
  -d @tests/fixtures/chatwoot_message.json
```

## 📚 Referências

- [`BOTS.md`](BOTS.md) — overview
- [`TROUBLESHOOTING_BOTS.md`](TROUBLESHOOTING_BOTS.md)
- [`LGPD_BOTS.md`](LGPD_BOTS.md) — compliance HITL
- `backend/app/services/chatwoot_handoff.py` — código
- `backend/app/services/chatwoot_canned_responses.py` — macros
- `backend/app/services/chatwoot_handoff_macros.py` — lógica de macros
- `docs/canned-responses-chatwoot.json` — JSON exportado
- `docs/chatwoot-setup-2026-06-25.json` — config setup

---

**Modified by**: OpenCode-MiniMax-M3-High · 2026-07-09T16:38:30Z