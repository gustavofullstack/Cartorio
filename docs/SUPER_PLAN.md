# Cartório AI OS — SUPER PLAN

**Versão:** 1.0.0 (2026-06-22)
**Owner:** Gustavo Almeida
**Orquestrador:** Pietra (Mavis root)
**Stack:** Evolution API + Supabase + n8n + OpenClaw + FastAPI (Python)

---

## 🧠 VISÃO

Plataforma de IA conversacional + automação para **Cartório 2º Notas Uberaba** (MG) e expansão para cadeia de cartórios brasileiros. Multi-canal (WhatsApp Business, Telegram, web), LGPD-compliant, auditável, escalável.

**Diferencial:** código com testes (90%+ coverage) na lógica crítica, n8n nos workflows, OpenClaw como gateway multi-canal — **híbrido, não monolítico**.

**Mercado-alvo (PQTA 2025/2026 — ANOREG/BR ranking):**
- MG lidera com 11,98% dos inscritos (cartórios qualificados)
- 5 categorias: Diamante, Ouro, Prata, Bronze, Rubi (Master + Evolução)
- ~10.000 cartórios no Brasil
- Case Auronix: 80-90% de resolução automática via WhatsApp+IA
- Case Wublo: chatbot cartórios (qualificação + agendamento + coleta docs)

---

## 🏛️ GOVERNANÇA — SQUAD

| Role | Responsibility | Implementação |
|------|---------------|---------------|
| **CEO (Pietra)** | Visão macro, decisões de produto/stack | Mavis root, sprint planning |
| **CTO (Mavis coder)** | Stack, arquitetura, integrações | Coder agent, FastAPI |
| **CMO** | Go-to-market, tração, oferta de canais | Output WhatsApp/Telegram |
| **CFO** | Custos API, ROI, otimização | LiteLLM router + budget |
| **COO** | Operações, fluxos, gargalos | n8n workflows |
| **Tech Lead** | Clean code, SOLID, sprints | Code review |
| **Backend Sênior** | FastAPI, PII scrubber, audit log | Python services |
| **DevOps SRE** | Docker Swarm, Traefik, Cloudflare | VPS 187.77.236.77 |
| **QA Master** | Tests 360° (unit/int/E2E/perf) | pytest + Playwright |
| **UX/UI** | Front, design system, conversão | React + Tailwind |
| **LGPD Gatekeeper** | Bloqueia PRs com PII/audit quebrado | agent `cartorio-lgpd` |

---

## 🔧 STACK & TOPOLOGIA

### Infraestrutura Atual (P0 ✅)

```
┌──────────────────────────────────────────────────────────┐
│                    VPS 187.77.236.77                      │
│                  Linux 6.8.0-124-generic                  │
│                  Docker Swarm + Easypanel                │
│                  Hostinger DC                             │
└──────────────────────────────────────────────────────────┘
                            │
        ┌───────────────────┼───────────────────┐
        │                   │                   │
   ┌────▼─────┐      ┌──────▼──────┐    ┌──────▼──────┐
   │  Traefik │      │ Docker Swarm│    │ Docker      │
   │  (L7)    │      │ (overlay)   │    │ Compose     │
   │          │      │             │    │ (bridge)    │
   └────┬─────┘      └──────┬──────┘    └──────┬──────┘
        │                   │                   │
        │ 5 Services:       │                   │ Supabase (14 cont.)
        │ • evolution-api   │                   │ • db-1 (Postgres 15)
        │ • n8n             │                   │ • auth (gotrue)
        │ • n8n-runner      │                   │ • rest (postgrest)
        │ • openclaw-gateway│                   │ • storage
        │ • redis (1)       │                   │ • supavisor
        │                   │                   │ • kong (gateway)
        │ + Easypanel       │                   │ • studio
        │                   │                   │ • meta, analytics
        │                   │                   │ • realtime, functions
        │                   │                   │ • imgproxy, vector
        └───────────────────┴───────────────────┘
                            │
                  ┌─────────▼─────────┐
                  │  Rede 2notasudi  │
                  │  Cloudflare proxy│
                  │  SSL Termination │
                  └───────────────────┘
```

### Subdomínios Configurados

| Subdomínio | Serviço | Porta | Status |
|------------|---------|-------|--------|
| `api.2notasudi.com.br` | cartorio-api (FastAPI) | 8000 | ⏳ Deploy pendente |
| `whatsapp.2notasudi.com.br` | evolution-api | 8080 | ✅ Traefik label |
| `flow.2notasudi.com.br` | n8n | 5678 | ✅ Traefik label |
| `agent.2notasudi.com.br` | openclaw-gateway | 18790 | ✅ Traefik label |
| `easypanel.2notasudi.com.br` | easypanel | 3000 | ✅ Traefik label |
| `vps.2notasudi.com.br` | easypanel alias | 3000 | ✅ Mesmo route |
| `supbase.2notasudi.com.br` | kong (Supabase) | 8000 | ✅ Traefik label (compose) |

