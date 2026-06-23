# Cartorio Sprint 2 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Levar o cartorio chatbot de "infraestrutura rodando" para "fluxo end-to-end executado por clientes reais via WhatsApp", cobrindo gaps reais identificados em 23/06/2026 16:50 BRT.

**Architecture:** 3 owners de execucao:
- **[Mavis/SSH]** tarefas que eu posso executar via `ssh root@100.99.172.84`
- **[UI]** tarefas que dependem EXCLUSIVAMENTE de UI web (Easypanel, Cloudflare, Chatwoot Manager, WhatsApp Manager)
- **[Decisao]** tarefas que precisam de Gustavo decidir antes (licoes, prioridades, custo)

**Tech Stack:** Python 3.12, FastAPI 0.115+, SQLAlchemy 2.0, N8N 2.27.3, Evolution API 2.3.7, Supabase, Traefik, systemd, Bash.

---

## Estado AGORA (baseline 23/06/2026 16:50 BRT)

| Componente | Status | Evidencia |
|---|---|---|
| API v0.4.5 | 🟢 healthy | curl /health 200 |
| Health Radar | 🟢 GREEN | 5/5 servicos |
| N8N workflows | 🟢 12/12 ativos | workflows #01-#11 |
| N8N credentials | 🟢 4 criadas | cartorio-api-bearer, supabase-postgres, opencode-go-deepseek, evolution-api-cartorio |
| N8N variables | ❌ bloqueado | licenca community nao tem feat:variables |
| Supabase | 🟢 13/13 healthy | analytics-1 OK |
| Backup diario | 🟢 03:00 | 3 backups retidos (7.3M) |
| Backup monitor | 🟢 a cada 6h | cartorio-backup-monitor.timer |
| Evolution instance | 🟡 created | cartorio-2notas (state: close, QR pendente) |
| OpenClaw Tailscale | 🟢 200 OK | vps-cartorio.tail2fe279.ts.net |
| Chatwoot accounts | 🟢 1 (super_admin) | precisa Agent Bot |
| API executions | ❌ zero | tabela atendimentos vazia |

---

## Area 1 - Evolution API + WhatsApp (CRITICO)

### Task 1.1: Conectar WhatsApp (UI - Gustavo)
- [ ] Gustavo acessa `https://whatsapp.2notasudi.com.br/manager/instance/cartorio-2notas`
- [ ] Escaneia QR Code com WhatsApp do cartorio
- [ ] Valida: `curl -sk -H "apikey: 429683C4C977415CAAFCCE10F7D57E11" "http://172.16.2.7:8080/instance/connectionState/cartorio-2notas"` retorna `state: open`
- **Tempo**: 2 min

### Task 1.2: Configurar webhook Evolution -> N8N (Mavis/SSH)
- [ ] SSH: configurar webhook URL no Evolution (`WEBHOOK_GLOBAL_URL=https://flow.2notasudi.com.br/webhook/evolution-event`)
- [ ] Eventos: `MESSAGES_UPSERT`, `MESSAGES_UPDATE`, `CONNECTION_UPDATE`
- [ ] Validar: `docker logs cartorio_evolution-api` mostra requests chegando
- **Tempo**: 10 min

### Task 1.3: Health check Evolution automatizado (Mavis/SSH)
- [ ] Criar `/usr/local/bin/cartorio-evolution-health.sh` que testa `connectionState` e alerta se != open
- [ ] Criar `cartorio-evolution-health.{service,timer}` (5min)
- [ ] Instalar e validar
- **Tempo**: 15 min

---

## Area 2 - N8N workflows (CORE)

### Task 2.1: Migrar workflows #02-#10 para usar credential cartorio-api-bearer (Mavis/SSH)
- [ ] Workflows #02, #04, #05, #06 hoje chamam API sem cred
- [ ] Atualizar cada um via `PUT /api/v1/workflows/{id}` adicionando `credentials.httpHeaderAuth.id=22Q8OUbeZ1bsGnlt`
- [ ] Reativar e validar 200
- [ ] **Validado em**: `curl -sk -X GET "https://flow.2notasudi.com.br/api/v1/workflows/{id}" | jq .active`
- **Tempo**: 30 min

