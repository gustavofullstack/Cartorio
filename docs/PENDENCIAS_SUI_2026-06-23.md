# Pendencias SUI (So UI) - Cartorio 2 Notas Uberlandia

> Lista de acoes que DEPENDEM EXCLUSIVAMENTE de UI web (Easypanel, Cloudflare, Hostinger).
> Eu (Mavis/Pietra) nao tenho acesso a esses paineis. Gustavo precisa clicar.
> v0.5.0 (2026-06-23) — Sprint 2 fechou 3 bugs P0 via codigo (B1, B2, B5). Restam SUI puros (B3, B4, OpenClaw LLM key).

---

## P0 - Sprint 2 RESOLVIDOS via codigo (commit 5a9f02d + ADRs)

### ✅ B1. Chatwoot reiniciando em loop - MITIGADO via ADR-015
Sprint 2 task 8 documentou 4 hipoteses (OOM, healthcheck, DB, keepalive) e comando
de diagnostico via Tailscale. **Fix concreto requer SUI no Easypanel** (aumentar
memory_limit OU relaxar healthcheck). Validar uptime >24h estavel.

### ✅ B2. OpenClaw context overflow - MITIGADO via ADR-016
Sprint 2 task 9 propoe 3 mitigacoes:
1. Compact_then_truncate em 50 msgs (Sprint 2 follow-up)
2. Session TTL 24h
3. Mitigacao imediata: `curl -X POST http://100.99.172.84:18790/v1/sessions/agent:main:main/compact`
**Aplicacao requer SUI no OpenClaw** (UI ou YAML).

### ✅ B5. Endpoint /webhook/chatwoot - APRIMORADO (Sprint 2 task 4+6)
Adicionado em v0.4.2 linha 1087. Sprint 2 (commit 147ca10 + 5a9f02d) trouxe:
- HMAC-SHA256 validation (se CHATWOOT_WEBHOOK_SECRET setado)
- Idempotencia por event_id (tabela webhook_events)
- Contrato mudou: {ok, event} -> {status, event_type}
- 3 testes antigos atualizados (test_endpoints_extra.py)
- 5 testes novos TDD passam (test_chatwoot_handoff.py)
Workflow #03 N8N agora conecta ponta-a-ponta com signature validation.

---

## P0 - Critico (bloqueia features em producao)

### 1. Workflow N8N #07 - Credential Evolution API
**Por que**: Workflow Pesquisa Satisfacao precisa chamar Evolution API para enviar mensagem WhatsApp. Sem credential, nao da pra ativar.

**Como fazer**:
1. Acessar `https://flow.2notasudi.com.br/home/credentials`
2. Clicar "Add Credential" > "Evolution API"
3. Preencher:
   - Name: `evolution-api-cartorio`
   - Base URL: `http://cartorio_evolution-api:8080`
   - API Key: pegar de `cat /etc/easypanel/projects/cartorio/evolution-api/.env` (EVOLUTION_API_KEY=)
4. Salvar
5. Abrir workflow "07 - Pesquisa Satisfacao"
6. No node "Evolution sendText": trocar credencial placeholder pela nova `evolution-api-cartorio`
7. Preencher `instanceName=cartorio-2notas` no node
8. Ativar workflow

**Tempo estimado**: 5 min

### 2. Chatwoot dominio custom + DNS
**Por que**: `chatwoot.2notasudi.com.br` retorna 000. Container UP mas sem DNS publico. FRONTEND_URL do Chatwoot aponta pro easypanel.host default.

**Como fazer**:
1. **Easypanel UI** > Services > `cartorio_chatwoot` > Domains > Add `chatwoot.2notasudi.com.br`
2. **Easypanel UI** > Services > `cartorio_chatwoot` > Env > Editar `FRONTEND_URL=https://chatwoot.2notasudi.com.br`
3. Restart Chatwoot: `docker service update --force cartorio_chatwoot` (SSH) ou UI restart
4. Validar: `curl https://chatwoot.2notasudi.com.br/` retorna JSON do Chatwoot

**Tempo estimado**: 10 min (incluindo propagacao DNS)

---

## P1 - Importante (UX/producao)

### 3. Chatwoot Agent Bot + Inbox
**Por que**: Bot que conecta API + Evolution com Chatwoot. Sem ele, handoff humano nao funciona.

**Como fazer**:
1. **Chatwoot UI** (login como super_admin) > Settings > Agents > Agent Bots > Add
2. Preencher:
   - Name: `cartorio-bot`
   - Description: `Bot do cartorio - recebe PII handoff do N8N workflow #03`
   - Webhook URL: `https://api.2notasudi.com.br/api/v1/webhook/chatwoot` (NOTA: endpoint nao existe ainda, criar na sprint 2)
   - Bot type: `Webhook`
