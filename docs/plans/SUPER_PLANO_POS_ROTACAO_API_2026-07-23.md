# SUPER PLANO — Validação Pós-Rotação de API em Produção (2026-07-23)

> **Contexto**: rotação urgente de chave em prod (MINIMAX_API_KEY em 2026-07-22 via `docker service update --env-add`, lesson 228) + hardening geral pedido pelo Gustavo: validar HARNESS, API, WEBSOCKET, WEBHOOK, MCP[SERVER/CLIENT], DB-POOL, BRAINS[MD], MEMORY, INPUT, OUTPUT, CONTEXT WINDOW, CACHE HIT.
> **Executor**: Kimi (k3) auxiliando sessão GPT-5.6 Terra ("Troca urgente da API do Cartório em produção").
> **Regras respeitadas**: sem PII raw, sem ações jurídicas automáticas (HITL), alterações locais pré-existentes NÃO tocadas (isolamento de autoria), nenhum secret impresso.

---

## 1. Goals & Metas (mensuráveis)

| ID | Goal | Meta (KPI) | Status |
|----|------|-----------|--------|
| G1 | Suite local íntegra | 100% passed, 0 falhas determinísticas | ✅ 5736–5742 passed / 0 failed (2 reruns) |
| G2 | API REST prod saudável | `/health`, `/ready`, `/radar`, `/integracoes` 200 + latência p95 < 1s | ✅ 200 em todos; radar 7/7, integrações 8/8 |
| G3 | Superfícies de borda protegidas | Webhook/WS/MCP rejeitam sem auth (401/403), nunca 500 | ✅ TG 401×2; MCP 401; WS path correto ping/pong |
| G4 | Audit chain íntegra | `chain_ok=True` via endpoint OU evidência indireta forte | ⚠️ Parcial — ver F-002 |
| G5 | Docs/memória atualizadas | SUPER PLANO + MEMORY.md + sessão | ✅ Este doc + entradas de memória |

## 2. Matriz de Rounds (R0–R9) — Evidências

| Round | Escopo | Resultado | Evidência |
|-------|--------|-----------|-----------|
| R0 | Baseline local (pytest 3×) | **Verde** 5742→5736 passed, 0 failed. 1ª run teve 3 falhas **não-determinísticas** (F-001) | `pytest --no-cov`: 5736 passed/21 skipped/19 deselected em 10m02s |
| R1 | API REST prod | **Verde** | `/health` 200 (71ms), `/ready` 200 `audit_chain_initialized=true`, `/radar` green 7/7, `/integracoes` 8/8 online (db 1ms, redis 3ms, n8n 9ms, openclaw 7ms, chatwoot 29ms, supabase 147ms, evolution 217ms, opencode_go 485ms) |
| R2 | Audit chain | **Bloqueado p/ chave** | `POST /api/v1/audit/verify` exige `X-API-Key` → chave local stale → 401 (F-002). Indireto: gauge `cartorio_audit_chain_length=1078`, `/ready` ok, dead-man's-switch 15min ativo |
| R3 | PII scrubbing | **Verde** | Métricas vivas: `pii_blocked_total{channel="api",tipo_scrub="ip"}=2`, `scr_latency` summary operante; suite PII (incl. `test_pii_telegram_output_g9.py`) verde |
| R4 | WebSocket | **Verde c/ ressalva** | Path real é `/api/v1/ws/atendimentos` (prefix no include_router) — AGENTS.md diz `/ws/atendimentos` (F-003). Handshake + `{"type":"ping"}` → `{"type":"pong"}` ✅ |
| R5 | Webhooks TG + WA | **TG verde / WA gap** | TG: sem secret→401 "Missing", secret errado→401 "Invalid"; `webhook/info`: URL prod correta, `pending_update_count=0`, `max_connections=40`, allowed_updates corretos ✅. WA: **processa mesmo com HMAC inválido** (F-004) |
| R6 | MCP server/client | **Verde c/ ressalva** | `/mcp`→307→`/mcp/`→401 "MCP authentication required" (fail-closed ✅, lesson 224). Handshake autenticado bloqueado: `MCP_API_KEY` local stale (F-002). Client config `~/.mavis/mcp/clients/` **não existe** (F-005) |
| R7 | DB pool + Redis | **Verde** | Radar: db 1ms / redis 3ms; `cartorio_dlq_pending=0`; idempotency/rate-limit/DLQ verdes na suite |
| R8 | Brains + Memory | **Verde** | `.brain/` íntegro (memory/2026-07-20.md mais recente); `.harness/memory/MEMORY.md` lessons até 228; este plano adiciona lesson 229 |
| R9 | Documentação | **Verde** | Este documento + entradas de memória |

## 3. Findings

### F-001 — Flake não-determinístico em parsing de data Telegram (severidade: média)
- **Sintoma**: run #1 falhou `test_parse_date_formato_invalido_retorna_none`, `test_state_agendar_data_formato_invalido`, `test_state_agendar_hora_formato_invalido`. Runs #2 e #3 (mesmos flags): **0 falhas**. Isolados e em pares: sempre passam.
- **Causa provável**: poluição de estado entre arquivos (ordem fixa, então suspeita é dependência de tempo/seed ou vazamento via fixture async). `_parse_date` em si é puro (`telegram.py:1124`).
- **Recomendação**: (a) adicionar `pytest-randomly` em CI para expor ordem; (b) loop de bisect `pytest --lf -vv` na próxima ocorrência (cacheprovider ON — a run que falhou estava com `-p no:cacheprovider`, perdendo o `--lf`); (c) marcar com marker dedicado quando reproduzido. **Não é regressão do commit dff5fcc** (o comportamento "conversational fallback" é intencional e testado por `test_state_agendar_data_conversacional_sai_do_wizard`).

