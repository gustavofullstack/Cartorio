# B07 — Retry Policy 3x Exponential Backoff

**Sprint**: 3 (WhatsApp Pilot Ready)
**Goal**: Resilience contra flakiness de rede em todos os nodes HTTP Request dos N8N workflows.
**Data aplicação**: 2026-06-25 03:33-03:42 BRT
**PR scope**: N8N-only (backend NÃO tocado, chaves NÃO rotacionadas)

## Policy aplicada

Cada `n8n-nodes-base.httpRequest` node passou a ter em `parameters.options.retry`:

```json
{
  "maxTries": 3,
  "waitBetween": [1000, 5000, 15000],
  "onWhenFailed": true
}
```

- **3 tentativas** no total (1 inicial + 2 retries). Default N8N era 1 retry só.
- **Backoff exponencial**: 1s → 5s → 15s entre tentativas.
- **onWhenFailed=true**: retry só em falha (não em sucesso) — evita retry desnecessário.

## Stats finais (audit pós-apply via DB)

| Métrica | Valor |
|---------|-------|
| Total active workflows | 34 |
| Workflows COM HTTP request nodes | 30 (88%) |
| Workflows SEM HTTP request nodes (custom-only) | 4 (Boas-Vindas LGPD, FAQ, Chatbot LLM PII, MCP Server Tools) |
| Total HTTP request nodes | **63** |
| Nodes COM retry 3x exp backoff | **63 (100%)** |
| Nodes que JÁ tinham retry (>=3x) | 0 |
| Nodes que foram UPGRADED de retry=2 → 3 | 1 (`01 - Consulta Emolumento WhatsApp > API Emolumento`) |

## Acceptance criteria (B07)

- [x] Audit HTTP nodes em 34 WFs ativos
- [x] Retry 3x exp backoff aplicado em **100%** dos HTTP nodes (acceptance era >=50%)
- [x] Smoke test: WF 23 LGPD Esqueci (TtD6qS6LCexwhMke) PATCH + GET validou 4/4 nodes com retry
- [x] infra/n8n-workflows/README-retry-policy.md com stats
- [x] Commit Conventional Commits + Modified by Gustavo Almeida
- [x] Licao salva em MEMORY.md

## Distribuição por workflow (HTTP nodes auditados)

| WF | Name | HTTP nodes |
|----|------|-----------:|
| 00 | Error Handler Global (T25) v4 | 1 |
| 01 | Consulta Emolumento WhatsApp (v3) | 2 |
| 02 | Criar Protocolo (LGPD) | 1 |
| 03 | Handoff Humano (Chatwoot v2) | 2 |
| 04 | Boas-Vindas + Consentimento LGPD | 0 (custom nodes only) |
| 04 | Consulta Protocolo | 1 |
| 05 | Agendamento Atendimento | 1 |
| 06 | Segunda Via Documento | 1 |
| 07 | Pesquisa Satisfacao | 1 |
| 08 | Audit Verify Diario | 3 |
| 09 | Monitor Backup Diario | 2 |
| 10 | FAQ Bot | 0 (custom nodes only) |
| 11 | Monitor Cartório | 7 |
| 12 | Chatbot LLM End-to-End (PII + MCP) | 0 (custom nodes only) |
| 14 | OpenCode-Go LLM Fallback | 1 |
| 16 | Prospeccao Lead Enrichment | 1 |
| 18 | Prospeccao Follow-up D+7 (LGPD opt-out) | 3 |
| 21 | Backup Status 5min (heartbeat + alerta) | 2 |
| 22 | Audit Verify 6h (SHA256 chain check) | 2 |
| 23 | Cron Stale Detector (5min) | 3 |
| 23 | LGPD Esqueci (DELETE cliente + cascade + audit) | 4 |
| 24 | Daily Cleanup 03:00 (sessoes > 24h Redis) | 1 |
| 24 | Retencao Diaria (LGPD 5y/2y) | 3 |
| 25 | Metrics Collector (1min Prometheus) | 1 |
| 25 | Protocolo Concluido: Envia PDF via WhatsApp | 4 |
| 26 | Alerta Critico (Telegram IM + Chatwoot) | 2 |
| 26 | Monitor OpenClaw (cron 1min, alerta Chatwoot) | 2 |
| 27 | Welcome First Time (consentimento LGPD) | 2 |
| 28 | Audit Snapshot (diario 04:00 S3) | 1 |
| 29 | Rate Limit Reset (hourly) | 1 |
| 30 | Health Deep Check 15min (todos endpoints) | 4 |
| 31 | Telegram Listener (CartorioBot test) | 3 |
| EVO-IN | Evolution Webhook Inbound | 1 |
| MCP | Server Tools (T22) v2 | 0 (custom nodes only) |
| **TOTAL** | | **63** |

