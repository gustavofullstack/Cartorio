
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

### PII signal flow N8N vs backend (LGPD P0.1, 2026-06-23)
Type: architecture

Mapa de quem produz/consome pii_blocked/needs_human_handoff/handoff_reason hoje:

N8N WF #12 (12-chatbot-llm-mcp.json, ATIVO):
- Faz PII scrub INLINE em Code node JS (espelho de backend/app/services/pii.py).
- Decide Response gera shape {pii_blocked, pii_redaction_count, needs_human_handoff, handoff_reason, model, tokens_in/out, latency_ms, provider, transport}.
- RespondToWebhook retorna ESSE shape para o caller (OpenClaw/Evolution).
- NAO chama backend /api/v1/webhook/evolution. LLM eh local via MCP tool.

N8N WF #03 (03-handoff-human-chatwoot.json, ATIVO):
- Recebe {sender, message.text, reason, message_id, instance, canal} no body.
- 'reason' vem no REQUEST, nao do response de #12. N8N NAO acopla #12 -> #03.
- Cria conversation + message no Chatwoot (node oficial n8n-nodes-chatwoot v1.0.2).

backend router.py:439 webhook_evolution:
- Faz PII scrub, salva conversas.handoff_to_human=True + handoff_reason='PII detectada' no DB.
- MAS return em router.py:631 eh MENTIRA: {status:ok, response, scrubbed} — perdeu pii_blocked/needs_human_handoff/handoff_reason.
- Esse endpoint NAO eh chamado pelo N8N. Chamado por Evolution API direto (caminho paralelo).

T19 (WebSocket atendimentos):
- backend/app/api/v1/ws/atendimentos.py existe + RedisBus cartorio:atendimentos.
- 0 publishers em runtime, 0 consumers N8N. Canal ORFÃO (construido mas nao usado).

Regra: quando audit LGPD apontar gap de signal, SEMPRE mapear (1) quem produz o signal, (2) quem consome, (3) onde o signal morre no caminho. N8N pode estar OK enquanto backend mente, ou vice-versa. Em cartorio: N8N OK, backend mente, T19 descoberto.

Regra: o test test_payload_com_pii_bloqueia_e_marca_pii_blocked (tests/test_webhook_evolution_e2e.py:170) ja espera pii_blocked no response. Fix do router.py:631 (~10 linhas) recupera o contrato do test.

Regra: o PII Scrubber JS do N8N diverge do backend em 1 label — backend usa 'placa_veiculo', N8N usa 'placa'. Backend eh a fonte de verdade. Se for comparar findings, normalizar.
