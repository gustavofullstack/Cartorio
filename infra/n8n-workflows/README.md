# infra/n8n-workflows — Cartório 2º Notas Uberlândia

> JSON exports canônicos dos workflows N8N ativos em produção.
> Source of truth: **`https://cartorio-n8n.dfgdxq.easypanel.host`** (Easypanel-hosted N8N).
> Owner: `cartorio-n8n` rein.

---

## Conteúdo

**Workflows ativos em produção** (exportados via `GET /api/v1/workflows/{id}` em 2026-06-23 13:55 BRT, atualizados 2026-06-23 18:50 BRT no Sprint 0 audit):

| Arquivo | Workflow | ID N8N | Trigger | Notes |
|---------|----------|--------|---------|-------|
| `01-consulta-emolumento.json` | Consulta Emolumento WhatsApp (v2) | `bR7qIo3bFpG4zgxO` | Webhook POST `/webhook/consulta-emolumento` | |
| `02-criar-protocolo.json` | Criar Protocolo (LGPD) | `MzeYTSDouymzdpRw` | Webhook POST `/webhook/criar-protocolo` | |
| `03-handoff-human.json` | Handoff Humano (Chatwoot v1, httpRequest) | `OQRIOVHcOjpkQ0Of` | Webhook POST `/webhook/handoff-human` | v1 — em produção até Gustavo importar v2 |
| `04-boas-vindas-lgpd.json` | Boas-Vindas + Consentimento LGPD | `sDtkfOJ5BA7M73wB` | Webhook POST `/webhook/boas-vindas` | |
| `04-consulta-protocolo.json` | Consulta Protocolo | `iXWuZRYZLR3FYPYB` | Webhook POST `/webhook/consulta-protocolo` | |
| `05-agendamento.json` | Agendamento Atendimento | `UUW8ulDTxZUqBsci` | Webhook POST `/webhook/agendamento` | |
| `06-2-via-protocolo.json` | Segunda Via Documento | `ukbRUEudoX3SvsqD` | Webhook POST `/webhook/segunda-via` | |
| `07-pesquisa-evolucao.json` | Pesquisa Satisfação | `D9XJmlJRXZ3lavoa` | Cron 24h | ⚠️ SUI: falta credencial Evolution no N8N |
| `08-audit-verify-diario.json` | Audit Verify Diário | `3rr2WFBCJZ16U4DH` | Cron 03:30 diário | |
| `09-backup-status.json` | Monitor Backup Diário | `pgtlDqGaMW1MGawt` | Cron 04:00 diário | |
| `10-faq-bot.json` | FAQ Bot | `jZhgQbJQ5z7atYfK` | Webhook POST `/webhook/faq` | |
| `11-monitor-cartorio.json` | Monitor Cartório (saúde 6 serviços) | `5ABAZCQVRLd7AmM5` | Cron 5min + Webhook POST `/webhook/monitor-cartorio` | |

**Workflows v2 — Sprint 3 Bloco 5** (usando nodes oficiais, prontos pra Gustavo importar):

| Arquivo | Workflow | Trigger | Diferença vs v1 |
|---------|----------|---------|-----------------|
| `03-handoff-human-chatwoot.json` | Handoff Humano (Chatwoot v2) | Webhook POST `/webhook/handoff-human` | Substitui httpRequest por `n8n-nodes-chatwoot` v1.0.2 (createConversation + sendMessage). Requer credencial `Chatwoot API` no N8N. |
| `12-chatbot-llm-mcp.json` | Chatbot LLM End-to-End (MCP) | Webhook POST `/webhook/chatbot-llm` | Substitui httpRequest OpenCode-Go por `n8n-nodes-mcp` v0.1.37 (`cartorio_chatbot_responder` tool call). Protocolo MCP 2025-03-26. |
| `22-mcp-server.json` | MCP Server Tools | `mcpTrigger` | **Reativado** (Sprint 3 prep): `active: true`. |
| `23-cron-stale-detector.json` | Cron Stale Detector (5min) | Cron 5min | **Reativado** (Sprint 3 prep): `active: true`. |
| `24-retencao-diaria.json` | Retenção Diária (LGPD 5y/2y) | Cron 02:00 diário | **Novo** (Sprint 3 Bloco 4.3). Chama `POST /api/v1/admin/retencao/run` + alerta Chatwoot + verifica audit chain. |

