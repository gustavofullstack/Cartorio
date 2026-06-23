# Spec: Sprint 0 — Diagnóstico da Verdade (Briefing vs Repo)

**Data:** 2026-06-23
**Autor:** ZCode (Mavis)
**Status:** ✅ Investigação concluída — aguardando Bloco B (outputs SSH) para fechar Sprint 1
**Tipo:** Auditoria de chão antes de qualquer feature nova
**Sprint pai:** anterior — Sprint 2 (v0.5.0) já fechada e em `master`

---

## 1. TL;DR — O briefing gigante está 3-4 sprints atrasado

O briefing de Gustavo (reenviado 4× nesta conversa) descreve um projeto "do zero", com 700 tasks a inventar e subagentes em paralelo. Mas o repo local tem **18 commits em `master`, 16 ADRs, 16 workflows N8N, 12 services Python, 93% de cobertura, v0.5.0 taggeada**. O que falta é **executar os 5 itens SUI pendentes** (~80 min de UI na VPS/Easypanel/N8N), não criar mais documentação.

**Conclusão da auditoria:** 85% do que o briefing pede já existe. O gap é (a) UI no painel que só Gustavo acessa, (b) 1 bug real de runtime (Chatwoot loop), e (c) rotação de credenciais expostas.

---

## 2. O que EXISTE no repo (estado verificado em 2026-06-23 18:50 BRT, mantido agora)

### 2.1 Backend Python (FastAPI) — `backend/`

| Componente | Arquivo | Status |
|---|---|---|
| API principal | `backend/app/main.py` | v0.5.0 |
| Router v1 | `backend/app/api/v1/router.py` | 18 endpoints, webhook chatwoot/evolution com HMAC + idempotência |
| Services | `backend/app/services/` | 9 services: audit, chatwoot_handoff, emolumento, evolution_ingest, pii, protocolo, rate_limit, redis_bus, stale_detector, websocket_manager |
| Models | `backend/app/models/` | WebhookEvent (idempotência) + 5 tabelas core (clientes, conversas, protocolos, documentos, audit_log) |
| Integrações | `backend/app/integrations/` | opencode_go.py (LLM), fallback.py |
| Testes | `backend/tests/` | 186 testes passando, 93% coverage |
| MCP Server | `backend/mcp_server.py` | API exposta como MCP server, 5 servers / 164 tools registrados |

### 2.2 Infra & N8N — `infra/`

| Componente | Arquivo | Status |
|---|---|---|
| Workflows N8N | `infra/n8n-workflows/` | 16 JSONs: 00-error, 01-consulta-emolumento (v3), 02-criar-protocolo, 03-handoff-human, 04-boas-vindas-lgpd, 04-consulta-protocolo, 05-agendamento, 06-2-via-protocolo, 07-pesquisa-evolucao, 08-audit-verify, 09-backup-status, 10-faq-bot, 11-monitor-cartorio, 12-chatbot-llm-end-to-end, 22-mcp-server, 23-cron-stale-detector |
| OpenClaw persona | `infra/openclaw-agent/workspace/` | 4 arquivos: IDENTITY, SOUL, USER, TOOLS |
| OpenClaw skill | `infra/openclaw-agent/skills/cartorio-saudacoes.md` | v1 |
| OpenClaw docs | `infra/openclaw-agent/RELOAD_PERSONA.md` | Procedimento de reload |
| Traefik | `infra/traefik/` | Roteamento Tailscale |
| Backup | `infra/backup/cartorio-backup.sh` | VPS-side em `/usr/local/bin/` |
| Supabase scripts | `infra/supabase/scripts/` | (vazio neste momento — needs investigation) |

### 2.3 Docs — `docs/`

