# PLANO 100 TASKS — Bot Telegram → WhatsApp (2026-07-09)

> **FOCO 100%**: Validar Bot Telegram (já 100% funcional via LiteLLM Proxy) como prova-de-conceito e ESPELHAR 100% do código Telegram para WhatsApp via Evolution API.
> **Modo**: 4 agents paralelos (Antigravity-Gemini-3.5-High, OpenCode-MiniMax-M3-High, Grok-Build-Grok-4.5-High, Claude-Code-MiniMax-M3-High) no mesmo repo/branch/ambiente.
> **Workspace**: `/Users/gustavoalmeida/projetos/Cartorio/` (MacBook-Pro, master branch).

## 🎯 META ÚNICA

**Bot Telegram 100% production-ready (validado 5x E2E) + WhatsApp Evolution API 100% espelhado (mesmo código, mesma UX, mesmo debounce, mesma LGPD, mesma fallback chain) — tudo sob CI verde (mypy 0 / ruff 0 / pytest ≥2318).**

## 🏆 10 GOALS (1 plano → 10 goals → 100 tasks)

| # | Goal | Status atual | Meta | Tasks |
|---|------|--------------|------|-------|
| **G1** | Bot Telegram E2E validado 5x consecutivas | ✅ 8/8 sent=True | Re-rodar 5x + stress + fallback | 10 |
| **G2** | Pipeline compartilhado `chat_pipeline.py` (Telegram↔WhatsApp) | ❌ não existe | Extrair lógica comum | 10 |
| **G3** | Bot WhatsApp `/api/v1/webhook/evolution` espelhado | 🟡 parcial | 100% paridade c/ Telegram | 10 |
| **G4** | Fallback chain LiteLLM→nemotron→opencode_free_1/2/3→opencode_go validado 3x | 🟡 1x | Validar 3x retry com troca modelo | 10 |
| **G5** | LGPD compliance (PII scrub 3 camadas + consent + audit) | ✅ OK | Adicionar consent banner WhatsApp | 10 |
| **G6** | Observability (logs estruturados + métricas + traces) | 🟡 parcial | OpenTelemetry spans em chat_pipeline | 10 |
| **G7** | Testes E2E (5 Telegram + 5 WhatsApp + 3 fallback) | 🟡 8 testes Telegram | Criar 5 WhatsApp + 3 fallback | 10 |
| **G8** | Documentação (README + ARCHITECTURE + FALLBACK_CHAIN + TELEGRAM_GUIDE + WHATSAPP_GUIDE) | 🟡 5/25 docs | 25/25 docs raiz | 10 |
| **G9** | CI verde (mypy 0 + ruff 0 + pytest ≥2318) | ✅ 2318 passed | Manter verde + adicionar novos testes | 10 |
| **G10** | Memória viva (lessons 141-160 + cross-cli-sync + PROGRESS) | 🟡 até lesson 154 | Salvar 20 lessons + 5 cross-sync | 10 |

## 📋 100 TASKS (10 × 10)

### G1 — Bot Telegram E2E validado 5x (T01-T10)
- T01 [ ] Re-rodar 5 testes E2E via webhook real (`curl POST /api/v1/webhook/telegram`)
- T02 [ ] Validar debounce 1.2s + rate limit 3s + idempotência 10min
- T03 [ ] Validar typing refresh 4s (typing expira em 5s na API Telegram)
- T04 [ ] Validar cancel typing ao terminar (chat_action vazio)
- T05 [ ] Validar anti-duplicação (mesmo update_id só processa 1x)
- T06 [ ] Validar LGPD scrub input/pre-LLM/output (3 camadas)
- T07 [ ] Validar fallback LiteLLM DOWN → opencode_free_1 (kill LiteLLM e testar)
- T08 [ ] Validar fast_llm path para saudações ("oi", "menu")
- T09 [ ] Validar agent path para perguntas técnicas (procuração, testamento)
- T10 [ ] Medir latência P50/P95/P99 em 50 chamadas

### G2 — Pipeline compartilhado `chat_pipeline.py` (T11-T20)
- T11 [ ] Criar `backend/app/services/chat_pipeline.py` (orquestrador)
- T12 [ ] Extrair `_process_debounce()` (comum Telegram/WhatsApp)
- T13 [ ] Extrair `_call_llm_with_fallback()` (LiteLLM → nemotron → opencode → ...)
- T14 [ ] Extrair `_send_response()` (sendMessage Telegram / sendText Evolution)
- T15 [ ] Extrair `_check_idempotency()` (chave: update_id / message_id)
- T16 [ ] Extrair `_scrub_pii_3_layers()` (input/pre-LLM/output)
- T17 [ ] Extrair `_audit_log()` (LGPD audit trail)
- T18 [ ] Refatorar `telegram.py` para usar `chat_pipeline.py`
- T19 [ ] Criar interface `ChannelAdapter` (send/receive typing/reaction)
- T20 [ ] Testes unitários `test_chat_pipeline.py` (10 casos)