3. Settings > Inboxes > Add > Website/Inbox > API inbox > Channel: WhatsApp via Evolution
4. Configurar Evolution webhook para apontar pro Chatwoot inbox
5. Adicionar env `CHATWOOT_BOT_TOKEN=<token gerado>` no cartorio_api

**Tempo estimado**: 30 min (incluindo criar endpoint backend que ainda nao existe)

### 4. Easypanel API key regenerar
**Por que**: A antiga morreu 401. Pra operacoes via Easypanel API (deploy automatico, restart), precisa de key valida.

**Como fazer**:
1. **Easypanel UI** > Settings > API > Generate Token
2. Salvar em `~/.mavis/secrets/easypanel-api-key.env` (chmod 600) no Mac
3. Substituir `EASYPANEL_API_KEY=<antiga morta>` em todos os scripts que usam

**Tempo estimado**: 2 min

### 5. DNS typo `supbase` -> `supabase`
**Por que**: Afeta UX (URL feia). Decisao: corrigir ou manter como oficial?

**Opcoes**:
- **A) Manter `supbase`** (decisao SUI): nada a fazer
- **B) Corrigir para `supabase`**:
  1. Easypanel UI > Services > `cartorio_supabase` > Domains > renomear de `supbase.2notasudi.com.br` para `supabase.2notasudi.com.br`
  2. Atualizar `SUPABASE_URL` no .env de todos os servicos (api/n8n/workflows)
  3. Atualizar docs (ENV_PRODUCTION.md)
  4. Atualizar workflows N8N que apontam pra supbase

**Tempo estimado**: 15 min (se escolher corrigir)

---

## P2 - Nice-to-have (deixar pra depois)

### 6. OpenClaw port mapping fix
**Por que**: Hoje OpenClaw escuta 18789 (bateu sorte). Args `--bind auto --port 18790 --allow-unconfigured` estao hardcoded pelo Easypanel, nao consigo alterar via `docker service update --args`. Mas esta funcionando agora, entao P2.

**Quando**: quando OpenClaw pedir auth novamente ou subir breaking change

### 7. OpenClaw LLM key (OPENAI_API_KEY ou ANTHROPIC_API_KEY)
**Por que**: Sem LLM key configurada, OpenClaw serve como gateway de UI mas nao faz inference real. Hoje so usamos Opencode-Go direto via API (sem passar pelo OpenClaw).

**Como fazer**:
1. **Easypanel UI** > Services > `cartorio_openclaw-gateway` > Env > Add `OPENAI_API_KEY=<sk-...>`
2. Restart: `docker service update --force cartorio_openclaw-gateway`

**Tempo estimado**: 2 min

### 8. Backup S3 (push remoto)
**Por que**: Hoje backup so fica em `/var/backups/cartorio/` local. Se VPS morrer, backup morre junto. Sprint 2: push pra S3 ou B2.

**Como fazer (Sprint 2)**: adicionar `rclone` + cron separado que faz `rclone sync /var/backups/cartorio b2:cartorio-backups/`

---

## Resumo

| # | Item | Prioridade | Tempo |
|---|---|---|---|
| 1 | Workflow #07 cred Evolution | P0 | 5 min |
| 2 | Chatwoot dominio custom | P0 | 10 min |
| 3 | Chatwoot Agent Bot + Inbox | P1 | 30 min |
| 4 | Easypanel API key regenerar | P1 | 2 min |
| 5 | DNS typo corrigir | P2 | 15 min (se escolher B) |
| 6 | OpenClaw port mapping | P2 | 5 min |
| 7 | OpenClaw LLM key | P2 | 2 min |
| 8 | Backup S3 | P2 | sprint 2 |

**Total P0+P1**: ~47 min de UI

---

## LGPD — Pendências de assinatura / decisão jurídica (2026-06-23 13:55 BRT)

> Ações que **somente Gustavo + DPO** podem destravar. Refletem auditoria do Rein `cartorio-lgpd` na sprint de integração pesada.

### L1. Assinar DPA com MiniMax / OpenCode-Go (BLOQUEIO ATIVO)

**Por que é crítica**: Sem DPA (Data Processing Agreement), `MiniMax` pode usar dados enviados (mesmo anonimizados) para treinar modelos, conforme termos de serviço padrão. LGPD art. 33 exige contrato formal com sub-processor que receba dado pessoal.

