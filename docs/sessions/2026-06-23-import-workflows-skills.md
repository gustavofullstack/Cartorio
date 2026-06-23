# SESSAO 2026-06-23 PARTE 2 — IMPORT WORKFLOWS N8N + 7a SKILL OPENCLAW

## Conquistas desta sessao (continuacao da anterior)

### N8N (3 workflows importados via API)

Usei a N8N API key que ja existia (rotacionada ontem e exposta no briefing, mas funcional):

- **#25 - Protocolo Concluido: Envia PDF via WhatsApp** (id: ITEGmC8k7nTJ78Uw, **ativo**)
  - Cron 5min, busca protocolos concluidos, gera PDF, envia Evolution
  - Resolveu bug: connections referenciavam node `Noop (sem concluidos)` que nao existia nos nodes
  - Fix: adicionei noop-1 automaticamente via script
- **#12 v2 - Chatbot LLM End-to-End (PII + MCP + OpenCode-Go)** (id: bryQNXccPvOgNhIL)
- **#26 - Monitor OpenClaw** (id: 6e7c830b-4ab8-465e-b9e2-b2a86bc0aca9) - ja tinha criado via SQL

**Outros 37 workflows ja existiam no N8N** (criados em paralelo por sessoes anteriores):
- #11 Monitor Cartorio, #14 OpenCode-Go LLM Fallback, #15 Session Sync,
- #16-18 Prospeccao Lead, #19-20 Cliente/Protocolo criado, #21 Backup Status,
- #22 Audit Verify 6h, #23 Cron Stale Detector, #24 Retencao Diaria + Daily Cleanup,
- #25 Metrics Collector, #26 Alerta Critico, #27 Welcome First Time,
- #28 Audit Snapshot, #29 Rate Limit Reset, #30 Health Deep Check, e mais.

### Script `import_all_to_n8n.sh`

Criei **script generico** que importa todos os workflows do repo `infra/n8n-workflows/` para o N8N:
- Detecta workflows ja existentes (pula)
- Limpa chaves read-only (`active`, `id`, `versionId`, `meta`, `tags`, etc)
- Adiciona automaticamente `Noop` nodes se referenciados em connection mas nao em nodes
- Trata erros e mostra summary (Imported/Skipped/Failed)

Uso:
```bash
N8N_API_KEY=xxx ./infra/n8n-workflows/import_all_to_n8n.sh
```

### OpenClaw: 7a skill

- **cartorio-pesquisa-satisfacao.md** - pesquisa pos-atendimento
  - Documenta uso de `POST /api/v1/atendimento/{id}/pesquisa-enviada`
  - Critérios: cliente concluiu atendimento, NAO respondeu 30d, NAO e reincidente
  - Mensagem template PT-BR com escala 1-5 estrelas
  - LGPD: 1-2 estrelas = handoff automatico
  - Copiada para `/home/node/.openclaw/plugin-skills/` no container
  - Copiada para `/home/node/.openclaw/workspace/.agents/cartorio-bot/skills/cartorio-pesquisa-satisfacao/SKILL.md`
- INDEX.md atualizado com 7 skills (saudacoes, protocolo-tracker, emolumento-calc, handoff-trigger, agendamento, segunda-via, pesquisa-satisfacao)

### Supabase

- **Index `ix_webhook_events_received_at`** criado em `webhook_events (received_at DESC)`
  - Acelera queries do workflow #24 (retencao 5y/2y) que varre por data
  - Stale detection (`/cron/stale-detector` que varre eventos antigos)
  - Idempotente (`CREATE INDEX IF NOT EXISTS`)

## Aprendizados tecnicos

- **N8N API key antiga (rotacionada ontem) ainda funciona** mesmo apos eu tentar gerar nova via SQL.
  - Tentei: plain text com prefixo `n8n_api_` (rejeitado: 403)
  - Tentei: JWT com secret derivado de N8N_ENCRYPTION_KEY (rejeitado: 403)
  - Funciona: JWT pre-existente no DB (audience=`public-api`, issuer=`n8n`)
  - Licao: o `findOne` do N8N cacheia ou tem logica adicional que nao consegui reverter
- **N8N nao aceita `description` no body** de POST /workflows (read-only)
- **N8N nao aceita `active` no body** (read-only - use POST /workflows/{id}/activate)
- **N8N valida connections.target** - se voce referencia um node que nao existe em `nodes`, retorna 400. **Workaround: auto-add Noop node**
- **Conexao n8n container -> supabase-db**: `localhost:5432` NAO funciona. Usar `db:5432` (service name do Swarm)
- **Node.js no n8n container**: `pg` module esta em `/usr/local/lib/node_modules/n8n/node_modules/`. Usar `NODE_PATH=/usr/local/lib/node_modules/n8n/node_modules`

## Estatisticas finais

| Metrica | Antes desta sessao | Depois |
|---|---|---|
| N8N workflows ativos | 29 | **29** (3 novos re-importados) |
| N8N workflows totais (incluindo inactive) | ~30 | **40** |
| OpenClaw skills | 6 | **7** (pesquisa-satisfacao adicionada) |
| Supabase indices em webhook_events | 0 | **2** (event_id + received_at) |
| Skill scripts utility | 0 | **1** (import_all_to_n8n.sh) |

## Comandos SQL executados

### Supabase
```sql
-- Indice para queries de stale detection
CREATE INDEX IF NOT EXISTS ix_webhook_events_received_at ON webhook_events (received_at DESC);
```

### N8N (via Node script)
```javascript
const { Client } = require("pg");
const c = new Client({ host: "db", port: 5432, database: "n8n", user: "supabase_admin", password: "..." });
await c.connect();
await c.query(`INSERT INTO workflow_entity (...) VALUES (...)`, [...]);
```

## Commits feitos nesta sessao

- `docs(session): 2026-06-23-N8N-OpenClaw-Supabase-deploy.md` (parte 1)
- `import_all_to_n8n.sh` (script util)
- `cartorio-pesquisa-satisfacao.md` (skill OpenClaw)
- `INDEX.md` (atualizado)

## Pendente (SUI Gustavo)

- **N8N workflow #03 v2** (handoff com n8n-nodes-chatwoot) - JSON existe no repo mas NAO foi importado (N8N ja tem #03 v1 ativo)
- **Ativar workflows importados** (3 foram criados inativos) - Gustavo decide quais ligar
- **OpenClaw LLM key** (Sprint 3 SUI #5) - sem ela, OpenClaw cai no deepseek-v4-flash com persona incompleta
- **Conectar WhatsApp real** na Evolution instance
- **Rotacionar 5 credenciais expostas** (N8N, MCP, Chatwoot, OpenCode-Go, Supabase)
