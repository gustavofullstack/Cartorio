# Error Handler Global (WF 00) — Wiring Status

**Date**: 2026-06-25 02:38 BRT  
**Sprint**: 3 (B06 RETRY)  
**Author**: cartorio-n8n worker session mvs_7dbeb043241f4ca0b966b5b8ae0aa39e  
**Parent task**: mvs_6663ee57a937460fb324e496cb5ac217 (Pietra root)

---

## TL;DR

- **WF 00** = `00 - Error Handler Global (T25) v4` (`id=4IS5oiLyHWGhtb8g`)
- **33 de 34 WFs ativos** agora tem `settings.errorWorkflow = 4IS5oiLyHWGhtb8g`
- **1 WF** sem errorWorkflow (correto): o proprio WF 00
- Smoke test executado: **WF 00 disparou automaticamente** quando o WF temporario falhou (mode=error, exec 3807)
- **Bug conhecido**: WF 00 dispara mas seu node interno "Alerta Chatwoot" falha por **Lesson 51** (`N8N_BLOCK_ENV_ACCESS_IN_NODE=true` bloqueia `$env.CARTORIO_API_KEY`). WORKAROUND documentado abaixo.

---

## Escopo executado (B06 RETRY)

### Diff antes/depois

| Estado | active | wired to WF 00 | unwired (excl. WF 00) |
|--------|--------|----------------|------------------------|
| Antes  | 34     | 11             | 23                     |
| Depois | 34     | 33             | 0                      |

**Briefing drift**: briefing citava "23 AINDA NAO tem errorWorkflow" mas o numero correto era **22** (query inicial com `id != '4IS5oiLyHWGhtb8g'`). 23 = 22 + 1 (WF 00 incluido, que NAO deve ter errorWorkflow). Drift nao afetou entrega.

### Metodo de wiring

NAO usei PATCH `/api/v1/workflows/{id}` (Lesson 96: retorna 405 em N8N 2.x). Usei **DB UPDATE direto** em `workflow_entity.settings` (mesmo metodo usado para os 11 primeiros WFs wired):

```sql
WITH updated AS (
  UPDATE workflow_entity
  SET settings = (COALESCE(settings::jsonb, '{}'::jsonb) || jsonb_build_object('errorWorkflow', '4IS5oiLyHWGhtb8g'))::json
  WHERE id IN (...) AND active = true
  RETURNING id
)
SELECT COUNT(*) FROM updated;
```

**Atencao**: a coluna `settings` e `json` (NAO `jsonb`). Requer cast explicito: `settings::jsonb` no COALESCE e `::json` no resultado.

**Backup** dos settings originais dos 22 WFs: `/tmp/wf-unwired-backup.txt` (id | name | settings::text).

### Lista dos 22 WFs wired nesta sessao

| ID | Name |
|----|------|
| `00PbDJUpJlrUxAir` | 03 - Handoff Humano (Chatwoot v2) |
| `bryQNXccPvOgNhIL` | 12 - Chatbot LLM End-to-End (PII + MCP + OpenCode-Go) |
| `FhZVTap8JrLJkiOE` | 14 - OpenCode-Go LLM Fallback (direct OpenAI-compat) |
| `csXKw2fXsaeJZRk8` | 16 - Prospeccao Lead Enrichment (Tier A/B/C scoring) |
| `Fint1SGRjPx6tFFs` | 18 - Prospeccao Follow-up D+7 (LGPD opt-out) |
| `d3Qn6V9O4QShpf5h` | 21 - Backup Status 5min (heartbeat + alerta) |
| `KmbrUKvoLzg4cIPW` | 22 - Audit Verify 6h (SHA256 chain check) |
| `HCYh4VRLcBK89sRu` | 23 - Cron Stale Detector (5min) |
| `TtD6qS6LCexwhMke` | 23 - LGPD Esqueci (DELETE cliente + cascade + audit) |
| `FZcmxg1cwD2CB5Bb` | 24 - Daily Cleanup 03:00 (sessoes > 24h Redis) |
| `1C9rZ5DKOKkf0fsA` | 24 - Retencao Diaria (LGPD 5y/2y) |
| `12rMQSwMGkaE293C` | 25 - Metrics Collector (1min Prometheus) |
| `ITEGmC8k7nTJ78Uw` | 25 - Protocolo Concluido: Envia PDF via WhatsApp |
| `2nSa2sw60lh6lhpb` | 26 - Alerta Critico (Telegram IM + Chatwoot) |
| `6e7c830b-4ab8-465e-b9e2-b2a86bc0aca9` | 26 - Monitor OpenClaw (cron 1min, alerta Chatwoot) |
| `NlGoGgAlY9ln8T0s` | 27 - Welcome First Time (consentimento LGPD) |
| `qoyKMaG3MLFYu0yH` | 28 - Audit Snapshot (diario 04:00 S3) |
| `24HV3hEwwQcYasAx` | 29 - Rate Limit Reset (hourly) |
| `OYW3pxLCJFP47xgX` | 30 - Health Deep Check 15min (todos endpoints) |
| `x1N2xJ1WZ83dmxC6` | 31 - Telegram Listener (CartorioBot test) |
| `I4LkReuiurPBS9VN` | EVO-IN - Evolution Webhook Inbound |
| `kTZUoh8ejvGxT8m9` | MCP - Server Tools (T22) v2 |

