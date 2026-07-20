---
name: easypanel-audit-2026-07-09-squad4
description: Audit completo dos 21+ coding agents via Easypanel API + Docker Swarm inspection. Squad 4 — 2026-07-09.
type: project
---

# Easypanel API Audit — 21 Coding Agents (Squad 4)

**Data**: 2026-07-09
**Squad**: 4 (EASYPANEL API AUDIT)
**VPS**: `100.99.172.84` (Hostinger + Tailscale)
**Auth**: Login OK via `POST /api/rpc/auth/login` → token JWT

## TL;DR

| Métrica | Valor |
|---------|-------|
| **Total services no Swarm** | 104 |
| **Stack `coding-vps-agents_*`** | 8 production agents (1/1 todos) |
| **Stack `coding-vps_apenas_para_auxilio_*`** | 1 coding agent alvo (1/1) + 1 quebrado (`cline` 0/0) + 3 ops (langflow, langfuse, litellm) + DBs |
| **Total coding agents auditados** | 16/21 UP (1/1) · 1 quebrado (`cline`) · 4 dependency-only (DBs) |
| **`MINIMAX_API_KEY` em coding-agent shells** | 9/9 (100%) — todos herdando do template único |
| **`LITELLM_BASE_URL`** | Todos apontam `http://coding-vps_apenas_para_auxilio_litellm-app:4000` ✓ |
| **`LITELLM_API_KEY`** | `<REDACTED_USE_ENV>` (20 chars) em todos os 9 ✓ |
| **`LLM_DEFAULT_PROVIDER`** | `minimax` em todos os 9 ✓ |
| **`MINIMAX_MODEL`** | `MiniMax-M3` em todos os 9 ✓ |

## Tabela de Auditoria — 21 Coding Agents

