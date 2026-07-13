# Evolution API — Instalação, QR, Webhook e Adapter

> **Versão**: 3.0 (2026-07-09)
> **Status**: ✅ Instalado + funcional
> **URL**: https://whatsapp.2notasudi.com.br/manager

## 📋 Visão Geral

Evolution API é um gateway open-source para integração com WhatsApp (similar à Twilio). Cartório usa v2.3.7 self-hosted em Docker Swarm.

## 🏗️ Arquitetura

```
┌──────────────────────────────────────────────────────────────────┐
│              EVOLUTION API v2.3.7 — STACK                        │
└──────────────────────────────────────────────────────────────────┘
                                │
       ┌────────────────────────┼────────────────────────┐
       ▼                        ▼                        ▼
   Evolution API          PostgreSQL              Redis
   (porta 8080)            (state)                (queue)
       │
       ▼
   cartorio_evolution-api container
   ├─ Express.js
   ├─ Baileys (lib WhatsApp Web)
   ├─ WebSocket para QR
   └─ REST API para webhooks
```

## 🔧 Instalação

### Docker Compose (referência)

```yaml
# /etc/easypanel/projects/cartorio/evolution-api/docker-compose.yml
version: "3.8"
services:
  evolution-api:
    image: atendai/evolution-api:v2.3.7
    ports:
      - "8080:8080"
    environment:
      - SERVER_TYPE=http
      - SERVER_PORT=8080
      - AUTHENTICATION_API_KEY=${EVOLUTION_API_KEY}
      - DATABASE_ENABLED=true
      - DATABASE_PROVIDER=postgresql
      - DATABASE_CONNECTION_URI=postgresql://evolution:${POSTGRES_PASSWORD}@cartorio_postgres:5432/evolution
      - REDIS_ENABLED=true
      - REDIS_URI=redis://cartorio_redis:6379/3
      - WEBHOOK_GLOBAL_ENABLED=true
      - WEBHOOK_GLOBAL_URL=https://api.2notasudi.com.br/api/v1/webhook/evolution
    networks:
      - cartorio_net
    volumes:
      - evolution_data:/evolution/instances
    deploy:
      replicas: 1
      restart_policy:
        condition: on-failure
        delay: 5s
        max_attempts: 3

volumes:
  evolution_data:

networks:
  cartorio_net:
    external: true
```

### Variáveis de Ambiente

```bash
# .env
EVOLUTION_API_KEY=24s6pdZqUwblg0v4UJTV3YilLm1WZQIu
EVOLUTION_BASE_URL=https://whatsapp.2notasudi.com.br
EVOLUTION_INSTANCE=cartorio-2notas
POSTGRES_PASSWORD=<gerado via openssl rand -hex 32>
```

### Deploy

```bash
cd /etc/easypanel/projects/cartorio/evolution-api
docker stack deploy -c docker-compose.yml cartorio
sleep 10

# Verificar health
curl -sS http://localhost:8080/ | jq .
# Espera: {"status":"SUCCESS","message":"Evolution API is running"}

# Verificar via Traefik
curl -sS https://whatsapp.2notasudi.com.br/manager | head -5
```

## 📱 QR Scan (Pairing WhatsApp)

### Fluxo (SUI Gustavo)

1. **Acessar Manager UI**: https://whatsapp.2notasudi.com.br/manager
2. **Login**: API Key (campo `apikey`)
3. **Criar instância**:
   ```bash
   curl -X POST http://localhost:8080/instance/create \
     -H "apikey: $EVOLUTION_API_KEY" \
     -H "Content-Type: application/json" \
     -d '{
       "instanceName": "cartorio-2notas",
       "qrcode": true,
       "integration": "WHATSAPP-BAILEYS"
     }'
   ```
4. **Obter QR**:
   ```bash
   curl http://localhost:8080/instance/connect/cartorio-2notas \
     -H "apikey: $EVOLUTION_API_KEY"
   # Resposta: {"pairingCode": "...", "code": "...", "base64": "data:image/png;base64,..."}
   ```
5. **Escanear no celular**:
   - WhatsApp → ⋮ (menu) → Aparelhos conectados → Conectar aparelho
   - Escanear QR
6. **Verificar status**:
   ```bash
   curl http://localhost:8080/instance/connectionState/cartorio-2notas \
     -H "apikey: $EVOLUTION_API_KEY"
   # Esperado: {"instance":{"state":"open"}}
   ```

### Pairing Code (alternativa)

