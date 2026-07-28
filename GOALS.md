# GOALS — Cartório 2º Notas Uberlândia (canônico)

Atualizado: 2026-07-28 · Fonte: MEMORY.md + task-bank.json + estado VPS ao vivo

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
- Status: **DONE 2026-07-28** — Lessons 286-294: identity guard, outbound guard (infra/latino/glitch), prompt resolutivo formal-carinhoso, Lark perfil final-only + reconciler + plugin pietra-public-output.

## F — Fontes de verdade
- task-bank.json: atualizado 2026-07-28.
- loop-state.json: **stale 2026-07-17** — atualizar na próxima wave.
- MEMORY.md: fresco (Lesson 294).

## Próximas ações (ordem)
1. **Gustavo**: decidir Chatwoot/OpenClaw (restore vs decomissionar).
2. **Gustavo**: decidir rotação Supabase keys (P0 leak).
3. **Gustavo**: mensagem real no Lark (camada 5) → LARK_E2E_VALIDATED.
4. Radar: ajustar check evolution (whatsapp-api) + remover chatwoot/openclaw se decomissionados.
5. loop-state.json refresh.