### F-002 — Chaves locais `.env` dessincronizadas de prod pós-rotação (severidade: alta operacional, risco zero de segurança)
- **Sintoma**: `CARTORIO_API_KEY` e `MCP_API_KEY` do `backend/.env` local → 401 em prod.
- **Estado**: **conhecido** — lesson 227(h) já registra dessincronia + cofre `~/.mavis/secrets/cartorio.env` inexistente + `ENV_PRODUCTION.md` não-confiável.
- **Impacto**: impede verificação remota da audit chain (G4) e handshake MCP autenticado.
- **Recomendação**: re-sincronizar `.env` local a partir do Swarm (`docker service inspect cartorio_api --format '{{json .Spec.TaskTemplate.ContainerSpec.Env}}'` na VPS) ou re-criar cofre; revisar `ENV_PRODUCTION.md`.

### F-003 — Doc drift: path do WebSocket (severidade: baixa)
- AGENTS.md/CLAUDE.md dizem `/ws/atendimentos`; real é `/api/v1/ws/atendimentos` (main.py:887, `include_router(ws_router, prefix="/api/v1")`).
- **Recomendação**: corrigir AGENTS.md + CLAUDE.md + skill `.agents/skills/api/SKILL.md`.

### F-004 — Webhook WhatsApp/Evolution: HMAC inválido NÃO rejeita (severidade: alta — decisão de segurança pendente)
- **Código**: `whatsapp.py:503-508` — `validate_evolution_signature` retorna False corretamente (secret configurado + sig ausente/errada), mas o handler **só loga warning e segue processando** (`return 401` comentado, "Evolution pode parar de enviar"). Prova live: POST sem assinatura → 200 (filtrado só pelo event gate).
- **Risco**: spoofing de `remoteJid` → injeção de mensagem no pipeline em nome de cliente com consentimento LGPD ativo. Mitigações parciais: consent gate, idempotency, rate limit 3s, possível allowlist de rede no Traefik (não verificável daqui).
- **Recomendação (não aplicada — toca PII → exige review cartorio-lgpd)**: trocar "logar e seguir" por **descarte silencioso** (200 sem processar pipeline) quando HMAC falha e `EVOLUTION_REQUIRE_SIGNATURE=true`; adicionar teste de regressão que falha se payload não-assinado chegar ao `process_message`; alerta Telegram (padrão Alertmanager G8) em rajada de HMAC failures.
- **Task sugerida**: `E9.S1.T1` (sec) com sign-off `cartorio-lgpd`.

### F-005 — MCP client config ausente (severidade: baixa)
- `~/.mavis/mcp/clients/cartorio-mcp-config.json` referenciado em CLAUDE.md não existe. Recriar quando F-002 for resolvido.

## 4. Não-objetivos (fora do escopo desta rodada)
- Prova de rotação MiniMax via log de container (`docker exec` + grep `provider`) — requer SSH/Tailscale (100.99.172.84 timeout neste Mac no momento). `/api/v1/health/llm` reporta `opencode_go/404` = padrão conhecido (lesson 228e), **não é evidência nem contra nem a favor**.
- E2E Telegram smoke 20 cenários (marker `smoke`, requer `SMOKE_TARGET=prod`).
- Correção dos findings (aplicar em branch própria, PR com checklist + review `cartorio-lgpd` para F-004).

## 5. Próximas tasks (padrão E_.S_.T_)

| Task | Descrição | Owner | Prioridade |
|------|-----------|-------|-----------|
| E9.S1.T1 | WA webhook HMAC fail-closed (descarte 200) + teste regressão + alerta | cartorio-dev + **review cartorio-lgpd** | P1 |
| E9.S1.T2 | Re-sync `.env` local (CARTORIO_API_KEY, MCP_API_KEY) + revisar ENV_PRODUCTION.md + recriar cofre | cartorio-dev | P1 |
| E9.S1.T3 | Fix docs WS path (AGENTS.md, CLAUDE.md, skill api) + recriar cartorio-mcp-config.json | cartorio-dev | P2 |
| E9.S1.T4 | Flake F-001: pytest-randomly em CI + bisect com cacheprovider ON | cartorio-dev | P2 |
| E9.S1.T5 | Prova de rotação MiniMax via log de container (SSH Tailscale) | cartorio-n8n / SRE | P2 |
| E9.S1.T6 | Rodar `/api/v1/audit/verify` com chave nova pós E9.S1.T2 e anexar `chain_ok` aqui | cartorio-lgpd | P1 |

## 6. Rollback
Nenhuma mudança de código/config aplicada nesta rodada (somente leitura + testes locais + chamadas GET/POST não-privilegiadas). Nada a reverter. Scratch files (`scratch_*.py`) e modificações locais pré-existentes permanecem **intocados**.

---
*Gerado 2026-07-23 · Workflow: analisar → testar → corrigir(N/A) → melhorar → otimizar → documentar → comentar → salvar memória*