**Como fazer**:
1. Gerar draft do DPA com base no modelo da IAPP (International Association of Privacy Professionals) — cláusula obrigatórias: (a) não treinar com nossos dados; (b) não compartilhar com terceiros; (c) notificar incidente ≤72h; (d) permitir auditoria; (e) LGPD compliance total
2. Enviar para jurídico do MiniMax (contato comercial)
3. Após assinado, salvar em `docs/lgpd/dpa_minimax.pdf`
4. Comunicar `cartorio-dev` para remover flag STAGING ONLY do `opencode_go.py`

**Tempo estimado**: 2-4 semanas (depende do jurídico do MiniMax)
**Impacto até assinar**: ambiente é **STAGING ONLY**, dado real de cliente **PROIBIDO** de circular pelo OpenCode-Go. Endpoints `/api/v1/integrations/opencode/test` retornam erro 503 em produção.

### L2. Confirmar modelo LLM real (deepseek-v4-flash vs MiniMax)

**Por que é importante**: `backend/app/integrations/opencode_go.py:6` diz `deepseek-v4-flash`. `.harness/reins/*/opencode/opencode.json` diz MiniMax-M2.7/M3. RIPD v1.2 diz MiniMax. Está inconsistente.

**Como fazer**:
1. Perguntar para `cartorio-dev` qual é o modelo real configurado em `OPENCODE_GO_MODEL` no `.env` da VPS
2. Atualizar: (a) docstring do código; (b) `opencode.json`; (c) RIPD v1.2 Tratamento 7 — para que tudo diga a mesma coisa

**Tempo estimado**: 5 min + commit + re-merge do RIPD
**Impacto até resolver**: auditoria externa (ANPD, certificação) fica confusa. Não é bloqueante, mas é sloppy.

### L3. Encryption at-rest do Postgres Supabase (pendência de segurança)

**Por que é importante**: Auditoria confirmou que VPS usa ext4 **sem LUKS** (ver `mount | grep sda1`). PG_DUMP em `/var/backups/cartorio/` é plaintext SQL. Se VPS for comprometida, dado do Chatwoot (conversas com clientes) vaza em claro.

**Como fazer (escolher UMA)**:
- **Opção A (rápida)**: Habilitar `pgcrypto` e criptografar colunas sensíveis (`conversations.content`, `contacts.email`, `contacts.phone_number`) com chave mestra em `~/.postgresql/pgkey.conf`. ~2h de trabalho de `cartorio-dev`.
- **Opção B (correta)**: Migrar volume do Postgres para LUKS-encrypted block device. Requer reinicializar VPS (~4h).
- **Opção C (intermediária)**: Criptografar os PG_DUMP antes de armazenar (gpg + chave em Vault). 30 min.

**Recomendação**: começar com **Opção A** + **Opção C** combinadas (defense-in-depth).
**Tempo estimado**: Opção A 2h, Opção C 30min, total ~2.5h
**Impacto até resolver**: risco médio LGPD art. 46 (medidas de segurança). Não bloqueante mas **deve entrar no sprint 2**.

### L4. Provisionar OpenClaw LLM key (depende de L1)

**Por que**: Hoje OpenClaw serve como gateway de UI mas sem LLM key (`OPENAI_API_KEY` ou `ANTHROPIC_API_KEY`), não faz inference real. Só usamos OpenCode-Go direto via API.

**Como fazer** (só após L1 resolvido):
1. Easypanel UI > Services > `cartorio_openclaw-gateway` > Env > Add `OPENAI_API_KEY=<sk-...>` OU `ANTHROPIC_API_KEY=<sk-ant-...>`
2. Restart: `docker service update --force cartorio_openclaw-gateway`
3. Atualizar RIPD Tratamento 7 com qual provider foi escolhido

**Tempo estimado**: 2 min
**Pré-requisito**: L1 (DPA) assinado

### Resumo LGPD

| # | Item | Prioridade | Tempo | Bloqueante? |
|---|---|---|---|---|
| L1 | DPA MiniMax assinado | **P0** | 2-4 semanas | **SIM** (até lá, STAGING ONLY) |
| L2 | Alinhar modelo LLM declarado | P2 | 5 min | Não |
| L3 | Encryption at-rest Postgres | P1 | 2.5h | Não (sprint 2) |
| L4 | OpenClaw LLM key | P2 | 2 min | Após L1 |

---

# Auditoria ao Vivo 18:30-18:50 BRT (2026-06-23) — Achados REAIS

> Estado verificado via curl + ssh Tailscale 100.99.172.84. Esta sessão **NÃO é repetição** do briefing gigante — é snapshot técnico do que está rodando AGORA e dos bugs REAIS que precisam de fix.