```bash
# Para números que não conseguem scan (ex: corporativo)
curl -X POST http://localhost:8080/instance/pairingCode/cartorio-2notas \
  -H "apikey: $EVOLUTION_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"phoneNumber": "5511999999999"}'

# Resposta: {"code": "ABCD-1234"}
# Inserir no WhatsApp → Configurações → Aparelhos conectados → Conectar com código
```

## 🔌 Webhook Configuration

### Webhook Global

```bash
curl -X POST http://localhost:8080/webhook/set/cartorio-2notas \
  -H "apikey: $EVOLUTION_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://api.2notasudi.com.br/api/v1/webhook/evolution",
    "webhook_by_events": false,
    "webhook_base64": false,
    "events": [
      "MESSAGES_UPSERT",
      "MESSAGES_UPDATE",
      "CONNECTION_UPDATE",
      "QRCODE_UPDATED"
    ],
    "enabled": true
  }'
```

### Webhook HMAC Signature

Evolution API envia `X-Hub-Signature-256: sha256=<hex>` calculado sobre o body bruto com a API Key.

**Backend valida** (`backend/app/services/evolution_ingest.py`):
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

## 📤 Endpoints Envio

### sendText

```bash
curl -X POST http://localhost:8080/message/sendText/cartorio-2notas \
  -H "apikey: $EVOLUTION_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "number": "5511999999999",
    "text": "Olá! Esta é uma mensagem do Cartório 2º Notas."
  }'
```

**Resposta**:
```json
{
  "key": {"remoteJid": "5511999999999@s.whatsapp.net", "fromMe": true, "id": "3EB0..."},
  "message": {"conversation": "Olá! ..."},
  "messageTimestamp": 1720544400,
  "status": "PENDING"
}
```

### sendReaction

```bash
curl -X POST http://localhost:8080/message/sendReaction/cartorio-2notas \
  -H "apikey: $EVOLUTION_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "key": {
      "remoteJid": "5511999999999@s.whatsapp.net",
      "fromMe": false,
      "id": "3EB0C2F8A8B4C0D0E1F2A3B4"
    },
    "reaction": "👍"
  }'
```

### sendPresence (typing)

```bash
curl -X POST http://localhost:8080/chat/sendPresence/cartorio-2notas \
  -H "apikey: $EVOLUTION_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "number": "5511999999999",
    "presence": "composing",
    "delay": 4000
  }'
```

**Presence values**: `composing` (digitando), `recording` (gravando áudio), `paused` (parou).

### sendButtons

```bash
curl -X POST http://localhost:8080/message/sendButtons/cartorio-2notas \
  -H "apikey: $EVOLUTION_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "number": "5511999999999",
    "title": "Menu Principal",
    "description": "Escolha uma opção",
    "footer": "Cartório 2º Notas",
    "buttons": [
      {"buttonId": "1", "buttonText": {"displayText": "📋 Protocolo"}, "type": 1},
      {"buttonId": "2", "buttonText": {"displayText": "📅 Agendar"}, "type": 1},
      {"buttonId": "3", "buttonText": {"displayText": "👤 Humano"}, "type": 1}
    ]
  }'
```

**Limite**: 3 botões (WhatsApp restriction). Para mais opções, usar list message.

### sendList

```bash
curl -X POST http://localhost:8080/message/sendList/cartorio-2notas \
  -H "apikey: $EVOLUTION_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "number": "5511999999999",
    "title": "Menu",
    "description": "Escolha o serviço",
    "buttonText": "Ver opções",
    "sections": [
      {
        "title": "Serviços",
        "rows": [
          {"title": "Reconhecimento de firma", "description": "R$ XX,XX", "rowId": "1"},
          {"title": "Procuração", "description": "R$ XX,XX", "rowId": "2"},
          {"title": "Testamento", "description": "R$ XX,XX", "rowId": "3"}
        ]
      }
    ]
  }'
```

## 📨 Webhook Payload (Recebimento)

