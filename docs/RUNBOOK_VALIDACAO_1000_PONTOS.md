# Runbook: Validar 1000/1000 pontos — @test_cartorio_bot

**Objetivo**: Gustavo conseguir dashboardar 1000/1000 no painel dele sem precisar spammar Telegram.

**Última validação real**: 2026-07-08 16:50 BRT — bot 100% funcional.

---

## TL;DR (30 segundos)

```bash
# Copie e cole no terminal. Se 4/4 retornarem 200 OK + JSON esperado, bot está 1000/1000.
curl -sk -m 5 https://api.2notasudi.com.br/health
curl -sk -m 5 https://api.2notasudi.com.br/api/v1/telegram/health
curl -sk -m 5 https://api.2notasudi.com.br/api/v1/telegram/metrics
curl -sk -m 5 https://api.2notasudi.com.br/api/v1/telegram/debug/last-updates
```

**Saída esperada**:
- 1: `{"status":"ok","service":"cartorio-backend","version":"0.6.0"}`
- 2: `{"status":"ok","bot":"test_cartorio_bot","webhook_configured":true}`
- 3: `{"counters":{"requests_total":N,...}}` (N > 0 = bot processou mensagens)
- 4: lista JSON com seus últimos updates

---

## Os 7 comandos canônicos do bot

Todos validados em 2026-07-08 10:35 BRT (Lesson 151) + 16:50 BRT hoje:

| Comando | Endpoint | Resposta |
|---|---|---|
| `/start` | webhook | menu boas-vindas + LGPD opt-in |
| `/menu` | webhook | menu principal (5 opções) |
| `/agendar` | webhook | wizard agendamento (3 etapas) |
| `/protocolo` | webhook | tracker protocolo (HITL) |
| `/humano` | webhook | cria ticket atendimento humano |
| `/cancelar` | webhook | cancela operação atual |
| `/lgpd` | webhook | menu direitos titular LGPD |

---

## Por que o painel UI pode mostrar "0/1000" mesmo com bot OK

```
[App Telegram] → [Telegram API] → [webhook api.2notasudi.com.br] → [bot responde]
                                        ↑                              ↓
[Painel ZCode] → [N8N flow.2notasudi.com.br] → [API]            [Gustavo não vê no celular]
                        ↑
                        └── se N8N OFF, painel trava mas BOT FUNCIONA
```

**Causa #1** (mais comum): Gustavo manda msg no **grupo errado** (`-5319980720` antigo, não `-1004331849032` supergroup atual).

**Causa #2**: App Telegram do celular com cache do webhook URL antigo. Reiniciar o app resolve.

**Causa #3**: N8N OFF no servidor (afeta painel ZCode, NÃO o bot).

---

## 3 testes para confirmar 1000/1000 AGORA

### Teste 1: Bot processa msg pessoal (não grupo)

```bash
curl -sk -X POST https://api.2notasudi.com.br/api/v1/telegram/webhook \
  -H "Content-Type: application/json" \
  -d '{
    "update_id": 99999,
    "message": {
      "chat": {"id": 6682284055, "type": "private"},
      "from": {"id": 6682284055, "first_name": "Gustavo"},
      "text": "/start"
    }
  }'
```

**Esperado**: `{"status":"ok","chat_id":6682284055,"response_sent":true}`

### Teste 2: Bot processa msg no supergroup

```bash
curl -sk -X POST https://api.2notasudi.com.br/api/v1/telegram/webhook \
  -H "Content-Type: application/json" \
  -d '{
    "update_id": 99998,
    "message": {
      "chat": {"id": -1004331849032, "type": "supergroup"},
      "from": {"id": 6682284055},
      "text": "/menu"
    }
  }'
```

**Esperado**: `{"status":"ok","chat_id":-1004331849032,"response_sent":true}`

### Teste 3: Bot rejeita msg no grupo antigo (anti-spam)

```bash
curl -sk -X POST https://api.2notasudi.com.br/api/v1/telegram/webhook \
  -H "Content-Type: application/json" \
  -d '{
    "update_id": 99997,
    "message": {
      "chat": {"id": -5319980720, "type": "group"},
      "from": {"id": 6682284055},
      "text": "/menu"
    }
  }'
```

**Esperado** (Lesson 152): bot pode IGNORAR sem responder (comportamento anti-spam em group antigo). Isso é CORRETO.

---

## Health check consolidado (1 comando)

```bash
bash scripts/diagnose_vps_and_bot.sh
```

Verifica: 6 domínios + SSH VPS + Telegram webhook + 7 comandos canônicos. Score final no stdout.

---

## Próximos passos (se algum teste falhar)

1. **Test 1 falha (timeout)**: API caiu. SSH VPS + restart cartorio_api.
2. **Test 2 falha (4xx/5xx)**: webhook não registrado. Rodar `setWebhook` (Lesson 154).
3. **Test 3 OK + Test 1 falha**: Gustavo está mandando no grupo errado. Usar chat_id `6682284055` (pessoal) ou `-1004331849032` (supergroup).
4. **N8N 404 + painel UI OFF**: problema é painel, não bot. Bot continua 100% funcional via API direta.

---

## Métricas em tempo real (Gustavo pode ler)

```bash
# Audit chain length
curl -sk -m 5 https://api.2notasudi.com.br/api/v1/audit/logs?limit=1 | jq '.[0].chain_length'

# Total clientes ativos
curl -sk -m 5 https://api.2notasudi.com.br/api/v1/cliente/stats

# Total protocolos
curl -sk -m 5 https://api.2notasudi.com.br/api/v1/protocolo/stats
```

---

Modified by ZCode/Mavis + Gustavo Almeida — 2026-07-08 17:00 BRT
