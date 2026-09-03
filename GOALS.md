# GOALS — Cartório 2º Notas Uberlândia (canônico)

Atualizado: 2026-08-26 · Fonte: MEMORY.md + PROGRESS.md + estado VPS ao vivo

## A — Backend FastAPI estável e verde
- Status: **DONE** — api.2notasudi 200, system-api 1/1, 6489 pytest passing, ruff/mypy 0, coverage ≥90%.
- Evidência: `make qa` local, radar `database/redis:online`.

## B — Canais de atendimento
- **Telegram**: OPERACIONAL (bot @TestCartorioBot regenerado pós-Lesson 178; webhook HMAC + idempotência).
- **WhatsApp (Evolution)**: evolution-api 1/1, whatsapp.2notasudi 200. Sessão WA = SUI (QR/reconnect).
- **iMessage (Photon/Mac)**: NOT_E2E_VALIDATED (Lesson 290) — exige round-trip real autorizado no iPhone.
- **Lark (Hermes VPS)**: serviço 1/1, gateway único, persona Pietra + MiniMax-M3 + fallback M2.7-highspeed + tool cartorio_calcular_emolumento (Lesson 294). Camada 5 (mensagem real no Lark) = SUI Gustavo.
- **Chatwoot**: REMOVIDO do Swarm 2026-07-27 (.env, volumes, DB `chatwoot` preservados) — **DECISÃO GUSTAVO**: restaurar vs decomissionar.
- **OpenClaw**: REMOVIDO do Swarm 2026-07-27 (agent.2notasudi 404, volumes preservados) — **DECISÃO GUSTAVO**.

## C — Infra VPS (Hostinger/Easypanel/Swarm)
- Status: **RECOVERED 2026-07-28** — n8n 1/1 (encryption key mismatch resolvido), n8n-runner 1/1, supabase realtime 1/1 (DB_HOST→banco_de_dados + schema realtime), postgrest recriado (root 200, rest 200), auth/storage DB migrados para banco_de_dados.
- Pendente: radar `evolution:offline` (check interno aponta p/ legado 0/0 — ajustar para cartorio_whatsapp-api).
- **P0 segurança**: SUPABASE_ANON_KEY + SERVICE_ROLE_KEY expostas em output de sessão 2026-07-28 — decisão de rotação = Gustavo (regra não-rotacionar sob pressão).

## D — LGPD by-design
- Status: **DONE** — P0.7 output scrub, P0.8 response shape pii_blocked+handoff, P0.9 audit conversa.pii_blocked (verificados em router.py 2026-07-28). task-bank p0_done 6/10.

## E — Pietra persona pública
- Status: **DONE 2026-08-26** — Lessons 286-294 + 2026-08-26: test phase banner, text integrity tests, setor routing HITL, ISS 5% validation.
- Banner "sistema em fase de testes" controlado via `PIETRA_TEST_PHASE_BANNER` env var.
- Testes de integridade textual (truncation, punctuation, ellipsis detection) em `TestTextIntegrity`.

## F — Fontes de verdade
- task-bank.json: atualizado 2026-07-28.
- loop-state.json: **stale 2026-07-17** — atualizar na próxima wave.
- MEMORY.md: fresco (Lesson 294).

## G — Requisitos Tabelião (2026-08-26) ✅ IMPLEMENTADO
- ✅ **G1** — Saudação "sistema em fase de testes" visível no agente Pietra (PIETRA_TEST_PHASE_BANNER)
- ✅ **G2** — Correção respostas truncadas + testes integridade textual (TestTextIntegrity 6 testes)
- ✅ **G3** — Setores configuráveis para roteamento HITL (14 setores, modelo Setor + setor_routing.py)
- ✅ **G4** — ISS Uberlândia 5% validado na Portaria CGJ/TJMG 8.664/2025 (emolumento_real_djalma.py)
- ✅ **G5** — Multi-usuário/telefone: estrutura pronta (telefone_hash PK, isolamento por canal)
- ✅ **G6** — Auditoria acesso chat: audit_log SHA256+HMAC + rate limit tiers + idempotência
- ⏳ **G7** — Backlog/checklist atualizado (PROGRESS.md)
- ⏳ **G8** — Áudios/imagens/vídeos: `PENDENTE_INGESTAO` (aguardando arquivos)
- 🚫 **G9** — WhatsApp real: BLOQUEADO sem aprovação específica
- 🚫 **G10** — Credenciais: BLOQUEADO alteração sem aprovação

## Próximas ações (ordem)
1. **Gustavo**: decidir Chatwoot/OpenClaw (restore vs decomissionar).
2. **Gustavo**: decidir rotação Supabase keys (P0 leak).
3. **Gustavo**: mensagem real no Lark (camada 5) → LARK_E2E_VALIDATED.
4. Radar: ajustar check evolution (whatsapp-api) + remover chatwoot/openclaw se decomissionados.
5. loop-state.json refresh.
6. Ingestão de anexos (áudios/imagens/vídeos) quando disponíveis.