Outros arquivos:
- `01-consulta-emolumento-v2.json` — versão legada (multi-line format) preservada para git history.
- `11_monitor_cartorio.js` + `11_monitor_cartorio_README.md` — **script Node standalone** com a mesma lógica do workflow N8N #11, para health-check fora do N8N (cron externo ou smoke test manual).

**Política de versionamento (ADR-020):**
- Workflows v1 ficam no repo até Gustavo confirmar migração no painel N8N.
- Cada v2 adiciona sufixo (`-chatwoot`, `-mcp`) ou ID numérico (`24-`).
- Gustavo decide via N8N UI qual fica ativo: import v2, deactivate v1, archive v1.

---

## Como importar workflow do repo para N8N

Pré-requisito: API key do N8N.

```bash
export N8N_API_KEY="<sua-key>"
export N8N_BASE="https://cartorio-n8n.dfgdxq.easypanel.host/api/v1"

# 1) Criar workflow (POST retorna o JSON completo com ID)
curl -s -X POST -H "X-N8N-API-KEY: $N8N_API_KEY" \
     -H "Content-Type: application/json" \
     -d @infra/n8n-workflows/01-consulta-emolumento.json \
     "$N8N_BASE/workflows" | tee /tmp/wf01-created.json

# 2) Ativar (substituir {ID} pelo id do retorno acima)
WF_ID=$(python3 -c "import json; print(json.load(open('/tmp/wf01-created.json'))['id'])")
curl -s -X POST -H "X-N8N-API-KEY: $N8N_API_KEY" \
     "$N8N_BASE/workflows/$WF_ID/activate"
```

> **Nota**: o N8N às vezes enriquece o JSON retornado (adiciona `id`, `versionId`, `shared`, `meta` etc.). Re-exportar após importar é uma boa prática.

---

## Como re-exportar workflow do N8N para o repo

```bash
export N8N_API_KEY="<sua-key>"
export N8N_BASE="https://cartorio-n8n.dfgdxq.easypanel.host/api/v1"

# Workflow 01
WF_ID="bR7qIo3bFpG4zgxO"
curl -s -H "X-N8N-API-KEY: $N8N_API_KEY" \
     "$N8N_BASE/workflows/$WF_ID" \
     -o infra/n8n-workflows/01-consulta-emolumento.json
```

Para exportar todos de uma vez, ver `infra/scripts/export-all-n8n.sh` (TODO se necessário).

---

## Convenção de credenciais (NÃO COMITAR secrets)

Os JSONs contêm apenas **IDs de credenciais** (`credentials: { evolutionApi: { id: "adbzRn9s...", name: "evolution-api-cartorio" } }`). Os **valores** (apiKey, password, etc.) ficam apenas no N8N, criptografados.

**Auditoria**: 11/11 workflows auditados em 2026-06-23 11:25 BRT — zero secrets hardcoded.

Para verificar:
```bash
grep -rE "sk-[a-zA-Z0-9]{20,}|@[A-Za-z0-9_]{8,}|password.*=.*['\"]" infra/n8n-workflows/ && echo "POSSIBLE LEAK!" || echo "OK"
```

---

## Backup automático

O cron `/etc/cron.d/cartorio-backup` na VPS roda diariamente às 03:00 BRT e inclui `n8n workflows/credentials + .env` em `/var/backups/cartorio/`. Retenção 7 dias. Validação manual ver `docs/SMOKE_TEST_REPORT.md`.

---

## Mudanças recentes

- **2026-06-23 13:55 BRT**: Re-export canônico dos 12 workflows ativos. 11 modificados, 1 novo (`11-monitor-cartorio.json`).
- **2026-06-23 13:48 BRT**: 4 credenciais registradas no N8N (`opencode-go-deepseek`, `supabase-postgres`, `cartorio-api-bearer`, `evolution-api-cartorio`).
- **2026-06-23 11:15 BRT**: 7 workflows bonus Sprint 2 importados (E1.S1.WF5-10).
- **2026-06-23 10:42 BRT**: Workflows Sprint 1 (#01-04) importados.

Ver `docs/CHANGELOG.md` para histórico completo.

---

Modified by Gustavo Almeida · 2026-06-23 13:55 BRT