**⚠️ DNS não propagado** — Gustavo configura no Registro.br/Cloudflare.
**⚠️ SSL Let's Encrypt** — automático quando DNS resolver.

### Credenciais & Segredos

Centralizado em `.env` (nunca commitado, em `/etc/easypanel/projects/cartorio/.env`):
- `DB_HOST=cartorio_supabase-db-1` (hostname)
- `DB_USER=supabase_admin`
- `DB_PASS=your-super-secret-and-long-postgres-password` (Supabase)
- `DB_NAME=cartorio`
- `REDIS_URL=redis://default:%40Techno832466@cartorio_redis:6379/0`
- `EVOLUTION_API_KEY=429683C4C977415CAAFCCE10F7D57E11`
- `OPENCLAW_GATEWAY_TOKEN=fz1qzo2xka8n82rn62irscuqws75mm1e17mpsnxzqlp13z1p35skrbg2ck8yg8pg`
- `ANTHROPIC_API_KEY=__PENDENTE_GUSTAVO__`
- `OPENAI_API_KEY=__PENDENTE_GUSTAVO__`

---

## 🚀 EPICS

### E0 — Fundação (Sprint 0 — ATUAL ✅)
- [x] Cartório 1º commit (FastAPI + 5 models + audit + PII)
- [x] `.harness/` (AGENTS.md, STANDARDS.md, TASKS.md, 5 reins)
- [x] SSH key dedicada `~/.ssh/id_ed25519_cartorio`
- [x] Supabase implantado (14 containers)
- [x] Redis centralizado (1, porta 1001→6379)
- [x] Postgres de evolution/n8n removidos (centralizado no Supabase)
- [x] 5/5 services UP (evolution-api, n8n, n8n-runner, openclaw-gateway, redis)
- [x] 6/7 Traefik labels configurados
- [x] OpenClaw agent 'main' scaffold + auth placeholder

### E1 — Chatbot WhatsApp MVP (Sprint 1 — PRÓXIMO)
**Objetivo:** Cliente envia "oi" no WhatsApp Business → bot responde, qualifica, agenda.

Tasks:
- [ ] T1.1: Deploy cartorio-api via webhook `ae186ebd...`
- [ ] T1.2: Criar 1 instância WhatsApp Business no Evolution (QR code Gustavo)
- [ ] T1.3: FastAPI endpoint POST `/webhook/evolution` (recebe msg, retorna reply)
- [ ] T1.4: FastAPI endpoint GET `/health`, `/status`
- [ ] T1.5: FastAPI endpoint POST `/chat` (input → PII scrub → LLM → output scrub)
- [ ] T1.6: Audit log middleware (toda msg gera log com hash chain)
- [ ] T1.7: PII scrubber (CPF, RG, CNPJ, phone, email, CEP)
- [ ] T1.8: n8n workflow "Triagem inicial" (boas-vindas, menu, escalação)
- [ ] T1.9: OpenClaw channel WhatsApp conectado à Evolution
- [ ] T1.10: Test E2E: msg → bot → reply

### E2 — Core Cartório (Sprint 2)
**Objetivo:** Lógica de negócio: emolumentos, agendamento, status de documento, envio PDF.

Tasks:
- [ ] T2.1: Model Emolumento (tabela 2026 MG, isenções)
- [ ] T2.2: Model Documento (status: solicitado, em_análise, pronto, entregue)
- [ ] T2.3: Model Agendamento (data, hora, serviço, cliente)
- [ ] T2.4: API endpoint `/emolumento/calcular` (input: ato, output: valor + custas)
- [ ] T2.5: API endpoint `/documento/status` (input: protocolo, output: status)
- [ ] T2.6: API endpoint `/agendamento/criar` (input: dados, output: confirmação)
- [ ] T2.7: API endpoint `/documento/pdf` (input: protocolo, output: PDF assinado)
- [ ] T2.8: Integração com e-Selo (assinatura digital ICP-Brasil)
- [ ] T2.9: Testes unitários (90%+ coverage)
- [ ] T2.10: Testes integração (pytest + httpx)

### E3 — Multi-canal (Sprint 3)
**Objetivo:** Telegram + Web Chat (mesma lógica, diferentes transports).

- [ ] T3.1: Telegram bot via BotFather
- [ ] T3.2: FastAPI endpoint POST `/webhook/telegram`
- [ ] T3.3: OpenClaw channel Telegram
- [ ] T3.4: Web chat (React + Vite + WebSocket)
- [ ] T3.5: Same business logic, transports diferentes
- [ ] T3.6: Session continuity (cliente troca canal, contexto preserva)

### E4 — Produção (Sprint 4)
**Objetivo:** DNS, SSL, Cloudflare, monitoring, backup.