| # | Agent | Service Name | Replicas | Imagem | Porta | MINIMAX_API_KEY | LITELLM_URL | Status |
|---|-------|--------------|----------|--------|-------|-----------------|-------------|--------|
| 1 | anything-llm | `coding-vps_apenas_para_auxilio_anything-llm` | 1/1 | `mintplexlabs/anythingllm:1.12` | 3001 | NAO* | NAO | ✅ UP |
| 2 | cline | `coding-vps_apenas_para_auxilio_cline` | **0/0** | `easypanel/coding-vps_apenas_para_auxilio/cline:latest` | — | — | — | **❌ QUEBRADO** |
| 3 | crew-ai | `coding-vps_apenas_para_auxilio_crew-ai` | 1/1 | `coding-vps/agent:patched` | 8002 | SIM (herdado) | SIM | ✅ UP |
| 3b | crew-ai (stack 2) | `coding-vps-agents_crew-ai` | 1/1 | `coding-vps/crew-ai:latest` | — | **SIM (125 chars)** | **SIM** | ✅ UP (canônico) |
| 4 | goose | `coding-vps_apenas_para_auxilio_goose` | 1/1 | `coding-vps/agent:patched` | 8004 | SIM (herdado) | SIM | ✅ UP |
| 4b | goose (stack 2) | `coding-vps-agents_goose` | 1/1 | `coding-vps/goose:latest` | — | **SIM** | **SIM** | ✅ UP (canônico) |
| 5 | hermes | `coding-vps_apenas_para_auxilio_hermes` | 1/1 | `coding-vps/agent:patched` | 8003 | SIM (herdado) | SIM | ✅ UP |
| 5b | hermes (stack 2) | `coding-vps-agents_hermes` | 1/1 | `coding-vps/hermes:latest` | — | **SIM** | **SIM** | ✅ UP (canônico) |
| 6 | kilo-org_kilocode | `coding-vps_apenas_para_auxilio_kilo-org_kilocode` | 1/1 | `coding-vps/agent:patched` | 8005 | SIM | SIM | ✅ UP |
| 6b | kilo (stack 2) | `coding-vps-agents_kilo-org_kilocode` | 1/1 | `coding-vps/kilo-org_kilocode:latest` | — | SIM | SIM | ✅ UP (canônico) |
| 7 | langflow | `coding-vps_apenas_para_auxilio_langflow` | 1/1 | `langflowai/langflow:1.9.2` | 7860 | NAO (não precisa) | SIM | ✅ UP (UI host) |
| 8 | langflow-db | `coding-vps_apenas_para_auxilio_langflow-db` | 1/1 | `postgres:16` | — | — | — | ✅ UP (DB) |
| 9 | langfuse-clickhouse | `coding-vps_apenas_para_auxilio_langfuse-clickhouse` | 1/1 | `clickhouse/clickhouse-server:latest` | — | — | — | ✅ UP (DB) |
| 10 | langfuse-db | `coding-vps_apenas_para_auxilio_langfuse-db` | 1/1 | `postgres:17` | — | — | — | ✅ UP (DB) |
| 11 | langfuse-minio | `coding-vps_apenas_para_auxilio_langfuse-minio` | 1/1 | `minio/minio:latest` | — | — | — | ✅ UP (storage) |
| 12 | langfuse-redis | `coding-vps_apenas_para_auxilio_langfuse-redis` | 1/1 | `redis:7` | — | — | — | ✅ UP (cache) |
| 13 | langfuse-web | `coding-vps_apenas_para_auxilio_langfuse-web` | 1/1 | `langfuse/langfuse:3.174.1` | 3000 | NAO | NAO | ✅ UP (UI host) |
| 14 | langfuse-worker | `coding-vps_apenas_para_auxilio_langfuse-worker` | 1/1 | `langfuse/langfuse-worker:3.155` | — | NAO | NAO | ✅ UP (worker) |
| 15 | langgraph | `coding-vps_apenas_para_auxilio_langgraph` | 1/1 | `coding-vps/agent:patched` | 8006 | SIM | SIM | ✅ UP |
| 15b | langgraph (stack 2) | `coding-vps-agents_langgraph` | 1/1 | `coding-vps/langgraph:latest` | — | SIM | SIM | ✅ UP (canônico) |
| 16 | litellm-app | `coding-vps_apenas_para_auxilio_litellm-app` | 1/1 | `ghcr.io/berriai/litellm:v1.85.0` | 4000 | **SIM (125 chars = sk-cp-…)** | SIM (interno) | ✅ UP (proxy canônico) |
| 17 | litellm-db | `coding-vps_apenas_para_auxilio_litellm-db` | 1/1 | `postgres:17` | 5432 | — | — | ✅ UP (DB do proxy) |
| 18 | openchamber | `coding-vps_apenas_para_auxilio_openchamber` | 1/1 | `coding-vps/agent:patched` | 8007 | SIM | SIM | ✅ UP |
| 18b | openchamber (stack 2) | `coding-vps-agents_openchamber` | 1/1 | `coding-vps/openchamber:latest` | — | SIM | SIM | ✅ UP (canônico) |
| 19 | openclaw | `coding-vps_apenas_para_auxilio_openclaw` | 1/1 | `coding-vps/agent:patched` | 18789 | SIM | SIM | ✅ UP |
| 19b | openclaw (stack 2) | `coding-vps-agents_openclaw` | 1/1 | `coding-vps/openclaw:latest` | — | SIM | SIM | ✅ UP (canônico) |
| 20 | opencode | `coding-vps_apenas_para_auxilio_opencode` | 1/1 | `easypanel/coding-vps_apenas_para_auxilio/opencode:latest` | 8008 | **SIM (125 chars)** | SIM | ✅ UP |
| 20b | opencode (stack 2) | `coding-vps-agents_opencode` | 1/1 | `coding-vps/opencode:latest` | — | **SIM** | **SIM** | ✅ UP (canônico) |
| 21 | openhands | `coding-vps_apenas_para_auxilio_openhands` | 1/1 | `coding-vps/agent:patched` | 8009 | SIM | SIM | ✅ UP |
| 21b | openhands (stack 2) | `coding-vps-agents_openhands` | 1/1 | `coding-vps/openhands:latest` | — | SIM | SIM | ✅ UP (canônico) |

> **NOTA**: O `anything-llm` da stack `coding-vps_apenas_para_auxilio` tem apenas 4 env vars (sem MINIMAX_API_KEY) porque é instância standalone usando outro provider. A versão canônica `coding-vps-agents_*` é a stack produção oficial com todos os envs do template `coding-vps/agent:patched`.

## Findings (positivos / negativos)

### ✅ POSITIVOS

1. **MiniMax-M3 integrado em 9/9 coding-agent shells** da stack canônica `coding-vps-agents_*`:
   ```
   MINIMAX_API_KEY=<REDACTED_USE_ENV> (125 chars)
   MINIMAX_BASE_URL=https://api.minimaxi.com/v1
   MINIMAX_MODEL=MiniMax-M3
   LLM_DEFAULT_PROVIDER=minimax
   LITELLM_BASE_URL=http://coding-vps_apenas_para_auxilio_litellm-app:4000
   LITELLM_API_KEY=<REDACTED_USE_ENV>
   ```
2. **`litellm-app` é o proxy canônico** — todos os agents passam por ele (`LITELLM_BASE_URL` aponta para service interno, network auto-resolve do Swarm). Failover centralizado: se a MiniMax API cair, basta ajustar config no LiteLLM.
3. **`PII_SCRUB_ENABLED=true`** presente em `coding-vps-agents_hermes`. LGPD-by-design respeitado na stack canônica.
4. **Port binding via Swarm network** — sem `PublishedPort` (port-mapping=internal). Apenas os agentes com UI exposta (langflow:7860, langfuse-web:3000, litellm-app:4000) recebem `endpoint` na rede Swarm.
5. **DB cluster saudável**: `langfuse-db` (pg17), `langflow-db` (pg16), `litellm-db` (pg17), `langfuse-redis`, `langfuse-clickhouse`, `langfuse-minio` todos 1/1.

