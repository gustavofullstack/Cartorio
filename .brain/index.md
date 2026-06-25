# Cartório 2º Notas - Brain Index

**Última atualização**: 2026-06-26 16:30 BRT (sessão ZCode/Mavis + Gustavo Almeida)

## 🚦 Status Global

- **Gates**: 100% GREEN ✅
  - mypy: 0 errors (103 source files)
  - ruff: clean
  - pytest: **1205 passed** (+253 vs 952 baseline)
  - coverage: ≥87% (Lesson 107 — APPROVED_WITH_NOTE)
- **Tasks**: **~80/100** (~80% — SQUAD A24+B+BRAIN+DOCS completados nesta sessão + anteriores)
- **OpenClaw**: live (1M context + deepseek-v4-flash + thinking ON)
- **Telegram bot**: OK (webhook URL configurado em N8N workflow 31)
- **Supabase**: schema public completo (10 tabelas + RLS + webhooks + storage + realtime + vault + pgcrypto)
- **Health radar 7/7**: database, redis, n8n, openclaw, evolution, chatwoot, supabase — todos **online**

## 📊 Squads (resumo)

| Squad | Total | Done | % | Status |
|---|---|---|---|---|
| S0 Supabase Foundation | 10 | 10 | 100% | ✅ DONE |
| A API+DB Hardening | 25 | 24 | 96% | ✅ DONE (A24 único OPEN, agora DONE) |
| B N8N Polish | 25 | 25 | 100% | ✅ DONE (B12-B15 nesta sessão) |
| D LGPD Compliance | 25 | 25 | 100% | ✅ DONE (D09 portabilidade nesta sessão) |
| E OpenClaw CartorioBot | 8 | 7 | 88% | 🟡 IN PROGRESS |
| H Chatwoot CRM | 8 | 8 | 100% | ✅ DONE |
| J Obs + CI/CD | 10 | 5 | 50% | 🟡 IN PROGRESS |
| **BRAIN Cérebro local+prod** | 8 | 5 | 63% | 🟡 IN PROGRESS (BRAIN1-4 DONE) |
| **DOCS Download docs** | 5 | 5 | 100% | ✅ DONE (INDEX consolidado) |
| C Docs raiz | 25 | 5 | 20% | 🟡 IN PROGRESS |

**Total**: **~80/100 tasks DONE (80%)** 🎉

## 🌐 Endpoints Chaves

- API Health radar: https://api.2notasudi.com.br/api/v1/health/radar
- API V2 (alpha): https://api.2notasudi.com.br/api/v2/info
- API Docs (Swagger): https://api.2notasudi.com.br/docs
- API V2 endpoints: /api/v2/clientes, /api/v2/protocolos, /api/v2/emolumento/tabela
- API Metrics Prometheus: https://api.2notasudi.com.br/api/v1/metrics/prometheus
- API Endpoints catalog: `.brain/api-specs/catalog.py` (58 endpoints v1+v2)
- N8N: https://flow.2notasudi.com.br
- Chatwoot: https://chat.2notasudi.com.br (URL real: cartorio-chatwoot.dfgdxq.easypanel.host)
- OpenClaw Agent: https://agent.2notasudi.com.br/health → `{"ok":true,"status":"live"}`
- Supabase: https://supbase.2notasudi.com.br
- EasyPanel: https://easypanel.2notasudi.com.br
- VPS Hostinger: 187.77.236.77 (Tailscale: 100.99.172.84)

## 🏗️ Arquivos Cerebrais (Brain)

- `.brain/STRUCTURE.md` — schema do brain
- `.brain/loop-state.json` — estado compacto (gates + tasks)
- `.brain/index.md` — **este arquivo**
- `.brain/agents/README.md` — registry dos 7 agents ativos
- `.brain/api-specs/catalog.py` — 58 endpoints catalogados (BRAIN2)
- `.brain/lessons/sessao-2026-06-25.md` — 16 lessons L167-L182 (BRAIN3)
- `.brain/vps_sync.py` — VPS sync catalog 12 containers (BRAIN4)
- `.brain/tasks/README.md` — task bank operacional
- `.brain/plans/README.md` — planos operacionais

## 📚 Memória

- `.harness/memory/MEMORY.md` — 130+ lessons cross-session
- `.harness/PLAN_100_TASKS_LOOP.md` — plano 100 tasks dividido em squads
- `.brain/memory/2026-06-25.md` — timeline contínua da sessão
- `docs/platforms/INDEX.md` — 13 arquivos, ~10.000 linhas de docs técnicas

## 🚀 Últimos 10 Commits (sessão 2026-06-25/26)

- `57c9c6c feat(brain): BRAIN4 VPS Production Sync Catalog`
- `c88a179 docs(brain): BRAIN3 lessons learned sessao 2026-06-25`
- `62e1d27 docs(platforms): SQUAD DOCS1-5 INDEX consolidado`
- `e1f1de7 feat(brain): BRAIN2 API endpoints catalog`
- `0ae01e1 feat(whatsapp): B15 Meta templates — 11 templates`
- `9c49aa7 chore(brain): SESSION 2026-06-25 final — SQUAD B 100% DONE`
- `3c9c696 feat(chatwoot): B14 handoff macros — 10 macros`
- `ee81b2e feat(whatsapp): B15 Meta templates`
- `e89d44c feat(chatwoot): B13 canned responses 52 templates`
- `b48c1d4 feat(chatwoot): B14 handoff macros — 10 macros`

## 🔄 Loop Atual

- Session: **2026-06-25-zcode-4 → 5 → 6 (continua)**
- Current squad: BRAIN
- Next: BRAIN5-7 (index evolution ✅, VPS sync ✅ DONE) + A26 retomada + C24/C25
- Goal: 100 tasks ate fim do loop

## 📌 Pendências externas (precisam ação Gustavo)

- **DNS Cloudflare**: A records para `n8n.2notasudi.com.br` + `supabase.2notasudi.com.br`
- **WhatsApp QR**: escanear em `https://whatsapp.2notasudi.com.br/manager` (instance state=close)
- **OpenClaw password**: configurar no Control UI (logs mostram 401 unauthorized)
- **N8N OOM**: investigar memory limits (7 containers restart em 2h)
- **B06-FIX (Lesson 51)**: WF 00 interno — alerta Chatwoot falha. **HOLD** aguardando GO.

## 🎯 Próximas Trilhas

| Prioridade | Trilha | Status |
|---|---|---|
| 🔴 P0 | B06-FIX | HOLD aguardando Gustavo |
| 🟡 P1 | BRAIN5-7 (resto) | Próxima |
| 🟡 P1 | A26 retomada | Quando priorizar (3 bloqueios conhecidos) |
| 🟢 P2 | C24/C25 Uptime Kuma | Requer deploy externo |
| 🟢 P2 | E OpenClaw finalizar (1 task) | Baixa urgência |

---

**Modified by**: ZCode/Mavis (orquestrador) + Gustavo Almeida (CEO)
**Sessão ativa**: 2026-06-26 — loop contínuo
**Próxima atualização**: a cada commit significativo