### G3 — Bot WhatsApp `/webhook/evolution` espelhado (T21-T30)
- T21 [ ] Refatorar `webhook_evolution` em router.py para usar `chat_pipeline.py`
- T22 [ ] Criar `backend/app/api/v1/whatsapp.py` (espelho de telegram.py)
- T23 [ ] Implementar debounce 1.2s + rate limit 3s + idempotência Evolution
- T24 [ ] Implementar typing indicator Evolution (`presence` subscribe)
- T25 [ ] Implementar reaction Evolution (`reactionMessage`)
- T26 [ ] Implementar menu inline WhatsApp (buttons/list messages)
- T27 [ ] Implementar comandos /start /menu /agendar /protocolo /humano /cancelar /lgpd
- T28 [ ] Validar HMAC Evolution webhook signature (X-Hub-Signature-256)
- T29 [ ] Registrar router em `main.py` (incluir whatsapp router)
- T30 [ ] Smoke test local: `curl POST /api/v1/webhook/evolution`

### G4 — Fallback chain validado 3x (T31-T40)
- T31 [ ] Testar LiteLLM UP → response em 4-10s (provider: nemotron-3-ultra-free)
- T32 [ ] Testar LiteLLM DOWN → opencode_free_1 direto em 2-4s (kill LiteLLM container)
- T33 [ ] Testar opencode_free_1 429 → opencode_free_2 fallback
- T34 [ ] Testar opencode_free_2 503 → opencode_free_3 fallback
- T35 [ ] Testar todos DOWN → cache local (resposta padrão "Sistema em manutenção")
- T36 [ ] Implementar circuit breaker (3 falhas → abre 60s)
- T37 [ ] Implementar retry com exponential backoff (1s, 2s, 4s)
- T38 [ ] Métricas por provider (success/fail/latência)
- T39 [ ] Documentar chain em `docs/FALLBACK_CHAIN.md`
- T40 [ ] Teste E2E fallback completo (LiteLLM→opencode→openclaw→cache)

### G5 — LGPD compliance WhatsApp (T41-T50)
- T41 [ ] LGPD notice WhatsApp (mensagem inicial obrigatória)
- T42 [ ] Consent banner WhatsApp (botão "Aceito" / "Não aceito")
- T43 [ ] PII scrub input WhatsApp (CPF/RG/telefone/email)
- T44 [ ] PII scrub pre-LLM (defesa em profundidade)
- T45 [ ] PII scrub output (não vazar dados pessoais no response)
- T46 [ ] Audit log LGPD: quem, quando, o que (canal, sender, content_hash)
- T47 [ ] Direito esquecimento: comando /cancelar + DELETE em 30 dias
- T48 [ ] Direito acesso: comando /lgpd → exporta JSON
- T49 [ ] Direito portabilidade: comando /lgpd export → zip + link
- T50 [ ] DPA DeepSeek assinado (lesson 138) — confirmar

### G6 — Observability (T51-T60)
- T51 [ ] Logs estruturados JSON (correlation_id, channel, chat_id, latency)
- T52 [ ] Métricas Prometheus: counter requests_total, histogram latency_seconds
- T53 [ ] OpenTelemetry spans: webhook → debounce → LLM → send
- T54 [ ] Trace ID propagation (X-Request-ID header)
- T55 [ ] Health check `/api/v1/health/integracoes` (já existe, validar)
- T56 [ ] Dashboard Grafana: latência por provider (LiteLLM, opencode_*, openclaw)
- T57 [ ] Alerta Telegram GRUPO Pietra: latência P95 > 15s
- T58 [ ] Dead man's switch A13: audit_log stale > 15min → alerta
- T59 [ ] Sentry SDK (lesson 145) capturar exceções LLM
- T60 [ ] Jaeger UI (lesson 144) ver trace webhook→send completo

### G7 — Testes E2E (T61-T70)
- T61 [ ] Teste E2E Telegram #1: "oi" → menu (fast_llm)
- T62 [ ] Teste E2E Telegram #2: "/protocolo 12345" → consulta DB
- T63 [ ] Teste E2E Telegram #3: "/agendar" → flow completo
- T64 [ ] Teste E2E Telegram #4: "/humano" → cria atendimento HITL
- T65 [ ] Teste E2E Telegram #5: "/lgpd" → mostra direitos
- T66 [ ] Teste E2E WhatsApp #1: "oi" → menu (mock Evolution)
- T67 [ ] Teste E2E WhatsApp #2: protocolo → consulta DB
- T68 [ ] Teste E2E WhatsApp #3: agendar → flow completo
- T69 [ ] Teste E2E fallback #1: LiteLLM UP
- T70 [ ] Teste E2E fallback #2: LiteLLM DOWN → opencode_free_1

