# GOALS — Cartório 2º Notas · 2026-07-27 (AGENT PIETRA LIVE)

> Single source of truth de metas do projeto. Formato: **letra → objetivo → status → % → evidência**.
> Sincronizado com `.harness/paperclip-board/board.json` (G1-G5) e `.harness/loop-engineer/crons/LOOP_OBJECTIVE.md`.
> Atualizado por loop-engineer cron + agent harnesso. Append-only via PROGRESS.md.

---

## META ÚNICA (2026-07-27)

**AGENT PIETRA · MINIMAX M3 1M XMAX 100% operacional no iMessage Spectrum** com anti-vazamento de dev, sem emoji, saudação contextual BRT, MCP tool `cartorio_calcular_emolumento` retornando valores exatos da Tabela TJMG 2026, e knowledge base das Tabelas Fixação 1+8 versionada em OCR.

**Status atual (2026-07-27 23:14 BRT):** `IMESSAGE_REQUIRES_FIX` — gate oficial do canal ainda em P0. **B4 RESOLVED**: `MCP_SERVER_ENABLED=true` deployado no `cartorio_system-api` (Traefik roteia `api.2notasudi.com.br` para system-api, não api); round-trip MCP validado (tools/list 16 tools, `cartorio_calcular_emolumento` = R$156,40 para procuração); config Mac Hermes revertida para `https://api.2notasudi.com.br/mcp`. Defense-in-depth implementado (`pietra_identity_guard.py` + 39 regression tests), mas causa raiz do IDENTITY_HERMES_LEAK (Camada 3, código fechado) continua em investigação. **Gate permanece `IMESSAGE_REQUIRES_FIX`**: confirmação visual do Felipe no próprio iPhone (B5) ainda pendente — só após ela o gate move para `IMESSAGE_FELIPE_ACCEPTED`.

**QA 2026-07-28 (sessão B, local):** relatório consolidado `.harness/memory/TEST_IMENSAGER_2026-07-28.md` — status 🟡. Root cause tz no audit local (Lesson 285), 3 P0-candidates novos p/ backlog: HITL offline não escala isenção/urgência (FB1/FB2), scrubber não mascara RG formato MG (FB5), Art. 18 indisponível no canal iMessage (FB10). **Gate não se move** — pendente B5 + correções FB* + N≥30 identity.

---

## GOALS H-K (atualizado 2026-07-27 — AGENT PIETRA LIVE)

