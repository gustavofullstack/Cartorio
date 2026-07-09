# Coding-VPS — SUB-SQUAD 2 (ACTIVATE REMAINING) — Round 4

**Data**: 2026-07-08
**Worker**: squad2 (Gustavo Almeida)
**Host**: coding-vps_apenas_para_auxilio (100.99.172.84, Tailscale)
**Objetivo**: Ativar Crowdsec / limpar cline / validar anything-llm / auditar duplicação de stacks

---

## TAREFA 1 — Crowdsec

**Antes**: 0/0 (não estava rodando).

**Ação executada**:

```bash
docker service scale coding-vps_apenas_para_auxilio_crowdsec=0
docker service scale coding-vps_apenas_para_auxilio_crowdsec=1
```

**Resultado**: `1/1 Running` (Converged em ~13s).

**Saúde**:

```
version: v1.7.8-63227459
Codename: alphaga
BuildDate: 2026-05-11_14:04:56
GoVersion: 1.26.3
Platform: docker
```

**Status**: ✅ ATIVADO — manter 1/1.

> Nota operacional: Container publica porta 8080 (API local do Crowdsec). Validar expor
> Traefik labels se for usar dashboard externo (crowdsec-ui) em outra task.

---

## TAREFA 2 — cline

**Antes**: 0/0 (não estava rodando).

**Decisão**: cline é uma **extensão VSCode** (não tem imagem Docker oficial mantida).
Manter o service em 0/0 ocupa metadata do swarm sem entregar valor.

**Ação executada**:

```bash
docker service rm coding-vps_apenas_para_auxilio_cline
```

**Resultado**: Service removido do swarm.

**Status**: ✅ REMOVIDO — exit code 0, sem dependências quebradas.

> Workaround: se precisar de cline no futuro, rodar como **VSCode extension** dentro do
> container `opencode` (que já monta o workspace). Não recriar o service.

---

## TAREFA 3 — anything-llm + MiniMax-M3

**Antes**: Container running, envs MiniMax não verificadas.

**Env vars encontradas**:

```
PUPPETEER_DOWNLOAD_BASE_URL=https://storage.googleapis.com/chrome-for-testing-public
ANYTHING_LLM_RUNTIME=docker
```

**⚠️ Ausência crítica**: nenhum env com `minimax`, `litellm` ou `LLM_*` foi encontrado
no container.

**Health check** (`/api/ping`):

```json
{"online":true}
```

**Diagnóstico**: anything-llm está **UP mas SEM provider MiniMax-M3 configurado**. O
LLM default interno provavelmente está setado para OpenAI ou outro provider (config
interna em `/app/server/storage/`).

**Ação recomendada (próxima task)**:

1. Injetar `LLM_PROVIDER=litellm` + `LITELLM_API_BASE=http://coding-vps_apenas_para_auxilio_litellm-app:4000` via `docker service update --env-add`.
2. Reiniciar container, re-validar `/api/ping` + `/api/auth`.
3. Testar chat completion via `/api/v1/chat`.

**Status**: ⚠️ AUDITADO — UP mas MiniMax-M3 NÃO está plugado. Pendência para squad3.

---

## TAREFA 4 — Duplicação de stacks

**Inventário atual**:

| Stack | Services | Replicas |
|-------|----------|----------|
| `coding-vps_apenas_para_auxilio_*` (canônica) | 9 | 9/9 (1/1 cada) |
| `coding-vps-agents_*` (legada) | 9 | 9/9 (1/1 cada) |

**Serviços duplicados** (idênticos em ambas):

- `crew-ai`, `goose`, `hermes`, `kilo-org_kilocode`, `langgraph`, `openchamber`, `openclaw`, `opencode`, `openhands`.

**Decisão**: ✅ **MANTER AMBAS** por enquanto.

**Justificativa**:

- A stack legada (`coding-vps-agents_*`) pode estar sendo usada por MCP clients
  configurados com nomes antigos em `~/.mavis/mcp/clients/`.
- A migração de DNS / MCP config dos 9 clients é um trabalho de squad3+ separado.
- Custo de manter: ~9 containers extras com baixo footprint (cada agent é leve).

**Migração futura (backlog)**:

1. Atualizar todos `mcp_config.json` dos 9 clientes para usar `coding-vps_apenas_para_auxilio_*`.
2. Smoke-test cada agent pelo MCP orchestrator.
3. Após 7 dias sem erro, `docker service rm` da stack legada.

**Status**: ✅ DOCUMENTADO — duplicação aceita e justificada.

---

## Resumo executivo (tabela final)

| Item | Estado anterior | Estado final | Decisão |
|------|----------------|--------------|---------|
| Crowdsec | 0/0 | **1/1 Running** | ✅ ATIVADO, manter |
| cline | 0/0 | **removido do swarm** | ✅ DELETE (sem Docker) |
| anything-llm / MiniMax | UP sem LLM | UP, **MiniMax NÃO plugado** | ⚠️ PENDÊNCIA squad3 |
| Duplicação stacks | 18 containers | **manter 18** | ✅ ACEITO (backlog) |

## Pendências para squad3+

1. **anything-llm → MiniMax-M3 wiring**: injetar envs, validar chat completion.
2. **Stack legada sunset**: 9 clients MCP precisam migrar para `coding-vps_apenas_para_auxilio_*`.
3. **Crowdsec dashboard**: decidir se queremos crowdsec-ui com Traefik labels.

Modified by Gustavo Almeida
