# C25 — Alertas Telegram via Uptime Kuma

> **[HOLD-DEPLOY]** Gustavo precisa decidir se vai deployar C24 (Uptime Kuma)
> antes de ativar este. C25 e dependencia de C24.

## Visao geral

Quando qualquer dos 7 monitores (ver `monitors.json`) cai ou recupera, Uptime
Kuma envia **1 mensagem Telegram** para Gustavo via `@cartorio_alerts_bot`.
A mensagem inclui:

- Nome do servico + tag
- Tipo de evento (`DOWN` ou `UP` recovered)
- Timestamp BRT
- Latencia / status code
- Link direto para a pagina de status

## Pre-requisitos

1. **Bot criado via @BotFather**:
   ```
   /newbot
   name: Cartorio Alerts Bot
   username: cartorio_alerts_bot
   ```
   BotFather retorna um token no formato `123456789:AA...`. Salvar em
   `~/.zcode/secrets/cartorio-alerts-bot.txt` (NUNCA comitar).

2. **Chat ID do Gustavo**:
   - Mandar qualquer mensagem para o bot
   - Acessar `https://api.telegram.org/bot<TOKEN>/getUpdates`
   - Copiar o campo `chat.id` (numero)

3. **Uptime Kuma deployado** (ver `README.md`).

## Setup (UI path)

1. Login em `https://status.2notasudi.com.br`
2. `Settings → Notifications → Setup Notification`
3. Type: **Telegram**
4. Preencher:
   - **Friendly Name**: `Cartorio Alerts Telegram`
   - **Bot Token**: `<token do passo 1>`
   - **Chat ID**: `<chat id do passo 2>`
   - ✅ **Send resolved notifications** (alerta tambem quando volta UP)
   - ✅ Default enabled (aplica a todos os monitores novos automaticamente)
5. Clicar **Test** → Gustavo recebe `✅ Test successful` no Telegram.
6. **Apply existing**: confirma para reaplicar aos 7 monitores.

## Setup (API path)

```bash
curl -X POST https://status.2notasudi.com.br/api/notification \
  -H "Authorization: Bearer $UPTIME_KUMA_API_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Cartorio Alerts Telegram",
    "type": "telegram",
    "isDefault": true,
    "applyExisting": true,
    "config": "{\"bot_token\":\"<TOKEN>\",\"chat_id\":\"<CHAT_ID>\",\"send_resolved\":true}"
  }'
```

> **Caveat**: o campo `config` precisa ser **JSON-as-string** (escape duplo).
> O import via UI e mais seguro — use UI primeiro.

## Templates de mensagem (Uptime Kuma nativo)

Uptime Kuma usa 2 templates, editaveis em `Settings → Notifications → Edit`:

### DOWN

```
🔴 [Cartorio] {{name}} DOWN

Servico: {{name}}
URL: {{url}}
Status: {{statusCode}}
Latencia: {{ping}}ms
Hora: {{datetime}} BRT
Duracao outage: {{downDuration}}

🔗 https://status.2notasudi.com.br
```

### UP (recovered)

```
🟢 [Cartorio] {{name}} RECOVERED

Servico: {{name}}
URL: {{url}}
Status: {{statusCode}}
Latencia: {{ping}}ms
Hora: {{datetime}} BRT
Downtime total: {{lastDownDuration}}

🔗 https://status.2notasudi.com.br
```

## Anti-spam

Uptime Kuma tem 3 camadas:

1. **Retry**: cada monitor tem `maxretries=2` — so alerta apos 2 falhas
   consecutivas (6 min default). Ja configurado em `monitors.json`.
2. **Resend cooldown**: cada notif tem `resendTimer` (5 min default) —
   mesmo DOWN NAO reenvia mensagem ate o cooldown expirar.
3. **Grouping**: se 5 monitores caem juntos (raro mas acontece em incident
   global), Uptime Kuma envia 5 mensagens separadas. Para agrupar:
   Settings → Notifications → `Group notifications by monitor`.

## Severidade escalation (planejado, nao implementado)

| Evento | Mensagem | Acao Gustavo |
|---|---|---|
| 1 monitor DOWN | `🔴` | Investigar 5-10 min |
| 2-3 monitors DOWN | `🔴🔴` | Investigar IMEDIATO (incident?) |
| 4+ monitors DOWN | `🚨 INCIDENT 🚨` | PagerDuty-style (NAO IMPLEMENTADO) |
| 1 monitor UP recovered | `🟢` | Log no SESSION_SUMMARY |
| 5+ monitors UP recovered | `🟢✅ ALL GREEN` | Post-mortem |

Para implementar escalation, usar Uptime Kuma **separately** com canais
diferentes (1 para `core`, 1 para `infra`, etc) OU script externo
`backend/scripts/uptime_kuma_escalate.py` que faz polling da API Uptime Kuma
e reenvia para Telegram com tag `🚨` se N >= 4.

## Gotchas

- **Telegram `parse_mode`** do Uptime Kuma: default `Markdown`. Para usar
  emojis, deixar Markdown; se quebrar, mudar para `HTML` em Edit Notification.
- **Bot bloqueado**: se Gustavo bloquear o bot, TODAS as mensagens falham
  silenciosamente (Uptime Kuma loga 403 mas nao reenvia). Workaround: avisar
  Gustavo para nunca bloquear `cartorio_alerts_bot`.
- **Rate limit Telegram**: 30 msgs/segundo por bot. Com 7 monitores e 1
  msg/evento, maximo esperado = 14 msg/min (todos DOWN + recovered).
  Bem abaixo do limite. Se crescer >20 monitores, considerar Telegram Pro.
- **HTTPS no webhook**: Uptime Kuma chama `api.telegram.org` direto, nao
  passa pelo VPS. Entao VPS offline NAO impede alertas Telegram.

## Status checklist (C25)

- [ ] Bot `@cartorio_alerts_bot` criado via @BotFather
- [ ] Token salvo em `~/.zcode/secrets/cartorio-alerts-bot.txt`
- [ ] Chat ID Gustavo capturado via `getUpdates`
- [ ] Uptime Kuma deployado (C24)
- [ ] Notification Telegram configurada (UI path)
- [ ] Test message recebida por Gustavo
- [ ] 7 monitores usando esta notification
- [ ] Test DOWN forcado em 1 monitor → alerta chegou
- [ ] Test UP forcado em 1 monitor → alerta recovered chegou

## Referencias

- Uptime Kuma Telegram notification:
  <https://github.com/louislam/uptime-kuma/wiki/Notification#telegram>
- BotFather: <https://t.me/BotFather>
- Telegram Bot API: <https://core.telegram.org/bots/api>
- Lesson 151 (Cloudflare tunnel rescue, 2026-07-08) — caso paralelo de
  alerta Telegram que motivou este setup

---

**Modified by**: cartorio-sre + Gustavo Almeida
**Status**: [HOLD-DEPLOY]
**Last reviewed**: 2026-07-15