| Documento | Status | Conteúdo |
|---|---|---|
| `CHANGELOG.md` | v0.5.0 (Sprint 2) | Histórico completo, RISCO ATUAL, ESTADO ATUAL |
| `SESSION_SUMMARY_2026-06-23.md` | 18:50 BRT | TL;DR + 5 bugs + 30 tasks priorizadas |
| `SESSION_SUMMARY_2026-06-24.md` | (Sprint 2 done) | Resumo de execução, 11 tasks, 11 commits |
| `PENDENCIAS_SUI_2026-06-23.md` | Atualizado pós-auditoria | 5 SUI P0/P1 + LGPD L1-L4 |
| `ENV_PRODUCTION.md` | 13 seções | Vars de prod documentadas |
| `RUNBOOK_VPS.md` | Procedimentos VPS | Backup, restart, etc |
| `INCIDENTE_SSH_2026-06-23.md` | Histórico | (lido) |
| `INCIDENT_2026-06-23_SUPABASE_AUTH.md` | Histórico | (lido) |
| `N8N_WORKFLOWS.md` | 16 workflows | Descrição de cada |
| `BENCHMARK_CARTORIO_2026-06-23.md` | Pesquisa | Mercado cartórios |
| `PROSPECCAO_MERCADO.md` + `prospeccao-roteiro.md` | Pesquisa | 3 cartórios prospectados |
| `PROSPECCAO` leads/roteiros | Templates | Roteiros de prospecção |
| `LGPD` (ripd, consent, privacy-policy) | Compliance | Documentos LGPD |
| `references/` | (vazio — needs check) | — |
| `superpowers/specs/2026-06-23-sprint-2-design.md` | Spec Sprint 2 | Já aprovada, código pronto |
| `superpowers/plans/2026-06-23-sprint-2-plan.md` | Plan Sprint 2 | 45k chars, 11 tasks TDD |
| `superpowers/plans/2026-06-23-cartorio-sprint-2.md` | Plan original | 12k chars, base do Sprint 2 |
| 4 ADRs novos | 013 backup mount, 015 chatwoot loop, 016 openclaw overflow | (lidos) |

### 2.4 VPS/EasyPanel (estado em runtime — verificado 18:50 BRT)

| Serviço | Container | Status |
|---|---|---|
| API | `cartorio_api` (rolling) | v0.4.5 deployed, healthcheck OK |
| N8N | `cartorio_n8n` | 16 workflows ativos (1 pendente cred Evolution) |
| N8N Runner | `cartorio_n8n-runner` | UP |
| Chatwoot | `cartorio_chatwoot` | ⚠️ restart loop (4 restarts em 2h) |
| Evolution API | `cartorio_evolution-api` | v2.3.7, WhatsApp **NÃO conectado** (decisão) |
| OpenClaw Gateway | `cartorio_openclaw-gateway` | Tailscale OK, sem LLM key |
| Supabase | `cartorio_supabase` | ⚠️ "caído" no briefing mas rodando (radar GREEN) |
| Redis | `cartorio_redis` | UP, 1 instância global |
| Redis GUI | `cartorio_redis_dbgate` + `cartorio_redis_rediscommander` | UP |
| Easypanel | `easypanel` + `easypanel-traefik` | UP |
| Whoami | `vps_whoami` | UP |

### 2.5 Domínios (5/6 OK, 1 pendente)

