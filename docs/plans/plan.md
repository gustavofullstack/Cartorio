# PLAN — Super Orquestração Cartório AI (2026-07-20)

## P0 — Telegram não responde (DM nem grupo) — CAUSA-RAIZ IDENTIFICADA

**Evidências coletadas (sem SSH, sem loop):**
1. Bot `@test_cartorio_bot` existe; webhook registrado em `https://api.2notasudi.com.br/api/v1/telegram/webhook`, `pending_update_count=0`.
2. API prod: `/health`, `/ready`, `/api/v1/health/radar` → **200 OK**.
3. Webhook prod **exige `X-Telegram-Bot-Api-Secret-Token`** → 401 "Missing secret token" sem header; 401 com secret errado.
4. `backend/.env` local **não tem** `TELEGRAM_WEBHOOK_SECRET` → o secret válido só existe no ambiente de prod (EasyPanel).
5. Commit `96fedc9` (hoje 11:30) criou `sync_telegram_webhook()` + endpoint `POST /api/v1/telegram/set-webhook` (protegido por API key) — é o mecanismo oficial de re-sync: prod registra o webhook na Telegram **com o secret do próprio ambiente prod**.
6. `can_join_groups=false` no BotFather → bot não entra em **novos** grupos (precisa `/setjoingroups` → Enable no @BotFather — ação manual do dono).

**Hipótese principal:** webhook registrado sem `secret_token` (ou com secret divergente do env de prod) → Telegram envia updates sem/com secret errado → backend 401 em 100% dos updates → silêncio total em DM e grupo.

**Fix P0 (sem SSH se possível):**
1. `POST /api/v1/telegram/set-webhook` com `X-API-Key` do cartório → prod re-registra webhook com seu próprio secret.
2. Validar com update simulado assinado (secret lido do ambiente prod via acesso VPS/EasyPanel — Squad Infra determina o caminho).
3. Bateria automatizada: `backend/tests/test_telegram_1000.py` + stress scripts contra webhook prod assinado.
4. Dono executa `/setjoingroups Enable` no @BotFather (única ação que exige humano).

## WAVES (4 agents por squad)

### Wave 1 — Squad DIAGNOSE (4× explore, paralelo, read-only)
- **E1 Telegram-Core:** mapear `backend/app/api/v1/telegram.py` (2481 linhas): fluxo webhook → handler → resposta; pontos de falha silenciosa; grupos/menções; parse HTML; debounce; idempotência.
- **E2 LLM-Chain:** `app/services/cartorio_agent.py` + providers (opencode zen ×3, fallback, litellm); por que resposta pode falhar em silêncio; test_llm*.py.
- **E3 Infra-Access:** como atualizar env de prod e reiniciar (EasyPanel API / SSH / Tailscale / scripts/deploy.sh, trigger_deploys.js); produzir runbook de comandos concretos SEM executar; verificar se dá para ler `TELEGRAM_WEBHOOK_SECRET` de prod.
- **E4 Tests-Plans:** `test_telegram_1000.py`, stress scripts, `scripts/test_telegram_e2e.sh`, smoke; consolidar SUPER_PLANO_* existentes + `.harness/TASKS.md` → base do plano de 100 tasks novo.

### Wave 2 — Squad FIX (4× coder, paralelo após Wave 1)
- **C1 Webhook-Sync:** executar `/set-webhook` com API key; validar 200 em update simulado assinado; documentar.
- **C2 Telegram-Code:** aplicar correções do relatório E1 (grupo/menção/HTML/debounce) + `make test-fast` no escopo telegram.
- **C3 LLM-Keys:** integrar as 3 contas OpenCode Zen no `backend/.env` (NUNCA commitar; `.env.example` só placeholders) + cadeia de fallback free conforme commit 96fedc9.
- **C4 Validation-Battery:** rodar suíte telegram (pytest + e2e script + bateria 1000 contra prod assinado); relatório com logs.

### Wave 3 — Squad SHIP (4× coder)
- **C5 CNJ-Export:** validar endpoint `/lgpd/cnj-exports/massive-dump` (streaming, JWT DPO, hash chain) + teste.
- **C6 Docs-Structure:** completar scaffold `cartorio-ai/` (já existe) — núcleo: AGENTS/README/ARCHITECTURE/MANIFEST/INDEX/BOOTSTRAP + brain/identity/planning/memory/security/compliance.
- **C7 Super-Plan:** gerar `SUPER_PLANO_G9_100_TASKS.md` consolidado (100 tasks / 25 squads × 4).
- **C8 Commit-Push:** `make qa` verde → commit convencional em `master` → push origin (autorizado explicitamente pelo dono nesta sessão).

### Wave 4 — VALIDATE & MEMORY
- Relatório final, atualizar `.harness/memory/MEMORY.md`, STATUS.md, PROGRESS.md.

## Regras duras
- Nunca commitar secrets; nunca rotacionar chaves sem ordem do dono.
- SSH sempre com `ConnectTimeout=8 BatchMode=yes` — proibido loop infinito.
- Erros tipados; ruff line-length 100; mypy strict em `app/`.
- Mensagem de commit termina com `Modified by Gustavo Almeida`.
