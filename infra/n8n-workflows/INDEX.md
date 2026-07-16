# N8N Workflows Registry — INDEX

**Auto-gerado**: rodar `python3 scripts/n8n_index_gen.py`.
**Total WFs**: 37 | **Ativos**: 31 | **Total nodes**: 281

## Tabela de workflows

| # | Arquivo | Nome | Ativo | Nodes | Triggers | Primeiros 5 nodes |
|---|---|---|---|---|---|---|
| 1 | `00-error-handler.json` | 00 - Error Handler Global (T25) v6 | ✅ | 15 | errorTrigger | `Init Correlation`, `Error Trigger`, `Extract Error Info`, `Alert Backend (HMAC)`, `Format Telegram` |
| 2 | `01-consulta-emolumento.json` | 01 - Consulta Emolumento WhatsApp (v3) | ✅ | 9 | webhook, respondToWebhook | `Init Correlation`, `Webhook consulta-emolumento`, `PII Scrub`, `Parse Tipo`, `API Emolumento` |
| 3 | `02-criar-protocolo.json` | 02 - Criar Protocolo (LGPD) | ✅ | 9 | webhook, respondToWebhook, respondToWebhook | `Init Correlation`, `Webhook WhatsApp`, `PII Scrub + LGPD Check`, `LGPD bloqueado?`, `POST /protocolo` |
| 4 | `03-handoff-human-chatwoot-v3-staging.json` | 03 - Handoff Humano (Chatwoot v3 - official node STAGING) | ✅ | 7 | webhook, respondToWebhook | `Webhook Handoff`, `Normalizar Payload`, `Chatwoot: Create Conversation`, `Chatwoot: Send Message`, `Respond Handoff` |
| 5 | `04-boas-vindas-lgpd.json` | 04 - Boas-Vindas + Consentimento LGPD | ✅ | 8 | webhook, respondToWebhook, respondToWebhook | `Init Correlation`, `Webhook Boas-Vindas`, `Detectar Usuario`, `Primeira interacao?`, `Welcome Novo Cliente` |
| 6 | `04-consulta-protocolo.json` | 04 - Consulta Protocolo | ✅ | 9 | webhook, respondToWebhook, respondToWebhook | `Init Correlation`, `Webhook WhatsApp`, `Extrair Protocolo + PII`, `Tem protocolo + sem PII?`, `GET /protocolo/{id}` |
| 7 | `05-agendamento.json` | 05 - Agendamento Atendimento | ✅ | 9 | webhook, respondToWebhook, respondToWebhook | `Init Correlation`, `Webhook WhatsApp`, `Parse dia/hora + PII`, `Sem PII e tem dia/hora?`, `API Disponibilidade` |
| 8 | `06-2-via-protocolo.json` | 06 - Segunda Via Documento | ✅ | 9 | webhook, respondToWebhook, respondToWebhook | `Init Correlation`, `Webhook WhatsApp`, `Extrai protocolo + PII`, `Tem protocolo?`, `POST /documento/segunda-via` |
| 9 | `07-pesquisa-satisfacao.json` | 07 - Pesquisa Satisfacao | ✅ | 6 | scheduleTrigger | `Init Correlation`, `Cron 24h`, `GET atendimentos`, `Evolution sendText`, `Log Final Correlation` |
| 10 | `08-audit-verify-diario.json` | 08 - Audit Verify Diario | ✅ | 9 | scheduleTrigger | `Init Correlation`, `Cron 03:30`, `POST /audit/verify`, `Check resultado`, `Critico?` |
| 11 | `10-faq-bot.json` | 10 - FAQ Bot | ✅ | 6 | webhook, respondToWebhook | `Init Correlation`, `Webhook WhatsApp`, `FAQ Knowledge Base`, `Respond FAQ`, `Log Final Correlation` |
| 12 | `11-monitor-cartorio.json` | 11 - Monitor Cartório | ✅ | 16 | webhook, respondToWebhook, scheduleTrigger | `Init Correlation`, `POST /monitor-cartorio`, `Check API`, `Combine Results`, `Check Evolution` |
| 13 | `12-chatbot-llm-end-to-end.json` | 12 - Chatbot LLM End-to-End (PII + MCP + OpenCode-Go) | ❌ | 6 | webhook, respondToWebhook | `Webhook Evolution`, `Extract Message Fields`, `PII Scrubber`, `MCP: cartorio_chatbot_responder`, `Decide Response` |
| 14 | `14-opencode-go-fallback.json` | 14 - OpenCode-Go LLM Fallback (direct OpenAI-compat) | ❌ | 5 | webhook, respondToWebhook | `OpenClaw Fallback Trigger`, `Extract Prompt`, `POST OpenCode-Go Direct`, `Parse OpenCode Response`, `Respond OpenCode-Go` |
| 15 | `16-prospeccao-enrichment.json` | 16 - Prospeccao Lead Enrichment (Tier A/B/C scoring) | ✅ | 8 | webhook, respondToWebhook | `Init Correlation`, `Lead Novo Webhook`, `Extract Lead`, `Score Tier`, `POST Lead to Supabase` |
| 16 | `18-prospeccao-followup-d7.json` | 18 - Prospeccao Follow-up D+7 (LGPD opt-out) | ✅ | 8 | scheduleTrigger | `Init Correlation`, `Cron Daily 10:00`, `GET Leads Enviados D+7`, `Build Follow-up D+7`, `Evolution Send D+7` |
| 17 | `21-backup-status-5min.json` | 21 - Backup Status 5min (heartbeat + alerta) | ✅ | 7 | scheduleTrigger | `Init Correlation`, `Cron 5min`, `GET Backup Status`, `Backup OK?`, `Alerta Backup Falhou` |
| 18 | `22-audit-verify-6h.json` | 22 - Audit Verify 6h (SHA256 chain check) | ✅ | 7 | scheduleTrigger | `Init Correlation`, `Cron 6h`, `POST Audit Verify`, `Chain OK?`, `Alerta Audit Chain Quebrada` |
| 19 | `22-mcp-server.json` | MCP - Server Tools (T22) v2 | ✅ | 4 | mcpTrigger | `Init Correlation`, `MCP Server Trigger`, `Log Final Correlation`, `Report Metrics N8N` |
| 20 | `23-cron-stale-detector.json` | 23 - Cron Stale Detector (5min) | ✅ | 8 | scheduleTrigger | `Init Correlation`, `Cron 5min`, `POST /cron/stale-detector`, `Tem stale?`, `Alerta Chatwoot` |
| 21 | `23-lgpd-esqueci-v2.json` | 23 - LGPD Esqueci (DELETE cliente + cascade + audit) | ❌ | 8 | webhook, respondToWebhook, respondToWebhook | `LGPD Esqueci Webhook`, `Extract Cliente ID`, `GET Cliente Historico`, `Pode Deletar?`, `POST Soft Delete` |
| 22 | `24-daily-cleanup.json` | 24 - Daily Cleanup 03:00 (sessoes > 24h Redis) | ✅ | 6 | scheduleTrigger | `Init Correlation`, `Cron Daily 03:00`, `POST Daily Cleanup`, `Log Result`, `Log Final Correlation` |
| 23 | `24-retencao-diaria.json` | 24 - Retencao Diaria (LGPD 5y/2y) | ✅ | 7 | scheduleTrigger | `Init Correlation`, `Cron Diario 02:00 BRT`, `POST /admin/retencao/run`, `Alerta Chatwoot`, `Verificar audit chain` |
| 24 | `25-metrics-collector.json` | 25 - Metrics Collector (1min Prometheus) | ✅ | 6 | scheduleTrigger | `Init Correlation`, `Cron 1min`, `POST Metrics to API`, `Fetch Metrics from Backend`, `Log Final Correlation` |
| 25 | `25-protocolo-concluido-pdf.json` | 25 - Protocolo Concluido: Envia PDF via WhatsApp | ✅ | 11 | scheduleTrigger | `Init Correlation`, `Cron 5min`, `API: buscar concluidos`, `Tem concluidos?`, `Split Out (1 item por vez)` |
| 26 | `26-alerta-critico.json` | 26 - Alerta Critico (Telegram IM + Chatwoot) | ✅ | 8 | webhook, respondToWebhook | `Init Correlation`, `Alerta Webhook`, `Extract Alerta`, `POST Telegram IM`, `Chatwoot Critical` |
| 27 | `27-welcome-first-time.json` | 27 - Welcome First Time (consentimento LGPD) | ❌ | 7 | webhook | `Init Correlation`, `Welcome First Time`, `Extract Cliente`, `Evolution Welcome`, `POST Welcome Tracking` |
| 28 | `28-audit-snapshot.json` | 28 - Audit Snapshot (diario 04:00 S3) | ✅ | 5 | scheduleTrigger | `Init Correlation`, `Cron Daily 04:00`, `POST Snapshot Audit`, `Log Final Correlation`, `Report Metrics N8N` |
| 29 | `29-rate-limit-reset.json` | 29 - Rate Limit Reset (hourly) | ✅ | 5 | scheduleTrigger | `Init Correlation`, `Cron Hourly`, `POST Reset Rate Limit`, `Log Final Correlation`, `Report Metrics N8N` |
| 30 | `30-health-deep-check.json` | 30 - Health Deep Check 15min (todos endpoints) | ✅ | 10 | scheduleTrigger | `Init Correlation`, `Cron 15min`, `Health Radar`, `Health Integracoes`, `Health Backup` |
| 31 | `31-telegram-listener.json` | 31 - Telegram Listener (CartorioBot test) | ✅ | 10 | webhook, respondToWebhook | `Init Correlation`, `Webhook Telegram`, `Extract Telegram fields`, `Mensagem de bot?`, `LLM: deepseek-v4-flash` |
| 32 | `33-whatsapp-qr-scan-helper.json` | 33-whatsapp-qr-scan-helper | ✅ | 4 | webhook | `Webhook Evolution Connection Trigger`, `Is Connection Closed?`, `Notify Closed to Admin (Telegram)`, `Notify Open to Admin (Telegram)` |
| 33 | `34-metrics-collector-5min.json` | 34-metrics-collector-5min | ✅ | 3 | scheduleTrigger | `Interval 5 Minutos`, `Get N8N System Metrics`, `POST to Cartorio API metrics/n8n` |
| 34 | `35-llm-fallback-3x.json` | 35-llm-fallback-3x | ✅ | 6 | webhook | `Webhook Trigger`, `Try Primary (opencode_go)`, `Try Secondary (openclaw)`, `Try Tertiary (openrouter)`, `Try Quaternary (gemini)` |
| 35 | `36-chatwoot-telegram-sync.json` | 36-chatwoot-telegram-sync | ✅ | 7 | webhook | `Chatwoot Webhook Trigger`, `Filter: message_created only`, `Filter: outgoing messages only`, `Lookup Atendimento by Chatwoot Conv`, `Send to Telegram` |
| 36 | `evo-in.json` | EVO-IN - Evolution Webhook Inbound | ❌ | 5 | webhook | `Init Correlation`, `Webhook`, `POST to Backend`, `Log Final Correlation`, `Report Metrics N8N` |
| 37 | `lgpd-esqueci-fix.json` | 23 - LGPD Esqueci (DELETE cliente + cascade + audit) | ❌ | 8 | webhook, respondToWebhook, respondToWebhook | `LGPD Esqueci Webhook`, `Extract Cliente ID`, `GET Cliente Historico`, `Pode Deletar?`, `POST Soft Delete` |

