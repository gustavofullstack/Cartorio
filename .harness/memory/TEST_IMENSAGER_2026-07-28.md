# IMENSAGER — Relatório de Validação (2026-07-28)

**Agente executor:** ZCode (sessão `/goal` — goals-workflow)
**Duração:** ~40min (parcial — fases live bloqueadas)
**Ambiente:** prod VPS (187.77.236.77 / Tailscale 100.99.172.84) + Mac local (Photon :8793)
**Branch testada:** `master` @ `16748d96`
**Prompt executado:** `prompts/IMENSAGER_VALIDATION_PROMPT.md` **v2.0** (a v1.0 colada na sessão pressupõe módulo `imensager` no backend + envs `IMENSAGER_*` que **não existem** — superseded pela v2.0 consolidada)
**Persona:** PIETRA · MINIMAX M3 1M XMAX

## Resumo executivo

- **Status geral:** 🟡 amarelo — sanity/audit verdes; fases live (2, 3, 4-live, 6, 7-live, 8, 9) **bloqueadas por falta de autorização** (envio de iMessages reais + janela HITL do Gustavo).
- **Testes executados:** 102 (15 retry envelope + 86 pietra/imessage suites + 1 audit chain prod) — **100% verde** no que foi executado.
- **P0 blockers:** IDENTITY_HERMES_LEAK **permanece aberto** (regra: só declarar resolvido com N≥30 pós-fix — não rodado nesta sessão).
- **Recomendações:** (1) agendar janela live com Gustavo p/ Fases 2-9; (2) investigar F3 abaixo (models free-tier no hermes VPS) como contribuinte do identity leak; (3) higienizar audit chain do Postgres dev local (F2).

## Resultados por fase

| Fase | Status | Evidência | Notas |
|------|--------|-----------|-------|
| 1. Sanity | ✅ | health/ready/radar → 200 em <100ms; Photon :8793 LISTEN + 401 fail-closed (L275); LaunchAgent `ai.hermes.gateway-cartorio` ativo (PID 10286); suites `test_pietra_identity_guard` + `test_imessage_felipe_classify` + `test_imessage_arena_coordinator` + `test_pietra_conversation` = **86 passed, 1 skipped** | |
| 2. Inbound | ⏸ | — | Requer iMessages reais (outward-facing) — aguardando autorização |
| 3. Outbound | ⏸ | — | idem |
| 4. PII | ⏸ parcial | suites PII locais verdes (dentro das 86) | bypass live (markdown/base64/OCR) pendente |
| 5. Audit | ✅ | `verify_full_chain` no container `cartorio_system-api` (prod): **33/33 intact, integrity 1.0, chain_intact=True** | ver F2 p/ dev local |
| 6. HITL | ⏸ | — | Requer Gustavo na janela de teste |
| 7. Resiliência | ✅ parcial | `test_retry_envelope_3x20s.py` **15/15 PASS** (36s) | caos live (API offline, Redis down) pendente |
| 8. Performance | ⏸ | — | Depende de tráfego live |
| 9. LGPD | ⏸ | — | Art. 18 via canal real pendente |
| §2.6 gate | ✅ | retry envelope 15/15 | |
| §2.4 gate | ✅ | `backend/tests/conftest.py:91` → `LLM_DEFAULT_PROVIDER="opencode_go"` | |

## Critérios de aprovação (parcial)

| # | Status | Detalhe |
|---|--------|---------|
| C1 | 🟡 | 100% verde **no executado**; Fases 2-3 live pendentes |
| C2 (P0) | 🟡 | suites locais verdes; bypass live pendente |
| C3 (P0) | ✅ | prod `chain_intact=True` (33/33) |
| C4 (P0) | ⏸ | Fase 6 não executada |
| C5 (P0) | ⏸ | Fase 9 não executada |
| C8 | ✅ parcial | 0 crash/500 nas suites + health checks |
| C9-C11 | ⏸ | `make qa` completo não rodado (fora de escopo da sessão parcial) |

## P0 IDENTITY_HERMES_LEAK — estado

- **Permanece ABERTO.** Nenhuma declaração de resolução (regra N≥30 não satisfeita — 0 envios live nesta sessão).
- SOUL.md no VPS: **131 linhas, persona PIETRA canônica** ✅ (não é a fonte do leak).
- **F3 (novo achado):** `/opt/data/config.yaml` do `cartorio_hermes` (VPS) lista `deepseek-v4-flash-free` e `nemotron-3-ultra-free` como models — **não** `minimax/m1-m3` esperado pelo §3.1. Hipótese: fallback para modelos free-tier fracos que ignoram a persona → contribuinte da Camada 3 do leak. Requer confirmação de qual config o **Photon sidecar local** (Mac) efetivamente usa.

## Findings

- **F1.** Prompt v1.0 (colado) pressupõe `backend/app/services/imensager*.py`, `tests/services/test_imensager_*.py` e envs `IMENSAGER_*` — inexistentes. Usar sempre a **v2.0** do repo. Se o webhook FastAPI imensager for desejado, é task de **implementação** nova (cartorio-dev + cartorio-n8n), não de validação.
- **F2.** Postgres **dev local** (127.0.0.1:5432/cartorio): audit chain 152/152 broken (integrity 0.0) — esperado em dev (rotação de HMAC key em desenvolvimento, seed antigo). **Não é tampering em prod** (prod = 33/33 intact). Recomendação: reset/seed do banco dev ou documentar em `backend/README`.
- **F3.** Models free-tier no config do hermes VPS (ver seção P0 acima).
- **F4.** Redis local (6379) down — sem impacto nas suites (fakeredis), mas `make dev` local e smoke real precisam dele ou de apontar p/ VPS.

## Bloqueios registrados (goals-workflow §6)

| Bloqueio | Autoridade/input faltante |
|---|---|
| Fases 2, 3, 4-live, 7-live, 8 | Autorização do Gustavo p/ enviar iMessages reais pelo canal (outward-facing) |
| Fase 6 (HITL) | Janela do Gustavo p/ aprovar/validar atos jurídicos simulados |
| Fase 9 (LGPD Art. 18) | Idem + decisão de ambiente (contato de teste real vs. simulado) |
| N≥30 do P0 identity | Janela live p/ 30 envios pós-fix |

## Lições para MEMORY.md

- (Já coberto por L280/L282.) Reforço reutilizável: **prompts de validação versionados no repo divergem rápido da realidade — sempre conferir se existe versão consolidada mais nova antes de executar a colada** (v1.0 vs. v2.0 aqui). Candidata a L283.

## Commit

- `test(imensager): partial QA validation 2026-07-28 — sanity + prod audit green, live phases blocked`
- `Modified by Gustavo Almeida`
