# IMENSAGER — Relatório de Validação (2026-07-28)

**Agentes executores:** ZCode — Sessão A (parcial, prod VPS, ~40min) + **Sessão B (local QA harness, ~1h, consolida)**
**Ambiente:** prod VPS (187.77.236.77 / Tailscale 100.99.172.84) + Mac local (Photon :8793) + **QA local isolado `cartorio_qa` (PG16 UTC, backend :8001)**
**Branch testada:** `master` @ `16748d96`
**Prompt executado:** `prompts/IMENSAGER_VALIDATION_PROMPT.md` **v2.0** (v1.0 colada pressupõe módulo `imensager` + envs `IMENSAGER_*` inexistentes — superseded)
**Persona:** PIETRA · MINIMAX M3 1M XMAX

## Resumo executivo (consolidado)

- **Status geral: 🟡 amarelo** — sanity/audit/PII-api/resiliência verdes; **3 findings P0-candidate novos** (HITL offline não escala isenção/urgência; RG formato MG não mascarado; Art. 18 indisponível no canal iMessage). Fases live com iMessages reais seguem bloqueadas (autorização Gustavo).
- **Testes executados:** Sessão A — 102 (100% verde). Sessão B — 206 focados + 25 casos live HTTP contra backend QA local + gates lint/mypy/secrets verdes.
- **P0 IDENTITY_HERMES_LEAK:** **permanece ABERTO** (regra N≥30 pós-fix não rodada em nenhuma das sessões).
- **Root cause definitivo do "audit chain quebrada" local:** artefato de **TimeZone** (F2 refinado — não era rotação HMAC). Prod intacto nas duas verificações.

## Resultados por fase (consolidado A+B)

| Fase | Status | Evidência | Notas |
|------|--------|-----------|-------|
| 1. Sanity | ✅ | A: health/ready/radar 200 <100ms, Photon LISTEN 401 fail-closed, 86 passed. B: backends :8000/:8001 up, genesis chain=True, Redis PONG, 206 passed | |
| 2. Inbound | ✅ via API | B: 8 casos live — texto 200+intent; vazio/whitespace 400 RFC7807; emojis graceful; anexos aceitos (ignorados offline) | iMessage real do device segue pendente (autorização) |
| 3. Outbound | ⏸ | — | Envio real = Hermes gateway/device (B5); typing/rich media não exercitáveis sem device |
| 4. PII | 🔴 1 gap | B: resposta API zero eco CPF/RG/tel/email; log backend zero PII raw (grep); scrub() direto: CPF/tel/email OK | **F5: RG `MG-12.345.678` NÃO mascarado** |
| 5. Audit | ✅ | A: prod 33/33 intact. B: QA local genesis→42 intact (score 1.000) pós-tráfego+burst; t024/t025 verdes (114 testes) | webhook ingest não audita (F8, menor) |
| 6. HITL | 🔴 2 gaps | B: `/humano`+"falar com escrevente" → hitl_required=true ✅. **"isenção"→intent:preco (F1B); "urgente/escritura"→welcome (F2B)** | path determinístico offline; LLM-only escalation |
| 7. Resiliência | ✅ | A: retry envelope 15/15. B: 70 burst → 30×200+40×429 (tier default exato); envelope 3×20s short-circuit c/ CB open; E3.09 chaos 6 cenários verde 2026-07-27 | |
| 8. Performance | ✅ | B: offline path P50=49.8ms; RSS 18.6MB; métricas `cartorio_*` em `/api/v1/metrics/prometheus` | throughput live com device pendente |
| 9. LGPD | 🔴 2 gaps | B: `/bot/lgpd/access` telegram 200 (controle); **imessage → 422 (F10)**; `lgpd_dsar.py` não montado + mock (F9) | Art. 18 indisponível no canal iMessage |
| §2.4/2.6 gates | ✅ | conftest LLM isolation `opencode_go`; envelope 15/15 | |

## Critérios de aprovação (consolidado)

| # | Status | Detalhe |
|---|--------|---------|
| C1 | 🟡 | 100% verde no executado; outbound real pendente |
| C2 (P0) | 🔴 | F5: variantes RG (`UF-12.345.678`, `SSP MG`, bare c/ contexto) passam em claro |
| C3 (P0) | ✅ | prod 33/33 (A) + QA local genesis→42 (B); t024/t025 verdes |
| C4 (P0) | 🔴 | F1B/F2B: isenção/urgência/escritura não escalam no path offline determinístico |
| C5 (P0) | 🔴 | F10: canal imessage rejeitado em `/bot/lgpd/*`; F9: DSAR router não montado |
| C6/C7 | ✅ | P50 ~50ms offline path; rate limiter preciso |
| C8 | ✅ | 0 crash, 0 500 não-tratado; erros via RFC7807 |
| C9-C11 | ✅ | B: suite completa + ruff 0 + mypy 0 (229 arquivos) + secrets 0 violações |
| C12 | ✅ | commits da sessão seguem padrão |

## P0 IDENTITY_HERMES_LEAK — estado

- **Permanece ABERTO** (N≥30 pós-fix não executado).
- SOUL.md VPS: persona PIETRA canônica ✅. Defesa-em-profundidade `pietra_identity_guard.py` deployada (39 regression tests).
- **F3 (Sessão A):** `/opt/data/config.yaml` do `cartorio_hermes` VPS lista `deepseek-v4-flash-free`/`nemotron-3-ultra-free` — hipótese de fallback free-tier ignorando persona (Camada 3). Confirmar config efetiva do Photon sidecar local.

## Findings (consolidados)

