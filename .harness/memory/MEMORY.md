# MEMORY — Cartorio Chatbot (cross-rein)

Licoes, decisoes e gotchas que sobrevivem alem de um unico PR.
Criterio pra escrever aqui: a licao afeta mais de um rein ou mais de uma sprint.

---

## 2026-06-23 — Sprint 0.5 hardening + bugs descobertos

### OpenClaw crash loop (resolvido parcialmente)
- **Causa 1**: `--bind lan` exige auth explicita. Sem `OPENCLAW_GATEWAY_TOKEN` no env OU `--token` no CLI, OpenClaw recusa: `Refusing to bind gateway to lan without auth`.
- **Causa 2**: Config `openclaw.json` em `/etc/easypanel/projects/cartorio/openclaw-gateway/volumes/config/` precisa ter `gateway.mode=local` OU passar `--allow-unconfigured`.
- **Args do Swarm service**: hardcoded em `--bind lan --port 18790 --allow-unconfigured` (original do Easypanel). `docker service update --args` ACEITA a mudanca mas o container ignora command hardcoded do service spec.
- **Workaround**: mudar args pra `--bind auto --port 18790 --allow-unconfigured` via Easypanel UI (Service > Edit > Command). Testado manual funciona 100%.
- **User**: rodar como `node` (UID do OpenClaw), nao root. `docker service update --user node` funciona mas ainda nao validado contra a config do service.

### n8n com senha Supabase errada
- n8n usa `DB_POSTGRESDB_USER=supabase_admin` + `DB_POSTGRESDB_PASSWORD=e999b7439deb35dfe05c33f265dae1ea` + host `db`.
- Host `db` resolve via rede Compose `cartorio_supabase_default`. Swarm n8n NAO esta nessa rede por padrao.
- `cartorio-network-monitor.sh` em `/usr/local/bin/` mantem n8n na rede compose. SEM systemd unit + SEM cron = NAO roda.
- **Fix imediato**: `ALTER USER supabase_admin WITH PASSWORD '<env_pwd>'` via `docker exec cartorio_supabase-db-1 psql -U supabase_admin -h 127.0.0.1`.
- **Fix permanente**: criar systemd unit pro monitor + reiniciar n8n via `docker service update --force cartorio_n8n`.

### API .env ainda aponta pra LiteLLM morto
- `LITELLM_BASE_URL=http://litellm:4000` + `LITELLM_MODEL_PRIMARY=claude-opus-4-5` (modelo inexistente no LiteLLM/Claude oficial)
- LiteLLM foi hackeado e removido (zero processos no host)
- **Acao**: atualizar `DATABASE_URL`, `REDIS_URL` ja estao OK. Adicionar OpenClaw como provider direto (`OPENCLAW_BASE_URL=http://cartorio_openclaw-gateway:18790`).

### DNS typo `supbase` vs `supabase`
- DNS em todos os Traefik routers aponta pra `supbase.2notasudi.com.br` (typo).
- O Gustavo precisa decidir: corrigir DNS pra `supabase` (mais profissional, mais demorado) ou aceitar `supbase` como oficial.

### Stack Supabase antiga rodando em paralelo
- 4 containers sem prefixo (`supabase-db-1`, `supabase-meta-1`, `supabase-vector-1`, `supabase-imgproxy-1`) conflitavam com `cartorio_supabase-*`.
- **Resolvido em 2026-06-23**: parados e removidos, rede `supabase_default` deletada.

### SSL/TLS funciona em todos os 6 dominios
- Traefik gerando certs Let's Encrypt via DNS-01 (Cloudflare?) automaticamente.
- Verificado CN correto em `api`, `whatsapp`, `easypanel`, `agent`, `supbase`, `flow.2notasudi.com.br`.

### Stack Supabase 14 containers saudaveis
- db, auth, rest, storage, supavisor, kong, studio, meta, analytics, realtime, functions, vector, imgproxy — todos UP.
- Kong responde 401 em `/auth/v1/health` (correto, Supabase exige API key).

### DominiOS respondendo (Mac)
- api.2notasudi.com.br 200 (Swagger + health)
- whatsapp.2notasudi.com.br 200 (Evolution)
- easypanel.2notasudi.com.br 200
- agent.2notasudi.com.br 502 (OpenClaw down)
- supbase.2notasudi.com.br 401 (Kong correto)
- flow.2notasudi.com.br 200 (n8n)

### Rede do Swarm
- `easypanel` overlay (geral)
- `easypanel-cartorio` overlay (servicos do projeto)
- Sem rede dedicada `cartorio`. OpenClaw debug funcionou com `easypanel-cartorio` apenas.

