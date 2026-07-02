# 🔬 LiteLLM Audit — 2026-07-02

> **Missão**: TODO-003 do SPRINT_REVIEW_2026-07-02 ("Auditar LiteLLM providers (10 do fallback chain)").
> **Status**: AUDIT COMPLETO · drift mapeado · **NENHUMA mudança aplicada** (gate v2.0 + AGENTS.md).
> **Modo**: read-only · probes reais via curl · zero side-effect.

---

## TL;DR

**3-way drift detectado entre config declarada, env vars e runtime proxy.**

| # | Source | Models | Realidade |
|---|---|---|---|
| 1 | `infra/litellm/config.yaml` (tracked, 4062 bytes) | **11 FREE models** | Sprint 2026-07-02, FREE chain |
| 2 | `127.0.0.1:4000` (Python 94221, custom proxy) | 4 MiniMax | Custom proxy antigo (MEMORY 2026-07-01T13:25) |
| 3 | `127.0.0.1:4001` (LiteLLM, PID 1482) | **7 MiniMax** | LiteLLM proxy antigo rodando |
| 4 | `.secrets/api.env` (97 vars) | — | 32 LLM-related vars |

**Config.yaml está definido mas nunca foi carregado** por nenhum proxy em runtime.

---

## 1. `infra/litellm/config.yaml` (11 models FREE — sprint 2026-07-02)

| model_name | model | api_base |
|---|---|---|
| `nemotron-3-ultra-free` | openai/nemotron-3-ultra-free | https://opencode.ai/zen/v1 |
| `mimo-v2.5-free` | openai/xiaomi/mimo-v2.5-free | https://opencode.ai/zen/v1 |
| `deepseek-v4-flash-free` | openai/deepseek-v4-flash-free | https://opencode.ai/zen/v1 |
| `north-mini-code-free` | openai/cohere/north-mini-code-free | https://opencode.ai/zen/v1 |
| `mistral-free` | openai/mistral-free | https://api.mistral.ai/v1 |
| `poolside-laguna-free` | openai/poolside/laguna-m.1:free | https://openrouter.ai/api/v1 |
| `north-mini-code-openrouter-free` | openai/cohere/north-mini-code:free | https://openrouter.ai/api/v1 |
| `gemma-4-31b-free` | openai/google/gemma-4-31b-it:free | https://openrouter.ai/api/v1 |
| `gemini-3.5-flash-free` | openai/gemini-3.5-flash | https://generativelanguage.googleapis.com/v1beta/openai |
| `gemini-3-flash-free` | openai/gemini-3-flash | https://generativelanguage.googleapis.com/v1beta/openai |
| `openclaw` | openai/openclaw | http://cartorio_openclaw-gateway:18789/v1 |

**Router settings:** num_retries=2, timeout=30s, exp_backoff, allowed_fails=3, cooldown=30s.
**LGPD:** cache=false ✓, telemetry=false ✓, request_timeout=30s ✓.

---

## 2. `127.0.0.1:4000` — Custom MiniMax Coding Plan proxy (legacy)

```json
{"status":"ok","provider":"MiniMax Coding Plan","upstream":"https://api.minimax.io/v1",
 "models":["MiniMax-M3","MiniMax-M2.7-highspeed","MiniMax-M2.7","MiniMax-M2.5"]}
```

PID 94221 · 4 models · **todos MiniMax**. Provavelmente o proxy criado em `~/bin/L-litellm-start.sh` da sessão 2026-07-01T13:25 (MEMORY.md).

---

## 3. `127.0.0.1:4001` — LiteLLM proxy oficial (PID 1482)

**`/health` resultado (validado):** 7 healthy · 0 unhealthy.

| model_id (hash curto) | model exposto | api_base |
|---|---|---|
| `1a37d1b9...` | openai/MiniMax-M3 | https://api.minimax.io/v1 |
| `bcec24d7...` | openai/MiniMax-M2.7-highspeed | https://api.minimax.io/v1 |
| `001e9c02...` | openai/MiniMax-M2.7 | https://api.minimax.io/v1 |
| `97f8ba18...` | openai/MiniMax-M2.7-highspeed | https://api.minimax.io/v1 |
| `1084ecbe...` | openai/MiniMax-M3 | https://api.minimax.io/v1 |
| `af3503a6...` | openai/MiniMax-M3 | https://api.minimax.io/v1 |
| `4fc0e378...` | openai/MiniMax-M3 | https://api.minimax.io/v1 |

