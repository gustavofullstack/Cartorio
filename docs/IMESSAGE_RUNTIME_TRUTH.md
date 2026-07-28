# IMESSAGE RUNTIME TRUTH — 2026-07-28 (campanha PIETRA iMESSAGE P0)

> Capturado evidence-first. `CONNECTED != OPERATIONAL`. Nada aqui é claim de documentação antiga.

## 1. Autoridades

| Alvo | Valor |
|---|---|
| VPS hostname | `Cartorio` |
| VPS Tailscale | `100.99.172.84` |
| VPS público | `187.77.236.77` |
| Data da captura | 2026-07-28 03:29–04:30 UTC |
| Repo HEAD (início) | `16748d96` (master) |
| Repo HEAD (pós-fixes) | `8507b6f4` |

## 2. Serviços Docker Swarm (estado real)

| Serviço | Réplicas | Notas |
|---|---|---|
| `cartorio_system-api` | **1/1 healthy** | **É o backend FastAPI real** (Pietra, audit, PII, MCP `/mcp`, `/api/v1/pietra/*`). Serve `api.2notasudi.com.br`. APP_VERSION 0.6.0, env GIT_SHA=`0c0dc79` (stale — código rodando ≈ HEAD) |
| `cartorio_api` | **0/0** | Serviço legado duplicado. Tasks `Rejected: No such image easypanel/cartorio/api:latest`. NÃO é o backend ativo |
| `cartorio_hermes` | 1/1 | Hermes Agent v0.19.0 **CLI interativo**; morre em seguida ("Input is not a terminal"). Não é gateway |
| `cartorio_evolution-api` | 0/0 | legado |
| `cartorio_whatsapp-api` | 1/1 | Evolution (WhatsApp) |
| `cartorio_redis` | 0/0 | legado |
| `cartorio_memory-cache` | 1/1 | Redis 8.8 — usado pelo app (`REDIS_URL`) |
| `cartorio_banco_de_dados` | 1/1 | pgvector/pg17 |
| `cartorio_supabase*` | misto | auth/storage 1/1; db e realtime 0/x |
| `cartorio_n8n` | 1/1 | |
| Traefik | 1/1 | `:80/:443` |

**Não existe Photon/Spectrum/iMessage service na VPS.**

## 3. Mac local (estado real — inspeção não-destrutiva)

| Processo | Evidência |
|---|---|
| LaunchAgent `ai.hermes.gateway-cartorio` | PID 730, `hermes_cli.main --profile cartorio gateway run` |
| Photon sidecar :8793 | node PID 751 (projeto Spectrum `438527e1-…`) |
| Photon sidecar :8789 | node PID 1166 (projeto `bcdcc0f7-…`, outro profile) |
| `imessage-router/router.mjs gemini` | PID 1050 — linha **outra** (grok/gemini), não a do cartório |
| Hermes local (2 instâncias) | PIDs 730/1127 |

## 4. CURRENT_IMESSAGE_PATH (verdade capturada)

```
iPhone → Messages.app (Mac) → Photon sidecar :8793 (Mac)
  → Hermes gateway profile=cartorio (Mac, SOUL.md=Pietra)
  → LLM: MiniMax-M3 DIRETO (api.minimax.io) — bypassa VPS
  → MCP tools: VPS https://api.2notasudi.com.br/mcp (19 tools registradas no boot)
  → Photon → Messages.app → iPhone
```

Provas: `~/.hermes/profiles/cartorio/config.yaml` (`base_url: https://api.minimax.io/v1`),
logs VPS `cartorio_agent skip provider=* circuit=open`, resposta canned em 77ms.

## 5. TARGET_IMESSAGE_PATH

```
iPhone → Messages.app (Mac) → Photon sidecar (Mac, transport-only)
  → Hermes gateway (Mac, thin shell)
  → LLM via VPS https://api.2notasudi.com.br/api/v1/pietra/chat/completions
     (system prompt Pietra + PII scrub + identity guard + circuit breaker)
  → MCP tools VPS /mcp (cartorio_calcular_emolumento = Portaria 8.664/2025)
  → Photon → Messages.app → iPhone
```

Restrição física: iMessage exige macOS (Messages.app). Mac é **transport adapter**
— aceito por Lesson 282 e pelo super prompt §0 ("transport adapter"). O que é
proibido é o Mac ser **runtime/decisor** (LLM direto, sem PII/audit/HITL da VPS).

## 6. ARCHITECTURE_DRIFT (encontrado)

1. **Mac bypassava a VPS** — `base_url: api.minimax.io/v1` desde 2026-07-28 00:22
   (backup 22:57 apontava para `/api/v1/pietra`). Reversão foi reação à VPS brain-dead.
2. **Endpoint pietra sem system prompt** → LLM se auto-identificou em prod:
   *"Eu sou o **MiniMax-M3**, um modelo de inteligência artificial desenvolvido pela
   **MiniMax**"* (reproduzido 03:51 UTC via endpoint público).
3. **Circuit breakers stale**: `cb:open:{MiniMax_direct,opencode_free_1/2/3}` com
   TTL 5h abertos desde ~23:20 UTC por blip transitório → endpoint servindo string
   fixa em ~80ms (`model: none`).
4. **`OPENCODE_GO_BASE_URL=http://localhost:9999/v1`** — aponta para localhost do
   container, nada escuta → LLM MONITOR reporta provider OFFLINE (mensagem de erro
   trocada: minimax reporta erro do opencode_go).
5. **Tabela de emolumentos placeholder errada** (P0 financeiro): autenticação 28,90
   (oficial 11,21), reconhecimento firma 32,10 (11,21), procuração 156,40 (68,94).
   Fonte oficial: Portaria CGJ/TJMG 8.664/2025 (`backend/data/fontes/cpo86642025.pdf`).
6. `cartorio_api` 0/0 com imagem inexistente — serviço zumbi no Swarm.
7. `PHOTON_ALLOW_ALL_USERS=true` — linha aberta a qualquer remetente (decisão humana pendente, Gap G4 do relatório paralelo).

## 7. Root causes → fixes (esta campanha)

| RC | Causa | Fix | Status |
|---|---|---|---|
| RC1 | cb:open stale 5h | delete Redis keys (operacional) | ✅ feito 03:55 UTC |
| RC2 | flood 02:44 → 429 | rate limit global funcionou | ✅ sem ação |
| RC3 | Mac→minimax direto | pendente: flip para VPS pós-deploy | ⏳ |
| RC4 | endpoint sem system prompt | `PIETRA_SYSTEM_PROMPT` prependido sempre | ✅ commit 76bffdf3 |
| RC5 | guard só-Hermes + think leak | guard estendido (MiniMax/Claude/GPT/Kimi/DeepSeek/Gemini/Grok) + `_strip_think_tags` + hard-stop | ✅ commit 76bffdf3 |
| RC6 | sem tools passthrough + sem PII scrub | `tools`/`tool_choice` + `pii.scrub` pre-LLM | ✅ commit 76bffdf3 |
| RC7 | emolumentos placeholder | `EMOLUMENTOS_2026` oficial + MCP tool→`emolumento_real_djalma` (HITL) | ✅ commit 8507b6f4 |
| RC8 | OPENCODE_GO_BASE_URL localhost:9999 | pendente (env Easypanel) | ⏳ documentado |