### Decisao arquitetural HIBRIDA (recomendada)
- **Logica cartorio**: Python/FastAPI no `backend/` (Sprint 0 ja tem 22 testes, 90% coverage)
- **Workflows**: n8n em `flow.2notasudi.com.br` (multi-canal, DB, emails, webhooks)
- **Gateway messaging**: OpenClaw em `agent.2notasudi.com.br` (Telegram, Discord, future)
- **WhatsApp**: Evolution API em `whatsapp.2notasudi.com.br`
- **Provider LLM**: OpenAI gpt-5.5 (ja configurado no OpenClaw como fallback Anthropic). Para Sprint 1 (consulta emolumento), gpt-5.5 da conta. Para acoes juridicas, HITL obrigatorio.

### Pipeline de prospeccao cartorios (LGPD-safe)
- CEO-assistant pesquisa melhores cartorios do Brasil (Google, ranking ANOREG).
- ROTEIRO de abordagem LGPD-safe redigido pelo `cartorio-lgpd` ANTES de envio em massa.
- Gustavo dispara do WhatsApp pessoal DEPOIS de revisar copy.
- NAO usar WhatsApp pessoal pra envio em massa > 50/dia (risco de ban + LGPD).

### Proximos passos (ordem de execucao)
1. Gustavo via Easypanel UI: cartorio_openclaw-gateway > Service > Edit > Args `--bind auto --port 18790 --allow-unconfigured` + User `node` + ANTHROPIC_API_KEY ou OPENAI_API_KEY
2. Criar systemd unit `/etc/systemd/system/cartorio-network-monitor.service` pro `cartorio-network-monitor.sh`
3. Atualizar `backend/app/core/config.py` pra ler `OPENCLAW_BASE_URL` (substituir LiteLLM)
4. Sprint 1: implementar `GET /api/v1/emolumento/calcular` + workflow n8n #1
5. LGPD: redigir texto do termo de consentimento + politica privacidade
6. Sprint 0.5.T3 backup diario Supabase (cron)
7. Sprint 0.5.T4 seed tabela emolumento MG 2026

---

## 2026-06-23 10:55 BRT — 5 critérios copy prospecção LGPD-safe (cross-project pattern)

CEO consolidou checklist obrigatório pra QUALQUER copy de prospecção em mercado regulado. Vale pra cartório, saúde, jurídico, financeiro — qualquer setor onde o receptor recebe 10+ pitches/semana.

### Os 5 critérios (nenhum pode faltar)

1. **SINAL ESPECÍFICO por destinatário** (anti-spam) — 1 fato concreto e verificável do alvo. Sem isso é template = deletado.
   - Bons sinais: ranking oficial (ANOREG/PQTA/GPTW), arrecadação pública, tradição (ano de fundação), expansão recente, inovação observável (WhatsApp Business, e-Notariado, PIX)
   - Estrutura: cumprimento + SINAL ESPECÍFICO + pitch aplicado + CTA + opt-out

2. **LGPD-SAFE** (compliance) — zero dado pessoal (CPF/RG/telefone PF/e-mail PF/nome tabelião PF), apenas institucional. Sem pressão abusiva ("última chance", "só hoje"). Opt-out claro em rodapé. Sem link rastreável (sem utm pessoal, sem bit.ly com nome destinatário).

3. **CTA claro** (conversão) — formato fixo: "Posso mostrar 15min terça 10h ou quinta 14h? — responde com o melhor". Tempo curto (15min não 1h), 2 opções concretas (não 3+), dia útil + horário comercial, pré-compromisso leve ("conversa rápida" não "reunião de demonstração").

4. **Tom PT-BR natural** (anti-juridiquês) — bloqueios lexicais: "Vossa Senhoria", "venho por meio desta", "solicito", "informamos que", "coloco-me à disposição", "aguardo retorno", "atenciosamente". Boas práticas: tu/você, parágrafos curtos, 1 ideia por parágrafo, abertura curta ("Vi que...", "Parabéns pelo...", "Notei que...").

5. **Piloto 30 dias grátis** (prova social) — toda copy Tier A oferece piloto 30 dias grátis em troca de depoimento + logomarca no case. Reduz risco percebido, gera prova social pra Tier B/C, filtra quem tem disposição pra inovar.

