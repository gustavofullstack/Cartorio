# OpenClaw Context Overflow Guards (G7.14.T3)

> **Wave 26 / A3** · `cartorio-dev` · 2026-07-17  
> Documenta guards de contexto (1M + compaction) e incidentes relacionados
> (overflow 131k, CORS/timeout LobeChat / Lesson 170).  
> **Implementação de código neste wave:** só alinhamento cosmético no spec
> `cartorio-bot.openclaw.json` (`context_window` 8000 → 1048576). Deploy VPS
> permanece SUI (snapshot + scripts).

## 1. Problema histórico

| Data | Sintoma | Causa | Ref |
|------|---------|-------|-----|
| 2026-06-23 | `Context overflow: prompt too large` (131073 > 111072) em sessão `agent:main:main` com 142 msgs | Cap default ~131k; compact falhou (`compactionAttempts=0`) | ADR-016, SESSION_SUMMARY 2026-06-23 |
| 2026-06-24 | B2 reapply | Schema legado ADR-016 **não existe** em OpenClaw 2026.6.10 | ADR-021 |
| 2026-06-25 | T5.0 | `contextTokens=1048576`, model 1M, thinking adaptive, 7 skills | gateway snapshot `_t50_*` |
| 2026-06-26 | E07 | Agent-level `models.json` / `agent.json` ainda 131k em alguns paths | `docs/E07_OPENCLAW_CONTEXT_FIX.md` |
| 2026-07-14 | LobeChat “sem agent” + chat 405/408 | CORS preflight + upstream timeout ~2.5s (não é overflow) | Lesson 170, TROUBLESHOOTING_LOBECHAT |

Overflow de **tokens** ≠ timeout de **upstream** ≠ falha de **CORS**. Tratar cada um com o knob certo.

---

## 2. Schema moderno (canônico) — guards de contexto

Fonte de verdade no repo: `infra/openclaw-agent/gateway-config-snapshot-t49.json`.

### 2.1 Context window / budget

```json
{
  "agents": {
    "defaults": {
      "model": "openai/qwen3.7-max",
      "thinkingDefault": "adaptive",
      "contextTokens": 1048576
    }
  },
  "models": {
    "providers": {
      "openai": {
        "baseUrl": "https://opencode.ai/zen/go/v1",
        "timeoutSeconds": 30,
        "models": [
          { "id": "deepseek-v4-flash", "contextWindow": 131072 },
          { "id": "anthropic-claude-sonnet-4.5", "contextWindow": 1048576 },
          { "id": "qwen3.7-max", "contextWindow": 1048576, "reasoning": true }
        ]
      }
    }
  }
}
```

| Campo | Valor canônico | Função |
|-------|----------------|--------|
| `agents.defaults.contextTokens` | `1048576` (1M) | Cap de contexto do agent |
| `models.providers.*.models[].contextWindow` | 131k ou 1M por modelo | Limite declarado do modelo |
| `agents.defaults.thinkingDefault` | `adaptive` | Reasoning effort (enum schema) |
| `models.providers.openai.timeoutSeconds` | `30` | Evita 408 em ~2.5s (Lesson 170) |

**⚠️** `timeoutSeconds` é em **segundos**, não ms (OpenClaw docs).

### 2.2 Compaction (anti-overflow) — ADR-021

```json
{
  "agents": {
    "defaults": {
      "compaction": {
        "keepRecentTokens": 16384,
        "maxActiveTranscriptBytes": "200mb",
        "truncateAfterCompaction": true
      }
    }
  }
}
```

| Campo | Snapshot atual | ADR-021 B2 original | Função |
|-------|----------------|---------------------|--------|
| `keepRecentTokens` | **16384** | 2048 | Tokens recentes preservados verbatim |
| `maxActiveTranscriptBytes` | **200mb** | 50mb | Threshold que **dispara** compaction |
| `truncateAfterCompaction` | true | true | Rotaciona transcript após compact |

**Mapeamento legado ADR-016 → moderno:**

| ADR-016 (inválido em 2026.6.x) | Equivalente |
|--------------------------------|-------------|
| `auto_compact.threshold_messages` | `maxActiveTranscriptBytes` |
| `strategy: compact_then_truncate` | `truncateAfterCompaction: true` |
| `max_context_tokens` | `agents.defaults.contextTokens` |
| `session_ttl_minutes` | (não no snapshot; session TTL ainda ops-only) |

### 2.3 Spec cartorio-bot (repo)

Arquivo: `infra/openclaw/cartorio-bot.openclaw.json`

| Campo | Antes (drift) | Depois G7.14.T3 |
|-------|---------------|-----------------|
| `context_window` | `8000` | `1048576` |
| `max_tokens` | `2000` | `2000` (output cap; mantido) |

Este JSON é **spec de produto**, não o `openclaw.json` do container. Alinhamento evita doc/config drift em G7.14.T1/T3.

---

## 3. CORS + timeout (Lesson 170) — relacionados mas não overflow

| Guard | Valor | Onde |
|-------|-------|------|
| `gateway.controlUi.allowedOrigins` | 8 origins explícitas (sem `*`) | snapshot + script T5.1 |
| Origins LobeChat | `https://cartorio-lobechat.dfgdxq.easypanel.host`, `https://lobechat.dfgdxq.easypanel.host`, localhost:3210, `*.2notasudi.com.br`, tauri | idem |
| Upstream timeout | `timeoutSeconds: 30` | `models.providers.openai` |