**`/models` endpoint:** `MiniMax-M3`, `MiniMax-M2.7-highspeed`, `MiniMax-M2.7`, `gpt-4-turbo`, `gpt-5`, `claude-opus-4-6`, `claude-opus-4-5` (7 modelos).

**Source real do config deste proxy:** provavelmente o `~/.litellm/config.yaml` (HOME) antigo da sessão 16:11 (MEMORY.md Line 222). **NÃO é o config.yaml do repo.**

---

## 4. `.secrets/api.env` (97 vars · 32 LLM-related)

**Grupos de providers configurados:**

| Provider group | Vars no api.env | Vars esperado pelo config.yaml | Match? |
|---|---|---|---|
| MINIMAX | `MINIMAX_API_KEY`, `MINIMAX_BASE_URL`, `MINIMAX_MODEL_PRIMARY` (3) | (não usado) | n/a |
| GOOGLE_AI_STUDIO | `GOOGLE_AI_STUDIO_API_KEY`, `GOOGLE_AI_STUDIO_BASE_URL`, `GOOGLE_AI_STUDIO_MODEL` (3) | `GOOGLE_API_KEY` (esperado) | ❌ **NOME DIFERENTE** |
| GROQ | `GROQ_API_KEY`, `GROQ_BASE_URL`, `GROQ_MODEL` (3) | (não usado) | n/a |
| MISTRAL | `MISTRAL_API_KEY`, `MISTRAL_BASE_URL`, `MISTRAL_MODEL` (3) | `MISTRAL_FREE_API_KEY` (esperado) | ❌ **NOME DIFERENTE** |
| OPENCODE_GO | `OPENCODE_GO_*` (6) | (não usado) | n/a |
| OPENCODE_FREE_1/2/3 | 9 vars | `OPENCODE_FREE_1/2/3_API_KEY` | ✅ match |
| OPENROUTER | `OPENROUTER_API_KEY`, `OPENROUTER_BASE_URL`, `OPENROUTER_MODEL` (3) | `OPENROUTER_API_KEY` | ✅ match |
| OPENCLAW | (ausente) | `OPENCLAW_GATEWAY_PASSWORD` | ⚠️ FALTA no api.env |

---

## 5. Probes diretos das URLs FREE (saúde real, validado 2026-07-02T19:14Z)

| URL | HTTP | Latência | Veredito |
|---|---|---|---|
| https://opencode.ai/zen/v1/models | **200** | 0.76s | ✅ REAL, atende |
| https://api.mistral.ai/v1/models | **401** | 0.57s | ✅ UP (needs auth, esperado) |
| https://openrouter.ai/api/v1/models | **200** | 1.04s | ✅ REAL, atende |
| https://generativelanguage.googleapis.com/v1beta/openai/v1/models | **404** | 0.31s | ⚠️ PATH errado — deveria ser `/v1beta/models` |
| https://api.minimax.io/v1/models | **401** | 0.61s | ✅ UP (MiniMax upstream) |
| http://cartorio_openclaw-gateway:18789/v1/models | **000** | 0.008s | ⏭ OK (Swarm DNS interno, não acessível do MacBook) |

---

## 🚨 Drifts detectados (4 reais)

| ID | Drift | Origem | Impacto se config.yaml fosse carregado |
|---|---|---|---|
| **D1** | config.yaml = 11 FREE; runtime proxy 4001 = 7 MiniMax | Configuração nova nunca carregada | FREE chain **NÃO está ativo** |
| **D2** | `MISTRAL_FREE_API_KEY` (config L42) vs `MISTRAL_API_KEY` (env) | Var name mismatch | `mistral-free` quebraria (key not found) |
| **D3** | `GOOGLE_API_KEY` (config L68/L73) vs `GOOGLE_AI_STUDIO_API_KEY` (env) | Var name mismatch | Gemini-3* quebrariam (key not found) |
| **D4** | Gemini URL: config `/v1beta/openai` (raiz OpenAI-compat) — probe `/v1beta/openai/v1/models` → 404 | Path drift real (validado por probe) | `gemini-3.5-flash-free` quebraria mesmo com key certa |
| **D5** | `OPENCLAW_GATEWAY_PASSWORD` ausente no api.env | Var não existe | `openclaw` model quebraria (gateway auth fail) |