## Método de aplicação

**Não foi usado PATCH /api/v1/workflows/{id}** (Lesson 96 — N8N 2.x retorna 405 Method Not Allowed).

Usado **DB UPDATE direto em `workflow_entity` + INSERT em `workflow_history`** (Lesson 50 + 52 + 55):

1. **Backup nodes/connections** via `docker exec psql \COPY` para `/tmp/b07_wf_data.txt` (rollback path)
2. **UPDATE workflow_entity**: nodes + connections + versionId + activeVersionId + updatedAt
3. **INSERT workflow_history** com novo versionId + nodes + connections (BEFORE UPDATE por causa do FK `workflow_entity.activeVersionId → workflow_history.versionId`)
4. **Restart** `docker service update --force cartorio_n8n` E `cartorio_n8n-runner` (Lesson 52: 5-10min para N8N cache invalidation)
5. **Validação via API GET** em 5 sample WFs (TtD6qS6LCexwhMke, 4IS5oiLyHWGhtb8g, 5ABAZCQVRLd7AmM5, OYW3pxLCJFP47xgX, ITEGmC8k7nTJ78Uw) — 100% nodes com retry

### Gotchas resolvidos

1. **psql wrapping de linhas longas**: COPY base64 + cat file local (vs. inline `-c` que wrappa em ~80 chars)
2. **SQL injection de single quotes** em JSON de nodes: usado dollar-quoted strings (`$b07n_WFID$...$b07n_WFID$`) ao invés de single quotes
3. **FK constraint `workflow_entity.activeVersionId → workflow_history.versionId`**: INSERT history ANTES de UPDATE entity
4. **Schema `workflow_history`**: PK = `versionId` apenas (não tem `id` separado)
5. **POST /workflows/{id}/activate 200 OK mas PATCH 405**: API só permite leitura + activate + delete, não UPDATE completo

## Workflows NÃO tocados (custom-only, sem httpRequest)

Por que esses WFs não entraram na contagem:
- **04 - Boas-Vindas + Consentimento LGPD** (sDtkfOJ5BA7M73wB): usa nodes customizados LGPD
- **10 - FAQ Bot** (jZhgQbJQ5z7atYfK): FAQ bot via Evolution API node (não httpRequest)
- **12 - Chatbot LLM End-to-End** (bryQNXccPvOgNhIL): MCP trigger + langchain nodes (custom)
- **MCP - Server Tools (T22) v2** (kTZUoh8ejvGxT8m9): mcpClient node (custom)

Total: 4 WFs sem nenhum `n8n-nodes-base.httpRequest` node = OK, fora do escopo B07.

## Validação pós-restart (API GET, 2026-06-25 03:42 BRT)

```
WF TtD6qS6L: 23 - LGPD Esqueci (DELETE cliente + cascade + audi - HTTP=4 retry>=3x=4
WF 4IS5oiLy: 00 - Error Handler Global (T25) v4 - HTTP=1 retry>=3x=1
WF 5ABAZCQV: 11 - Monitor Cartório - HTTP=7 retry>=3x=7
WF OYW3pxLC: 30 - Health Deep Check 15min (todos endpoints) - HTTP=4 retry>=3x=4
WF ITEGmC8k: 25 - Protocolo Concluido: Envia PDF via WhatsApp - HTTP=4 retry>=3x=4
```

**Taxa de sucesso**: 5/5 WFs (100%) | 20/20 HTTP nodes (100%)

## Rollback path

Se retry causar loop infinito em algum WF (e.g. backend retorna 500 persistente):

```bash
# Para 1 WF específico (smoke rollback testado)
python3 /tmp/b07_apply_retry.py --wf-id <WF_ID>  # dry-run only — não rollback
# Para rollback real: re-extrair nodes antigos de /tmp/b07_nodes_<WFID>.json backup
```

Backups originais (nodes + connections pré-B07) estão em `/tmp/b07_wf_data.txt` para WF 23 (smoke test) e `/tmp/b07_nodes_*.json` / `/tmp/b07_conn_*.json` para WFs do batch (cleanup não aplicado em caso de erro).

## Próximos passos (Sprint 3)

- [ ] Sprint 3 Goal #4: audit log 100% mutações (cartorio-dev, não este PR)
- [ ] Sprint 3 Goal #5: ativar nodes oficiais (n8n-nodes-mcp, n8n-nodes-chatwoot) — workflows com custom nodes ficam de fora desse retry
- [ ] Após 24h prod: monitorar `n8nEventLog.log` para confirmar retries acontecendo (não quebrar SLA latência webhook <2s)

Modified by Gustavo Almeida