**Script deploy (idempotente, VPS):**  
`infra/scripts/openclaw_fix_lobechat_cors_timeout.sh`

**Runbook:**  
`infra/openclaw-agent/TROUBLESHOOTING_LOBECHAT_2026-07-14.md`

**Nota:** se `gateway.controlUi.allowedOrigins` não emitir ACAO em `/v1/chat/completions`, fallback documentado:

1. Traefik middleware CORS no serviço Swarm  
2. Env `OPENCLAW_HTTP_CORS_ALLOWED_ORIGINS` (se schema aceitar)  
3. Alternativa schema `gateway.http.cors.allowedOrigins` (validar com `openclaw config schema`)

---

## 4. Scripts de fix (já no repo — não reinventar)

| Script | Uso |
|--------|-----|
| `scripts/fix_openclaw_context_1M.sh` | Agent-level models.json / agent.json → 1M + thinking |
| `infra/openclaw-agent/scripts/setup_1m_context.sh` | Setup 1M no workspace agent |
| `infra/scripts/openclaw_fix_lobechat_cors_timeout.sh` | CORS origins + timeout 30s + restart Swarm |
| `scripts/diagnose_openclaw.sh` | Diagnóstico geral |
| `scripts/openclaw_health_check.py` | Health programático |

Procedimento de persona reload: `infra/openclaw-agent/RELOAD_PERSONA.md`  
(`docker service update --force cartorio_openclaw-gateway`).

---

## 5. Checklist de validação (pós-deploy VPS)

```bash
# 1. Health
curl -sS https://agent.2notasudi.com.br/health
# expect: {"ok":true,"status":"live"}

# 2. Context / compaction (dentro do container)
docker exec $(docker ps -q --filter name=cartorio_openclaw-gateway) \
  openclaw config get agents.defaults.contextTokens
# expect: 1048576

docker exec $(docker ps -q --filter name=cartorio_openclaw-gateway) \
  openclaw config get agents.defaults.compaction
# expect: keepRecentTokens + maxActiveTranscriptBytes + truncateAfterCompaction

# 3. Timeout
docker exec $(docker ps -q --filter name=cartorio_openclaw-gateway) \
  openclaw config get models.providers.openai.timeoutSeconds
# expect: 30

# 4. CORS preflight (Lesson 170)
curl -sS -o /dev/null -w "%{http_code} acao=%header{access-control-allow-origin}\n" \
  -X OPTIONS \
  -H "Origin: https://cartorio-lobechat.dfgdxq.easypanel.host" \
  -H "Access-Control-Request-Method: POST" \
  https://agent.2notasudi.com.br/v1/chat/completions
# expect: ACAO ecoa origin (não vazio)

# 5. Chat sem 408
curl -sS --max-time 35 -X POST https://agent.2notasudi.com.br/v1/chat/completions \
  -H "Authorization: Bearer $OPENCLAW_GATEWAY_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"model":"openclaw","messages":[{"role":"user","content":"oi"}],"max_tokens":20}'
# expect: 200 chatcmpl-*, não 408
```

---

## 6. O que NÃO implementar agora

| Ideia | Por quê deferir |
|-------|-----------------|
| N8N WF forçar compact a cada 40 msgs (ADR-016 follow-up) | Precisa SUI + WF id estável; não é “small clear fix” |
| Session TTL 24h no gateway | Campo não está no snapshot validado; risco schema |
| Subir `keepRecentTokens` além de 16k | Trade-off custo/latência; 16k já > B2 (2k) |
| Patch em prod sem SSH | Snapshot no git **não** aplica sozinho no volume |

---

## 7. Estado repo vs prod (honestidade)

| Item | Repo (snapshot/spec) | Prod (precisa SSH) |
|------|----------------------|--------------------|
| contextTokens 1M | ✅ snapshot | Validar com `openclaw config get` |
| compaction block | ✅ snapshot (16k/200mb/true) | Validar |
| timeoutSeconds 30 | ✅ snapshot + script | Script T5.1 pode estar pendente |
| CORS origins explícitas | ✅ snapshot + script | Lesson 170: deploy manual |
| cartorio-bot `context_window` | ✅ alinhado 1M (G7.14.T3) | Spec only |

---

## 8. Refs

- ADR-016: `docs/adr/016-openclaw-context-overflow.md` (legacy schema; resolvida)
- ADR-021: `docs/adr/021-pre-deploy-config-validation.md` (schema moderno + dry-run)
- E07: `docs/E07_OPENCLAW_CONTEXT_FIX.md`
- Lesson 170: `.harness/memory/lesson-170-lobechat-agent-fix-2026-07-14.md`
- Skills registry: `docs/OPENCLAW_SKILLS_REGISTRY_G7.md`
- Snapshot: `infra/openclaw-agent/gateway-config-snapshot-t49.json`

---

**Task:** G7.14.T3 · **Status:** DOC DONE + small spec align; VPS apply = SUI  
**Modified by Gustavo Almeida — Wave 26 A3 (cartorio-dev)**