### Task 2.2: Workflow #03 (Handoff Chatwoot) - configurar URL real (Mavis/SSH)
- [ ] Hoje workflow #03 aponta pra placeholder `https://api.2notasudi.com.br/health` (proxy)
- [ ] Trocar pra `https://cartorio-chatwoot.dfgdxq.easypanel.host/api/v1/accounts/1/conversations`
- [ ] Ativar
- **Tempo**: 10 min

### Task 2.3: Workflow #07 (Pesquisa) - testar envio real (Mavis/SSH)
- [ ] Primeiro cliente real precisa concluir atendimento
- [ ] Aguardar 24h
- [ ] Workflow #07 dispara via cron
- [ ] Validar via logs N8N: `grep "Evolution sendText" /var/log/n8n/`
- [ ] **Bloqueado por**: Task 1.1 (WhatsApp conectado)
- **Tempo**: 5 min setup + 24h espera

### Task 2.4: Workflow #09 (Monitor Backup) - melhorar com alerta Chatwoot (Mavis/SSH)
- [ ] Hoje workflow #09 so loga; faltava alerta se backup falhar
- [ ] Adicionar node httpRequest que chama `https://cartorio-chatwoot.dfgdxq.easypanel.host/.../messages` quando `r.ok == false`
- [ ] Reativar
- **Tempo**: 15 min

### Task 2.5: Workflow #11 (Monitor Cartório) - validar 6 checks (Mavis/SSH)
- [ ] Hoje workflow #11 do Gustavo faz 6 httpRequest paralelos
- [ ] Disparar via `POST /webhook/monitor-cartorio` com curl
- [ ] Validar resposta: 200 + items_count: 6
- [ ] Se algum check falhar, ajustar URL
- **Tempo**: 15 min

---

## Area 3 - Chatwoot CRM (UX)

### Task 3.1: Criar Chatwoot Agent Bot (UI - Gustavo)
- [ ] Login em `https://cartorio-chatwoot.dfgdxq.easypanel.host/super_admin/agent_bots`
- [ ] Criar bot: name=`cartorio-bot`, webhook URL=`https://api.2notasudi.com.br/api/v1/webhook/chatwoot`
- [ ] Anotar `CHATWOOT_BOT_TOKEN` retornado
- **Tempo**: 5 min

### Task 3.2: Configurar env CHATWOOT_BOT_TOKEN na API (Mavis/SSH)
- [ ] Editar `/etc/easypanel/projects/cartorio/api/code/.env` adicionando `CHATWOOT_BOT_TOKEN=<token>`
- [ ] `docker service update --force cartorio_api`
- [ ] Validar via `curl -sk https://api.2notasudi.com.br/mcp-servers | jq .servers`
- **Tempo**: 10 min

### Task 3.3: Criar Inbox WhatsApp no Chatwoot (UI - Gustavo)
- [ ] Chatwoot UI > Inboxes > Add > Website/Inbox > API
- [ ] Channel: WhatsApp via Evolution (CHATWOOT_ENABLED=true no Evolution API env)
- [ ] Anotar INBOX_ID
- [ ] Adicionar `CHATWOOT_INBOX_ID={id}` no .env API
- **Tempo**: 10 min

### Task 3.4: Configurar Evolution -> Chatwoot integration (Mavis/SSH)
- [ ] No Evolution, ativar `CHATWOOT_ENABLED=true`, `CHATWOOT_URL=https://cartorio-chatwoot.dfgdxq.easypanel.host`, `CHATWOOT_ACCOUNT_ID=1`, `CHATWOOT_TOKEN=<token>`
- [ ] `docker service update --force cartorio_evolution-api`
- [ ] Validar: webhook Chatwoot recebe eventos de mensagem
- **Tempo**: 15 min

---

## Area 4 - API (BACKEND)

### Task 4.1: Adicionar endpoint webhook Chatwoot signature validation (Mavis/SSH)
- [ ] Hoje `/api/v1/webhook/chatwoot` aceita qualquer payload
- [ ] Adicionar validacao HMAC header `X-Chatwoot-Signature` (webhook_secret do Chatwoot)
- [ ] Teste com request invalido (deve 401) e valido (200)
- **Tempo**: 30 min

