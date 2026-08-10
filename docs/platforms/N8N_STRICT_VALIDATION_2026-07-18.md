# N8N Strict Validation Report

- generated_at: 2026-07-18T16:40:04+00:00
- dir: `/Users/gustavoalmeida/Projetos/Cartorio/infra/n8n-workflows`
- strict_mode: True
- total: 39
- valid: 39
- invalid: 0
- broken_json: 0
- basic_ok_only: 0
- active: 33
- inactive: 6
- total_nodes: 342

## Workflows

| file | status | nodes | name | first_error |
|------|--------|-------|------|-------------|
| `00-error-handler.json` | valid | 15 | 00 - Error Handler Global (T25) v6 | - |
| `01-consulta-emolumento.json` | valid | 11 | 01 - Consulta Emolumento WhatsApp (v3) | - |
| `02-criar-protocolo.json` | valid | 11 | 02 - Criar Protocolo (LGPD) | - |
| `03-handoff-human-chatwoot-v3-staging.json` | valid | 7 | 03 - Handoff Humano (Chatwoot v3 - official node STAGING) | - |
| `04-boas-vindas-lgpd.json` | valid | 10 | 04 - Boas-Vindas + Consentimento LGPD | - |
| `04-consulta-protocolo.json` | valid | 11 | 04 - Consulta Protocolo | - |
| `05-agendamento.json` | valid | 11 | 05 - Agendamento Atendimento | - |
| `06-2-via-protocolo.json` | valid | 11 | 06 - Segunda Via Documento | - |
| `07-pesquisa-satisfacao.json` | valid | 6 | 07 - Pesquisa Satisfacao | - |
| `08-audit-verify-diario.json` | valid | 9 | 08 - Audit Verify Diario | - |
| `10-faq-bot.json` | valid | 8 | 10 - FAQ Bot | - |
| `11-monitor-cartorio.json` | valid | 18 | 11 - Monitor Cartório | - |
| `12-chatbot-llm-end-to-end.json` | valid | 8 | 12 - Chatbot LLM End-to-End (PII + MCP + OpenCode-Go) | - |
| `14-opencode-go-fallback.json` | valid | 7 | 14 - OpenCode-Go LLM Fallback (direct OpenAI-compat) | - |
| `16-prospeccao-enrichment.json` | valid | 10 | 16 - Prospeccao Lead Enrichment (Tier A/B/C scoring) | - |
| `18-prospeccao-followup-d7.json` | valid | 8 | 18 - Prospeccao Follow-up D+7 (LGPD opt-out) | - |
| `21-backup-status-5min.json` | valid | 7 | 21 - Backup Status 5min (heartbeat + alerta) | - |
| `22-audit-verify-6h.json` | valid | 7 | 22 - Audit Verify 6h (SHA256 chain check) | - |
| `22-mcp-server.json` | valid | 4 | MCP - Server Tools (T22) v2 | - |
| `23-cron-stale-detector.json` | valid | 8 | 23 - Cron Stale Detector (5min) | - |
| `23-lgpd-esqueci-v2.json` | valid | 24 | 23 - LGPD Esqueci (DELETE cliente + cascade + audit) | - |
| `24-daily-cleanup.json` | valid | 6 | 24 - Daily Cleanup 03:00 (sessoes > 24h Redis) | - |
| `24-retencao-diaria.json` | valid | 7 | 24 - Retencao Diaria (LGPD 5y/2y) | - |
| `25-metrics-collector.json` | valid | 6 | 25 - Metrics Collector (1min Prometheus) | - |
| `25-protocolo-concluido-pdf.json` | valid | 11 | 25 - Protocolo Concluido: Envia PDF via WhatsApp | - |
| `26-alerta-critico.json` | valid | 10 | 26 - Alerta Critico (Telegram IM + Chatwoot) | - |
| `27-welcome-first-time.json` | valid | 9 | 27 - Welcome First Time (consentimento LGPD) | - |
| `28-audit-snapshot.json` | valid | 5 | 28 - Audit Snapshot (diario 04:00 S3) | - |
| `29-rate-limit-reset.json` | valid | 5 | 29 - Rate Limit Reset (hourly) | - |
| `30-chatwoot-status-sync-g8.json` | valid | 4 | G8.03.T3 - Chatwoot Status Sync → API HITL Mute | - |
| `30-health-deep-check.json` | valid | 10 | 30 - Health Deep Check 15min (todos endpoints) | - |
| `31-telegram-listener.json` | valid | 12 | 31 - Telegram Listener (CartorioBot test) | - |
| `33-whatsapp-qr-scan-helper.json` | valid | 6 | 33-whatsapp-qr-scan-helper | - |
| `34-metrics-collector-5min.json` | valid | 3 | 34-metrics-collector-5min | - |
| `35-llm-fallback-3x.json` | valid | 8 | 35-llm-fallback-3x | - |
| `36-chatwoot-telegram-sync.json` | valid | 9 | 36-chatwoot-telegram-sync | - |
| `37-agendamento-notarial-sync.json` | valid | 7 | 37-agendamento-notarial-sync | - |
| `38-emolumento-calculator.json` | valid | 6 | 38-emolumento-calculator | - |
| `evo-in.json` | valid | 7 | EVO-IN - Evolution Webhook Inbound | - |

## Schema

- Validator: `app.schemas.n8n_workflow.N8nWorkflow` (Pydantic v2 strict)
- `ConfigDict(strict=True, extra='forbid')` em todos os modelos
- LGPD Art. 46: regex anti-PII (CPF/CNPJ/RG/tel/email) em `name`, `description`, `tags`, `webhookId`
- IANA timezone via `zoneinfo` (stdlib)
