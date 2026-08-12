# N8N Error Handler Integration Audit

**Data**: 2026-07-16T15:46:12.079116+00:00
**Total workflows**: 36
**Error handler**: `NOT FOUND`

## [HOLD] 29 workflow(s) SEM error handler

## Detalhes por WF

| WF | name | errorWorkflow? | aponta OK | timezone |
|---|---|---|---|---|
| `00-error-handler.json` | 00 - Error Handler Global (T25) v6 | ✅ | ✅ | ? |
| `01-consulta-emolumento.json` | 01 - Consulta Emolumento WhatsApp (v3) | ✅ | ✅ | ? |
| `02-criar-protocolo.json` | 02 - Criar Protocolo (LGPD) | ❌ | ❌ | ? |
| `03-handoff-human-chatwoot-v3-staging.json` | 03 - Handoff Humano (Chatwoot v3 - official node STAGING) | ✅ | ✅ | ? |
| `04-boas-vindas-lgpd.json` | 04 - Boas-Vindas + Consentimento LGPD | ❌ | ❌ | ? |
| `04-consulta-protocolo.json` | 04 - Consulta Protocolo | ❌ | ❌ | ? |
| `05-agendamento.json` | 05 - Agendamento Atendimento | ❌ | ❌ | ? |
| `06-2-via-protocolo.json` | 06 - Segunda Via Documento | ❌ | ❌ | ? |
| `07-pesquisa-satisfacao.json` | 07 - Pesquisa Satisfacao | ✅ | ✅ | ? |
| `08-audit-verify-diario.json` | 08 - Audit Verify Diario | ❌ | ❌ | ? |
| `10-faq-bot.json` | 10 - FAQ Bot | ❌ | ❌ | ? |
| `11-monitor-cartorio.json` | 11 - Monitor Cartório | ❌ | ❌ | ? |
| `12-chatbot-llm-end-to-end.json` | 12 - Chatbot LLM End-to-End (PII + MCP + OpenCode-Go) | ✅ | ✅ | ? |
| `14-opencode-go-fallback.json` | 14 - OpenCode-Go LLM Fallback (direct OpenAI-compat) | ✅ | ✅ | ? |
| `16-prospeccao-enrichment.json` | 16 - Prospeccao Lead Enrichment (Tier A/B/C scoring) | ❌ | ❌ | ? |
| `18-prospeccao-followup-d7.json` | 18 - Prospeccao Follow-up D+7 (LGPD opt-out) | ❌ | ❌ | ? |
| `21-backup-status-5min.json` | 21 - Backup Status 5min (heartbeat + alerta) | ❌ | ❌ | ? |
| `22-audit-verify-6h.json` | 22 - Audit Verify 6h (SHA256 chain check) | ❌ | ❌ | ? |
| `22-mcp-server.json` | MCP - Server Tools (T22) v2 | ❌ | ❌ | ? |
| `23-cron-stale-detector.json` | 23 - Cron Stale Detector (5min) | ❌ | ❌ | ? |
| `23-lgpd-esqueci-v2.json` | 23 - LGPD Esqueci (DELETE cliente + cascade + audit) | ❌ | ❌ | ? |
| `24-daily-cleanup.json` | 24 - Daily Cleanup 03:00 (sessoes > 24h Redis) | ❌ | ❌ | ? |
| `24-retencao-diaria.json` | 24 - Retencao Diaria (LGPD 5y/2y) | ❌ | ❌ | ? |
| `25-metrics-collector.json` | 25 - Metrics Collector (1min Prometheus) | ❌ | ❌ | ? |
| `25-protocolo-concluido-pdf.json` | 25 - Protocolo Concluido: Envia PDF via WhatsApp | ❌ | ❌ | ? |
| `26-alerta-critico.json` | 26 - Alerta Critico (Telegram IM + Chatwoot) | ❌ | ❌ | ? |
| `27-welcome-first-time.json` | 27 - Welcome First Time (consentimento LGPD) | ❌ | ❌ | ? |
| `28-audit-snapshot.json` | 28 - Audit Snapshot (diario 04:00 S3) | ❌ | ❌ | ? |
| `29-rate-limit-reset.json` | 29 - Rate Limit Reset (hourly) | ❌ | ❌ | ? |
| `30-health-deep-check.json` | 30 - Health Deep Check 15min (todos endpoints) | ❌ | ❌ | ? |
| `31-telegram-listener.json` | 31 - Telegram Listener (CartorioBot test) | ❌ | ❌ | ? |
| `33-whatsapp-qr-scan-helper.json` | 33-whatsapp-qr-scan-helper | ❌ | ❌ | ? |
| `34-metrics-collector-5min.json` | 34-metrics-collector-5min | ❌ | ❌ | ? |
| `35-llm-fallback-3x.json` | 35-llm-fallback-3x | ❌ | ❌ | ? |
| `evo-in.json` | EVO-IN - Evolution Webhook Inbound | ❌ | ❌ | ? |
| `lgpd-esqueci-fix.json` | 23 - LGPD Esqueci (DELETE cliente + cascade + audit) | ✅ | ✅ | ? |

---

**Modified by Gustavo Almeida + cartorio-n8n — G6 wave 8 (auto-gerado)**