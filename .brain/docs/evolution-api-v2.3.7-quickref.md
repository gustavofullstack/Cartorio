# Evolution API v2.3.7 — Quick Reference

**Source**: https://doc.evolution-api.com/v2/api-reference
**Versao em uso**: 2.3.7 (whatsapp.2notasudi.com.br)
**Atualizado**: 2026-06-25

## 1. Autenticacao

Todas as rotas exigem header `apikey: <EVOLUTION_API_KEY>`.

```bash
EVOLUTION_URL="https://whatsapp.2notasudi.com.br"
EVOLUTION_KEY="429683C4C977415CAAFCCE10F7D57E11"
```

## 2. Endpoints Principais

### 2.1 Instance Management

| Metodo | Path | Descricao |
|---|---|---|
| POST | `/instance/create` | Cria instance (com qrcode:true para gerar QR) |
| GET | `/instance/fetchInstances` | Lista todas instances |
| GET | `/instance/connectionState/{name}` | State (open/close/connecting) |
| DELETE | `/instance/logout/{name}` | Logout (mantem instance) |
| DELETE | `/instance/delete/{name}` | Deleta instance |
| POST | `/instance/restart/{name}` | Restart (regenera QR) |

### 2.2 Mensagens (Send)

```bash
# Texto simples
POST /message/sendText/{instance}
Body: {"number": "5534999999999", "text": "Ola!"}

# Texto com delay
POST /message/sendText/{instance}
Body: {"number": "...", "text": "...", "delay": 1200}

# Imagem
POST /message/sendImage/{instance}
Body: {"number": "...", "image": "https://..."}

# Audio
POST /message/sendAudio/{instance}
Body: {"number": "...", "audio": "https://..."}

# Documento
POST /message/sendDocument/{instance}
Body: {"number": "...", "document": "https://...", "fileName": "doc.pdf"}
```

### 2.3 Webhook

```bash
# Configurar webhook
POST /webhook/set/{instance}
Body: {
  "url": "https://api.2notasudi.com.br/api/v1/webhook/evolution",
  "webhook_by_events": false,
  "events": ["MESSAGES_UPSERT", "MESSAGES_UPDATE", "CONNECTION_UPDATE"]
}
```

Eventos comuns:
- `MESSAGES_UPSERT` - nova msg recebida
- `MESSAGES_UPDATE` - msg editada/deletada
- `CONNECTION_UPDATE` - status mudou
- `QRCODE_UPDATED` - QR regenerado
- `SEND_MESSAGE` - msg enviada

## 3. Instance cartorio-2notas (criada 2026-06-25)

```json
{
  "instanceName": "cartorio-2notas",
  "instanceId": "333beb72-f279-459e-b466-003731aba6ac",
  "integration": "WHATSAPP-BAILEYS",
  "status": "connecting"
}
```

**Status atual** (verificar antes de cada deploy):
```bash
curl https://whatsapp.2notasudi.com.br/instance/connectionState/cartorio-2notas \
  -H "apikey: $EVOLUTION_KEY"
# Esperado: {"instance": {"state": "open"}}
```

## 4. Pareamento

1. Acesse https://whatsapp.2notasudi.com.br/manager
2. Login (credenciais em BACKUP_KEYS)
3. Instance cartorio-2notas > Connect
4. Escanear QR com WhatsApp TriQ Hub
5. State -> open

## 5. Webhook Config (producao)

```bash
curl -X POST "https://whatsapp.2notasudi.com.br/webhook/set/cartorio-2notas" \
  -H "apikey: $EVOLUTION_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://api.2notasudi.com.br/api/v1/webhook/evolution",
    "events": ["MESSAGES_UPSERT", "MESSAGES_UPDATE", "CONNECTION_UPDATE"],
    "webhook_by_events": false
  }'
```

## 6. Gotchas

- Webhook NAO funciona com instance state=close (precisa open)
- QR Code expira em 60s (restart regenera)
- N8N nao tem node Evolution oficial (usa community `n8n-nodes-evolution-api`)
- Database WhatsApp (Baileys) eh volátil - se container reiniciar, perde sessoes NÂO pareadas

## 7. Backup

Estado da instance fica em volume Docker `cartorio_evolution-api_evolution_instances`:
```bash
docker exec cartorio_evolution-api-1 ls /evolution/instances
# cartorio-2notas/
#   ├── store/
#   ├── chats/
#   └── ...
```

Modified by Pietra + Gustavo Almeida 2026-06-25
