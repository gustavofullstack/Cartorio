# WhatsApp Bot — Guia Operacional Completo

> **Versão**: 3.0 (2026-07-09)
> **Instância Evolution**: `cartorio-2notas`
> **Production status**: 🟡 100% espelhado (paridade Telegram via `chat_pipeline.py`)
> **SUI**: Gustavo Almeida (QR scan + Evolution API key)

## 📋 Sumário

1. [Setup Evolution API (SUI Gustavo)](#setup-evolution-api-sui-gustavo)
2. [Arquitetura](#arquitetura)
3. [Webhook + HMAC validation](#webhook--hmac-validation)
4. [Comandos](#comandos)
5. [WhatsApp-specific (typing/reaction/keyboard)](#whatsapp-specific)
6. [LGPD consent banner](#lgpd-consent-banner)
7. [Troubleshooting](#troubleshooting)

## 🔧 Setup Evolution API (SUI Gustavo)

### Manager UI

```
URL:     https://whatsapp.2notasudi.com.br/manager
Instance: cartorio-2notas
API Key: gerenciada por ambiente (`EVOLUTION_API_KEY`), não documentada.
```

### QR Scan (uma vez)

1. Acessar `https://whatsapp.2notasudi.com.br/manager`
2. Login com API Key
3. Criar instância `cartorio-2notas`
4. Clicar em "Connect" → QR code aparece
5. Abrir WhatsApp no celular → ⋮ → Aparelhos conectados → Conectar aparelho
6. Escanear QR
7. Status esperado: `OPEN` (verde)

### Webhook (configurar na Evolution API)

```bash
# Apontar webhook para nosso endpoint
curl -X POST "https://whatsapp.2notasudi.com.br/webhook/set/cartorio-2notas" \
  -H "apikey: $EVOLUTION_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://api.2notasudi.com.br/api/v1/webhook/evolution",
    "events": ["MESSAGES_UPSERT", "MESSAGES_UPDATE", "CONNECTION_UPDATE"],
    "enabled": true
  }'
```

### Validation Gustavo (celular)

```
1. Abrir WhatsApp no celular
2. Adicionar contato cartório (número configurado na instância)
3. Enviar "oi"
4. Tempo esperado: < 10s (mesma métrica Telegram)
5. Se aparecer LGPD notice → consent banner está ativo (correto)
6. Responder "Aceito" → bot começa a responder dúvidas
```

## 🏗️ Arquitetura

```
Cliente WhatsApp              Evolution API               Cartório Backend              LiteLLM Proxy
   │                              │                              │                            │
   │ 1. "oi"                      │                              │                            │
   ├─────────────────────────────►│                              │                            │
   │                              │ 2. webhook POST              │                            │
   │                              │    /webhook/evolution        │                            │
   │                              ├─────────────────────────────►│                            │
   │                              │    HMAC X-Hub-Signature-256  │                            │
   │                              │                              │ 3. validate_evolution_sig   │
   │                              │                              │ 4. ingest_evolution_event   │
   │                              │                              │    → InboundMessage        │
   │                              │                              │    (channel=whatsapp)      │
   │                              │                              │                            │
   │                              │                              │ 5. check_idempotency       │
   │                              │                              │ 6. scrub_pii_3_layers      │
   │                              │                              │ 7. enqueue + debounce 1.2s │
   │                              │                              │ 8. typing_loop             │
   │                              │                              │    POST /chat/sendPresence │
   │                              │◄─────────────────────────────┤    (composing)            │
   │  "Bot digitando..."          │                              │                            │
   │                              │                              │ 9. call_llm_with_fallback  │
   │                              │                              ├───────────────────────────►│
   │                              │                              │                            │
   │                              │                              │ 10. response              │
   │                              │                              │◄───────────────────────────┤
   │                              │                              │ 11. scrub output           │
   │                              │                              │ 12. POST /message/sendText │
   │                              │◄─────────────────────────────┤     (HTML)                │
   │  Mensagem do bot             │                              │                            │
   │  "Olá! Sou o assistente..."  │                              │                            │
   │                              │ 13. POST /message/sendReaction                            │
   │                              │◄─────────────────────────────┤     (👍)                  │
   │  Reação 👍                   │                              │                            │
```

## 🔐 Webhook + HMAC Validation

### HMAC Signature

Evolution API envia header `X-Hub-Signature-256: sha256=<hex>`.

**Validação** (`backend/app/services/evolution_ingest.py`):
```python
import hmac, hashlib

def validate_evolution_signature(raw_body: bytes, signature: str | None) -> bool:
    if not signature or not signature.startswith("sha256="):
        return False
    expected = hmac.new(
        settings.evolution_api_key.encode(),
        raw_body,
        hashlib.sha256,
    ).hexdigest()
    received = signature.removeprefix("sha256=")
    return hmac.compare_digest(expected, received)
```

**Rejeitar** se inválida (HTTP 401).

### Payload Evolution API

```json
{
  "event": "MESSAGES_UPSERT",
  "instance": "cartorio-2notas",
  "data": {
    "key": {
      "remoteJid": "5511999999999@s.whatsapp.net",
      "fromMe": false,
      "id": "3EB0C2F8A8B4C0D0E1F2A3B4"
    },
    "pushName": "João Silva",
    "message": {
      "conversation": "oi"
    },
    "messageType": "conversation",
    "messageTimestamp": 1720544400
  }
}
```

**Mapeamento** (`InboundMessage`):
```python
InboundMessage(
    channel=Channel.WHATSAPP,
    sender_id="5511999999999@s.whatsapp.net",
    sender_name="João Silva",
    text="oi",
    update_id="3EB0C2F8A8B4C0D0E1F2A3B4",  # message_id
    message_ids=["3EB0C2F8A8B4C0D0E1F2A3B4"],
    is_group="@g.us" in remoteJid,
    extra={"instance": "cartorio-2notas"},
)
```

## 🎮 Comandos Suportados (mesmos Telegram)

| Comando | Telegram | WhatsApp |
|---|---|---|
| `/start` | ✅ | ✅ |
| `/menu` | ✅ | ✅ |
| `/protocolo <n>` | ✅ | ✅ |
| `/agendar` | ✅ | ✅ |
| `/humano` | ✅ | ✅ |
| `/cancelar` | ✅ | ✅ |
| `/lgpd` | ✅ | ✅ |

**Nota**: WhatsApp não tem "comandos" nativos. Bot detecta `/start` na primeira palavra da mensagem.

**Implementação**:
```python
async def detect_command(text: str) -> tuple[str, list[str]] | None:
    parts = text.strip().split(maxsplit=1)
    cmd = parts[0].lower()
    if cmd in ["/start", "/menu", "/agendar", "/humano", "/cancelar", "/lgpd"]:
        args = parts[1].split() if len(parts) > 1 else []
        return cmd, args
    if cmd == "/protocolo" and len(parts) > 1:
        return cmd, parts[1].split()
    return None
```

## 📱 WhatsApp-Specific

### Typing Indicator (presence)

```python
# whatsapp.py:WhatsAppAdapter.typing()
async def typing(self, recipient_id: str, action: str = "composing") -> bool:
    if not action:  # cancel
        return True
    url = f"{EVOLUTION_BASE_URL}/chat/sendPresence/{INSTANCE}"
    payload = {"number": recipient_id.replace("@s.whatsapp.net", ""), "presence": action}
    async with httpx.AsyncClient(timeout=5) as client:
        r = await client.post(url, json=payload, headers={"apikey": EVOLUTION_API_KEY})
    return r.status_code == 200
```

**Refresh loop**: a cada 4s (chat_pipeline.TYPING_REFRESH_SEC).

### Reactions

**Limitações WhatsApp** (vs Telegram): só 6 emojis permitidos.
- 👍 `thumbsup`
- ❤️ `heart`
- 😂 `laugh`
- 😮 `wow`
- 😢 `sad`
- 🙏 `pray`

```python
async def react(self, recipient_id: str, message_id: str, reaction: str = "thumbsup") -> bool:
    emoji_map = {
        "thumbsup": "👍", "heart": "❤️", "laugh": "😂",
        "wow": "😮", "sad": "😢", "pray": "🙏",
    }
    url = f"{EVOLUTION_BASE_URL}/message/sendReaction/{INSTANCE}"
    payload = {
        "key": {"remoteJid": recipient_id, "fromMe": False, "id": message_id},
        "reaction": emoji_map.get(reaction, "👍"),
    }
    ...
```

### Inline Keyboard (buttons + list)

**Limites**: max 3 botões (WhatsApp), ou usar list message (sections).

```python
def build_menu_buttons() -> dict:
    return {
        "buttons": [
            [{"buttonId": "1", "buttonText": {"displayText": "📋 Protocolo"}, "type": 1}],
            [{"buttonId": "2", "buttonText": {"displayText": "📅 Agendar"}, "type": 1}],
            [{"buttonId": "3", "buttonText": {"displayText": "👤 Humano"}, "type": 1}],
        ],
        "headerText": "Menu Principal",
        "footerText": "Cartório 2º Notas",
    }
```

```python
async def send_buttons(self, recipient_id: str, buttons: dict, text: str) -> bool:
    url = f"{EVOLUTION_BASE_URL}/message/sendButtons/{INSTANCE}"
    payload = {"number": recipient_id.replace("@s.whatsapp.net", ""), **buttons}
    ...
```

## 🔒 LGPD Consent Banner

### Fluxo Obrigatório

**1º contato** (sempre, antes de qualquer resposta):

```
🔒 Aviso de Privacidade (LGPD)

Este bot processa suas mensagens para atendimento do Cartório 2º Notas.

📋 Dados coletados: nome, telefone, conteúdo das mensagens
🎯 Finalidade: responder dúvidas, agendar atendimentos, consultar protocolos
⏰ Retenção: 5 anos após último contato
🔐 Seus direitos: acesso, correção, eliminação, portabilidade

Para continuar, escolha:
[1] Aceito os termos
[2] Não aceito (vou ser redirecionado a humano)
```

**Resposta**:
- `1` / "Aceito" / "aceito" → `whatsapp_consent.granted = True` + bot responde dúvidas
- `2` / "Não aceito" → HITL Chatwoot + bloqueia bot

**Storage**:
```sql
CREATE TABLE whatsapp_consent (
    id BIGSERIAL PRIMARY KEY,
    remote_jid TEXT NOT NULL,
    granted_at TIMESTAMPTZ,
    revoked_at TIMESTAMPTZ,
    ip_hash TEXT,
    user_agent TEXT
);
CREATE UNIQUE INDEX idx_whatsapp_consent_jid ON whatsapp_consent(remote_jid);
```

### Sem Consent

- Bot responde APENAS: `🔒 Para continuar, digite "Aceito" ou "Não aceito"`
- PII scrub **desabilitado** (não processa até consent)
- Audit log registrado como `consent_pending`

### Com Consent

- PII scrub 3 camadas ativo
- Audit log completo (LGPD art. 37)
- Retention 5 anos após último contato

## 🚀 Deploy + Monitoramento

### Variáveis de Ambiente

```bash
EVOLUTION_BASE_URL=https://whatsapp.2notasudi.com.br
EVOLUTION_API_KEY=<INJECT_FROM_SECRET_MANAGER>
EVOLUTION_INSTANCE=cartorio-2notas
WHATSAPP_CONSENT_REQUIRED=true
```

### Métricas (mesmas Telegram)

```
bot_requests_total{channel="whatsapp",status="ok"} 567
bot_requests_total{channel="whatsapp",status="fallback"} 8
bot_requests_total{channel="whatsapp",status="error"} 2
bot_consent_pending{channel="whatsapp"} 12
```

## 🛠️ Troubleshooting

### QR code expirado

```bash
# 1. Reconectar via Manager UI
curl https://whatsapp.2notasudi.com.br/instance/restart/cartorio-2notas \
  -H "apikey: $EVOLUTION_API_KEY"

# 2. Novo QR code
curl https://whatsapp.2notasudi.com.br/instance/connect/cartorio-2notas \
  -H "apikey: $EVOLUTION_API_KEY" | jq -r '.qrcode'
```

### Webhook não recebe eventos

```bash
# Verificar webhook configurado
curl https://whatsapp.2notasudi.com.br/webhook/find/cartorio-2notas \
  -H "apikey: $EVOLUTION_API_KEY"

# Reconfigurar
curl -X POST https://whatsapp.2notasudi.com.br/webhook/set/cartorio-2notas \
  -H "apikey: $EVOLUTION_API_KEY" \
  -d '{"url": "https://api.2notasudi.com.br/api/v1/webhook/evolution", "events": ["MESSAGES_UPSERT"], "enabled": true}'
```

### HMAC signature inválida

```bash
# Verificar EVOLUTION_API_KEY no .env bate com a configurada na Evolution
grep EVOLUTION_API_KEY /etc/easypanel/projects/cartorio/api/code/.env

# Verificar header enviado
docker logs cartorio_api --since 5m 2>&1 | grep "X-Hub-Signature-256"
```

Ver [`TROUBLESHOOTING_BOTS.md`](TROUBLESHOOTING_BOTS.md) para cenários avançados.

## 📚 Referências

- [`BOTS.md`](BOTS.md) — overview Telegram + WhatsApp
- [`EVOLUTION_API.md`](EVOLUTION_API.md) — instalação detalhada
- [`LGPD_BOTS.md`](LGPD_BOTS.md) — compliance completo
- [`FALLBACK_CHAIN.md`](FALLBACK_CHAIN.md) — 7 providers LLM
- [`CHANGELOG_BOTS.md`](CHANGELOG_BOTS.md) — v1.0 → v2.0 → v3.0

---

**Modified by**: OpenCode-MiniMax-M3-High · 2026-07-09T16:37:00Z
**Lesson**: 143 (WhatsApp espelhado 100%), 147 (LGPD consent banner WhatsApp)
