# SUPER RELATÓRIO — Projeto Cartório 2º Notas UDI
## Período: 22/06/2026 → 28/07/2026 (37 dias de atividade real)

> Compilado em 2026-07-28 por orquestração de 6 subagents sobre todas as fontes de verdade:
> git (1.398 commits), MEMORY.md (Lessons 1–296), .brain/memory (39 logs diários),
> docs/sessions + reports + plans (338 docs), .trae/documents, GOALS.md, task-bank.json,
> ROADMAP.md, TASKS.md e inventário técnico completo do backend.

---

# 1. RESUMO EXECUTIVO

Em **37 dias**, o projeto saiu do **zero absoluto** (primeiro commit = skeleton do backend,
22/jun) para um **sistema de produção validado** com bot de IA multicanal, LGPD-by-design,
audit log imutável e agente pessoal "Pietra" com identidade blindada.

| Métrica | Valor |
|---|---|
| Commits | **1.398** (~38/dia; pico 292 em 25/jun) |
| Linhas adicionadas/removidas | +2.382.152 / −74.861 (inflado por artefatos; código efetivo é fração) |
| Testes | **6.489 passing** (5.313 funções `def test_`, 402+ arquivos) |
| Coverage | ≥90% (gate CI, chegou a 95,04%) |
| Lessons aprendidas | **296 numeradas** (~246 registradas, 93 de junho arquivadas) |
| Docs produzidos | 267 docs raiz + 35 sessões + 23 relatórios + 13 planos |
| Workflows n8n | 61 JSONs versionados; 39 restaurados inativos no banco live |
| MCP tools | servidor autenticado; profile Hermes = 1 selecionada |
| Endpoints API | 50+ (25 routers v1) |
| Models DB | 14 |
| Incidentes P0 documentados e resolvidos | 10+ |
| Super-planos executados | 7 (v25, G6, G7, G8, G9, E25, F0-F6) |
| Canais | 4 (Telegram, WhatsApp, iMessage, Lark) + Web/API |

**Versão:** v0.4.5 → **v0.6.0**. **Autor único dos commits:** Gustavo Almeida (com trabalho
de ~15 agentes de IA distintos orquestrados).

---

# 2. O QUE O SISTEMA É HOJE

**Backend API do 2º Serviço Notarial de Uberlândia** (CNS 05.799-2) — bot WhatsApp /
Telegram / iMessage / Lark / Web com:

- **LGPD-by-design**: PII scrubbing em 3 camadas (input → pre-LLM → output), 7 endpoints
  de direitos Art. 18 (acesso, correção, anonimização, portabilidade, eliminação, oposição,
  não-automação), RIPD v1.4, DPA MiniMax, Privacy Policy v3, retenção automatizada (5y/2y),
  DLQ com encryption-at-rest Fernet (Art. 46), export CNJ com dupla aprovação.
- **Audit log imutável**: SHA256 hash chain + HMAC com rotação de chave, verificação
  diária (cron), dead-man's switch a cada 15min, RLS no Postgres.
- **HITL obrigatório**: todo protocolo nasce `DRAFT`; escrevente valida; bot nunca decide
  isenção/urgência/ato jurídico sozinho.
- **Persona Pietra**: agente pública com identity guard (17 regex + accent-bypass NFD),
  outbound guard (infra leak + language mixing), sanitizador determinístico pós-LLM,
  60+ frases proibidas, response planner de 14 steps, conversation state L0-L4.
- **Stack**: FastAPI 0.115 + SQLAlchemy 2.0 + Pydantic v2 + Postgres 17 (pgvector) +
  Redis 8.8 + Evolution 2.3.7 + n8n + Hermes Agent + MiniMax-M3 (fallback M2.7-HighSpeed)
  + LiteLLM (cadeia de até 11 providers) + Traefik (6 domínios SSL) + Docker Swarm
  (EasyPanel) + Prometheus/Grafana/Loki/Alertmanager.

---

# 3. LINHA DO TEMPO — SEMANA A SEMANA

## Semana 1 (22–28/jun) — FUNDAÇÃO · 657 commits (semana recorde)

