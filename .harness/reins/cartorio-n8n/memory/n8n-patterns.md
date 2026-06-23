---
description: Padroes arquitetonicos de N8N - MCP server lifecycle, roadmap de migracao httpRequest->node oficial, regra de ouro staging vs prod. Carregar quando for criar/editar WF ou planejar migracao de integracao.
---

# N8N Patterns

## MCP server vazio = client nao consome

Node core `@n8n/n8n-nodes-langchain.mcpTrigger` so EXPOSE o path do servidor MCP (ex: `mcp-cartorio`). Para um workflow cliente usar `n8n-nodes-mcp` client, o servidor precisa ter **tools registradas em nodes subsequentes**.

No cartorio: WF `kTZUoh8ejvGxT8m9` MCP - Server Tools (T22) v2 tem so o trigger → servidor existe mas esta VAZIO → client nao acha tools → fluxo quebra.

**Regra**: antes de migrar WF ativo (#12 Chatbot) de `httpRequest` para `n8n-nodes-mcp` client, **PRIMEIRO popular o servidor MCP com as tools** que serao chamadas.

## Roadmap de migracao httpRequest → node oficial

```
PHASE 0 — fix DNS/host typos ANTES de criar credencial UI (5min, evita retrabalho)
PHASE 1 — popular servidor/dependência vazia (MCP server, etc.) em isolamento, gate = health check
PHASE 2 — staging clone do WF ativo (NAO mexer no prod), shadow mode paralelo 24h
PHASE 3 — promote staging, rollback = toggle active em <30s
PHASE 4 — cleanup apos 7 dias estaveis (deletar staging + httpRequest archive)
```

- WF original ativo NUNCA eh deletado antes de 7 dias com WF novo estavel
- Toggle `active=false + true` = rollback instantaneo
- WFs INATIVOS (ENHANCED, drafts) viram SANDBOX — renomear pra `<num>_staging_<feature>` antes de usar como base de teste

## Regra de ouro: arquivos locais ≠ prod

OS ARQUIVOS em `infra/n8n-workflows/` sao STAGING/TEMPLATES (`id=null`). NAO sao o que esta em prod. Prod = export via `n8n export:workflow --all --id=X`.

Exemplos reais descobertos (2026-06-23):
- WF #12 ativa no N8N = `WuQAi2ttarGGdPyD` ('12 - Chatbot LLM End-to-End (PII + OpenCode-Go)') USA `httpRequest 'POST api/integrations/opencode/test'`. NAO usa MCP.
- Arquivo local `12-chatbot-llm-mcp.json` (com drift `placa`->`placa_veiculo`) eh STAGING que NUNCA foi deployed. Servidor MCP `kTZUoh8ejvGxT8m9` tem so trigger, sem tools.
- WF #03 ativa (OQRIOVHcOjpkQ0Of) USA `httpRequest 'POST chatwoot.2notasudi.com.br/...'`. Arquivo local `03-handoff-human-chatwoot.json` (com node oficial `n8n-nodes-chatwoot.Chatwoot`) eh STAGING nao deployed.

**Regra**: ANTES de editar QUALQUER arquivo em `infra/n8n-workflows/`, validar qual WF ID eh o de prod (via `n8n export:workflow --id=X --pretty`). Editar staging pensando que eh prod = mudanca nunca chega em prod.

## Cross-rein alignment: esperar merge em master

Quando LGPD-by-design alignment pedido (ex: drift de label), **ESPERAR plano cross-rein ser mergeado em master primeiro**. Alinhar com referencia nao-commitada = rework.

Em 2026-06-23: drift `placa` -> `placa_veiculo` no PII scrubber JS do N8N vs backend Python. Fix depende de PR LGPD-015 (cartorio-dev) + cartorio-lgpd review.

## Master real referencia

Master real = `dff1bb9` (avancou alem de `d030e9c` e `3b85746` que foram citados em handoffs). SEMPRE `git log --oneline -5 master` antes de comitar pra confirmar referencia. `d030e9c` e `3b85746` NAO sao master head — sao referencias de handoff stale.