### Task 4.2: Seed emolumento MG 2026 oficial (Mavis/SSH)
- [ ] Hoje emolumento tem placeholder (10 valores)
- [ ] Buscar tabela oficial 2026 no Diario Oficial MG via WebFetch
- [ ] Criar migration Alembic que popula tabela `emolumento_regras` com valores oficiais
- [ ] Validar: `curl https://api.2notasudi.com.br/api/v1/emolumento/calcular?tipo=escritura_compra_venda`
- **Tempo**: 1h

### Task 4.3: Implementar endpoint `POST /api/v1/documento/{id}/assinar` (Mavis/SSH)
- [ ] Roadmap sprint 4. Sem provedor escolhido ainda.
- [ ] MVP: gera hash SHA256 + timestamp + retorna URL de PDF placeholder
- [ ] Provedor real (Certisign/SERPRO) = decisao de Gustavo (Task D1)
- **Tempo**: 1h

### Task 4.4: Adicionar testes E2E com Playwright (Mavis/SSH)
- [ ] Hoje tem 44 unit tests + 1 smoke test
- [ ] Criar `tests/e2e/` com Playwright
- [ ] Testar fluxo: webhook N8N -> API -> response
- **Tempo**: 2h

---

## Area 5 - OpenClaw + Tailscale

### Task 5.1: Adicionar OpenClaw ao MCP config global (Mavis/SSH)
- [ ] Ja foi adicionado em ~/.mavis/mcp/clients/cartorio-mcp-config.json
- [ ] Validar com `~/.mavis/bin/mavis communication peers --human | head -10`
- [ ] **Ja feito em**: v0.4.3 sprint
- **Tempo**: 0

### Task 5.2: Documentar brain architecture do OpenClaw (Mavis/SSH)
- [ ] Hoje OpenClaw eh usado como gateway HTTP, mas a documentacao do "agent cartorio" com memory/skills/tools ainda nao foi feita
- [ ] Criar `docs/OPENCLAW_AGENT_ARCHITECTURE.md` com: SOUL.md, TOOLS.md, memory layout
- [ ] Validar com Gustavo que isso bate com a visao
- **Tempo**: 30 min

### Task 5.3: Adicionar Tailscale ACL pra limitar quais nodes acessam OpenClaw (Decisao)
- [ ] Hoje qualquer node na rede Tailscale acessa `vps-cartorio.tail2fe279.ts.net`
- [ ] Restringir so `macbook-pro-gus` (100.83.180.16) + `iphone-17-pro` (100.122.101.33)
- [ ] **Decisao de Gustavo**: outras pessoas podem acessar?
- **Tempo**: 5 min config + decisao

---

## Area 6 - Supabase (DATABASE)

### Task 6.1: Mover 90 tabelas N8N core do DB cartorio pro DB n8n (Mavis/SSH)
- [ ] Hoje N8N core (workflow_entity, executions, etc) estao no DB cartorio (poluicao)
- [ ] Migrar via `pg_dump` + restore no DB `n8n` + update config N8N
- [ ] **Risco**: exige downtime do N8N. Fazer em janela de manutencao
- **Bloqueado por**: Gustavo autoriza janela de manutencao
- **Tempo**: 30 min

### Task 6.2: Criar tabela `atendimentos_full` (Mavis/SSH)
- [ ] Hoje tabela `atendimentos` tem 13 colunas (suficiente para MVP)
- [ ] Sprint 2: adicionar `chatwoot_conversation_id`, `protocolo_id`, `nota_pesquisa`, `comentario_pesquisa`, `tags JSONB`
- [ ] Alembic migration
- **Tempo**: 30 min

### Task 6.3: Criar RLS policies em todas tabelas backend (Mavis/SSH)
- [ ] Hoje backend confia 100% na API (sem RLS)
- [ ] Sprint 2: habilitar Row Level Security + policies por servico
- [ ] **Validar**: API continua funcionando + testes passam
- **Tempo**: 1h

---

## Area 7 - Backup + Observabilidade (DEVOPS)

### Task 7.1: Backup S3 / B2 (Mavis/SSH + Decisao)
- [ ] Hoje backup so fica em `/var/backups/cartorio/` local (risco de perda total VPS)
- [ ] Sprint 2: push diario pra S3 ou B2 via `rclone sync`
- [ ] **Decisao de Gustavo**: AWS S3 ou Backblaze B2? (custo ~$1-5/mes)
- **Tempo**: 30 min