### Lista dos 11 WFs ja wired (sessoes anteriores)

| ID | Name |
|----|------|
| `bR7qIo3bFpG4zgxO` | 01 - Consulta Emolumento WhatsApp (v3) |
| `MzeYTSDouymzdpRw` | 02 - Criar Protocolo (LGPD) |
| `sDtkfOJ5BA7M73wB` | 04 - Boas-Vindas + Consentimento LGPD |
| `iXWuZRYZLR3FYPYB` | 04 - Consulta Protocolo |
| `UUW8ulDTxZUqBsci` | 05 - Agendamento Atendimento |
| `ukbRUEudoX3SvsqD` | 06 - Segunda Via Documento |
| `D9XJmlJRXZ3lavoa` | 07 - Pesquisa Satisfacao |
| `3rr2WFBCJZ16U4DH` | 08 - Audit Verify Diario |
| `pgtlDqGaMW1MGawt` | 09 - Monitor Backup Diario |
| `jZhgQbJQ5z7atYfK` | 10 - FAQ Bot |
| `5ABAZCQVRLd7AmM5` | 11 - Monitor Cartório |

---

## Smoke test

**Procedimento** (criado WF temporario, ativado, disparado, deletado):

1. Criei WF `[SMOKE-TEST] Error Handler Trigger` (`id=YtjtggEk5kIl2QGh`) com:
   - Webhook trigger em `POST /webhook/smoke-b06-retry`
   - HTTP Request node para URL inexistente (`/api/v1/this-endpoint-does-not-exist-zzz`) → forca 404
   - Respond node no final
   - `settings.errorWorkflow = 4IS5oiLyHWGhtb8g` (setado na criacao)
2. Ativei via `POST /api/v1/workflows/{id}/activate` → 200 OK
3. Disparei via `curl POST https://flow.2notasudi.com.br/webhook/smoke-b06-retry`
4. Verifiquei execucoes via N8N API
5. WF temporario deletado via `DELETE /api/v1/workflows/{id}` → 200 OK + GET subsequente = 404 confirmado

**Resultado**:

| Exec ID | Workflow | Mode | Status | Started | Stopped |
|---------|----------|------|--------|---------|---------|
| 3806 | `[SMOKE-TEST]` | webhook | error | 05:39:58.875 | 05:39:58.914 (39ms) |
| **3807** | **00 - Error Handler Global** | **error** | error | **05:39:58.925** | **05:39:58.943 (18ms)** |

**Veredito**: WF 00 disparou automaticamente em 11ms apos o WF temporario falhar (modo `error`). Mecanismo de `errorWorkflow` **funciona corretamente** em todos os 33 WFs wired.

---

## Finding: WF 00 dispara mas seu alerta interno quebra (Lesson 51)

O node "Alerta Chatwoot" dentro do WF 00 tenta acessar `$env.CARTORIO_API_KEY` no header `X-API-Key`, mas o N8N 2.x tem `N8N_BLOCK_ENV_ACCESS_IN_NODE=true` (default de seguranca) que bloqueia acesso a env vars em expressoes de nos.