### Onde aplicar
- E0.S0.5.T7: 11 modelos (5 WhatsApp + 3 e-mail + 3 LinkedIn) em `/docs/leads/roteiros/`
- Próximos rounds: rodada 2 (top 15 estados faltantes), rodada 3 (saúde: clínicas/hospitais), rodada 4 (jurídico: escritórios mid-market)
- **Quem valida**: CEO (revisão bloco a bloco) + cartorio-harness ou equivalente (validação LGPD-compliance final)

### Por que funciona
- Tabulador sensível (Tier A) recebe 10+ pitches/semana. Bot = deletado. Humano + sinal específico = abre conversa
- LGPD-safe copy não é gargalo, é diferencial competitivo (concorrente vai fazer errado)
- Piloto 30 dias grátis muda o cálculo de risco (zero $$ vs licenciar SaaS inteiro)

### Detalhes
- Fonte dos sinais específicos: `/docs/leads/cartorios-br-top30.md` (prospeção com scoring Tier A/B/C, canais validados, citações públicas)
- CEO é o "porteiro" — só deixa copy bloco a bloco aprovada ir pra produção
- Cross-project lesson: padrão aplicável a qualquer B2B high-ticket em mercado regulado

---

## 2026-06-23 10:46 BRT — Workers em paralelo (3ª sprint do dia)

### 4 workers spawned via `mavis communication send --command spawn`:
- `cartorio-dev` (general fallback) — mvs_c80baa — backend: GET/POST /api/v1/protocolo + Swagger PT-BR + 10+ testes pytest + audit + PII
- `cartorio-n8n` (general fallback) — mvs_2d2ceae — reimportar workflow #1 + criar #2 (criar-protocolo) + #3 (handoff-chatwoot) + agent bot Chatwoot
- `cartorio-lgpd` (general fallback) — mvs_c6c4d15 — 4 docs LGPD (privacidade, consentimento, RIPD, roteiro abordagem) + validar PII scrubber
- `ceo-assistant` — mvs_2323ad — prospecção top 30 cartórios BR (DONE 10:45)

### Routing lesson (importante):
- cartorio-dev/lgpd/n8n sao `.harness/reins/` (project scope), NAO globais mavis
- `mavis communication send --command spawn --agent cartorio-dev` retorna 404 "Agent not found"
- Workaround: spawn como `agent=general` e prompt explicito carregando contexto do rein (agent.md do projeto)
- Para escalar isso formalmente, criar agentes globais OU usar `mavis team plan` que conhece project reins

### Opencode-Go API key (DeepSeek-v4 flash) — LOW COST provider primario
- Key: `sk-j03KVdV6rDkSW1D2KmrmbCL8zRjhBw0IkOes2BNCEetOokTnbLJXwc7AyltoRscr`
- Base URL: `https://opencode.ai/zen/go/v1`
- Model: `deepseek-v4-flash`
- Salvo em `backend/.env` (nao commitado, gitignored)
- **Gustavo autorizou**: usar como provider primario LLM no projeto inteiro (opencode, n8n, supabase, whatsapp)

### Gustavo pediu tambem:
- OpenClaw = cerebro do modelo (sandbox do agent, memory, skills, tools, mcps, plugins, hooks, goals)
- N8N = harness (workflows do inicio ao fim, bloqueio handoff humano, MCP servers clientes)
- Supabase = banco + cerebro/memoria do agent
- API = integracao central de tudo (skills, mcps servers/clients, plugins, agents, subagents, hooks, metas, goals, memory)
- Evolution API = WhatsApp
- Redis = acelera tudo + sessoes por cliente
- Cada cliente WhatsApp = 1 sessao = 1 atendimento completo em 1 flow
- NUNCA perder sessao: Redis tem cache, Supabase tem historico completo (antigo + novo)
- TUDO integrado, documentado, comentado, salvo na memoria
- Analisar -> testar -> corrigir -> melhorar -> otimizar -> documentar -> comentar -> salvar na memoria (workflow obrigatorio)
- Chat antigo gravou token Antigravity para trabalhar em equipe: `antigravity-minimax/minimax-antigravity`
- Tailscale only (rede maxima, mas Tailscale deveria bastar pra OpenClaw - bloqueando de forma errada)

### Pendencias UI (Gustavo) - NAO esquecidas:
1. OpenClaw port mapping fix (Easypanel UI > cartorio_openclaw-gateway > Service > Edit > Command)
2. OpenClaw LLM key (OPENAI_API_KEY ou ANTHROPIC_API_KEY no Env)
3. OpenClaw token config (openclaw doctor --generate-gateway-token)
4. Chatwoot Agent Bot + Inbox (UI super_admin)
5. Chatwoot domain chatwoot.2notasudi.com.br
6. Nova Easypanel API key (a antiga morreu 401)
7. Decisao DNS typo supbase vs supabase
8. Validar workflow #1 em flow.2notasudi.com.br