- **22/jun**: Nascimento do repo. Backend skeleton Sprint 0, coverage 99,71%.
- **23/jun**: SUPER_PLANO v0.6.0, merge T22 N8N MCP trigger, incidente SSH.
- **24/jun**: ADR-010 (DB_HOST IP direto — bug de alias Swarm). Regra permanente:
  **"NUNCA rotacionar chaves sob pressão"** (D29-G1).
- **25/jun**: Docs das 5 plataformas (Evolution/N8N/Chatwoot/Supabase/Redis), auth
  migration 7 endpoints, INC-004 OpenClaw restaurado. **292 commits no dia** (recorde).
- **26/jun**: Validação 6-agent: **95% production ready**, 8/8 serviços GREEN, 1.549
  testes. Incidente Tailscale → cascade Supabase/Traefik → recuperação total. API v0.6.0.
  Achados críticos: JWT secret default Supabase, Redis maxmemory=0.
- **25/jun**: Nascimento do `.brain/` (memória de sessão diária) + BRAIN1-8 + 5 endpoints
  `/api/v1/brain/`. 40.739 chamadas LLM num só dia.

## Semana 2 (29/jun–05/jul) — LGPD LIVE + TURBULÊNCIA · 197 commits

- **29/jun**: **LGPD D26-D32 LIVE em prod** (7 endpoints JWT+DPO, 48 testes), compliance
  68%→90%. WhatsApp real: QR escaneado, chain E2E. Deploy Mac M1→VPS amd64 (buildx+QEMU).
- **30/jun**: Chain LLM 10→**11 providers**. WhatsApp respondendo E2E com Pietra.
  Hardening Fail2ban/iptables/Traefik auth. PDF executivo para Felipe/Djalma.
- **01/jul**: **Dia mais turbulento** ("TÁ TUDO QUEBRADO"): N8N crash pós-migração →
  recuperação total (login SQL bcrypt, 30 workflows reimportados). **Decisão: REMOVER o
  N8N** (migração OpenClaw + API direta — depois revertida). Telegram 20/20 E2E.
  **INC-2026-07-01-A: vazamento de chave DeepSeek + credenciais Hostinger no chat** →
  política de secrets (dono decidiu não rotacionar).
- **02/jul**: 6 hosts fantasma no Swarm → deploy corretivo. Chatwoot bootstrap completo.
  Epopeia do token Cloudflare (10 estratégias falharam → HOLD humano permanente).
- **03/jul**: TRAE CENTRAL FULL MAX — loops autônomos (master-loop 5min, watchdog 1min,
  YOLO-100t 10min). MEGA BATCH: 19 skills + 12 MCPs + 6 subagents (total 98 skills).

## Semana 3 (06–12/jul) — COBERTURA + VPS P0 · 104 commits

- **06/jul**: Ciclo Antigravity completo (redis_client singleton, 4 módulos LGPD, +35 testes).
- **07/jul**: Coverage 87,65%→91,10% (gate 90% atingido). Jules 17→99%.
- **08/jul**: **P0: VPS Hostinger TOTALMENTE DOWN** (6 domínios timeout) → bypass via
  Cloudflare tunnel, bot 7/7 em <2s. Coding-VPS: 17/17 agents LLM E2E, MCP orchestrator
  92 tools, 89 serviços descobertos. MiniMax-M3 1M XMax Thinking ativado.
- **09/jul**: P0 Telegram HITL — `fn_auto_audit` sem hash/HMAC (500 em /atendimento) →
  fix live + migration 0020.

## Semana 4 (13–19/jul) — SUPER-PLANOS EM CASCATA · 252 commits

- **13/jul**: Simulação WhatsApp 10 personas (5 TRAE + 5 Antigravity). Bot Telegram morto
  (token revogado no BotFather).
- **14/jul**: **P0 OUTAGE: 7/9 canais 502** — Easypanel sobrescreveu envs do Supabase.
  OUTAGE_RECOVERY_RUNBOOK criado. Coverage 94→95,04%.
