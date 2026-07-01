# N8N Operational Snapshot — 2026-07-01 (Turno 42)

> **Status runtime real medido agora** contra `https://flow.2notasudi.com.br`.
> Skill `n8n/SKILL.md` corrigida nesta sessão (MCP URL + MCP_API_KEY dedicada).

## 1. Inventário de Workflows

- **35 totais no servidor** (34 ativos + 1 inativo)
- **Inativo:** `#kZmO4g7w` "03 - Handoff Humano v3 staging" — versão de teste com node oficial Chatwoot
- **31 JSONs exportados em** `infra/n8n-workflows/` (drift de 4 = criados direto no painel UI)

### Ativos por categoria

| Categoria | Count | IDs/Nomes |
|---|---|---|
| Webhook inbound (cliente) | 12 | `evo-in`, `boas-vindas`, `consulta-protocolo`, `consulta-emolumento`, `criar-protocolo`, `chatbot-llm`, `handoff-human`, `agendar-atendimento`, `welcome-first`, `segunda-via`, `lgpd-esqueci`, `faq`, `lead-novo`, `telegram-cartoriobot` |
| Crons (manutenção) | 14 | `backup-status-5min`, `audit-verify-6h`, `cron-stale-detector`, `daily-cleanup`, `metrics-collector`, `audit-verify-diario`, `monitor-backup-diario`, `audit-snapshot`, `rate-limit-reset`, `health-deep-check`, `monitor-cartorio`, `monitor-openclaw`, `retencao-diaria`, `pesquisa-satisfacao` |
| Sub-workflows | 4 | `error-handler-global`, `alerta-critico`, `openclaw-fallback`, `protocolo-concluido-pdf` |
| Prospecção | 3 | `prospeccao-enrichment`, `prospeccao-followup-d7`, 1 Telegram follow |
| MCP + Integração | 1 | `mcp-server-tools-T22-v2` |
| Boas-vindas LGPD | 1 | `welcome-first-time` (consent) |

## 2. Saúde e Conectividade

| Verificação | Resultado |
|---|---|
| `GET https://flow.2notasudi.com.br/healthz` | ✅ **200 OK** em 0.065s |
| 15/16 webhooks POST com payload vazio | ✅ 15×200 (evo-in, consulta-emolumento, chatbot-llm, handoff-human, boas-vindas, agendar-atendimento, welcome-first, consulta-protocolo, segunda-via, faq, alerta-critico, telegram-cartoriobot, monitor-cartorio, lead-novo) |
| `POST /webhook/lgpd-esqueci` | 🔴 **500 "No Respond to Webhook node found"** |
| DNS `flow.2notasudi.com.br` | ✅ 187.77.236.77 |
| DNS `cartorio-n8n.dfgdxq.easypanel.host` | ✅ 187.77.236.77 (mesmo IP) |
| `cartorio-n8n.dfgdxq.easypanel.host:443` | 🔴 **timeout porta 443** (MCP público off) |
| API `N8N_API_KEY` | ✅ autenticada |
| MCP server endpoint | 🔴 off-line (proxy easypanel de `cartorio-n8n.dfgdxq.easypanel.host`) |

## 3. Bugs / Achados Operacionais

### 🔴 P0 — LGPD Esqueci (workflow `TtD6qS6LCexwhMke`)
- **Sintoma:** POST sem payload → 500 "No Respond to Webhook node found"
- **Causa raiz:** Workflow tem 7 nodes (webhook + extract + 4 HTTPRequests + IF) **MAS nenhum `respondToWebhook`** — qualquer fluxo de erro (cliente inexistente, falha de API) deixa o webhook órfão
- **Impacto:** Cliente pede "esqueça meus dados" via WhatsApp → erro genérico → escrevente recebe reclamação
- **Fix:** Adicionar node `respondToWebhook` final conectado a TODOS os ramos (sucesso + erro). Setar `onError: continueRegularOutput` nos HTTPRequest nodes OU criar ramo paralelo que captura e responde 200 com mensagem amigável.

### 🟡 P1 — MCP server público off-line
- **Sintoma:** Endpoint `https://cartorio-n8n.dfgdxq.easypanel.host/mcp-server/http` timeout porta 443
- **Causa:** Conflito com rota Traefik/proxy do Easypanel — host público tem DNS OK mas serviço MCP interno não está exposto por HTTPS
- **Impacto:** Ferramentas MCP externas não conseguem se conectar ao servidor de tools N8N. O workflow interno `12 - Chatbot LLM End-to-End` usa MCP client e pode estar degradado.
- **Workaround:** usar MCP via rede interna Docker (`http://cartorio_n8n:5678/mcp-server/http`) para tools dentro do mesmo Swarm.

### 🟡 P2 — Drift disco × servidor
- 31 JSONs exportados em `infra/n8n-workflows/` vs 35 workflows no servidor
- 4 não exportados: provavelmente criados via UI pós-sprint (audit, handoff v3 staging, openclaw monitor)
- **Fix:** Rodar `scripts/export_workflows.py` (ou criar) que puxa da API e salva em `infra/n8n-workflows/` antes de cada commit/release.

### 🟢 Info — 96/200 execuções com `status=error, finished=false`
- Confirmei lendo payload: é **bug do N8N 1.x** marcando webhook executions como erro quando não fecha normalmente
- Não impacta produção (zero erros reais `finished=true, status=error`)
- Workaround documentado em Lesson 109 (já na skill)

## 4. Correções aplicadas nesta sessão

1. ✏️ **Skill `n8n/SKILL.md`** corrigida:
   - Tabela top com MCP URL **correta** (`cartorio-n8n.dfgdxq.easypanel.host`) e flag de host timeouting
   - Bloco "MCP Tools via N8N" agora usa `MCP_API_KEY` dedicada, não `N8N_API_KEY`
   - Header `Accept: application/json, text/event-stream` adicionado (MCP spec)

## 5. Próximas ações (lista de tasks — memória)

- [ ] **P0-N8N:** Adicionar `respondToWebhook` no workflow 23 (LGPD Esqueci) — via PUT/UI export. Owner: cartorio-n8n
- [ ] **P1-N8N:** Investigar Easypanel proxy para expor MCP público na 443. Owner: cartorio-devops
- [ ] **P2-N8N:** Exportar workflows faltantes e commitar em `infra/n8n-workflows/`. Owner: cartorio-n8n
- [ ] **P2-N8N:** Atualizar `scripts/export_workflows.py` se não existir. Owner: cartorio-n8n
- [ ] **P3-N8N:** Validar com `12 - Chatbot LLM End-to-End` se MCP client interno funciona pós-recovery Turno 16:05.

## 6. Métricas finais

- 34 workflows ativos ✅
- 15/16 webhooks verificados 200 ✅
- 0 erros reais em 200 execuções inspecionadas ✅
- API autenticada ✅
- Health 200 ✅
- MCP server 🔴 off-line
- 1 bug P0 real (LGPD esqueci sem respondToWebhook)
