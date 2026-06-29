# OpenClaw M3 Fix — 2026-06-24 18:35 BRT

> Sessão ZCode+MiniMax-M3 (orquestrador).
> 4 mudanças aplicadas via SSH direto (sem agent).

## Contexto
OpenClaw Gateway (container `cartorio_openclaw-gateway`) estava usando:
- `model: deepseek-v4-flash` (131k context, não 1M)
- `temperature: NOT SET` (default ~0.7 — nondeterministic para emolumento!)
- `systemPrompt` antigo com emoji `📜` (CartórioBot)
- Provider `codex` apontando para `https://chatgpt.com/backend-api` (gpt-5.5 → 401, não tem key)
- `gateway.http.endpoints.chatCompletions.enabled` **false** → 404 em /v1/chat/completions

## Fixes aplicados

### 1. `agents/main/agent/agent.json`
- `model: deepseek-v4-flash` → **`minimax-m3`** (1M context)
- `fallbackModel: deepseek-v4-flash` (mantido como fallback)
- `temperature: null` → **`0.0`** (P0.1 do deepening plan)
- `topP: 1.0`, `maxTokens: 4096`
- `systemPrompt`: reescrito **sem emojis**, **direto**, LGPD-by-design, persona mineira, max 2 frases
- `toolsEnabled`: evolution-api, supabase, n8n, audit-log, chatwoot, calendar

### 2. `openclaw.json` (gateway)
- `agents.defaults.thinking`: **Deletado** (Mavis tentou `enabled: "adaptive"` com triggers mas OpenClaw 2026.6.10 rejeitou — invalid config)
- `agents.defaults.thinking`: **Recriado** com `{"enabled": true}` (formato bool simples)
- Backup: `openclaw.json.bak-fix2-1782325685`

### 3. `agents/main/agent/models.json` (FIX CRÍTICO)
- **Provider `codex`** (gpt-5.5 → 401 not supported) → **Provider `openai`** com `baseUrl: https://opencode.ai/zen/go/v1` + key `sk-xcRwExjQ` (Opencode-Go nova)
- Models listados: `minimax-m3` (1M), `deepseek-v4-flash` (1M), `minimax-m2.7` (1M) — todos com `contextWindow: 1048576`
- `defaultModel: openai/minimax-m3`, `defaultProvider: openai`
- Backup: `models.json.bak-codex-removed-1782326092`

### 4. `openclaw.json` HTTP endpoints
- Adicionado `gateway.http.endpoints.chatCompletions.enabled: true` (estava false → 404)
- Adicionado `gateway.http.endpoints.models.enabled: true`
- `embeddings.enabled: false` (default, não usado)
- `responses.enabled: false` (default, não usado)
- Backup: `openclaw.json.bak-http-enabled-1782326197`

## Status atual (verificar)
- Container reiniciando (scale 0→1, mas Easypanel tá tendo "host-mode port already in use")
- Logs: `[gateway] agent model: openai/gpt-5.5 (thinking=medium, fast=off)` — ANTES do fix de models.json
- Após restart com fix: deve mostrar `minimax-m3` com thinking ON

## Testes pendentes
- `GET /v1/models` deve retornar 200 JSON (não HTML)
- `POST /v1/chat/completions` com `model=minimax-m3` deve retornar reply em <5s
- Healthcheck agent deve mostrar `minimax-m3 1M context, thinking=ON`

## Lições aprendidas
1. **OpenClaw tem 3 arquivos de config** (não 1): `openclaw.json` (gateway), `agents/main/agent/agent.json` (per-agent), `agents/main/agent/models.json` (per-agent providers)
2. **Provider no `agent/models.json` OVERRIDE o de `openclaw.json`** — sempre editar ambos
3. **thinking aceita só `bool` em 2026.6.10**, não `string: "adaptive"` nem `object: {triggers, complexity_threshold}`
4. **HTTP endpoints são opt-in** — `gateway.http.endpoints.{chatCompletions, models, embeddings, responses}.enabled`
5. **Backup é importante**: 4 backups criados com timestamps antes de cada fix

## Próximos passos
- Aguardar OpenClaw subir + testar M3
- Testar Telegram bot @test_cartorio_bot (manda /start e ver reply com M3+thinking)
- Sync memory com Mavis agent (que estava aplicando fix em paralelo)
- Considerar aumento de memory limits (causa do restart loop OOM)

Modified by Gustavo Almeida