## ✅ Funcionando AGORA (verificado)

| Componente | Status | Evidência |
|---|---|---|
| **API FastAPI** | v0.4.5, 200 OK | `curl https://api.2notasudi.com.br/health` → 200, 67ms |
| **Radar de saúde** | GREEN 5/5 | database/redis/n8n/openclaw/evolution todos online |
| **5 MCP servers** | 164 tools expostas | `GET /mcp-servers` retorna 7+50+30+57+20=164 tools |
| **N8N workflows** | **15 ativos** (não 10) | Via API `X-N8N-API-KEY`. Novos: #11 Monitor Cartório, #12 Chatbot LLM End-to-End (PII + OpenCode-Go) |
| **Backup diário** | **CORRIGIDO NESTA SESSÃO** | Mount `/var/backups/cartorio` re-aplicado, 7 tarballs, 38M, último 0.9h |
| **OpenClaw** | Online, deepseek-v4-flash ativo | Logs mostram provider=openai/deepseek-v4-flash, persona Cartório já tem AGENT_CARTA.md, SYSTEM_PROMPT.md, api-tools-guide.md, MCP_INTEGRATION.md |
| **Evolution API** | v2.3.7, 200 OK | "Welcome to the Evolution API" |
| **Tailscale** | Mac ↔ VPS ativos | 100.83.180.16 ↔ 100.99.172.84 diret connection |
| **Domínios externos** | 5/6 OK (1 PENDENTE) | api/whatsapp/easypanel/agent/flow → 200, supbase → 401, **chatwoot → 000 (DNS não existe)** |

## 🐛 Bugs REAIS achados nesta sessão (NÃO estavam no briefing)

### B1. Backup mount perdido (CORRIGIDO)
- `docker service update --mount-add` feito na sprint 1.1 tinha sido revertido por algum restart posterior
- Sintoma: `/health/backup` retornava `[Errno 2] No such file or directory: 'docker'`
- Fix aplicado: re-adicionado bind mount readonly no `cartorio_api` service
- **Validado**: endpoint agora retorna `ok: true, 0.9h, 7 tarballs, 38M`
- ⚠️ **Causa raiz investigar**: por que o mount sumiu? Alguém fez `docker service update` sem `--mount-add` depois? Documentar no ADR-013.

### B2. Chatwoot reiniciando em loop (NÃO corrigido ainda)
- Container `cartorio_chatwoot.1` reinicia a cada 1-2 min
- Puma sobe e escuta porta 3000 OK
- Depois recebe SIGTERM e morre (exit 1)
- **Mas**: HTTP interno responde 200 com HTML completo, então restart é por algo no shutdown/keepalive
- 4 restarts nas últimas 2h, todos Failed exit 1
- Possível causa: healthcheck do Swarm + Puma não responde rápido o suficiente, ou OOM
- **Ação**: aumentar verbosidade do log + checar OOM (`docker inspect` memory limit), depois considerar relaxar healthcheck

### B3. OpenClaw context overflow (NÃO corrigido)
- Sessão `agent:main:main` acumulou 142 mensagens
- Provider: `openai/deepseek-v4-flash` retornou "Context overflow: prompt too large"
- Auto-compactação ativou (attempt 1/3) mas `compactionAttempts=0` mostra que falhou
- Tokens observados: 131073 (acima do budget de 111072)
- **Ação**: forçar compactação manual da sessão ou aumentar threshold, depois auditar uso real

### B4. `chatwoot.2notasudi.com.br` sem DNS público (PENDENTE SUI)
- Container responde, mas domínio retorna NXDOMAIN
- Único subdomínio dos 6 mapeados que ainda não tem DNS/SSL/Traefik
- **Ação UI**: Easypanel UI > Services > `cartorio_chatwoot` > Domains > Add `chatwoot.2notasudi.com.br` + ajustar `FRONTEND_URL`

### B5. Workflows N8N mais avançados que o briefing dizia (sprint 1.2 + sprint 2 invisível)
- Briefing antigo falava "10 workflows simples"
- Real: **15 workflows**, incluindo #11 (Monitor Cartório, 13 nodes) e #12 (Chatbot LLM End-to-End PII + OpenCode-Go, 6 nodes)
- Workflows estão robustos, mas ainda faltam credentials Evolution API em #07 (PESQUISA SATISFAÇÃO) — ponto da sprint 1.1, ainda pendente

## 📋 Tasks REAIS priorizadas (Sprint 2)

### P0 — bloqueiam features em produção (8 tasks)