## Por trigger

- **respondToWebhook**: 23 workflow(s)
- **webhook**: 21 workflow(s)
- **scheduleTrigger**: 15 workflow(s)
- **errorTrigger**: 1 workflow(s)
- **mcpTrigger**: 1 workflow(s)

## Por squad

| Squad | WFs | Detalhes |
|---|---|---|
| **A (MCP)** | 1 | 22-mcp-server |
| **A (alertas)** | 1 | 26-alerta-critico |
| **A (audit)** | 2 | 08-audit-verify-diario, 22-audit-verify |
| **A (backup)** | 1 | 21-backup-status |
| **A (cron)** | 2 | 23-cron-stale-detector, 24-daily-cleanup |
| **A (health)** | 1 | 30-health-deep-check |
| **A (monitor)** | 1 | 11-monitor-cartorio |
| **A (observability)** | 1 | 25-metrics-collector |
| **A (rate limit)** | 1 | 29-rate-limit-reset |
| **B (2ª via)** | 1 | 06-2-via-protocolo |
| **B (FAQ)** | 1 | 10-faq-bot |
| **B (N8N infra)** | 1 | 00-error-handler |
| **B (NPS)** | 1 | 07-pesquisa-satisfacao |
| **B (PDF)** | 1 | 25-protocolo-concluido-pdf |
| **B (Telegram)** | 1 | 31-telegram-listener |
| **B (agendamento)** | 1 | 05-agendamento |
| **B (consulta)** | 2 | 01-consulta-emolumento, 04-consulta-protocolo |
| **B (handoff)** | 1 | 03-handoff-human |
| **B (prospecção)** | 2 | 16-prospeccao-enrichment, 18-prospeccao-followup |
| **B (protocolo)** | 1 | 02-criar-protocolo |
| **B+C (LGPD consent)** | 1 | 04-boas-vindas |
| **B+C (onboarding)** | 1 | 27-welcome-first-time |
| **D (LGPD audit)** | 1 | 28-audit-snapshot |
| **D (LGPD)** | 1 | 23-lgpd-esqueci |
| **D (retenção)** | 1 | 24-retencao-diaria |
| **E (LLM)** | 2 | 12-chatbot-llm-end-to-end, 14-opencode-go-fallback |

## Stats finais
- Total: 37 workflows
- Ativos: 31 (83%)
- Total nodes: 281
- Trigger mais comum: respondToWebhook (23 WFs)

---

**Modified by Gustavo Almeida + Pietra orquestrador — G6 wave 2 (auto-gerado)**