# RELEASE MANIFEST — RC Etapa 3 (2026-07-25)

> Gerado pelo orquestrador E3.12. **Sem push. Sem deploy 0028. Sem secrets/PII.**
> Itens marcados `⟨PÓS-QA⟩` são preenchidos após a FULL QA E3.11.

## 1. Commit range

- Base: `origin/master` → HEAD local (**39 commits à frente**) — sem push
- Range: `origin/master..HEAD`
- Verdade de progresso: `docs/G9_EVIDENCE_LEDGER_E302.md` (**41 DONE / 43 TODO / 16 BLOCKED_HUMAN**)

## 2. Migrations

| Arquivo | Ação | Gate |
|---------|------|------|
| `backend/alembic/versions/2026_07_24_0028-fix-fn-auto-audit-ts-consistency.py` | Fix trigger `fn_auto_audit` (canonicalização timestamp — root cause chain break Lesson 231) | **BLOCKED_LGPD** — deploy só após sign-off DPO (ADR-030) |
| Alembic heads | `0028 (head)` — **single head ✓** | gate E3.11 |

- Rollback migration: `alembic downgrade 0027` (reverte trigger ao estado 0027; cadeia legacy permanece — default no-rewrite ADR-030).

## 3. Env vars novas

| Var | Uso | Obrigatória? |
|-----|-----|--------------|
| `CARTORIO_DPO_API_KEY` | tier DPO (60 req/min) via match exato timing-safe | Opcional (fail-secure → padrão 30) |

## 4. Dependency changes

- `mcp` 1.28.0 → 1.28.1 (PYSEC fixes) — commit `922b2549`
- `setuptools` 82 → 83 (PYSEC fixes) — commit `922b2549`

## 5. Security changes (esta etapa)

| Mudança | Commit | Evidência |
|---------|--------|-----------|
| TrustedProxyMiddleware XFF fail-closed (somente proxies 127/8, 10/8, 172.16/12, 187.77.236.77/32) | `73989420` | 12 testes + cenários E3.04 |
| XFF cru removido de `deps.py`, `integrations.py`, `request_context.py`, `rate_limit_by_key.py` | `73989420` | diff review |
| Tier DPO por key registrada (nunca prefixo) + timing-safe | `73989420` | testes registry |
| Rate limit usa IP resolvido no trust boundary | `73989420` | teste não-bypass |
| Secret scanner no `make lint` | `73989420` | make lint local |
| Gate CI secrets_scan (full + incremental, hard gate) | `7a2fd377` | bateria scanner + `test_cd_workflow_g8` |
| Chaos matrix offline (redis down, LLM all-down, replay, DLQ backoff, webhook never-5xx, ato não-final) | `ae60ea69`, `8ba27979` | 6 testes |
| Métricas observability + 9 alertas + runbook | `3ddc3371` | `test_observability_e306` 21 testes |

## 6. Test evidence

- **FULL QA E3.11 (2026-07-25, pós-todas as mudanças — SUBSTITUI o baseline 92.07%):**
  - Suite: **6049 passed, 22 skipped** (712s) + 1 falha em pin G8 do CI → fixada e re-rodada verde (`test_cd_workflow_g8.py` 9 passed)
  - Coverage: **92.44%** (gate 90%) — 13516 statements, 1022 missed
  - ruff: **0** · mypy: **0** (210 source files)
  - Secret scanner gate: **exit 0** (baseline documentada, 6 fingerprints)
  - pip-audit: **No known vulnerabilities found**
  - Alembic heads: **1** (`0028`) · telegram1000 marker: **1 passed** (15.6s)
  - PII leaks: **0** (canary CNJ + gates LGPD) · new secrets: **0**

## 7. Known risks

1. **Audit chain legacy** (pré-0022) — remediação é decisão DPO (ADR-030 default no-rewrite). Verificador tem fallback marcado, fail-closed em link quebrado.
2. **Tracked findings do scanner** (n8n workflow JSONs, webhook secrets) — BLOCKED_SUI: confirmação/rotação do dono. Valores nunca impressos.
3. **WhatsApp session** — `connectionState != open` até QR (BLOCKED_SUI).
4. **pytest advisory** — dev-only documentado; não major-bump neste ciclo.

## 8. Rollback plan

| Componente | Comando/ação |
|-----------|--------------|
| Código (sem push) | `git revert <hash>` local; nada saiu da máquina |
| Migration 0028 (pós-deploy aprovado) | `alembic downgrade 0027` |
| Env DPO key | remover var → tier DPO some (fail-secure) |
| Trusted proxy | `app.add_middleware(TrustedProxyMiddleware)` removível em 1 commit; rate limit volta a comportamento anterior documentado |
| Alertas | desabilitar regra no Alertmanager (métricas são aditivas) |

## 9. Smoke checklist (pós-deploy autorizado)

1. `GET /health` → 200 `status=ok`
2. `GET /api/v1/health/radar` → todos componentes UP
3. `POST /api/v1/audit/verify` → `chain_ok=true` (após 0028)
4. Webhook Telegram com secret válido → 200; inválido → 401
5. `GET /metrics` → séries novas presentes (circuit, webhook_auth, whatsapp session)
6. Request direto com `X-Forwarded-For` falso → IP efetivo = peer (não o spoof)
7. DLQ: mensagem falha entra em retry 1m/5m/15m

## 10. Deploy order (quando autorizado)

1. Push autorizado → CI verde
2. Canary 1 réplica → smoke 1–6
3. `alembic upgrade head` (0028, após sign-off DPO)
4. Verify audit `chain_ok=true`
5. Scale restante → radar verde
6. WhatsApp QR (dono) → `connectionState=open` → inbound/outbound real

_Modified by Gustavo Almeida — orquestrador Etapa 3 (E3.12)._