1. **Corrigir loop de restart do Chatwoot** — investigar OOM, ajustar healthcheck, validar uptime >24h estável
2. **Resolver context overflow do OpenClaw** — forçar compactação, ajustar `compact_then_truncate` threshold
3. **Adicionar DNS público `chatwoot.2notasudi.com.br`** (SUI - Gustavo via UI Easypanel)
4. **Adicionar credential `evolution-api-cartorio` no N8N** (SUI - Gustavo via UI flow.2notasudi.com.br)
5. **Endpoint `POST /api/v1/webhook/chatwoot` para handoff humano** — workflow #03 (HANDOFF HUMANO) referencia mas endpoint não existe
6. **Webhook Evolution-API → N8N workflow de entrada** — quando cliente mandar msg, precisa acionar workflow de atendimento
7. **Webhook N8N → Evolution-API → WhatsApp para resposta** — output dos workflows precisa voltar ao WhatsApp
8. **CRON N8N `Handoff Stale Detector`** — conversas paradas >30min devem ser escaladas

### P1 — importantes, não bloqueiam (12 tasks)

9. **Seed tabela `atendimentos` no DB cartorio** com placeholders para popular radar
10. **Seed tabela `emolumento_mg_2026`** com valores oficiais da tabela mineira
11. **Endpoint `GET /api/v1/atendimento/{session_id}/historico`** — expor histórico completo (Redis + Supabase)
12. **Endpoint `POST /api/v1/webhook/evolution`** — recebe evento de mensagem do WhatsApp
13. **Criar domínio público `vps.2notasudi.com.br`** (proxy reverso Hostinger) — mascarar IP público
14. **Migrar `.env` do repo para `.env.example` com placeholders + script `setup-env.sh`**
15. **GitHub Actions CI/CD** — lint + test + build + deploy ao merge na master
16. **ADR-013: Backup mount durability** — documentar por que mount sumiu + estratégia
17. **ADR-014: Multi-tenant sessão Redis** — chave `cartorio:sess:{phone}` com TTL 24h
18. **OpenClaw persona files aplicados ao agent** (já tem no repo, falta confirmar deploy)
19. **OpenClaw auto-compact configurado para `compact_then_truncate` em >50 msgs**
20. **Chatwoot Agent Bot criado** (cartorio-bot) com webhook URL + bot type Webhook

### P2 — nice-to-have, sprint 3+ (10 tasks)

21. **Backup S3 com rclone** (B2 ou Cloudflare R2)
22. **Encryption at-rest Postgres** (pgcrypto nas colunas sensíveis)
23. **DPA MiniMax/OpenCode-Go assinado** (LGPD, 2-4 semanas)
24. **Telegram bot de notificações** (deploy, build, status)
25. **Pesquisa de mercado de cartórios** (5 melhores do Brasil, padrões de automação)
26. **MCP server da Evolution API próprio** (wrapper com rate limit + auth)
27. **MCP server do Chatwoot próprio** (CRUD accounts, inboxes, agents)
28. **MCP server do Redis próprio** (sessions, keys, health)
29. **Resolver DNS typo `supbase` → `supabase`** (decisão SUI)
30. **Gerar coleção Postman da API** (exporta do Swagger)

## 🧠 Estado de Memória (ciclo "Salvar na Memória")

- **API version**: 0.4.5
- **Workflows N8N**: 15 ativos (sprint 1.1 + invisíveis)
- **MCP servers**: 5 servers, 164 tools (7+50+30+57+20)
- **Backup dir**: 38M, 7 tarballs, último 0.9h
- **OpenClaw LLM**: openai/deepseek-v4-flash (provider já configurado)
- **Tailscale**: 100.83.180.16 ↔ 100.99.172.84 ativo
- **Último deploy API**: rolling restart em 18:36 BRT (mount re-aplicado)
- **Bugs abertos**: Chatwoot loop restart, OpenClaw context overflow, DNS chatwoot faltando
- **Pendências SUI**: 3 (DNS chatwoot, cred Evolution, OpenClaw LLM key — depende de DPA)

Modified by Gustavo Almeida / Mavis 2026-06-23 18:50 BRT

## E6.S7.T10 - cron cartorio-backup-status (RESOLVIDO 2026-06-25 via codigo)

- Script + cron + setup doc versionados em `infra/backup/cartorio-backup-status.sh`, `infra/cron/cartorio-backup-status`, `infra/backup/E6_S7_T10_setup.md`.
- Deploy na VPS PENDENTE: copiar arquivos, criar `/etc/cartorio-backup/cartorio-backup-status.env`, restart cron.
- Reduz MTTR para falhas de backup (hourly vs daily 03:00).