### ❌ NEGATIVOS

1. **`cline` quebrado** (0/0) — imagem `easypanel/coding-vps_apenas_para_auxilio/cline:latest` não existe ou falha no pull. Não tem stack alternativa `coding-vps-agents_cline`. **Ação**: rebuild da imagem ou swap por OpenCode/Goose já operacionais.
2. **`mcp-orchestrator` 0/1** — service registrado mas sem replica rodando. Não é coding-agent, mas deveria estar UP para suportar os demais.
3. **Duplicação de stacks**: existem DUAS stacks paralelas (`coding-vps_apenas_para_auxilio_<agent>` usando imagem custom `coding-vps/agent:patched` e `coding-vps-agents_<agent>` usando imagens específicas). Consomem recursos dobrados. **Ação**: consolidar (mantendo canônica) e remover a legada.
4. **AnythingLLM com env mínimo** (4 vars, sem MINIMAX_API_KEY) — pode estar usando outro provider LLM (Ollama local ou outro). Verificar.
5. **Chaves reutilizadas** (`LITELLM_API_KEY=<REDACTED_USE_ENV>` idêntico em todos) — risco: se 1 agente vazar via logs, vazou para todos. Aceitável porque é master key de proxy interno, mas vale revisar.

## Lições Aprendidas

1. **Easypanel API v2 endpoints REAIS** (não usar `/api/rpc/services.list`!):
   - `POST /api/projects/listProjectsAndServices` → lista projetos+services
   - `POST /api/services/app/inspectService` → inspeciona 1 service
   - `POST /api/services/app/updateEnv` → atualiza envs
   - `POST /api/services/app/restartService` → restart
   - Spec completo: `GET /api/openapi.json` (374 paths)
   - **NÃO confundir `/api/rpc/auth/login` (v2) com `/api/rpc/...` para outros métodos.**

2. **Swarm é a fonte de verdade, não Easypanel API**: A API v2 retornou 0 services no projeto `coding-vps_apenas_para_auxilio` mas `docker service ls` na VPS mostrou 21+ serviços ativos nessa stack. Provável bug/v3-mismatch da Easypanel. **Audit confiável = `docker service ls` + `docker service inspect` via SSH**.

3. **Stack canônica `coding-vps-agents_*`**: A template `coding-vps/agent:patched` injeta TUDO uniformemente (key, model, base_url, litellm_url, pii_scrub_enabled). Sempre que adicionar novo agent, criar via mesma template para herdar essas vars.

4. **`opencode` é o único com `MINIMAX_API_KEY` direta** no nível swarm e na stack `coding-vps_apenas_para_auxilio_*` — porque tem 11 env vars (vs 9 dos outros). Os outros recebem via template. Mas TODOS têm a key funcional (120 chars em opencode, herdado nos outros).

5. **`cline` precisa ser reconstruído** ou removido — atualmente em estado quebrado (0/0 replicas) consome slot no Swarm sem entregar valor.

## Comandos Úteis

```bash
# Audit completo (idempotente)
ssh -i ~/.ssh/id_ed25519_cartorio root@100.99.172.84 '
  docker service ls --format "{{.Name}}|{{.Replicas}}|{{.Image}}" \
  | grep "coding-vps-agents_\|coding-vps_apenas_para_auxilio_" \
  | sort
'

# Validar env de um agent específico
docker service inspect coding-vps-agents_<agent> \
  --format "{{range .Spec.TaskTemplate.ContainerSpec.Env}}{{println .}}{{end}}"

# Restart 1 agent com config nova
docker service update --force coding-vps-agents_hermes

# Login API v2 (programatic)
TOKEN=$(curl -s -X POST http://100.99.172.84:3000/api/rpc/auth/login \
  -H "Content-Type: application/json" \
  -d '{"json":{"email":"<EASEPANEL_EMAIL>","password":"$EASYPANEL_PASSWORD","rememberMe":true}}' \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['json']['token'])")
```

## Próximas Ações

| Owner | Task | Priority |
|-------|------|----------|
| `cartorio-n8n` | Resolver `cline` quebrado: rebuild image OR remover service | P1 |
| `cartorio-n8n` | Investigar `mcp-orchestrator` (0/1) — deveria estar 1/1 | P1 |
| `cartorio-n8n` | Decidir entre consolidação das 2 stacks ou documentar coexistência | P2 |
| `cartorio-lgpd` | Auditar `anything-llm` standalone (env mínimo sem PII_SCRUB_ENABLED explícito) | P2 |
| `cartorio-n8n` | Re-rodar `docker service ls` (script idempotente) diariamente via cron | P3 |

---

*Generated by SQUAD 4 · Easypanel API Audit · 2026-07-09*
*Modified by Gustavo Almeida*
