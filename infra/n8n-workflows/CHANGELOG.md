# Changelog Workflows N8N

> Versionamento semver: **major.minor** (major = breaking change, minor = adicao).
> Mantido por `cartorio-n8n` rein. Source of truth: `/infra/n8n-workflows/*.json`.

## Legenda de Breaking Change

Uma major version (v1 -> v2) e necessaria quando:
- Trigger mudou (webhook path, cron expression, event type)
- Autenticacao mudou (HMAC, API key, OAuth)
- Contrato de input/output (payload schema) mudou
- Credenciais N8N renomeadas ou removidas
- Webhook IDs (`webhookId`) regerados

Minor version (v1.0 -> v1.1) e OK para:
- Adicionar/ajustar nos de PII scrub ou logging
- Adicionar retry policy ou timeout
- Adicionar audit log
- Trocar httpRequest por node oficial

## Workflow: 01-consulta-emolumento

| Versao | Data | Mudanca | Breaking |
|--------|------|---------|----------|
| v1 | 2026-06-22 | baseline webhook POST /consulta-emolumento (3 nos) | - |
| v2 | 2026-06-23 | adiciona node Parse Tipo + retry 2x | nao |
| v3 | 2026-06-23 | adiciona node Audit Log + PII Scrub reforcado | nao |
| v3-fixed | 2026-06-23 | corrige validacao `$json.response` no Respond | nao |

### v2 -> v3
- Adicionado: no PII Scrub com regex email + phone
- Adicionado: no Audit Log (POST /audit/verify/log)
- Alterado: timeout API Emolumento 5s -> 8s
- Removido: fallback LiteLLM (morto, 0 chamadas em 30d)

## Workflow: 03-handoff-human

| Versao | Data | Mudanca | Breaking |
|--------|------|---------|----------|
| v1 | 2026-06-23 | httpRequest direto para Chatwoot (4 nos) | - |
| v2 (chatwoot) | 2026-06-23 | node oficial `n8n-nodes-chatwoot` v1.0.2 | sim (credencial renomeada) |

### v1 -> v2 (BREAKING)
- Removido: httpRequest customizado
- Adicionado: node `chatwoot` createConversation + sendMessage
- **Breaking**: credencial `Chatwoot API` deve ser recriada
- **Breaking**: payload de entrada agora exige campo `conversation_id` opcional

## Workflow: 11-monitor-cartorio

| Versao | Data | Mudanca | Breaking |
|--------|------|---------|----------|
| v1 | 2026-06-23 | baseline 11 nos (saude 6 servicos) | - |
| v1.1 | 2026-06-23 | adiciona silent hours 00:00-05:00 BRT | nao |

## Workflow: 12-chatbot-llm

| Versao | Data | Mudanca | Breaking |
|--------|------|---------|----------|
| v1 (end-to-end) | 2026-06-23 | httpRequest direto para OpenCode-Go (6 nos) | - |
| v2 (mcp) | 2026-06-23 | substitui httpRequest por `n8n-nodes-mcp` v0.1.37 | sim (protocolo MCP 2025-03-26) |

### v1 -> v2 (BREAKING)
- Removido: httpRequest OpenCode-Go
- Adicionado: `mcpClient` tool `cartorio_chatbot_responder`
- **Breaking**: requer backend MCP no ar (`wf22-mcp-server.json` ativo)
- Adicionado: fallback graceful se MCP indisponivel

## Workflow: 22-mcp-server

| Versao | Data | Mudanca | Breaking |
|--------|------|---------|----------|
| v1 | 2026-06-22 | mcpTrigger inativo | - |
| v2 | 2026-06-23 | reativado + tools registradas | nao |

## Workflow: 24-retencao-diaria

| Versao | Data | Mudanca | Breaking |
|--------|------|---------|----------|
| v1 | 2026-06-23 | novo (Sprint 3 Bloco 4.3) - LGPD 5y/2y | - |

## Workflow: 00-error-handler

| Versao | Data | Mudanca | Breaking |
|--------|------|---------|----------|
| v3 | 2026-06-22 | baseline | - |
| v4 | 2026-06-23 | autenticacao via `$env.CARTORIO_API_KEY` | sim (removido hardcoded) |

### v3 -> v4 (BREAKING)
- Removido: API key hardcoded no jsonBody
- Adicionado: header `X-API-Key: {{$env.CARTORIO_API_KEY}}`
- **Breaking**: env `CARTORIO_API_KEY` deve estar configurado no N8N

## Workflow: 25-protocolo-concluido-pdf

| Versao | Data | Mudanca | Breaking |
|--------|------|---------|----------|
| v1 | 2026-06-23 | novo - 7 nos (cron 5min + split + PDF + WhatsApp) | - |

## Workflow: 30-health-deep-check

| Versao | Data | Mudanca | Breaking |
|--------|------|---------|----------|
| v1 | 2026-06-23 | novo - 7 nos (cron 15min + aggregate) | - |

## Resumo de Breaking Changes Globais (Sprint 0-3)

| Data | Workflow | Migracao |
|------|----------|----------|
| 2026-06-23 | 00-error-handler v3->v4 | setar env CARTORIO_API_KEY no N8N |
| 2026-06-23 | 03-handoff-human v1->v2 | recriar credencial `Chatwoot API` |
| 2026-06-23 | 12-chatbot-llm v1->v2 | subir backend MCP (wf22) |

---

Modified by ZCode/Mavis + Gustavo Almeida — 2026-06-24