### G8 — Documentação 25/25 (T71-T80)
- T71 [ ] `docs/ARCHITECTURE.md` (atualizar c/ chat_pipeline)
- T72 [ ] `docs/BOTS.md` (overview Telegram + WhatsApp)
- T73 [ ] `docs/TELEGRAM_GUIDE.md` (guia operacional completo)
- T74 [ ] `docs/WHATSAPP_GUIDE.md` (guia operacional completo)
- T75 [ ] `docs/FALLBACK_CHAIN.md` (todos os providers + retry policy)
- T76 [ ] `docs/LGPD_BOTS.md` (compliance específico chatbots)
- T77 [ ] `docs/CHATWOOT_HANDOVER.md` (HITL fluxo humano)
- T78 [ ] `docs/EVOLUTION_API.md` (instalação + QR + webhook)
- T79 [ ] `docs/TROUBLESHOOTING_BOTS.md` (cenários + soluções)
- T80 [ ] `docs/CHANGELOG_BOTS.md` (histórico de versões)

### G9 — CI verde (T81-T90)
- T81 [ ] mypy 0 erros (rodar `make mypy`)
- T82 [ ] ruff 0 erros (rodar `make lint`)
- T83 [ ] pytest ≥2318 passed (rodar `make test`)
- T84 [ ] coverage ≥90% (rodar `make coverage`)
- T85 [ ] CI workflow `.github/workflows/ci.yml` verde
- T86 [ ] CD workflow `.github/workflows/cd.yml` verde (Render)
- T87 [ ] OpenAPI validator passando (lesson 145)
- T88 [ ] Pre-commit hooks todos passando
- T89 [ ] Dockerfile builds sem warnings
- T90 [ ] Mutmut mutation score ≥80% (lesson 150)

### G10 — Memória viva (T91-T100)
- T91 [ ] Lesson 141: chat_pipeline.py extraído (refactor Telegram/WhatsApp)
- T92 [ ] Lesson 142: fallback chain LiteLLM validado 3x
- T93 [ ] Lesson 143: bot WhatsApp espelhado 100%
- T94 [ ] Lesson 144: Jaeger trace webhook→send completo
- T95 [ ] Lesson 145: Sentry SDK em produção
- T96 [ ] Lesson 146: OpenTelemetry spans em chat_pipeline
- T97 [ ] Lesson 147: LGPD consent banner WhatsApp
- T98 [ ] Lesson 148: circuit breaker pattern LLM providers
- T99 [ ] Lesson 149: 100 tasks plano completo (10 goals)
- T100 [ ] Cross-cli-sync 2026-07-09T17:00Z (4 agents assinaram)

## 🚦 EXECUÇÃO

**Paralelização 4 agents** (mesmo repo, mesmo branch):
- **Antigravity-Gemini-3.5-High**: G1, G4 (testes + fallback)
- **OpenCode-MiniMax-M3-High**: G2, G3 (refactor + WhatsApp espelho)
- **Grok-Build-Grok-4.5-High**: G5, G6 (LGPD + observability)
- **Claude-Code-MiniMax-M3-High**: G7, G8, G9, G10 (testes + docs + CI + memória)

**Sequência crítica** (não paralelizar):
- G2.1 (chat_pipeline.py) → G3.1 (whatsapp.py usa pipeline)
- G4.1 (circuit breaker) → G7 (testes fallback)
- G9 (CI verde) ANTES de qualquer merge

## 📊 MÉTRICAS DE SUCESSO

```
G1: 5/5 testes E2E Telegram sent=True ✅
G2: chat_pipeline.py < 500 linhas, 10 unit tests ✅
G3: whatsapp.py paridade 100% c/ telegram.py (mesmas funções) ✅
G4: 3/3 fallback validado E2E ✅
G5: LGPD 100% (consent + scrub + audit + direitos) ✅
G6: Grafana dashboard + 4 alertas Telegram ✅
G7: 13 testes E2E (5 TG + 5 WP + 3 fallback) ✅
G8: 25/25 docs raiz ✅
G9: mypy 0 / ruff 0 / pytest ≥2318 / coverage ≥90% ✅
G10: 20 lessons + 5 cross-cli-sync + 1 PROGRESS entry ✅
```

## 🔗 SUI — Só Gustavo Resolve

1. **WhatsApp QR scan**: `https://whatsapp.2notasudi.com.br/manager` → criar instância `cartorio-2notas`
2. **Render deploy key**: confirmar `RENDER_API_KEY` + service ID
3. **Telegram BotFather**: confirmar `@CartorioAssistantBot` ativo

## 📅 TIMELINE

- **Cycle 1 (hoje)**: G1 + G2 + G9 (validar Telegram + extrair pipeline + CI verde)
- **Cycle 2 (amanhã)**: G3 + G4 + G7 (WhatsApp + fallback + testes)
- **Cycle 3 (3 dia)**: G5 + G6 + G8 (LGPD + observ + docs)
- **Cycle 4 (4 dia)**: G10 + cross-cli-sync + SUI Gustavo (WhatsApp QR)

---
**Autor**: Master Agent (OpenCode-MiniMax-M3-High) · 2026-07-09T16:30:00Z
**Status**: 🟡 in_progress · 0/100 tasks done · 4 agents em paralelo