---

## 📊 Resumo executivo

- **Realidade runtime**: 1 proxy LiteLLM (4001) carregando 7 modelos MiniMax aliases.
  **Não está usando 100% dos recursos FREE** configurados em `infra/litellm/config.yaml`.
- **Custo atual**: 100% MiniMax Coding Plan (pago/limitado, mesmo que free tier).
  **Custo potencial com FREE chain**: $0 (opencode.ai/zen, mistral free, openrouter free, google free).
- **Risco**: config.yaml está em git como "production config" mas nunca foi testado em prod.
  Se alguém rodar `litellm --config infra/litellm/config.yaml --port 4001` AGORA,
  vai falhar por D2/D3/D4/D5.

---

## 🛠️ Recomendações (NÃO aplicadas — aguardando aprovação)

**Ordem de execução quando Gustavo aprovar** (per AGENTS.md "Mudanças em infra exigem review" + v2.0 rule):

1. **Fix D2** — Editar `infra/litellm/config.yaml` L42: `MISTRAL_FREE_API_KEY` → `MISTRAL_API_KEY`.
2. **Fix D3** — Editar L68/L73: `GOOGLE_API_KEY` → `GOOGLE_AI_STUDIO_API_KEY` (não é ideal, melhor criar alias no api.env).
3. **Fix D4** — Trocar `https://generativelanguage.googleapis.com/v1beta/openai` → `https://generativelanguage.googleapis.com/v1beta/openai/` ou usar endpoint nativo (`/v1beta/models`).
4. **Fix D5** — Adicionar `OPENCLAW_GATEWAY_PASSWORD` em `.secrets/api.env` OU remover model `openclaw` do config.
5. **Smoke-test** — `litellm --config infra/litellm/config.yaml --port 4002` (porta paralela, sem afetar prod).
6. **Cutover** — Só após smoke-test OK: scale 0 → update → scale 1 no proxy 4001.

**Comando pronto pra quando aprovado** (read-only dry-run):

```bash
# Validar config sem subir proxy
litellm --config infra/litellm/config.yaml --dry 2>&1 | head -50

# Subir em porta paralela pra smoke-test
litellm --config infra/litellm/config.yaml --port 4002 &
sleep 3 && curl http://127.0.0.1:4002/health

# Comparar com proxy atual (4001)
diff <(curl -s :4001/models | jq '.data[].id' | sort) \
     <(curl -s :4002/models | jq '.data[].id' | sort)
```

---

## 📁 Arquivos modificados nesta sessão

- **Nenhum.** (audit read-only por design)

## 📁 Arquivos novos criados nesta sessão

- `docs/LITELLM-AUDIT-2026-07-02.md` (este arquivo, ~6.2KB)

---

## 🎓 Lições (cross-rein)

- **D1, D2, D3, D4, D5**: 5 drifts foram prevenidos por AUDIT antes de deploy.
  Sem auditoria, cutover teria causado 5 falhas em cascata.
- **Lesson 290** (MEMORY): 1 missão por chamada. Esta missão foi TODO-003 isolada, sem tentar resolver D1-D5 junto.
- **AGENTS.md § Security**: nenhum secret exposto (probe de URL não vazou keys, status 401 confirma auth required).
- **LGPD**: LiteLLM `cache=false` no config (linha 98) — preserva isolamento de mensagens de clientes cartorários.

---

## Próximo passo (gate user)

Aprovar cutover FREE chain (5 fixes acima)? Ou manter MiniMax proxy como primary?

**Modified by Gustavo Almeida — gerado pelo skill `/prompt-cartorio` · 2026-07-02T19:15Z**