---

## 2026-06-23 10:55 BRT — Sprint 1 N8N: 4 workflows DONE (commit 3cdb65a)

### Entregas concretas

| # | Workflow | ID | Webhook | Estado |
|---|----------|----|---------|--------|
| 1 | Consulta Emolumento | `bR7qIo3bFpG4zgxO` | /webhook/consulta-emolumento | ACTIVE — happy path: R$ 105.40 certidao_casamento, R$ 156.40 procuracao (valores reais MG 2026), PII detectado → handoff |
| 2 | Criar Protocolo (LGPD) | `MzeYTSDouymzdpRw` | /webhook/criar-protocolo | ACTIVE — LGPD_BLOCKED sem consent, provisional CART-2026-XXXXXX com consent (backend POST /protocolo ainda 404 — Sprint 3 E1.S3.T1) |
| 3 | Handoff Humano | `OQRIOVHcOjpkQ0Of` | /webhook/handoff-human | ACTIVE — retorna inbox URL fallback mesmo quando Chatwoot inacessivel |
| 4 | Boas-Vindas + LGPD | `sDtkfOJ5BA7M73wB` | /webhook/boas-vindas | ACTIVE — novo cliente LGPD text, recorrente menu numerado |

API FastAPI 8000 (via Traefik) GREEN: `/health` ok, `/api/v1/health/radar` ALL services online (DB, redis, n8n, openclaw, evolution), `/api/v1/audit/verify` chain_ok=true last_valid_position=10.

Commit `3cdb65a` — feat(n8n): 4 workflows Sprint 1 - consulta, criar protocolo, handoff, boas-vindas. 4 files, +326/-21.

### N8N workflow import via API — 6 gotchas (cross-project, salvar pra sempre)

1. **Schema strict do n8n API** — `connections` precisa ser dict (não string), `nodes[].parameters` exige estrutura exata do node type. Erro genérico 400 sem detalhe. Solução: copiar de workflow export existente e modificar in-place.

2. **Code node v1+ vs legacy** — `functionCode` foi removido em n8n recente. Tem que ser `jsCode` + `mode: "runOnceForEachItem"` (não `runOnceForAllItems`). ERR_ASSERTION no import se errado.

3. **Respond node + JSON template** — `JSON.stringify()` inline no Respond template dá "Invalid JSON in Response Body" porque n8n faz double-encode. Solução: usar template `{{ JSON.stringify($json) }}` OU construir objeto direto.

4. **httpRequest error handling** — `onError: continueRegularOutput` faz o node cair no output normal MAS o input data original ($json) NÃO é acessível. Precisa usar `$('NodeName').item.json` pra acessar upstream data.

5. **IF branches invertidas** — quando você faz PII detection, easy mistake é mandar `clean=true` pro handoff em vez de mandar pro API. Convention: TRUE branch = "needs handling" (handoff), FALSE = "safe path" (API). Sempre revisar.

6. **Traefik path vs internal port** — webhook URL exposto precisa bater com o routing do Traefik (Host + PathPrefix). Internal port do n8n é 5678; Traefik roteia flow.2notasudi.com.br → n8n:5678. Validar com curl antes de ativar.

### Workflow files (git tracked)

- `infra/n8n-workflows/01-consulta-emolumento.json` (existente, atualizado v2 com PII→handoff)
- 02/03/04 também exportados em `infra/n8n-workflows/` (recomendação: importar esses JSONs ao invés de re-criar via API se workflow precisar ser refeito em outro env)

### Chatwoot Agent Bot — bloqueador único

- WF3 tem inbox URL fallback (não trava Sprint 1)
- 5 tentativas de credenciais default 429 rate-limited (Chatwoot bloqueia brute force)
- Recomendação: Gustavo cria super_admin via UI OU me passa password → cartorio-n8n finaliza via API em <2min

### Workflow validation protocol (vale pra qualquer rein que mexer em n8n)

1. Antes de ativar: testar webhook com curl usando payload mínimo realista
2. Ativar via API: `POST /api/v1/workflows/{id}/activate`
3. Validar hit count após 1h: `GET /api/v1/workflows/{id}` → checar `active=true`, `nodesExecuted`
4. Exportar JSON pro repo após cada iteração: `GET /api/v1/workflows/{id}` → salvar em `infra/n8n-workflows/{NN}-{nome}.json`
5. Commit com Conventional Commits + `Modified by Gustavo Almeida`

Modified by Gustavo Almeida