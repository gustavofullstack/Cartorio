
### N8N workflow audit pattern (2026-06-23)
Type: workflow

Para auditar TODOS os workflows n8n via CLI sem usar a API (que exige credenciais UI):
```bash
ssh cartorio "docker exec \$(docker ps --format '{{.Names}}' | grep '^cartorio_n8n\.' | head -1) n8n export:workflow --all --pretty --output=/tmp/n8n-workflows.json"
ssh cartorio "docker cp \$(docker ps --format '{{.Names}}' | grep '^cartorio_n8n\.' | head -1):/tmp/n8n-workflows.json /tmp/"
scp cartorio:/tmp/n8n-workflows.json /tmp/
```

`/home/node/.n8n/config` so tem a `encryptionKey`, nao tem basic auth. A API key (env `CARTORIO_API_KEY`) bate 401 — entao CLI export:workflow e o caminho confiavel.

Depois: `jq '.[] | {id, name, active, nodes: [.nodes[].type] | unique}'` para inspecionar.

### MCP server vazio = client nao pode consumir (2026-06-23)
Type: pitfall

O n8n trigger `@n8n/n8n-nodes-langchain.mcpTrigger` (core) so EXPOSE o path do servidor MCP (ex: `mcp-cartorio`). Para um workflow cliente usar `n8n-nodes-mcp` client, o servidor precisa ter tools registradas em nodes subsequentes. No cartorio: WF `kTZUoh8ejvGxT8m9` MCP - Server Tools (T22) v2 tem 1 no SO (o trigger) - significa que o servidor existe mas esta VAZIO.

Regra: antes de migrar um workflow ativo (#12 Chatbot) de `httpRequest` para `n8n-nodes-mcp` client, PRIMEIRO popular o servidor MCP com as tools que serao chamadas. Senao o client nao acha tools para invocar e o fluxo quebra.

### N8N migration roadmap pattern (2026-06-23)
Type: workflow

Para migrar WF n8n ativo de httpRequest para node oficial (community):
PHASE 0 — fix DNS/host typos ANTES de criar credencial UI (5min, evita retrabalho)
PHASE 1 — popular servidor/dependência vazia (MCP server, etc.) em isolamento, gate = health check
PHASE 2 — staging clone do WF ativo (NÃO mexer no prod), shadow mode paralelo 24h
PHASE 3 — promote staging, rollback = toggle active em <30s
PHASE 4 — cleanup após 7 dias estáveis (deletar staging + httpRequest archive)

Regra: WF original ativo NUNCA é deletado antes de 7 dias com WF novo estável. Toggle active=false + true = rollback instantâneo.

Regra: workflows INATIVOS (ENHANCED, drafts) viram SANDBOX, não são deletados nem promovidos direto. Renomear pra "<num>_staging_<feature>" antes de usar como base de teste.