### MESSAGES_UPSERT (mensagem recebida)

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
    "messageTimestamp": 1720544400,
    "status": "DELIVERED"
  },
  "sender": "5511999999999@s.whatsapp.net"
}
```

### MESSAGES_UPDATE (status update)

```json
{
  "event": "MESSAGES_UPDATE",
  "instance": "cartorio-2notas",
  "data": {
    "key": {"remoteJid": "5511999999999@s.whatsapp.net", "fromMe": true, "id": "..."},
    "update": {"status": "READ"},
    "messageTimestamp": 1720544460
  }
}
```

### CONNECTION_UPDATE

```json
{
  "event": "CONNECTION_UPDATE",
  "instance": "cartorio-2notas",
  "data": {
    "state": "open",
    "statusReason": 200
  }
}
```

**States**: `open` (conectado), `close` (desconectado), `connecting` (reconectando).

## 🔧 Adapter Implementation

**Arquivo**: `backend/app/api/v1/whatsapp.py`

```python
class WhatsAppAdapter(ChannelAdapter):
    """Adapter polimórfico para Evolution API."""

    async def send(self, msg: OutboundMessage) -> bool:
        url = f"{EVOLUTION_BASE_URL}/message/sendText/{INSTANCE}"
        payload = {
            "number": msg.recipient_id.replace("@s.whatsapp.net", ""),
            "text": msg.text,
        }
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.post(url, json=payload, headers={"apikey": EVOLUTION_API_KEY})
        return r.status_code == 200

    async def typing(self, recipient_id: str, action: str = "composing") -> bool:
        if not action:
            return True
        url = f"{EVOLUTION_BASE_URL}/chat/sendPresence/{INSTANCE}"
        payload = {"number": recipient_id.replace("@s.whatsapp.net", ""), "presence": action}
        async with httpx.AsyncClient(timeout=5) as client:
            r = await client.post(url, json=payload, headers={"apikey": EVOLUTION_API_KEY})
        return r.status_code == 200

    async def react(self, recipient_id: str, message_id: str, reaction: str = "thumbsup") -> bool:
        emoji = {"thumbsup": "👍", "heart": "❤️", "laugh": "😂"}.get(reaction, "👍")
        url = f"{EVOLUTION_BASE_URL}/message/sendReaction/{INSTANCE}"
        payload = {
            "key": {"remoteJid": recipient_id, "fromMe": False, "id": message_id},
            "reaction": emoji,
        }
        async with httpx.AsyncClient(timeout=5) as client:
            r = await client.post(url, json=payload, headers={"apikey": EVOLUTION_API_KEY})
        return r.status_code == 200

    async def verify_signature(self, raw_body: bytes, signature: str | None) -> bool:
        return validate_evolution_signature(raw_body, signature)
```

## 🔍 Troubleshooting

### Instância desconectada

```bash
# Status
curl http://localhost:8080/instance/connectionState/cartorio-2notas \
  -H "apikey: $EVOLUTION_API_KEY"

# Reconectar
curl http://localhost:8080/instance/restart/cartorio-2notas \
  -H "apikey: $EVOLUTION_API_KEY"

# Logout (limpar sessão, pedir novo QR)
curl -X DELETE http://localhost:8080/instance/logout/cartorio-2notas \
  -H "apikey: $EVOLUTION_API_KEY"
```

### Webhook não recebe eventos

```bash
# Listar webhooks configurados
curl http://localhost:8080/webhook/find/cartorio-2notas \
  -H "apikey: $EVOLUTION_API_KEY"

# Reconfigurar
curl -X POST http://localhost:8080/webhook/set/cartorio-2notas \
  -H "apikey: $EVOLUTION_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"url": "https://api.2notasudi.com.br/api/v1/webhook/evolution", "events": ["MESSAGES_UPSERT"], "enabled": true}'
```

### HMAC signature inválida

```bash
# Verificar API Key bate
grep EVOLUTION_API_KEY /etc/easypanel/projects/cartorio/api/code/.env
grep AUTHENTICATION_API_KEY /etc/easypanel/projects/cartorio/evolution-api/.env

# Devem ser IGUAIS
```

### Container crash loop

```bash
# Logs
docker service logs cartorio_evolution-api --tail 100

# Verificar Postgres + Redis
docker exec cartorio_postgres pg_isready -U evolution
docker exec cartorio_redis redis-cli PING

# Restart
docker service update --force cartorio_evolution-api
```

## 📚 Referências

- [`BOTS.md`](BOTS.md) — overview
- [`WHATSAPP_GUIDE.md`](WHATSAPP_GUIDE.md) — guia operacional
- [`TROUBLESHOOTING_BOTS.md`](TROUBLESHOOTING_BOTS.md)
- [`LGPD_BOTS.md`](LGPD_BOTS.md) — consent WhatsApp
- `backend/app/api/v1/whatsapp.py` — código adapter
- `backend/app/services/evolution_ingest.py` — webhook ingest
- `infra/evolution-api/` — Docker compose + config
- `docs/EVOLUTION_API_INTEGRATION.md` — integração histórica
- Lesson 143 (WhatsApp espelhado)

---

**Modified by**: OpenCode-MiniMax-M3-High · 2026-07-09T16:39:00Z