- [ ] T4.1: DNS 2notasudi.com.br (7 subdomínios → 187.77.236.77)
- [ ] T4.2: Cloudflare proxy + WAF rules
- [ ] T4.3: SSL Let's Encrypt (via Traefik, automático)
- [ ] T4.4: Monitoring: UptimeRobot + Grafana
- [ ] T4.5: Backup Supabase (pg_dump diário → S3)
- [ ] T4.6: Backup Evolution (instances → S3)
- [ ] T4.7: Cron health-check 7 subdomínios
- [ ] T4.8: Documentação OpenAPI/Swagger completa
- [ ] T4.9: Load testing (Locust)
- [ ] T4.10: Runbook + disaster recovery

### E5 — Escala (Sprint 5+)
- [ ] T5.1: LiteLLM gateway (Claude Opus 4.5 + GPT-5.5 fallback)
- [ ] T5.2: Multi-tenant (múltiplos cartórios)
- [ ] T5.3: Dashboard analytics (admin)
- [ ] T5.4: RAG com documentos do cartório (Supabase Vector)
- [ ] T5.5: Voice bot (Twilio + Whisper + TTS)
- [ ] T5.6: Mobile app (React Native + Expo)

---

## 🔄 PROTOCOLO CORE (CIÇÃO OBRIGATÓRIA)

Para **toda** task técnica:

1. **ANALISAR** — Mapear problema, dependências, impacto
2. **TESTAR** — Ambiente isolado, validar viabilidade
3. **CORRIGIR** — Eliminar bugs, vulnerabilidades
4. **MELHORAR** — Refatorar (Clean Code, patterns)
5. **OTIMIZAR** — Complexidade, latência, memória
6. **DOCUMENTAR** — Swagger, JSDoc, README
7. **COMENTAR** — Lógica de negócio complexa
8. **SALVAR NA MEMÓRIA** — Pine lessons, atualizar AGENTS.md

**Padrões:**
- DDD + Clean Architecture (domain/application/infra)
- TypeScript (front), Python (back)
- SOLID, OOP, Clean Code
- MVP primeiro, evolui pra enterprise
- CI/CD contínuo (GitHub Actions)
- Tests 360° (front, back, DB, Redis, VPS, Cloudflare)
- Security Master: rate limit, JWT, sanitization, DDoS, SQLi

---

## 📊 MÉTRICAS DE SUCESSO

| Métrica | Target Sprint 1 | Target Sprint 4 |
|---------|----------------|-----------------|
| Uptime | 95% | 99.9% |
| Latência msg→reply | <3s p50, <8s p95 | <1.5s p50, <3s p95 |
| Resolução automática | 50% | 80% |
| LGPD compliance | Audit log 100% msgs | + PII scrub + retention |
| Coverage tests | 70% | 90%+ |
| Custo API/mês | <$50 | <$200 (10k conversas) |

---

## 🛠️ FERRAMENTAS DISPONÍVEIS

**10 agents** (Mavis):
- mavis (root, eu), coder, general, verifier
- ceo-assistant, devops-sre, code-reviewer
- udiapods-incident-commander, udiapods-test-engineer, udiapods-fe-mobile

**4 MCPs:**
- cu (computer use)
- matrix (web search, image/video/audio generation, TTS)
- playwright (browser automation)
- trash (recoverable file deletion)

**15 crons ativos** (stack-health, redis, evolution, etc)

**Cross-session:** `mavis communication send --to <sid> --command prompt`

**Bridge Mavis → Antigravity:** `agy-high -p '...'` (workers)

**Skills ativas:** ceo-assistant, mavis, mavis-doctor, deep-research, web-search, + 60+

---

## 🚦 DECISÕES PENDENTES (bloqueios)

| # | Decisão | Impacto | Recomendação |
|---|---------|---------|--------------|
| 1 | DNS 2notasudi.com.br | Sem DNS, subdomínios não resolvem | Gustavo configura hoje |
| 2 | API keys (Anthropic, OpenAI) | OpenClaw não tem LLM | Gustavo gera + adiciona env |
| 3 | Webhooks deploy (5 URLs) | Quais são exatamente? | Gustavo confirma nomes |
| 4 | Estratégia WhatsApp pessoal | "Use MEU WhatsApp" — não posso | Criar WhatsApp Business via Evolution |
| 5 | Senhas expostas (logs) | Rotacionar ASAP | Gustavo autoriza |
| 6 | LiteLLM ou direto? | Custo vs controle | LiteLLM gateway (recomendo) |

---

## 📚 DOCUMENTAÇÃO VIVA

- `docs/ARCHITECTURE.md` — diagrama + decisões
- `docs/SUPER_PLAN.md` — este doc
- `docs/RUNBOOK.md` — operacional (deploys, rollback)
- `docs/LGPD.md` — checklist conformidade
- `backend/AGENTS.md` — workflow + standards
- `backend/docs/openapi.json` — Swagger gerado
- `~/.mavis/agents/mavis/memory/` — Mavis memory (cross-session)

---

**Status:** Em execução. Próximo marco: E1 Sprint 1 (chatbot MVP) — alvo 7 dias.
**Última atualização:** 2026-06-22 19:50 BRT

Modified by Gustavo Almeida
