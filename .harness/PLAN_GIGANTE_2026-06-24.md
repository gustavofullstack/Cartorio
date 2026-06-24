# PLAN GIGANTE 2026-06-24 — Cartório Chatbot

> Documento-mãe orquestrador. Criado por Pietra/Mavis (session mvs_410a1b1266d64830b9dfa31973fdd9fe) em 2026-06-24 14:50 BRT após diagnóstico real via SSH cartório (Tailscale 100.99.172.84) + API + Telegram bot test.

## 0. STATUS REAL (validado agora — não chute)

| Serviço | Status | Versão | Notas |
|---|---|---|---|
| cartorio_api | ✅ healthy | v0.5.4 | /health 200 OK; /api/v1/health 200 OK |
| cartorio_n8n | ✅ up | 2.x | /healthz 200; 33 workflows ativos |
| cartorio_n8n-runner | ✅ up | 2.x | cadência idle 1/min normal (Lesson 57) |
| cartorio_chatwoot | ✅ up | - | HTTP 200; Account.count=1 |
| cartorio_chatwoot-sidekiq | ✅ up | - | processando jobs |
| cartorio_evolution-api | ✅ up | 2.3.7 | Welcome 200 OK |
| cartorio_openclaw-gateway | ✅ up | 2026.6.10 | /health {"ok":true,"status":"live"} |
| cartorio_redis | ✅ up | 8.8 | 1744 keys, PONG (auth @Techno832466 URL-encoded) |
| cartorio_supabase-db | ✅ healthy | PG 15.8 | 15 schemas, **public VAZIO** (zero tabelas custom) |
| cartorio_supabase-{kong,studio,storage,meta,analytics,supavisor,realtime,auth,rest,vector,imgproxy,functions} | ✅ healthy | - | stack completa UP |
| easypanel + traefik | ✅ up | - | proxy reverso |
| Telegram Bot @test_cartorio_bot | ✅ ativo | API Bot 6 | webhook deletado p/ teste (N8N workflow 31 seta de novo) |

**OpenClaw config ANTES (estado quebrado que estava)**:
- API key: `sk-j03KVdV6...` (ANTIGA, tinha limitado)
- Thinking: **NÃO habilitado**
- contextWindow: 131072 (deepseek-v4-flash limit)
- Skills: 0 habilitadas (todas desabled)
- Agent cartorio: inexistente

**OpenClaw config DEPOIS (aplicado 14:43 BRT)**:
- API key: `sk-xcRwExjQjqmlc5swP8umqK2YqWUfVt23H3Xl6dpd9TqEyi16ssJXzHeUFGNNIfsJ` (NOVA do Gustavo)
- Skills habilitadas: coding-agent, gemini, gh-issues, github, healthcheck, mcporter, session-logs
- Plugins: openai enabled
- Compaction: keepRecentTokens=16384 (era 2048), maxActiveTranscriptBytes=200mb (era 50mb)
- Backup: `/home/node/.openclaw/openclaw.json.pre-fix-2026-06-24T14-37`
- Validação: gateway live, doctor --fix rodou OK

**Bug raiz workflows N8N** (workflow 25 - Metrics Collector):
- POST https://api.2notasudi.com.br/api/v1/metrics/n8n → **404 Not Found**
- Endpoint NÃO EXISTE na API — métricas computadas (clientes_total=1, audit_chain_length=290, uptime=212s) mas POST falha
- Outros erros prováveis: workflows 21, 26, 30, 31 — investigação adicional em task dedicada

**`.env` local**: completo e organizado (61 vars, 14.7KB), bloco "API KEYS — Gustavo prompt 2026-06-24 14:20 BRT" com warning Lesson 58.

## 1. REGRAS DE OURO (NÃO QUEBRAR)

1. **NÃO rotacionar chaves** — Gustavo + Pietra únicos detentores (Lesson 58)
2. **Master-only branch** — merge direto ou apagar (hook rejeita branch != master)
3. **Conventional Commits** + final `Modified by Gustavo Almeida`
4. **Coverage gate ≥ 90%** — pytest --cov-fail-under=90 (NÃO BAIXAR)
5. **mypy strict 0 errors** + ruff check + ruff format antes de commit
6. **LGPD review obrigatório** em mudança de `audit` ou `pii` (cartorio-lgpd assina)
7. **Coordenação via mavis communication send** (não chat direto)
8. **Modo**: 1-2 agents por vez, sequencial, sem paralelo pesado (preserva quota 5h)
9. **Sprint 3 SUI Gustavo-only** (DNS, credenciais UI) — Pietra nunca toca UI
10. **Workflow obrigatório**: analisar → testar → corrigir → melhorar → otimizar → documentar → comentar → salvar na memória

## 2. STACK TARGET (referência única)

```
EVO(8080) → API FastAPI(8000) → N8N(5678) → Chatwoot(3000) → Redis(6379) → Supabase(DB+REST+Realtime+Storage+Vault+pgmq+Auth+Functions)
   ↑                                                                                                    ↓
   ←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←←
```

OpenClaw Gateway(18789) ↔ Chatwoot ↔ N8N (via MCP server HTTP)
OpenClaw Provider = openai/deepseek-v4-flash @ opencode.ai/zen/go/v1 (Thinking ON)
OpenClaw Fallback = anthropic-claude-sonnet-4.5 (1M context)

