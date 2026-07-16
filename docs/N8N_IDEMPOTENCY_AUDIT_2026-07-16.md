# N8N Idempotency Audit

**Data**: 2026-07-16T16:54:14.763140+00:00
**Total workflows**: 37
**WFs com webhook**: 21
**Webhooks SEM idempotencia**: 20

## [HOLD] 20 webhook(s) sem protecao SETNX

## Detalhes por WF

| WF | name | Webhooks | Redis? | Marker? | Missing |
|---|---|---|---|---|---|
| `01-consulta-emolumento.json` | 01 - Consulta Emolumento WhatsApp (v3) | consulta-emolumento | ❌ | ❌ | consulta-emolumento |
| `02-criar-protocolo.json` | 02 - Criar Protocolo (LGPD) | criar-protocolo | ❌ | ❌ | criar-protocolo |
| `03-handoff-human-chatwoot-v3-staging.json` | 03 - Handoff Humano (Chatwoot v3 - official node STAGING) | handoff-human | ❌ | ✅ | nenhum |
| `04-boas-vindas-lgpd.json` | 04 - Boas-Vindas + Consentimento LGPD | boas-vindas | ❌ | ❌ | boas-vindas |
| `04-consulta-protocolo.json` | 04 - Consulta Protocolo | consulta-protocolo | ❌ | ❌ | consulta-protocolo |
| `05-agendamento.json` | 05 - Agendamento Atendimento | agendar-atendimento | ❌ | ❌ | agendar-atendimento |
| `06-2-via-protocolo.json` | 06 - Segunda Via Documento | segunda-via | ❌ | ❌ | segunda-via |
| `10-faq-bot.json` | 10 - FAQ Bot | faq | ❌ | ❌ | faq |
| `11-monitor-cartorio.json` | 11 - Monitor Cartório | monitor-cartorio | ❌ | ❌ | monitor-cartorio |
| `12-chatbot-llm-end-to-end.json` | 12 - Chatbot LLM End-to-End (PII + MCP + OpenCode-Go) | chatbot-llm | ❌ | ❌ | chatbot-llm |
| `14-opencode-go-fallback.json` | 14 - OpenCode-Go LLM Fallback (direct OpenAI-compat) | openclaw-fallback | ❌ | ❌ | openclaw-fallback |
| `16-prospeccao-enrichment.json` | 16 - Prospeccao Lead Enrichment (Tier A/B/C scoring) | lead-novo | ❌ | ❌ | lead-novo |
| `23-lgpd-esqueci-v2.json` | 23 - LGPD Esqueci (DELETE cliente + cascade + audit) | lgpd-esqueci | ❌ | ❌ | lgpd-esqueci |
| `26-alerta-critico.json` | 26 - Alerta Critico (Telegram IM + Chatwoot) | alerta-critico | ❌ | ❌ | alerta-critico |
| `27-welcome-first-time.json` | 27 - Welcome First Time (consentimento LGPD) | welcome-first | ❌ | ❌ | welcome-first |
| `31-telegram-listener.json` | 31 - Telegram Listener (CartorioBot test) | telegram-cartoriobot | ❌ | ❌ | telegram-cartoriobot |
| `33-whatsapp-qr-scan-helper.json` | 33-whatsapp-qr-scan-helper | webhook/evolution/connection | ❌ | ❌ | webhook/evolution/connection |
| `35-llm-fallback-3x.json` | 35-llm-fallback-3x | llm-fallback-chain | ❌ | ❌ | llm-fallback-chain |
| `36-chatwoot-telegram-sync.json` | 36-chatwoot-telegram-sync | chatwoot-telegram-sync | ❌ | ❌ | chatwoot-telegram-sync |
| `evo-in.json` | EVO-IN - Evolution Webhook Inbound | evo-in | ❌ | ❌ | evo-in |
| `lgpd-esqueci-fix.json` | 23 - LGPD Esqueci (DELETE cliente + cascade + audit) | lgpd-esqueci-fix | ❌ | ❌ | lgpd-esqueci-fix |

## Padrao obrigatorio (lesson 22)

```javascript
// Antes do processing principal:
const webhookId = $input.item.json.headers['x-webhook-id'] || $input.item.json.body.id;
const dedupKey = `webhook:${webhookId}`;
const isNew = await redis.set(dedupKey, '1', 'EX', 86400, 'NX');
if (!isNew) {
  throw new Error('DUPLICATE_WEBHOOK');
}
```

---

**Modified by Gustavo Almeida + cartorio-n8n — G6 wave 12 (auto-gerado)**