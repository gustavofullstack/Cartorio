# STATUS — Sessão 2026-07-20 (Telegram P0 resolvido + SUPER PLANO G9 criado)

> **TL;DR**: P0 "Telegram não responde" **RESOLVIDO** — causa-raiz: webhook sem `secret_token`
> (backend 401 em 100% dos updates). Re-sync via `/api/v1/telegram/set-webhook` (commit `96fedc9`)
> e probes prod validam: `/start` → `response_sent=true`; texto livre/grupo → `scheduled=true`.
> Diagnósticos E1–E4 mapearam regressões A1–A6 (telegram) e falhas de slots/timeout/payload (LLM).
> **SUPER_PLANO_G9_100_TASKS.md** criado (14/100 já evidenciadas hoje). Núcleo `cartorio-ai/`
> (15 arquivos) preenchido. Pendências: código das regressões A1–A6, coerência slots zen,
> segredos em scripts locais e SUI do dono (DNS/Tailscale/QR/OpenClaw).
>
> Substitui o snapshot de 2026-07-15 (SUPER PLANO 100/100 F0-F6) — histórico em PROGRESS.md.

---

## ✅ Validado HOJE em produção (com evidência)

| Item | Evidência |
|---|---|
| Webhook prod com secret | getWebhookInfo OK, `pending_update_count=0`; 401 sem header / com secret errado (correto) |
| Re-sync webhook | `POST /api/v1/telegram/set-webhook` com `X-API-Key` → prod re-registrou com o próprio secret |
| Probe síncrono | `/start` em chat real → `response_sent=true` |
| Probe async | texto livre e mensagem em grupo → `scheduled=true` (debounce 1.2s) |
| Fallback LLM zen | 3 contas OpenCode Zen integradas + agente live restaurado (`96fedc9`, `9522cce`) |
| CNJ export | `/api/v1/lgpd/cnj-exports/massive-dump` em prod: streaming `yield_per(1000)` + API key + JWT DPO + scrub + audit gate (`ff599aa`, `0d15da6`, `6c029fc`) |
| Bateria telegram | `backend/tests/test_telegram_1000.py` — 1000 interações mockadas (`4f43ff8`) |

## 🔬 Diagnósticos (E1–E4, read-only) — base do G9

- **E1 telegram.py (A1–A6)**: A1 boot sync em TODOS os workers (`main.py:305-307`) — worker sem
  `TELEGRAM_WEBHOOK_SECRET` chama setWebhook sem `secret_token` (`telegram.py:2435-2436`) e derruba
  a verificação das réplicas (tempestade 401 = causa-raiz do P0). A2 URL hardcoded (`:2429`).
  A3 webhook pode 5xx (`:1964-1966`, `:2357`) — regra: sempre-200 exceto 401. A4 fallback síncrono
  morto (`:2315-2352`). A5 `_DEBOUNCE_METADATA` por `chat_id` vs fila `chat_id:user_id` → 2 usuários
  no mesmo grupo na janela de 1.2s → um sem resposta. A6 debounce falha silenciosa → usuário sem feedback.
- **E2 cartorio_agent.py**: slots free 1/2/3 (`:66-82`) herdam só `API_KEY` (mistura chave×modelo);
  timeout único 50s × até 6 tentativas (`:616`) → pior caso 15–20min de silêncio; payload
  `thinking`/`tools` para todos os providers (`:610-614`) → risco de HTTP 400 em zen free.
- **E3 infra**: mecanismo de re-sync sem SSH confirmado (`set-webhook` + API key); env de prod via EasyPanel.
- **E4 testes/planos**: inventário consolidado → base das 100 tasks do G9.

## 📦 Entregue hoje (docs)

1. `SUPER_PLANO_G9_100_TASKS.md` — 100 tasks / 25 squads; **14/100 [x] com evidência**.
2. Núcleo `cartorio-ai/` — 15 arquivos reais (AGENTS, README, ARCHITECTURE, MANIFEST, INDEX,
   BOOTSTRAP, ROADMAP + brain/BRAIN, identity/SOUL, identity/IDENTITY, planning/GOALS,
   planning/TASKS, memory/MEMORY, security/SECURITY, compliance/CNJ). Resto do layout (~400
   arquivos) = fase posterior (`cartorio-ai/ROADMAP.md`).
3. `STATUS.md` (este) + `PROGRESS.md` atualizados (G9.25.T2).

## ⏭️ Próximos passos (ordem das waves G9)

1. **W54** — código das regressões A1–A5: boot sync líder-only + fail-fast sem secret (G9.01.T3);
   webhook sempre-200 (G9.01.T4); fallback morto (G9.02.T2); metadata debounce por `chat_id:user_id` (G9.02.T3).
2. **W55** — A6 feedback garantido; E2E grupo 2-usuários; stress prod assinado; confirmar entrega
   async pós-debounce (hoje só `scheduled=true` observado).
3. **W56** — slots zen herdam tupla completa; timeout por tentativa + deadline; payload por provider.
4. **Dono (SUI, packs prontos em `docs/`)**: `/setjoingroups Enable` no @BotFather (`can_join_groups=false`
   bloqueia grupos novos); 3 A records DNS (G9.16.T2); Tailscale restore (G9.17.T1/T2); QR WhatsApp
   (G9.15); OpenClaw E8 (G9.17.T3); WA live emolumento (G9.17.T4).
5. **Segurança**: sanitizar segredos literais em `backend/test_*.py`, `scripts/test_telegram_e2e.sh`,
   `stress_telegram_prod*.py` (G9.09) — sem rotação sem ordem do dono; checker hex-64 (G9.10.T1).

## ⚠️ Riscos abertos

- **A1 recaída**: qualquer worker/restart sem `TELEGRAM_WEBHOOK_SECRET` pode derrubar o secret do
  webhook de novo até G9.01.T3 ser implementado.
- **A5/A6**: em grupo com 2+ usuários simultâneos, um pode ficar sem resposta hoje.
- **LLM pior caso**: até 15–20min percebidos como silêncio quando slots falham em sequência.
- **Segredos em arquivos locais** (maioria untracked) — contidos no disco do dono; tratar no G9.09.

---

**Modified by**: squad G9 (orquestrador + E1–E4 + C4_Docs_SuperPlan) + Gustavo Almeida (CEO)
**Sessão**: 2026-07-20 · **Próxima atualização**: após W54 (código das regressões A1–A5)
