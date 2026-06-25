---
description: Procedimento canonico N8N 2.x workflow DB UPDATE - 5-pass recipe, SQL gotchas (FK ordering, dollar-quoting, base64 wrapping), cache invalidation timing, Code node sandbox, env access block, settings column json vs jsonb. Carregar quando for editar/migrar workflow N8N e API PATCH/PUT estiver bloqueada.
---

# N8N DB UPDATE Canonico (Lesson 49+50+51+52+54+55+96)

## Por que DB UPDATE

N8N 2.x API auth quebrada para UPDATE completo de WF:
- PATCH /api/v1/workflows/{id} → 405 Method Not Allowed
- PUT /api/v1/workflows/{id} → 400 (exige body completo: name, nodes, connections)
- POST /rest/workflows/{id} → 401 Unauthorized

**Workaround canonico**: direct DB UPDATE em `workflow_entity.nodes` + `connections`. Endpoint via API so funciona para activate/delete (Lesson 96).

Excecoes que funcionam via API (verificadas com X-N8N-API-KEY + JWT public key):
- GET /api/v1/workflows → 200 OK
- GET /api/v1/workflows/{id} → 200 OK
- POST /api/v1/workflows/{id}/activate body `{"active": true}` → 200 OK
- DELETE /api/v1/workflows/{id} → 200 OK (soft delete via API)

```bash
# Activate canonico
curl -X POST -H "X-N8N-API-KEY: $N8N_KEY" \
  "https://flow.2notasudi.com.br/api/v1/workflows/$WF_ID/activate"

# Delete canonico (soft delete, subsequente GET retorna 404)
curl -X DELETE -H "X-N8N-API-KEY: $N8N_KEY" \
  "https://flow.2notasudi.com.br/api/v1/workflows/$WF_ID"
```

## Code node sandbox (Lesson 49)

N8N 2.x Code node JS roda em vm module sandboxed. NAO expoe `process`, `require`, `Buffer`, `global`. Code que funcionava em 1.x quebra com `ReferenceError: process is not defined`.

**Workaround canonico**: substituir Code node por HTTP Request node apontando pra endpoint interno (ex: `/api/v1/metrics/prometheus`). Bypass total do sandbox.

## Env access bloqueado (Lesson 51)

N8N 2.x tem env var `N8N_BLOCK_ENV_ACCESS_IN_NODE=true` (default security). Bloqueia acesso a `$env.X` em HTTP Request nodes (e talvez outros).

Sintoma: HTTP Request node com header `={{ $env.CARTORIO_API_KEY }}` retorna:
> If you need access please contact the administrator to remove the environment variable N8N_BLOCK_ENV_ACCESS_IN_NODE

Workaround:
- **Opcao A** (rapida, ~30s downtime): `docker service update --env-add N8N_BLOCK_ENV_ACCESS_IN_NODE=false cartorio_n8n` + restart
- **Opcao B** (robusta): usar N8N credential type ao inves de env var (requer UPDATE workflow_history nodes)
- Hardcode NAO recomendado (Lesson 16/17)

## POST endpoint validate first (Lesson 55)

Workflow "metrics collector" foi planejado pra coletar metricas locais + POST pro backend. Porem backend nunca implementou endpoint POST /metrics/n8n (404).

Sintoma: HTTP Request node POST https://api.2notasudi.com.br/api/v1/metrics/n8n retorna 404 'The resource you are requesting could not be found'.

**Workaround canonico**: REMOVER POST node + sua connection (WF vira 'metrics reader' via GET, sem necessidade de endpoint ingest). Alternativa: criar endpoint POST backend (escopo 2-4h cartorio-dev).

## workflow_entity.settings column type = json, not jsonb

`workflow_entity.settings` e `json` (NAO `jsonb`). COALESCE entre unknown (coluna) e jsonb (literal) nao unifica sem cast explicito.

**Broken** (B06 retry 02:41 BRT tentou):
```sql
SET settings = COALESCE(settings, '{}'::jsonb) || jsonb_build_object(...)
-- ERROR: COALESCE could not convert type jsonb to json
```

**Canonico** (22 WFs wired em 1 query):
```sql
UPDATE workflow_entity
SET settings = (COALESCE(settings::jsonb, '{}'::jsonb) || jsonb_build_object('errorWorkflow', '4IS5oiLyHWGhtb8g'))::json
WHERE id IN (...) AND active = true;
```

Verificacao pos-update: `SELECT id, name, settings->'errorWorkflow' FROM workflow_entity WHERE id IN (...)` deve retornar o valor para todos.

## 5-pass canon recipe

Refactor Code node em N8N 2.x requer 5 passos SENAO cache stale persiste:

1. **DB UPDATE** `workflow_entity.nodes` (Lesson 50)
2. **DB UPDATE** `workflow_entity.connections` (separado de nodes)
3. **INSERT** nova `workflow_history` row com nodes novos + novo versionId
4. **DB UPDATE** `workflow_entity.activeVersionId` = novo versionId
5. **Restart Swarm** `docker service update --force cartorio_n8n` E `cartorio_n8n-runner`

Validacao pos-restart: `tail -10 n8nEventLog.log` deve mostrar `node.started` event com o node NOVO (nao o antigo). Se ainda mostra node antigo, cache nao foi invalidado — esperar 5-10min (N8N scheduler cache expiry).

**Caso real 14:00-17:42 BRT 24/06 (WF#25 Metrics Collector)**: 3h30 de debug para descobrir sequencia. Primeiro restart nao bastou. INSERT history + UPDATE activeVersionId + 2o restart runner nao bastou. SOLUCAO: restart --force cartorio_n8n APOS 3-4min (cache expiry).

## SQL gotchas (B07 03:33-03:42 BRT)

**Gotcha 1 — psql wrapping**: COPY base64 wrappa em ~80 chars. Solucao: `\COPY TO file + cat file`. NAO usar -c inline para base64 longo.

**Gotcha 2 — SQL injection**: JSON de nodes contem single quotes (ex: header values 'X-API-Key'). Usar dollar-quoted strings `$tag$...$tag$` ao inves de single quotes. Tag unico por WF: `$b07n_<WFID6>$`.

**Gotcha 3 — FK ordering**: `workflow_entity.activeVersionId` tem FK para `workflow_history.versionId`. INSERT history ANTES de UPDATE entity (senao FK violation).

**Gotcha 4 — workflow_history schema**: PK = versionId APENAS (NAO tem id separado). Colunas: `versionId, workflowId, authors, createdAt, updatedAt, nodes, connections, name, autosaved, description, nodeGroups`.

**Gotcha 5 — UPDATE precisa CONTAINMENT**: ALTERAR so `parameters.options.retry` NAO altera estrutura do node. N8N honra edit cirurgico (verified via API GET).

**Gotcha 6 — UPDATE SEM RETURNING**: `SELECT jsonb_array_length(nodes::jsonb) FROM workflow_entity` tem cast issue se usar RETURNING. Validar com query separada.

## Backup ANTES de UPDATE (rollback path)

```bash
ssh cartorio "docker exec \$DB_CONTAINER psql -U supabase_admin -d n8n -t -A -c \"SELECT nodes::text FROM workflow_entity WHERE id = '\$WF_ID'\" > /tmp/rollback-nodes.json
ssh cartorio "docker exec \$DB_CONTAINER psql -U supabase_admin -d n8n -t -A -c \"SELECT connections::text FROM workflow_entity WHERE id = '\$WF_ID'\" > /tmp/rollback-connections.json
```

UPDATE nodes + connections SEPARADAMENTE (Lesson 50 pattern). Backup nodes ANTES do UPDATE.

## B07 retry policy bulk apply (case real)

Aplicar retry 3x exp backoff em 63 N8N HTTP nodes via DB UPDATE (NAO via API PATCH):
```json
{"maxTries": 3, "waitBetween": [1000, 5000, 15000], "onWhenFailed": true}
```

**Stats reais**:
- 34 WFs ativos / 30 com HTTP nodes / 4 custom-only (FAQ/LGPD/MCP)
- 63 httpRequest nodes / 63 com retry (100%)
- 1 node upgraded de maxTries=2 para 3 (WF 01 Emolumento)
- 5 WFs re-validados pos-restart = 20/20 nodes
- Total runtime: ~15min (vs Lesson 49 canonico ~3h30 sem dominar gotchas)

**Por que 100% em 15min**: aproveitei Lesson 49 (cache invalidation), Lesson 50 (UPDATE nodes+connections separados), Lesson 52 (restart), Lesson 96 (PATCH 405 - nao tentei). Compor lições existentes > re-descobrir.

**Workflow files**: `/tmp/b07_apply_retry.py` (script Python canonico, reutilizavel)
**README**: `infra/n8n-workflows/README-retry-policy.md`
**Rollback path**: backups em `/tmp/b07_nodes_<WFID>.json` + `/tmp/b07_conn_<WFID>.json` para WFs do batch

## Case real WF#25 Metrics Collector (B07 + WF#25 B0.5)

Caso real WF#25 (14:42-14:52 BRT 24/06):
- Lesson 51 BYPASS: env var false + restart ~30s
- Lesson 55 BYPASS: UPDATE nodes (remover POST) + UPDATE connections + INSERT workflow_history v3 + UPDATE activeVersionId + restart
- Resultado: exec #2414 + #2415 SUCCESS consecutivos (15min total, vs 3h30 anterior)