### Da Sessão A
- **FA1.** Prompt v1.0 diverge do repo (módulo/endpoints/envs inexistentes). Usar v2.0. Webhook FastAPI imensager dedicado seria task de **implementação** (cartorio-dev + cartorio-n8n), não validação.
- **FA2 → refinado por FB0 (root cause provado).**
- **FA3.** Models free-tier no config hermes VPS (ver P0 acima).

### Da Sessão B
- **FB0 (root cause, NÃO-tampering) — "audit chain quebrada" local = TimeZone.** Coluna `audit_log.timestamp` é `timestamp without time zone`; brew PG local com `TimeZone=America/Sao_Paulo`; ORM escreve tz-aware UTC → Postgres converte p/ BRT ao armazenar → verify recomputa com valor shiftado → mismatch em 152/152. **Prova:** recomputar entry 152 com +3h → `match=True`; structlog UTC 03:36 vs DB 00:36. Corrige FA2 (não era rotação HMAC). Prod usa UTC → intacto (coerente com A). Fix local: `ALTER DATABASE ... SET "TimeZone"='UTC'`; QA em `cartorio_qa` (UTC) → genesis→N intact.
- **FB1 (P0-candidate) — "isenção" não escala HITL offline.** Repro: `POST /agent-hermes/execute {"user_message":"Preciso de isenção de emolumentos..."}` → `intent:preco`, `hitl_required:false`. Causa: classificador offline (`cartorio_agent.py:470`) só escala c/ palavras explícitas ("humano"/"escrevente"/...). Fix sugerido: keyword gate determinístico (`isenç`,`urgente`,`escritura`,`certidão`,`testamento`,`inventário`,`usucapião`) → `action=humano` **antes** do intent preço. Review `cartorio-lgpd`.
- **FB2 (P0-candidate) — "urgente/escritura" cai em welcome offline.** Mitigação: bot não DECIDE ato (invariante preservada); gap é escalonamento proativo.
- **FB3 (menor) — falso positivo HITL por substring.** `agent_hermes.py:135`: `"escrevente" in answer` → boilerplate LGPD marca hitl=true sem escalonamento real. Confiar só em `reply.action`.
- **FB4 (ambiental) — anexos ignorados offline** (OCR/transcrição/DRAFT por anexo exigem LLM online).
- **FB5 (P0-candidate) — RG formato MG não mascarado.** `scrub("RG MG-12.345.678")` → claro; idem `RG: 12.345.678 SSP MG`, `meu rg 123456789`. Mascara só `12.345.678-9` (exige verificador). RG é DATASENSITIVE (AGENTS.md) e `UF-XX.XXX.XXX` é o formato MG. Fix em `pii.py` ⇒ `cartorio-dev` implementa + `cartorio-lgpd` assina.
- **FB6 (design question) — protocolo/escritura não mascarados.** Bot precisa discutir protocolo com titular (welcome sugere exemplo). Mascarar pre-LLM/logs ≠ mascarar resposta ao titular. Decisão `cartorio-lgpd`.
- **FB7 (limitação) — base64 bypass** não coberto (registrar em RIPD).
- **FB8 (menor) — `/agent-hermes/webhook` ingest não audita** (só `/execute` gera entry).
- **FB9 (P0-candidate LGPD) — `lgpd_dsar.py` não montado** (ausente do OpenAPI) e implementação é mock sem persistência. Montar+persistir ou remover.
- **FB10 (P0-candidate LGPD) — Art. 18 indisponível no canal iMessage.** `bot_lgpd.py` schemas usam `Literal["telegram","whatsapp"]` → `channel:"imessage"` = 422. Estender p/ `"imessage"` (4 schemas) + testes. Review `cartorio-lgpd`.

## Bloqueios registrados (goals-workflow §6)

| Bloqueio | Autoridade/input faltante |
|---|---|
| Outbound real, typing indicator, rich media, N≥30 identity | Autorização Gustavo + device iPhone (B5 Felipe) — outward-facing |
| HITL end-to-end (aprovação escrevente real) | Janela do Gustavo |
| LLM-online paths (anexos OCR, escalation semântica) | Provider `opencode_go` offline local; validar em staging c/ LLM up |

## Lições para MEMORY.md

1. **(L283 candidata) Audit chain em clone local exige `TimeZone=UTC` no Postgres** — coluna naive + ORM tz-aware + GUC local ≠ UTC = 100% false-positive no verify (prova: recompute +3h → match). Diagnosticar tz ANTES de suspeitar tampering ou rotação de chave.
2. **(reforço A) Prompts versionados divergem — conferir versão consolidada no repo antes de executar a colada.**

## Ambiente de QA local (reproduzível — Sessão B)
```bash
brew services start redis && brew services start postgresql@16
psql -d postgres -c "CREATE DATABASE cartorio_qa OWNER supabase_admin"
psql -d postgres -c "ALTER DATABASE cartorio_qa SET \"TimeZone\"='UTC'"
pg_dump --schema-only --no-owner --no-privileges "$SRC" \
  | grep -viE "pg_net|pgsodium|pg_graphql|supabase_vault" | psql "$DST" -f-
DATABASE_URL=.../cartorio_qa... uv run uvicorn app.main:app --port 8001
```

## Artefatos
- Logs backend QA: `/tmp/imensager_qa_backend_8001.log` (zero PII raw — grep verificado)
- Suite completa B: `/tmp/qa_testfast_20260728.log`
- Provas tz: `/tmp/qa_audit_tz.py`, `/tmp/qa_audit_brute.py`, `/tmp/qa_audit_entry152.py`

## Commit
- `test(imensager): consolidated QA 2026-07-28 — tz root cause + 10 findings (3 P0-candidates: HITL offline, RG scrub, LGPD imessage)`
- `Modified by Gustavo Almeida`