## 3. 100 TASKS DE MELHORIA (continua em `.harness/task-bank-100-melhorias.json`)

Resumo por squad:
- **SQUAD_A API/DB HARDENING** (25 tasks, owner cartorio-dev) — A01..A25 ✅ 12/25 done
- **SQUAD_B N8N/OPENCLAW/MULTI-CANAL** (25 tasks, owner cartorio-n8n) — B01..B25 ✅ 5/25 done
- **SQUAD_C LGPD/COMPLIANCE** (25 tasks, owner cartorio-lgpd) — C01..C25 ✅ 5/25 done
- **SQUAD_D SUPABASE/CENTRAL BD** (25 tasks, owner cartorio-dev + cartorio-lgpd) — D01..D25 ✅ 5/25 done

**TOP 10 PRIORIDADE AGORA (sprint 3)**:
1. **B0.1** Criar endpoint `POST /api/v1/metrics/n8n` na API (corrige erro workflow 25)
2. **B0.2** Investigar e corrigir erros workflows 21 (Backup), 26 (Monitor OpenClaw), 30 (Health), 31 (Telegram)
3. **D0.1** Criar 5 tabelas core no schema public do Supabase (cliente, conversa, protocolo, documento, emolumento + audit_log)
4. **D0.2** Habilitar Supabase Realtime para conversas ativas (webhook → frontend)
5. **D0.3** Configurar pgmq queues (alta prioridade: webhook_in, audit_out, n8n_callback, dlq)
6. **A0.1** Audit log 100% mutações com request_id/ip/user_agent (já tem 1/6 hoje — workflow 22)
7. **A0.2** DELETE /cliente/{id} (LGPD art. 18 VI) — workflow 23 LGPD Esqueci tá INATIVO, precisa ativar
8. **C0.1** Job retenção 5y/até-revogação (workflow 24 Retenção inativo)
9. **B0.3** Ativar n8n-nodes-mcp em workflow 12 e n8n-nodes-chatwoot em workflow 03
10. **G0.1** Rotação de credenciais expostas: OpenCode-Go (✅ FEITO nova key), N8N JWTs MCP+public, OpenClaw Token/Password, Redis default, Supabase DB

## 4. COMO EXECUTAR

```
Pietra (root, eu)
  ↓ task chega
  ↓ decide rein (dev/n8n/lgpd) — 1 por vez
  ↓ envia via mavis communication send
  ↓ aguarda ACK
  ↓ valida critérios de done
  ↓ se parcial, devolve com lista do que falta
  ↓ se done, atualiza .harness/TASKS.md + Linear
  ↓ próximo task
```

**Modo squad**: até 2 squads simultâneos no máximo. Sequencial preferencial.

## 5. LIÇÕES MEMORIZADAS (cross-project)

- Lesson 16/17: cred em chat = queimada → rotacionar IMEDIATO (exceto Lesson 58)
- Lesson 22: peer sem supervisão em prod = bomba-relógio
- Lesson 44 v4: watchdog n8n-runner — TID-resolved probe
- Lesson 47 v4: TID-resolved probe canônico
- Lesson 56: anti-spam pós-IM-CRITICAL
- Lesson 57: decisão C canônica — N8N idle restart = working-as-designed
- Lesson 58: chaves em chat = queimadas MAS user "não rotacionar" = seguir + warning

## 6. FONTES DE VERDADE

- `docs/ROADMAP.md` — 12 semanas visão negócio
- `.harness/TASKS.md` — Epic/Sprint/Task tree
- `.harness/task-bank.json` — tasks atuais
- `.harness/task-bank-100-melhorias.json` — 100 melhorias (4 squads)
- `.harness/memory/MEMORY.md` — memória compartilhada cross-rein
- `.harness/memory/N8N-AUDIT-2026-06-23.md` — audit N8N
- `.harness/memory/LGPD-AUDIT-2026-06-24.md` — audit LGPD
- `.harness/AGENTS.md` — regras cartório
- `.harness/STANDARDS.md` — code style + gates
- `backend/.env` — runtime config local (master reference)
- `backend/AGENTS.md` — workflow + roster + segurança

Modified by Gustavo Almeida (Pietra orquestrou 2026-06-24 14:50 BRT)
## 5. ATUALIZACAO 14:58 BRT — CHATWOOT DNS_LOST RESOLVIDO PARCIAL

**Status**: Traefik router OK, DNS Hostinger PENDENTE Gustavo.

- Backup: /etc/easypanel/traefik/config/custom.yaml.bak-pre-chatwoot-20260624-175500
- Patch aplicado: chatwoot-http, chatwoot-https, chatwoot-service no custom.yaml
- SIGHUP Traefik, router ativo
- Letsencrypt tentou ACME → falhou NXDOMAIN (esperado, sem DNS)
- SUI Gustavo: 2min no painel Hostinger (A + AAAA records)
- Apos DNS: cert letsencrypt auto em <60s
- Detalhe completo: .harness/memory/MEMORY.md secao "CHATWOOT DNS_LOST 2026-06-24 14:55 BRT"
