# cartorio-ai · security/SECURITY.md

Modelo de segurança do agente/backend do Cartório. Derivado de `../../AGENTS.md` e das regras P0.

## 1. Segredos

- Fonte: `.env` / `.secrets/` (nunca commitados; `.env.example` só com placeholders).
- **Proibido commitar ou imprimir valores** — mascarar sempre (`****` + últimos 4 quando inevitável).
- **Proibido rotacionar qualquer chave sem ordem expressa do dono.**
- Checker: `scripts/check_no_literal_keys.py` bloqueia `lin_api_*`, `sk-*`, `rnd_*`, `AQ.*`,
  `gAAAAA`, `ghp_*`, `xox*`, `AKIA*`, `AIza*` (opt-out: `# noqa: ALLOW_KEY_FALLBACK`);
  extensão para hex-64 genérico = G9.10.T1.
- Achado de 2026-07-20: segredos literais em scripts/testes ad-hoc locais (token bot, webhook
  secret, chave zen) — saneamento no G9 Squad 09; recomendação de rotação é decisão do dono.

## 2. PII (DATASENSITIVE)

- 3 camadas de scrub: Pydantic field validators → Sentry `before_send` → log `MaskingFilter`.
- PII nunca raw para LLM pública, log ou storage externo. Nunca ecoar CPF ao usuário.
- `app/services/pii.py` é leitura obrigatória antes de integrar qualquer LLM novo.
- LGPD-015 (G9 Squad 06): saída do LLM também passa por scrub antes de canal/log.

## 3. Audit chain

- Append-only: SHA256 chain + HMAC. Edição retroativa invalida a cadeia (testes `t024`/`t025`).
- Dead-man's switch: verificação a cada 15min no lifespan da API.
- Falha de audit **bloqueia** operações sensíveis (ex.: CNJ massive-dump → 500 `AUDIT_FAILURE`).

## 4. Borda (Telegram/Webhooks)

- Webhook exige `X-Telegram-Bot-Api-Secret-Token` → 401 sem header ou com secret errado.
- Regra: **sempre 200 exceto 401 de secret** (5xx vira ack + DLQ — A3).
- Idempotência Redis SETNX TTL 24h; rate limit sliding 60/min por IP + 3-tier por API key
  (N8N 600 / DPO 60 / default 30), fail-open se Redis cair.
- Re-sync de webhook somente via endpoint protegido por `X-API-Key`; boot sync em todos os
  workers sem secret é o risco A1 — líder-only + fail-fast (G9.01.T3).

## 5. LLM / providers

- 3 contas OpenCode Zen em slots com fallback; cada slot deve herdar a tupla completa
  (`API_KEY`, `BASE_URL`, `MODEL`) da mesma conta (G9.04.T3).
- `thinking`/`tools` só para providers que suportam (G9.05.T2) — zen free recebe payload mínimo.
- Em testes, `tests/conftest.py` força `LLM_DEFAULT_PROVIDER="opencode_go"` — nunca chamar LLM real.

## 6. Resposta a incidente

1. Conter (desligar via flag/env, nunca apagar audit). 2. Evidenciar (export + hash chain).
3. Reportar ao dono + `cartorio-lgpd`. 4. Lesson em `.harness/memory/`. 5. Rotação SÓ com ordem.