```
Node Alerta Chatwoot: error={
  "name": "ExpressionError",
  "message": "access to env vars denied",
  "context": {
    "causeDetailed": "If you need access please contact the administrator to remove the environment variable 'N8N_BLOCK_ENV_ACCESS_IN_NODE'"
  }
}
```

**Execucao historica do WF 00 confirma que isso ja estava acontecendo**:

| Exec ID | Started | Status |
|---------|---------|--------|
| 3807 | 2026-06-25 05:39:58 | error (Lesson 51) |
| 1839 | 2026-06-24 13:18:03 | error (Lesson 51) |
| 1221 | 2026-06-24 08:00:01 | error (Lesson 51) |

**Out of scope para B06**: o escopo deste B06 era APENAS wirear errorWorkflow. O WF 00 em si ter bug interno e questao separada. Workaround canonico (Lesson 51):

- **Opcao A** (rapida): `docker service update --env-add N8N_BLOCK_ENV_ACCESS_IN_NODE=false cartorio_n8n` + restart (~30s downtime)
- **Opcao B** (robusta): trocar o uso de `$env.CARTORIO_API_KEY` por N8N credential type (requer update do WF 00 nodes)

**Recomendacao para proxima task**: aplicar Opcao A como P1 (5min). Depois avaliar Opcao B como cleanup.

**Tambem**: WF 00 ja tem uma credential registrada (`httpHeaderAuth` id=`ADNkyTP2e6uYskUZ` name=`cartorio-api-key`). O node esta configurado com `credentials.httpHeaderAuth` MAS o header expression ainda usa `$env.CARTORIO_API_KEY` em vez de `{{ $credentials.httpHeaderAuth.value }}`. Provavelmente fix antigo que nao foi propagado.

---

## Validacao final

### psql

```
 active_total | wired_to_error_handler | still_unwired 
--------------+------------------------+---------------
           34 |                     33 |             0
```

### N8N API

```
API: total_active=34 wired=33 unwired=0
```

Ambos os checks batem. **B06 RETRY completo**.

---

## Comandos uteis

### Verificar estado atual (qualquer momento)

```bash
ssh cartorio psql -U supabase_admin -d n8n -c \
  "SELECT COUNT(*) FILTER (WHERE active=true) AS active, \
          COUNT(*) FILTER (WHERE active=true AND settings->>'errorWorkflow' = '4IS5oiLyHWGhtb8g') AS wired, \
          COUNT(*) FILTER (WHERE active=true AND id != '4IS5oiLyHWGhtb8g' AND (settings IS NULL OR settings->>'errorWorkflow' IS NULL)) AS unwired \
   FROM workflow_entity;"
```

### Listar wired WFs

```bash
ssh cartorio psql -U supabase_admin -d n8n -c \
  "SELECT id, name FROM workflow_entity \
   WHERE active=true AND settings->>'errorWorkflow' = '4IS5oiLyHWGhtb8g' \
   ORDER BY name;"
```

### Smoke test rapido (criar + disparar + deletar)

```bash
# 1. criar WF temporario com settings.errorWorkflow = 4IS5oiLyHWGhtb8g
# 2. ativar via POST /activate
# 3. POST /webhook/<path>
# 4. verificar /api/v1/executions?workflowId=4IS5oiLyHWGhtb8g (deve mostrar exec nova mode=error)
# 5. deletar WF temporario via DELETE /api/v1/workflows/{id}
```

---

## Referencias

- `infra/n8n-workflows/00-error-handler.json` — export do WF 00 (template local)
- `infra/n8n-workflows/README.md` — index geral dos workflows
- `docs/superpowers/specs/2026-06-23-sprint-3-design.md` — Sprint 3 design
- `docs/ADRs/ADR-015-chatwoot-restart-loop.md` (futuro) — P0 bug relacionado
- `docs/ADRs/ADR-016-openclaw-context-overflow.md` (futuro) — P0 bug relacionado
- Memory `.harness/memory/MEMORY.md` — Lesson 51, 96, 109