### Task 7.2: Health check consolidado cron (Mavis/SSH)
- [ ] Ja temos cartorio-backup-monitor (6h)
- [ ] Ja tem workflow #11 (5min via N8N)
- [ ] Falta: cron unificado que valida TUDO e alerta via webhook
- [ ] Criar `/usr/local/bin/cartorio-all-health.sh` que checa 8 servicos em paralelo + alerta se algum cai
- **Tempo**: 30 min

### Task 7.3: Setup Prometheus + Grafana (Decisao + Mavis/SSH)
- [ ] Hoje monitor eh so `docker stats` + logs
- [ ] Sprint 2: deploy Prometheus + Grafana + alertas
- [ ] **Decisao de Gustavo**: quer dashboards visuais? (peso 4GB RAM no Prometheus + Grafana)
- **Tempo**: 2h + decisao

### Task 7.4: CI/CD GitHub Actions (Mavis/SSH)
- [ ] Hoje push no master requer deploy manual via Easypanel
- [ ] Sprint 2: GitHub Action que roda pytest + ruff + build + push pra registry
- [ ] Trigger: push em master (build) + tag (deploy staging)
- **Tempo**: 1h

---

## Area 8 - Frontend (NICE TO HAVE)

### Task 8.1: Web widget cliente (Decisao)
- [ ] Hoje cliente so pode interagir via WhatsApp
- [ ] Sprint 3: web widget embedable que chama mesma API
- [ ] **Decisao de Gustavo**: prioridade? (roadmap diz sprint 3)
- **Tempo**: 1 semana

### Task 8.2: Painel admin para escreventes (Decisao)
- [ ] Hoje nao ha UI para acompanhar protocolos (so API)
- [ ] Sprint 3: Next.js com auth Supabase + visualizacao de protocolos
- **Tempo**: 2 semanas

---

## Decisoes pendentes de Gustavo

- **D1**: Provedor de assinatura digital (Certisign vs SERPRO vs gov.br ICP-Brasil)?
- **D2**: B2 ou S3 para backup remoto? Budget aprovado?
- **D3**: Upgrade N8N Enterprise (libera Variables + Data Tables) ou continuar community?
- **D4**: Deploy Prometheus+Grafana (4GB RAM extra)?
- **D5**: Frontend web widget ou so WhatsApp por enquanto?
- **D6**: Janela de manutencao para mover 90 tabelas N8N pro DB separado (Task 6.1)?

---

## Resumo de tempo (estimado)

| Owner | Tasks | Tempo total |
|---|---|---|
| **[Mavis/SSH]** (eu faco) | 1.2, 1.3, 2.1, 2.2, 2.3, 2.4, 2.5, 3.2, 3.4, 4.1, 4.2, 4.3, 4.4, 5.2, 6.1, 6.2, 6.3, 7.1, 7.2, 7.4 | ~13h |
| **[UI]** (Gustavo faca) | 1.1, 3.1, 3.3 | ~17 min |
| **[Decisao]** (Gustavo decide) | D1-D6 + 5.3, 7.3, 8.1, 8.2 | depende |
| **Bloqueado** | 6.1 (janela manutencao) | espera |

Total executavel **AGORA** sem decisao: ~13h de trabalho SSH.

---

## Execucao

Vou executar **tasks SSH consecutivas** nas proximas 1-2h, priorizando ordem de impacto:

1. Area 1 Task 1.3 (Evolution health cron) - 15min
2. Area 2 Task 2.1 (migrar workflows com cred) - 30min
3. Area 2 Task 2.2 (workflow #03 Chatwoot URL real) - 10min
4. Area 4 Task 4.1 (webhook Chatwoot HMAC) - 30min
5. Area 7 Task 7.2 (cron all-health) - 30min
6. Atualizar CHANGELOG v0.5.0 + commit - 15min

**Bloqueado ate Gustavo decidir/fazer**:
- Task 1.1 (escanear QR WhatsApp) - 2min UI
- Task 3.1 (criar Agent Bot Chatwoot) - 5min UI
- Decisoes D1-D6 - varia

Modified by Gustavo Almeida
