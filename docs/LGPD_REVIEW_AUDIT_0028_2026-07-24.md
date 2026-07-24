# LGPD Review Package — Audit chain fix (a84303bc + re-id 0028)

**Status:** `BLOCKED_REVIEW` — aguarda sign-off `cartorio-lgpd`  
**Data:** 2026-07-24  
**Superfície:** `audit*` (obrigatório Art. review)  
**Commit base:** `a84303bc` — `fix(audit): root cause chain break — trigger fn_auto_audit diverge do verificador Python`  
**Follow-up local:** re-id Alembic `0022` → `0028` (colisão com RLS 0022)

---

## 1. Problema (produção)

- Endpoint: `POST /api/v1/audit/verify` → `chain_ok=false`, `last_valid_position=667`
- **NÃO é tampering:** `prev_hash` linkage 100% contínuo nas ~1130 entradas
- Causa-raiz (2 defeitos na `fn_auto_audit` da migração 0020):
  1. Canonicalização `jsonb::text` (ordem len/bytewise + espaços) ≠ `json.dumps` Python compact+sort_keys
  2. Hash usava `clock_timestamp()` mas coluna gravava `NOW()` (microssegundos divergentes)
- ~158 entradas sistemáticas escritas pelo trigger desde 2026-07-09

## 2. Fix proposto (2 frentes, fail-closed)

| Frente | Artefato | Efeito |
|---|---|---|
| Verificador | `backend/app/services/audit.py` | Mirror `_compute_hash_sql_trigger` + fallback **somente** se `_is_trigger_written` e hash SQL bate exatamente |
| Trigger futuro | Alembic **0028** (`2026_07_24_0028-fix-fn-auto-audit-ts-consistency.py`) | `v_ts` deriva do mesmo `NOW()` gravado na coluna `timestamp` |
| Testes | `tests/test_audit_trigger_canonical_p0.py` | jsonb::text, canonical SQL, accept trigger, reject tamper, reject broken link, contrato estático migração |

### O que o fix **NÃO** faz

- **Não reescreve** `audit_log` histórico
- **Não re-cadeia** as ~158 entradas legacy
- **Não** afrouxa fail-closed para link quebrado ou entrada não-trigger adulterada

## 3. Decisão DPO pendente (legacy)

Opções (default recomendado em negrito):

1. **Anotar** entradas legacy não-recomputáveis (metadado/flag + relatório) e manter append-only — **DEFAULT**
2. Re-cadeiar com cerimônia DPO + dual-control + janela de manutenção (alto risco jurídico; só com ordem explícita)

**Proibido:** rewrite unilateral da cadeia.

## 4. Colisão Alembic corrigida (W0 2026-07-24)

Antes do re-id, existiam **duas** revisões `revision = "0022"` ambas com `down_revision = "0021"`:

- `0022_audit_log_rls_no_edit_no_delete.py` (RLS append-only) — legítima 0022
- `2026_07_24_0022-fix-fn-auto-audit-ts-consistency.py` — **colidia**

Correção:

- Arquivo renomeado → `2026_07_24_0028-fix-fn-auto-audit-ts-consistency.py`
- `revision = "0028"`, `down_revision = "0027"`
- Cadeia linear: `0021 → 0022(RLS) → 0023 → 0024 → 0025 → 0026 → 0027 → 0028`
- Head numérica 00xx: **0028 única**

## 5. Evidências de teste (local, 2026-07-24)

```
pytest tests/test_audit_trigger_canonical_p0.py + audit suite + webhook hmac
→ 190 passed (audit*.py + webhook hmac), 0 failed

pytest focados (dead_code + audit_trigger + telegram FSM/parsers/g9 + agent + pii out + keys)
→ 105 passed

ruff check (audit.py, cartorio_agent, metrics, cnj_export, migração 0028, testes)
→ All checks passed
```

## 6. Produção (smoke, sem secrets)

| Probe | HTTP | Resultado |
|---|---|---|
| `/api/v1/health/live` | 200 | alive v0.6.0 |
| `/api/v1/health/ready` | 200 | db+redis online |
| `/api/v1/health/radar` | 200 | green; evolution=online (**≠** WA session) |
| `/api/v1/telegram/health` | 200 | webhook_configured=true |
| `POST /api/v1/audit/verify` | 401 | auth gate OK (X-API-Key ausente) |

**UNVERIFIED em prod pós-fix:** `verify_chain` com API key após aplicar migração 0028 — requer deploy + secret (SRE) e sign-off LGPD.

## 7. Checklist sign-off `cartorio-lgpd`

- [ ] Aceitar fallback dual-format apenas para trigger-written
- [ ] Aceitar migração 0028 (CREATE OR REPLACE fn_auto_audit) para entradas futuras
- [ ] Decidir legacy: anotar (default) vs re-cadeiar (cerimônia)
- [ ] Confirmar que nenhum path reescreve `audit_log`
- [ ] Após deploy: `POST /api/v1/audit/verify` → `chain_ok` documentado (sem PII no relatório)
- [ ] Entrada no audit log do próprio sign-off (ator DPO/lgpd)

## 8. Rollback

- Código Python: `git revert` do commit de audit (volta verify estrito Python-only)
- SQL: `downgrade()` da 0028 restaura fn da 0020 — **não usar em prod sem decisão DPO**
- Dados: nenhuma mutação histórica; rollback não toca linhas antigas

## 9. Owners

| Papel | Ação |
|---|---|
| cartorio-dev | Implementação + testes (feito em a84303bc + re-id 0028) |
| cartorio-lgpd | **Sign-off obrigatório** (este pacote) |
| DPO | Decisão legacy 158 entradas |
| cartorio-sre | Aplicar 0028 em prod **após** sign-off; smoke verify_chain |

---

Modified by Gustavo Almeida — Wave W1_P0_GOVERNANCE 2026-07-24