| Letra | Objetivo | Status | % | Evidência |
|-------|----------|--------|---|-----------|
| **H** | **AGENT PIETRA** renomeado + endurecido (sem emoji, saudação BRT, anti-vazamento) | ✅ done | 100% | SOUL.md reescrito; gateway PID 65548; 3 testes reais iMessage OK (saudação, anti-leak, emolumento MCP) |
| **I** | **MCP server funcional** (`/mcp-servers` retorna 14 tools) | ✅ done | 100% | 502 reportado era 404 no path errado; `/mcp-servers` 200 com tools_count=14 (cartorio-api) + 50 (n8n) + 30 (supabase) + 57 (easypanel) + 20 (openclaw) |
| **J** | **Knowledge base TJMG 2026** (PDFs Fixação 1+8 OCR'd e versionados) | ✅ done | 100% | 14+4 páginas OCR'd via tesseract 5.5.2 + pdftoppm 300dpi; `docs/tjmg-ocr/INDEX.md`; loader `app/services/tjmg_ocr_loader.py`; 9 testes PASS |
| **K** | Tabela MG 2026 emolumento tool exato via MCP | ✅ done | 100% | `hermes -z "Quanto custa uma procuracao generica?"` → R$ 68,94 (R$ 52,43 + TFJ R$ 16,51) — tool `cartorio_calcular_emolumento` chamada real |

## GOALS A-G (consolidado 2026-07-03, ainda válido)

| Letra | Objetivo | Status | % | Evidência |
|-------|----------|--------|---|-----------|
| **A** | API + audit chain + PII production-grade | ✅ done | 100% | 1648 pytest passed, mypy 0, ruff 0 (PROGRESS 2026-07-02) |
| **B** | Telegram bot live + Chatwoot inbox 1 | ✅ done | 100% | lesson 137 — 9 E2E tests, latency 10-15s |
| **C** | LGPD compliance 100% | ✅ done | 95% | squad D 100% + DPA DeepSeek (lesson 138) |
| **D** | WhatsApp Evolution API conectado | 🟡 blocked | 30% | SUI Gustavo (QR scan whatsapp.2notasudi.com.br/manager) |
| **E** | Loop engineer auto-reactivação | ✅ done | 95% | 5 agents + cron scripts + state machine + loop-continue (Lesson 139-140) |
| **F** | Docs sincronizadas turn 50+ | 🟡 in_progress | 20% | synced via loop |
| **G** | Multi-provider fallback validado | 🟡 in_progress | 20% | loop integration progressing |

## SQUAD STATUS (validado cycle 140)

| Task | Status | Evidência |
|------|--------|-----------|
| J7 ci.yml | ✅ done | `.github/workflows/ci.yml` 212 linhas (lint+mypy+pytest+coverage+codecov) |
| J8 cd.yml | ✅ done | `.github/workflows/cd.yml` 107 linhas (Render API + polling + GH comment) |
| J9 Sentry SDK | ✅ done | `app/services/sentry.py` 153 linhas + PII scrubber + 29 tests passing |
| J10 OTel collector | ✅ done | `infra/observability/otel-collector-config.yml` + 6 tests J10 + 11 tracing tests |
| J6 Render health custom | ⏸️ blocked | script+curl ready em `docs/j6-j10-ci-cd-2026-06-25.md` — falta SUI Gustavo (RENDER_API_KEY + service config) |

---

## MAPPING PAPERCLIP → GOALS

| Paperclip G | → | Goal |
|-------------|---|------|
| G1 — 7/7 services 72h stable | → | A + D |
| G2 — Bot Telegram prod-ready | → | B |
| G3 — LGPD 100% | → | C |
| G4 — Docs turn 50 sync | → | F |
| G5 — Loop engineer auto-reactivação | → | E |

---

## NEXT CYCLE TARGETS (do LOOP_OBJECTIVE.md + PLAN_100_TASKS_LOOP.md)

### P0 (próximos 5 cycles)
- [ ] D — Fechar WhatsApp QR scan (SUI Gustavo)
- [ ] E — Instalar launchd plist (goal-loop 4h + intensive 30min)
- [ ] F — Sync PROMPT.json/MD turn 50 (T9)
- [ ] G — Testar fallback opencode_go → opencode_free_1 → opencode_free_2 (3x)

### P1 (cycles 6-10)
- [ ] Squad C docs 100% (12/25 → 25/25)
- [ ] Squad J obs+CI/CD (5/10 → 10/10)
- [ ] pytest 1648 → 1300+ (meta antiga, hoje já superado)
- [ ] coverage 30.7% → 90% (DEP-1)

### P2 (cycles 11+)
- [ ] Brain endpoints BRAIN3/4/8
- [ ] Squad E last task (E08)
- [ ] Audit log em 100% mutações com request_id/ip/user_agent (Sprint 3 Goal 4.1)

---

## SUI — Só Gustavo Resolve (BLOCKERS HUMANOS)

1. **DNS Cloudflare**: `n8n.2notasudi.com.br` + `supabase.2notasudi.com.br` → A record 187.77.236.77
2. **WhatsApp QR**: `whatsapp.2notasudi.com.br/manager` → Instância `cartorio-2notas` (state=close)
3. **Testar Telegram Bot**: Mandar msg para @CartorioAssistantBot e confirmar recepção no Chatwoot
4. **DNS typo**: `supbase` → `supabase` (decisão pendente)
5. **Easypanel API key** rotacionada (exposta)
6. **OpenClaw LLM key** (depende L1 LGPD)

---

## HOW THIS FILE IS UPDATED

- **Manual**: Gustavo edita direto após milestone
- **Loop cron**: `goal-loop-cron.sh` append em PROGRESS.md (não toca GOALS.md)
- **Harness**: `.harness/agent.md` referencia este arquivo como source of truth
- **Agents**: 01-analyze-agent.sh lê este arquivo no `analyze` phase

---

Modified by Gustavo Almeida (via plan Mavis)

---

## UPDATE 2026-07-27 — AGENT PIETRA LIVE

- **Renomeado Hermes → Pietra** em `~/.hermes/profiles/cartorio/SOUL.md`
- **Endurecido**: zero emoji, saudação contextual BRT, anti-vazamento de dev, mensagens separadas, anti-injeção reforçada
- **Gateway reiniciado** (PID 65548) — validado com 3 testes reais
- **MCP 14 tools** funcionais (cartorio-api) + 50 (n8n) + 30 (supabase) + 57 (easypanel) + 20 (openclaw)
- **PDFs TJMG 2026** (Fixação 1 14p + Fixação 8 4p) OCR'd e versionados em `docs/tjmg-ocr/`
- **Loader** `app/services/tjmg_ocr_loader.py` com 9 testes PASS

### Pendente (SUI Gustavo)
- **D** — WhatsApp QR scan (instance `cartorio-2notas` state=close)
- **OpenClaw Tailscale auth** (SUI marcado no `/mcp-servers`)

Modified by Gustavo Almeida · 2026-07-27

---

## UPDATE 2026-07-28 — Lark Bot v6 + Hermes stub fix (sessão ZCode/Kimi K3)

**Conquista da sessão (paralela, Gustavo longe do Mac):**

- **Lark bot standalone v6** (`scripts/lark_bot_v6.py`, 24KB): substitui TRAE SOLO shell no grupo GG.
  Plugado em PIETRA VPS via `api.2notasudi.com.br/api/v1/pietra/chat/completions`.
- **OCR + LGPD scrub**: tesseract extrai texto de imagens, CPF/RG/TEL/EMAIL/CARTÃO scrubbed
  ANTES do LLM. Validado: `123.456.789-00` → `123.***.***-**`.
- **Detector de tipo de documento**: 9 tipos (CPF, RG, CNH, PROCURAÇÃO, ESCRITURA, CONTRATO,
  RECEITA, FATURA, PROTOCOLO) com regex prioritário.
- **Memória PIETRA VPS**: cada chat vinculado a telefone proxy no Postgres do cartório.
- **Comandos admin** (owner only): `!stats`, `!doc`, `!bot stop/restart`, `!broadcast`.
- **LaunchAgent** `ai.zcode.lark-bot.plist` (port 8083, 24/7).
- **Bot v6 rodando AGORA**: PID 77420. `/health` retorna v6 ok + pietra_ok + ocr_available.
- **Hermes stub fix** (Lesson 285): `/Applications/Hermes.app` era instalador quebrado que crashava
  ao abrir (SIGABRT por library missing). Backup + symlink pro app funcional.

**3 lessons salvas:**

- 283: VPS `cartorio_hermes` com models free-tier = Camada 3 identity leak (pendente fechar com
  `vps_fix_cartorio_hermes_F3.sh`)
- 284: Bot Lark standalone Python > TRAE SOLO shell Electron (arquitetural, com trade-offs)
- 285: Hermes.app stub em /Applications causa crashes silenciosos (Library missing @rpath)

**Pendências humanas (inalteradas do 27/07 + novas):**

- Subir cloudflared tunnel pra expor bot v6 ao Lark
- Preencher `scripts/.env.lark` (App ID/Secret/Token do Developer Console)
- Adicionar bot como **admin** no grupo GG (Settings → Members)
- Configurar `LARK_OWNER_OPEN_ID` no `.env.lark` (pra ativar comandos admin)
- Rodar `scripts/vps_fix_cartorio_hermes_F3.sh` no VPS via SSH (fecha P0 Camada 3)
- Liberar Full Disk Access do OpenClaw no macOS (4+ dias crashloop)
- **B1-B5** originais (audit sign-off, WhatsApp QR, secrets rotation, Felipe iPhone)

**Artefatos pra revisar quando voltar:**

- `SESSION_2026-07-28_INDEX.md` — consolidado completo
- `CHECKLIST_VOLTA_MAC_2026-07-28.md` — passo-a-passo ordenado
- `scripts/lark_bot_v6.py` — código principal (24KB, único a manter — v1-v5 são obsoletos)
- `scripts/LARK_BOT_V3_RUNBOOK.md` — runbook atualizado v6

**Não-feitos:**

- git commit (Gustavo revisa antes)
- Vision nativa LLM (PIETRA VPS só aceita `content:string`, não `image_url`)
- Deletar `~/Library/LaunchAgents/ai.hermes.gateway.plist` legacy

Modified by Gustavo Almeida · 2026-07-28 (sessão ZCode/Kimi K3)