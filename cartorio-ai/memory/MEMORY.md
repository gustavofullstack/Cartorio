# cartorio-ai · memory/MEMORY.md

Memória viva do pacote. **Não duplicar** o que já está em git/código — só o não-óbvio.
Memória de projeto cross-rein: `../../.harness/memory/MEMORY.md` · Diária de sessão: `../../.brain/memory/`.

## Fatos-chave — 2026-07-20 (sessão Telegram P0 + G9)

1. **Causa-raiz do silêncio do Telegram**: webhook registrado sem `secret_token` (ou divergente do
   env de prod) → backend 401 em 100% dos updates. Fix: `POST /api/v1/telegram/set-webhook` com
   `X-API-Key` faz o prod re-registrar com o próprio secret (commit `96fedc9`). Hoje: getWebhookInfo
   OK, `pending_update_count=0`, 401 sem header = comportamento correto.
2. **Probes prod**: `/start` em chat real → `response_sent=true`; texto livre e grupo →
   `scheduled=true` (debounce async). **Aberto**: confirmar a entrega da resposta async (G9.03.T4).
3. **Regressões A1–A6** (diagnóstico E1, com linhas): boot sync em todos workers (A1) é o risco de
   recaída do P0 — worker sem `TELEGRAM_WEBHOOK_SECRET` derruba a verificação das réplicas.
4. **LLM**: fallback OpenCode Zen (3 contas) integrado (`96fedc9`); diagnóstico E2 achou slot
   herdando só `API_KEY` (mistura chave×modelo), timeout único 50s × até 6 tentativas (pior caso
   15–20min de silêncio) e payload `thinking`/`tools` enviado a providers que não suportam.
5. **CNJ**: `/api/v1/lgpd/cnj-exports/massive-dump` em produção — streaming `yield_per(1000)`,
   API key + JWT DPO, scrub de payload, audit gate (falha de audit bloqueia o dump).
6. **`can_join_groups=false`** no BotFather — bot não entra em grupos novos até o dono rodar
   `/setjoingroups Enable` (única ação que exige humano).
7. **Segredos em arquivos locais** (maioria untracked): `backend/test_send_tg.py`, `test_webhook*.py`,
   `test_llm*.py`, `scripts/test_telegram_e2e.sh:92,98`, provável em `stress_telegram_prod*.py` —
   tratamento no G9 Squad 09. **Nunca rotacionar sem ordem do dono.**
8. **Commits do dia**: `ff599aa` (deploy prod + opencode keys + CNJ), `9522cce` (fallback live),
   `0838c56`/`c49508a`/`4f43ff8` (telegram cmd/mídia, HTML safe, 1000 mockadas), `e718d0b`
   (rate-limit drop, mention strip, offline LLM hijack), `647bf8a` (redact credenciais em logs),
   `96fedc9` (webhook sync + zen fallbacks), `6c029fc` (telegram + CNJ + chatwoot signup),
   `1206341` (contextWindow 1M), `4867c85` (max_tokens 4096), `f2b4b9e` (REQUIRED_RECORDS).

## Lições reaproveitáveis

- Diagnóstico read-only em squad (E1–E4) antes de patch evita tiro no escuro em prod.
- `scheduled=true` ≠ usuário atendido — telemetria de debounce precisa de confirmação de entrega.
- 502 Traefik ≠ Traefik down (Lesson 176); Telegram HTML parse = 502 silencioso (Lesson 170).