- **15/jul**: **SUPER PLANO 100/100 (F0-F6) em ~3,3h com 8 sub-agents paralelos** —
  maior entrega coordenada: RIPD D21-D25, Privacy Policy, Erasure Orchestrator, DPO
  Dashboard, SOLID/DRY/KISS refactor.
- **16/jul**: **25 waves G6 em 1 dia**: mutation testing (mutmut), Hypothesis, 5 gates CI,
  OpenAPI snapshot+diff, LGPD consent API + DSAR, Loki/Promtail, SLO Grafana.
- **17/jul**: G7 waves: índices DB, backup n8n versionado, DLQ drill, HMAC PREV + CI gates.
- **19/jul**: **SUPER PLANO G8 100/100 concluído** (com "honesty gate": 43/100 com
  evidência real — política de só marcar com commit+testes+lesson). CNJ export LGPD
  dual-control. 3 contas OpenCode Zen (14 providers).

## Semana 5 (20–26/jul) — HARDENING + MULTICANAL · 87 commits

- **20/jul**: P0 Telegram: validação bot + roteamento 3-tier Zen + suíte 1000 interações
  (31/31 WORK). G9 criado. MiniMax contextWindow 131k→1M.
- **22/jul**: **Decisão LLM**: cérebro = MiniMax Token Plan ($20, IFBench #1 +
  anti-alucinação #2) + Groq whisper. Regra de ouro: assinatura consumer ≠ backend de bot.
- **23/jul**: Rotação MINIMAX_API_KEY sem rebuild (`docker service update --env-add`).
- **24/jul**: WhatsApp webhook **HMAC fail-closed** (vulnerabilidade real: `return 401`
  comentado) + dual-auth (Evolution Baileys não assina body). Circuit breaker. **Root
  cause audit chain quebrada desde 09/07**: trigger PL/pgSQL canonicalizava JSON diferente
  do Python — 158 entradas legacy viraram decisão DPO (ADR-030).
- **25/jul**: **FULL QA: 6.049 passed / 92,44% / 39 commits**. Ledger honesto G9 49/100
  (claim 75 **revertido** por falta de evidência — Lesson 233 "ledger, não entusiasmo").
  RC_READY técnico; bloqueios 100% humanos.
- **26/jul**: **Cartorio OS multicanal v1** (Hermes profile + Spectrum + MCP 14 tools).
  ADR-031: arquitetura multicanal definitiva.

## Semana 6 (27–28/jul) — PIETRA + iMESSAGE + LARK · 102 commits

- **27/jul**: Hermes deploy Swarm prod. **P0 IDENTITY_HERMES_LEAK** ("Sou o Hermes" em
  3/10 msgs): criado `pietra_identity_guard.py` (39 testes). Rename Hermes→Pietra no
  SOUL.md. PIETRA P0 hardening 16 fases. Dossiê deep research Tabelionato Djalma.
  OCR de 2 PDFs TJMG. Campanha iMessage 10K: 6/10 → root cause 00:40: **state.db congela
  system_prompt na criação da sessão**.
- **28/jul** (dia mais denso): BUG P0 gateway Mac (constante deletada → NameError → 100%
  erros) resolvido. Rogue gateway sem `--profile` eliminado (2 sidecars no mesmo Spectrum).
  Consumidor VPS paralelo neutralizado. **P0 emolumentos**: tabela era placeholder
  ("TODO Gustavo") servindo valores errados → tabela oficial Portaria CGJ/TJMG 8.664/2025
  (autenticação 28,90→11,21; procuração 156,40→68,94). **P0 MiniMax inline tool_call
  vazando markup** ao cliente (3 formatos). **Campanha #2: 81/100, gate de identidade
  VERDE (0/100 "Sou o Hermes", N=100)**. Bulk 10K HTTP: 7.481 PASS. Lark bot v6 (OCR +
  LGPD scrub + detector de documentos). QA: **6.330→6.489 testes**. Purga de
  OPENCODE_GO_API_KEY de 14 arquivos. **Felipe liberado no Lark** e comprovado ao vivo
  às 22:18; Gustavo permaneceu autorizado. Não existe sincronizador automático de
  pairing — os dois usuários já estavam nos stores global e do profile.

---

# 4. MAPA DE AGENTES — QUEM FEZ O QUÊ

| Agente | Papel no projeto | Trabalhos marcantes |
|---|---|---|
| **ZCode / Mavis** | Orquestrador dominante | Skill zcode-fallback, consolidações, Lark bot v6, campanhas iMessage, defesa identity leak, commits assinados |
| **Kimi (K3 / K2.6 / K2.7-HighSpeed)** | Sessões de código + Lark | Etapa 4 runtime inventory, gateway TS 12/12, Lark bot v6 (com ZCode), profile kimi no Hermes |
| **Codex (GPT 5.6 SOL)** | Sessões paralelas | Threads de orquestração VPS, profile codex no Hermes |
| **TRAE** | Loops autônomos + simulações | TRAE CENTRAL FULL MAX (YOLO loop), 5 personas WhatsApp, integração coding-vps MCP |
| **Claude Code** | Hub supremo + fallback | CLAUDE-CODE-SUPREMO hub, Opus 4.6/5 como fallback topo da chain |
| **Grok** | Builds e runtime truth | "Grok-Build Telegram delivery" (deploy live + fix fn_auto_audit), Runtime Truth Etapa 4 (reinstalou Hermes gateway) |
| **Antigravity (AGY)** | Provider + ciclos completos | Provider OAuth2/Gemini (11º da chain), ciclo 07-06 (mypy 0 + LGPD), 5 personas WhatsApp |
| **Hermes Agent** | Runtime do agente em produção | Gateway cartorio (iMessage + Lark), MiniMax-M3, 23 toolsets, 80+ skills, thin-shell → VPS |
| **MiniMax (M3 / M2.7-HS)** | Cérebro LLM principal | Todos os canais; M3 1M XMax Thinking; M2.7-HighSpeed p/ latência |
| **Sub-agents cartorio-*** (9 reins) | Execução especializada | dev, lgpd, n8n, data, evolution, front, security, sre, watchdog — SUPER PLANO F0-F6 com 8 paralelos |
| **Jules (Google)** | Fallback terciário + cobertura | API REST async, cobertura 17→99% |
| **OpenCode (Go/Zen/free)** | Providers da chain | 3 contas Zen, 14 providers, opencode_go (alias MiniMax) |
| **GPT / DeepSeek / Groq / Mistral / Gemini** | Chain de fallback | deepseek-v4-flash, gpt-5.5 (OpenClaw legacy), groq compound, kimi-k2.6, nemotron-3-ultra |

**Loops/automação criados**: master-loop (5min), cartorio-yolo-100t (10min), master-watchdog
(1min), G6/G7/G8/G9/E25 wave orchestrators, campanha iMessage com trigger de linha quieta.

---

# 5. CANAIS — ESTADO FINAL (28/07)

| Canal | Estado | Evidência |
|---|---|---|
| **Telegram** | 🟢 Operacional | Bot @TestCartorioBot, webhook HMAC + idempotência, 20/20 E2E, subset 1000 pts 31/31, debounce, typing, 7 comandos |
| **Lark/Feishu** | 🟢 TRANSPORT_E2E_PASS / 🟡 LGPD_RELOAD_PENDING | Hermes 1/1 Swarm, MiniMax-M3 + fallback M2.7-HS, escopo oficial atual Gustavo+Felipe, pairings idênticos, **Felipe respondido ao vivo 22:18**; filtro de PII nos logs aguarda janela controlada |
| **iMessage** | 🟡 Operacional em DM (não certificado p/ grupo) | DM real ponta-a-ponta (iPhone→Photon :8793→thin-shell→VPS Pietra→MiniMax→MCP), identity gate VERDE N=100, emolumento oficial via tool call em prod |
| **WhatsApp** | 🟡 Código em paridade com Telegram; E2E assinado pendente | Evolution 2.3.7 1/1, HMAC dual-auth fail-closed, instância cartorio-2notas (QR = SUI) |
| **Web/API/MCP** | 🟢 Operacional no contrato testado | api.2notasudi.com.br 200, /mcp autenticado, `hermes mcp list` = 1 tool selecionada |

---

# 6. INFRA VPS — ESTADO FINAL

**VPS Hostinger** (187.77.236.77 / Tailscale 100.99.172.84), Docker Swarm via EasyPanel,
Traefik :80/:443, 6 domínios SSL.

| Serviço | Estado | Nota |
|---|---|---|
| cartorio_system-api | ✅ 1/1 | Backend real (api.2notasudi) — Pietra, audit, PII, MCP |
| cartorio_hermes | ✅ 1/1 | Gateway Lark (MiniMax-M3), perfil público final-only |
| cartorio_whatsapp-api | ✅ 1/1 | Evolution 2.3.7 (novo nome) |
| cartorio_banco_de_dados | ✅ 1/1 | pgvector/pg17 |
| cartorio_memory-cache | ✅ 1/1 | Redis 8.8 |
| cartorio_n8n (+runner) | ⚠️ 1/1, HTTP 200 | 39 workflows restaurados inativos; 0 execuções, credenciais e API keys; ativação funcional pendente |
| supabase (auth/storage/realtime/postgrest) | ✅ recuperados 28/07 | DB_HOST legado + postgrest órfão corrigidos |
| Chatwoot / OpenClaw | ⏸️ REMOVIDOS 27/jul | Volumes preservados; **decisão Gustavo: restore vs decomissionar** |
| Zumbis (api, evolution-api, redis, supabase) | 0/0 | Legados intencionais |

**Mac do Gustavo** = transport-only para iMessage (Photon :8793, LaunchAgent
ai.hermes.gateway-cartorio). O Lark operacional desta auditoria roda no Hermes da VPS.
A regra "MacBook = só UI" vale para o backend, com exceção física do canal iMessage.

---

# 7. INCIDENTES P0 — REGISTRO E BLOQUEIOS ABERTOS

1. **08/jul** — VPS Hostinger down total (6 domínios) → Cloudflare tunnel bypass.
2. **09/jul** — Telegram HITL 500: `fn_auto_audit` sem hash/HMAC → migration 0020.
3. **14/jul** — Outage 502 em 7/9 canais: Easypanel sobrescreveu envs Supabase.
4. **01/jul** — Vazamento de credenciais no chat → política de secrets + scanner CI fail-closed.
5. **24/jul** — Audit chain quebrada desde 09/07 (trigger divergia do verificador) → ADR-030.
6. **24/jul** — Webhook Evolution sem validação HMAC (`return 401` comentado) → fail-closed dual-auth.
7. **27/jul** — IDENTITY_HERMES_LEAK ("Sou o Hermes") → guard 3 camadas + N≥30 rule + rogue gateways eliminados.
8. **28/jul** — Emolumentos placeholder em prod (valores errados ao vivo) → Portaria 8.664/2025 com lastro PDF.
9. **28/jul** — MiniMax inline tool_call markup vazando ao cliente (3 formatos) → conversor estruturado + 13 testes.
10. **28/jul** — Gateway Mac 100% erro (constante deletada em diff local) → restore + canário obrigatório.
11. **28/jul** — Exposição de SUPABASE keys em diagnóstico → regra: nunca grep env sem sed.

**Padrões aprendidos (transversais)**: evidência ao vivo > claims · fail-closed em
segurança · HITL/DRAFT em atos jurídicos · reconciliar git antes de despachar lanes ·
CONNECTED ≠ OPERATIONAL (só round-trip real valida).

---

# 8. LGPD — ENTREGAS COMPLETAS

- 7 endpoints Art. 18 (D26-D32) LIVE com JWT+DPO · portabilidade D09 · DELETE /cliente
- PII scrubbing 3 camadas + output scrub (P0.7) + response shape pii_blocked (P0.8/0.9)
- Audit log SHA256+HMAC append-only, RLS, rotação HMAC (PREV), verificação diária
- RIPD v1.4 · DPA MiniMax READY_TO_SIGN · Privacy Policy v3 · inventário de dados ·
  relatório ANPD · Erasure Orchestrator · DPO Dashboard
- DLQ: encryption-at-rest Fernet (Art. 46) + expiração two-phase 30d/180d (Art. 16+37) +
  alertas Telegram sem payload
- Retenção automatizada (conversas 5y/2y, job diário 03:00 BRT) · anonimização de stale data
- Export CNJ: só agregados, dupla aprovação, manifesto SHA-256, transmissão nunca automática
- Consent API + DSAR endpoint + consentimento em uploads · handoff multicanal pseudonimizado

---

# 9. NÚMEROS DE QUALIDADE

| Data | Testes | Coverage | Marcos |
|---|---|---|---|
| 22/jun | ~100 | 99,71% | skeleton |
| 26/jun | 1.549 | 90,29% | validação full |
| 07/jul | 2.302 | 91,10% | gate 90% |
| 14/jul | — | 95,04% | pico coverage |
| 19/jul | 3.270 | — | G8 100/100 |
| 25/jul | 6.049 | 92,44% | FULL QA 39 commits |
| 28/jul | **6.489** | ≥90% | estado atual |

Gates CI: ruff 0 · mypy strict 0 · coverage ≥90 · secrets scan fail-closed · OpenAPI
snapshot diff · dead-code audit · audit chain verify.

---

# 10. FONTES DE VERDADE / DOCUMENTAÇÃO

- **PROGRESS.md** (175KB) — log append-only de todas as sessões (fonte primária)
- **MEMORY.md** — 296 lessons (~153 em julho + 93 junho arquivadas)
- **.brain/memory/** — 39 logs diários (25 dias ativos de 34; ~1.034 entradas timestamped)
- **docs/** — 267 docs + 35 sessões + 23 relatórios + 13 planos + 24 ADRs + C4 completo
- **GOALS.md / STATUS.md** — estado canônico e live
- **task-bank.json** — 100 tasks: P0 6/10 done (2 SUI, 2 decisão), P1 1/30, P2 17/60
- **TASKS.md** — 132 done / 317 pending na árvore Epic/Sprint/Task

---

# 11. PENDÊNCIAS (todas decisão/ação humana — SUI Gustavo)

1. **Chatwoot + OpenClaw**: restaurar (volumes preservados, restore barato) ou
   decomissionar (ajustar radar + docs) — removidos 27/jul ~23:53.
2. **Rotação SUPABASE_ANON_KEY + SERVICE_ROLE_KEY** (P0 segurança, expostas 28/jul).
3. **DNS Cloudflare**: 3 A records (chatwoot/n8n/supabase) — arrastado desde 02/jul.
4. **QR WhatsApp Evolution** (instância cartorio-2notas, state=close).
5. **Token Telegram BotFather** regenerado em 13/jul (bot de prod).
6. **iMessage**: certificação de grupo + multiusuário + PHOTON_ALLOW_ALL_USERS (decisão).
7. **Lark LGPD**: ativar o filtro de PII dos logs em replacement controlado e repetir
   um round-trip sintético; o transporte do Felipe já passou.
8. **n8n**: revisar os 39 workflows restaurados inativos, recriar credenciais/API key
   pela UI e ativar um por vez com teste.
9. loop-state.json stale desde 17/jul; radar evolution aponta p/ serviço legado.
10. Fase 4 ROADMAP (ICP-Brasil, assinatura digital, pagamento) — não iniciada.
11. Gap de qualidade: memória do modelo (856 fails no bulk 10K) — maior dívida de QA.

---

# 12. CONCLUSÃO

37 dias. 1.398 commits. 6.489 testes. 296 lessons. 4 canais. Mais de 10 incidentes
P0 tratados, com bloqueios restantes agora explicitados. O projeto tem hoje um
backend endurecido, controles LGPD extensos, uma agente com identidade pública
protegida e memória institucional das decisões. O estado final ainda depende da
ativação do filtro de logs, da restauração funcional do n8n e dos E2Es dos canais
que permanecem amarelos; processo saudável isolado não foi promovido a operacional.

**Assinatura de compilação**: orquestrador ZCode + 6 subagents (git, lessons, brain,
docs, goals, canais) · 2026-07-28 · Modified by Gustavo Almeida