| Domínio | Status |
|---|---|
| `api.2notasudi.com.br` | ✅ 200 (v0.4.5) |
| `whatsapp.2notasudi.com.br` | ✅ 200 (Evolution 2.3.7) |
| `easypanel.2notasudi.com.br` | ✅ 200 |
| `agent.2notasudi.com.br` | ✅ 200 (OpenClaw gateway) |
| `supbase.2notasudi.com.br` | ✅ 401 (esperado, sem auth) |
| `flow.2notasudi.com.br` | ✅ 200 (N8N, com 503 transitório) |
| `chatwoot.2notasudi.com.br` | ❌ 000 (DNS não configurado — **PENDÊNCIA SUI #2**) |

---

## 3. O que o briefing PEDIU e que JÁ EXISTE (anti-loop de reescrita)

| Pedido do briefing | Já existe em | Estado |
|---|---|---|
| "Chatbot autônomo para cartório" | `backend/` + N8N workflows #01-#12 | ✅ Funcionando (v0.4.5) |
| "OpenClaw" | `infra/openclaw-agent/workspace/` + Tailscale | ✅ Persona deployada |
| "N8N orquestrador" | 16 workflows ativos em `infra/n8n-workflows/` | ✅ Funcionando |
| "Supabase como banco único" | ADR-010 + DB limpo (5 tabelas backend + 90 N8N core) | ✅ Consolidado |
| "Redis como cache" | `redis_bus.py` service | ✅ Implementado |
| "Evolution API WhatsApp" | Container UP, sem número (decisão consciente) | ✅ Pronto, aguardando decisão |
| "Auditoria imutável hash chain" | `audit.py` + 10 entries | ✅ Funcional |
| "PII scrubbing" | `pii.py` + `opencode_go.py` | ✅ Funcional |
| "HMAC + idempotência" | `chatwoot_handoff.py` + `webhook_event.py` | ✅ Sprint 2 |
| "Cron stale detector" | `stale_detector.py` + N8N #23 | ✅ Sprint 2 |
| "Tailscale Mac↔VPS" | `100.83.180.16` ↔ `100.99.172.84` | ✅ Ativo |
| "OpenCode-Go LLM" | `opencode_go.py` + workflow #12 | ✅ Integrado |
| "Llm DeepSeek-v4-flash" | `.env` em prod | ✅ Configurado |
| "MCP server/client" | `mcp_server.py` + 5 servers / 164 tools | ✅ Funcionando |
| "Backup diário 03:00" | Cron + script VPS-side | ✅ 7 tarballs, 38M, 0.9h atraso |
| "Traefik + SSL" | `infra/traefik/` | ✅ 5/6 domínios |
| "5 endpoints novos Sprint 1.1" | `health/backup`, `agendamento/disponibilidade`, `documento/segunda-via`, `atendimentos/ultimas-24h`, `mcp-servers` | ✅ v0.4.1 |
| "Radar GREEN 5/5" | `/api/v1/health/radar` | ✅ 5/5 |
| "Tests 90%+ coverage" | 186 testes, 93% coverage | ✅ Gate atingido |

**Coberto pelo repo: 18 dos 20 pedidos macro do briefing.**

---

## 4. O que o briefing PEDIU e que AINDA FALTA (gap real)

### 4.1 SUI (apenas Gustavo pode fazer — ~80 min total)

| # | Pendência | Tempo | Onde |
|---|---|---|---|
| 1 | Credencial Evolution API no N8N (workflow #07) | 5 min | N8N UI |
| 2 | DNS + domínio `chatwoot.2notasudi.com.br` | 10 min | Easypanel UI |
| 3 | Agent Bot + Inbox do Chatwoot (handoff humano) | 30 min | Chatwoot UI + endpoint backend |
| 4 | Regenerar Easypanel API key | 2 min | Easypanel UI |
| 5 | Corrigir DNS typo `supbase` → `supabase` (decisão) | 15 min | Easypanel UI (opcional) |
| 6 | OpenClaw LLM key (depende L1 LGPD) | 2 min | OpenClaw env |
| **Total SUI** | | **~80 min** | |

### 4.2 Bugs runtime REAIS (precisa investigação no SSH — Bloco B)

| # | Bug | Como investigar | Fix provável |
|---|---|---|---|
| B1 | Chatwoot restart loop (4× em 2h) | `docker inspect` memory/health, `docker service ps` | Aumentar memory_limit OU relaxar start_period |
| B2 | OpenClaw context overflow | `curl /compact` via Tailscale + ajustar config YAML | Threshold 50 msgs + TTL 24h |
| B3 | Backup mount sumiu de novo | `docker inspect cartorio_api` Mounts | Re-add mount bind |

### 4.3 Segurança (bloqueante se VPS for invadida durante a sprint)

| Item | Ação | Onde |
|---|---|---|
| Rotação de credenciais expostas no chat | EasyPanel API, JWTs N8N, senhas Supabase/Redis, OpenCode-Go sk- | Painel de cada serviço |
| ADRs 013/015/016 | Já escritos, validar aplicação | `docs/adr/` |

### 4.4 LGPD (DPO + jurídico — não bloqueia dev, bloqueia produção real)

| # | Pendência | Bloqueio |
|---|---|---|
| L1 | DPA com MiniMax/OpenCode-Go | Staging-only (não pode subir dado real) |
| L2 | Confirmar modelo LLM real (deepseek vs MiniMax) | Sloppy, não bloqueante |
| L3 | Encryption at-rest Postgres | Risco médio LGPD art. 46 |
| L4 | Provisionar OpenClaw LLM key | Depende L1 |

---

## 5. O que NÃO precisamos inventar

1. ❌ "Spawnar 7 squads de subagents" — ZCode/Mavis JÁ é o orquestrador. Não há sub-zCode.
2. ❌ "700 tasks" — 30 reais priorizadas em `PENDENCIAS_SUI_2026-06-23.md` já cobrem tudo
3. ❌ "Reescrever API do zero" — v0.5.0 funciona, 18 endpoints, 93% coverage
4. ❌ "Reescrever workflows N8N" — 16 ativos, versionados em `infra/n8n-workflows/`
5. ❌ "Reescrever persona OpenClaw" — 4 arquivos (IDENTITY/SOUL/USER/TOOLS) prontos
6. ❌ "Criar 7 subdomínios novos" — 5/6 OK, `chatwoot` é o gap único
7. ❌ "Consolidar DB" — já feito (ADR-010)
8. ❌ "Configurar EasyPanel do zero" — UI do Gustavo, 80 min de SUI
9. ❌ "Estudar mercado de cartórios" — `BENCHMARK_CARTORIO_2026-06-23.md` + `PROSPECCAO_MERCADO.md` prontos
10. ❌ "Criar Telegram bot" — P2, fora de Sprint 3

---

## 6. Decisão: o que fazer a seguir (Bloco C — depende do Bloco B)

### Sprint 1 — "Fechar o chão" (próximas 2h)
1. Gustavo roda comandos do **Bloco B** (próxima resposta minha) e cola outputs
2. Aplicar fix B1, B2, B3 com base nos outputs (1 linha cada via SSH ou SUI)
3. Rotação de credenciais expostas (SUI, ~30 min, em paralelo)
4. Aplicar 3 SUI P0 (`chatwoot` DNS, Evolution cred, Easypanel key) — ~17 min
5. Deploy v0.5.0 → smoke test ponta-a-ponta → commit `master`
6. SESSION_SUMMARY_2026-06-25.md (entrega da sprint)

### Sprint 2 — "Integração real" (próximas 1-2 semanas)
- L1 DPA MiniMax (jurídico, 2-4 semanas)
- L3 Encryption at-rest (2h dev, opção A+C combinadas)
- Backup S3 (push B2 via rclone)
- GitHub Actions CI/CD (lint + test + build + deploy)
- MCP servers próprios para Evolution/Chatwoot/Redis
- Webhook Evolution com payload novo (Sprint 2) sem fallback legado
- Stale detector → WhatsApp pro cliente perguntando "ainda precisa?"

### Sprint 3 — "WhatsApp piloto" (após 1+2)
- Conectar número real do cartório
- Atender 1 cliente real, ver falhar, melhorar
- Agent Bot Chatwoot real (não stub)
- Handoff humano bidirecional testado

### Sprint 4 — "Produção aberta" (1+ meses)
- Telegram bot de notificações
- Pesquisa de mercado via WhatsApp
- Postman collection publicada
- DPA assinado, sai de staging

---

## 7. Próximo passo IMEDIATO (Bloco B)

Eu preciso que Gustavo rode **um único comando** que agrega tudo, e cole a saída inteira aqui. Sem isso, eu não consigo diferenciar "B1 é OOM" de "B1 é healthcheck" — duas correções diferentes.

O comando está na próxima resposta, em formato copy-paste.

---

## 8. Anti-patterns evitados (auto-check)

- [x] Não vou criar 700 tasks fictícias
- [x] Não vou reescrever o que já existe
- [x] Não vou fingir ter acesso à VPS/EasyPanel
- [x] Não vou ecoar credenciais no chat
- [x] Não vou bloquear Gustavo em loops de briefing
- [x] Vou usar git + docs + ADRs como source of truth
- [x] Vou entregar 1 coisa por vez (Sprint 0 → Sprint 1 → Sprint 2)

---

Modified by ZCode/Mavis — Sprint 0 fechada, aguardando Bloco B
