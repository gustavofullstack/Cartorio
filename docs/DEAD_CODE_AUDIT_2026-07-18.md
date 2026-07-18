# Dead Code Audit — 2026-07-18 (G8.12.T4)

> **Task:** G8.12.T4 — "Validar ausência de código morto no diretório `/app` via análise estática."
> **Rein:** cartorio-dev · **Wave:** 45 (Squad 12 — DRY & KISS cleanup)
> **Policy:** **NUNCA** remove código automaticamente. Apenas **reporta** para revisão humana (HITL).

---

## 1. Sumário Executivo

| Ferramenta | Findings | Status |
|---|---|---|
| **ruff** (F401 unused imports + F841 unused vars) | 0 | ✅ **CLEAN** |
| **pyflakes** (`app/`) | 0 | ✅ **CLEAN** |
| **vulture** (≥80% confidence) | 8 | ⚠️ CHECK (decisão humana) |
| **coverage gaps** (<100%) | 86 arquivos | (top-2 são candidatos a remoção) |
| **zero-coverage files** (orfãos) | **2** | ⚠️ CHECK |

**Veredito:** Backend está **LIMPO** em unused imports/variables (gate CI já passaria). Restaram **2 arquivos órfãos** (zero test coverage, não registrados) e 8 vulture findings de variáveis de baixa confiança (em sua maioria assinaturas estilísticas ou branches inalcançáveis).

---

## 2. Metodologia

```text
ruff F401/F841 ──┐
pyflakes  ───────┼──> scripts/dead_code_audit.py → docs/DEAD_CODE_AUDIT_<date>.json
vulture ≥80 ─────┤
coverage ────────┘ (lê .coverage existente; roda pytest só se faltar)
```

Cache: 1h TTL · Timeout por linter: 60-180s · Output: JSON + console summary.

---

## 3. Top-10 candidatos HITL (atual)

| # | Kind | Path | LOC/Stmts | Severidade | Observação |
|---|------|------|-----------|------------|------------|
| 1 | `orphan_module` | `app/api/v1/lgpd_dsar.py` | 27 stmts / 0% cov | 🔴 ALTA | **Não registrado em `main.py`** (cf. outros routers `lgpd_*`). Schema `lgpd_dsar.py` (sibling) é usado em testes pydantic strict. |
| 2 | `orphan_module` | `app/services/materialized_views.py` | 14 stmts / 0% cov | 🔴 ALTA | **Zero importers.** Provável stub descartável. Candidato limpo a remoção. |
| 3 | `unreachable` | `app/api/v1/router.py:1937` | 1 branch | 🟡 MÉDIA | `else` block em `try/except` cujo `try` sempre dá `return`. Branch morto. |
| 4 | `unused_variable` | `app/api/v1/brain.py:119` | `from_date` | 🟢 BAIXA | Provavelmente parâmetro ignorado (talvez placeholder para paginação futura). |
| 5 | `unused_variable` | `app/api/v1/telegram.py:647` | `reply_markup` | 🟢 BAIXA | Variável atribuída mas nunca usada (likely bot_inline button). |
| 6-8 | `unused_variable` | `app/services/bot_metrics.py:145` × 2 + `app/services/lgpd/{opposition,portability}.py` | `exc_tb`, `exc_val`, `db_session` | 🟢 BAIXA | **Estilístico.** `__exit__` aceita `exc_val`/`exc_tb` por convenção (mantido intencionalmente). `db_session` placeholder. |

> ⚠️ Vulture lista 60+ funções quando usado com `--min-confidence 60`, mas a maioria são **falsos positivos** (FastAPI endpoints registrados via `app.include_router`, Pydantic `model_config`, etc.) que ferramenta não detecta. **Apenas ≥80% é confiável.**

---

## 4. Decisão (HITL — Gustavo Almeida)

### Não removemos automaticamente.

A análise estática detectou os candidatos acima, mas o S8.12.T4 explicitamente exige revisão humana antes de qualquer remoção porque:

1. **Risco regulatório:** `app/audit*` e `app/pii.py` são P0 (G8 — cartorio-lgpd review obrigatório).
2. **`audit*` e `pii.py` protegidos** pela lista `FALSE_POSITIVE_GLOBS` no script. Mesmo que vulture marque, eles ficam intactos.
3. **FastAPI endpoints** parecem "unused" para vulture mas são registrados dinamicamente em `main.py`. Remoção automática quebraria rotas em prod.
4. **`exceptions signature` (`__exit__` exc_val/exc_tb)** é convenção Python — remoção quebraria protocolo.

### Recomendação para próximas waves

| Candidato | Ação sugerida | Onde |
|-----------|---------------|------|
| `app/services/materialized_views.py` | 🟢 **Remover** (órfão confirmado, 14 LOC, zero teste). Risk: zero. | PR separado, 1 commit, refactor scope only |
| `app/api/v1/lgpd_dsar.py` (router) | 🟡 **Investigar com cartorio-lgpd**. Schema `app/schemas/lgpd_dsar.py` (sibling) ainda é usado em 2 testes (Pydantic strict G7/G8). Possível: (a) arquivar em `app/api/_archive/` ou (b) implementar registro no `main.py` se LGPD art. 18 §5o for roadmap. | Issue aberta, decisão humana |
| `app/api/v1/router.py:1937` `else` block | 🟡 **Remover** (dead branch, sem side-effect). Risk: zero. | PR de cleanup |
| `bot_metrics.py:145` exc_val/exc_tb | 🔴 **MANTER** (assinatura Python). | Não fazer |
| `brain.py:119` from_date | 🟡 Review com squad BRAIN para decidir se param deve virar query filter (`?from_date=...`). | issue |

---

## 5. Como rodar

```bash
# Local (default cache 1h):
python3 scripts/dead_code_audit.py

# Forçar re-run (ignora cache):
python3 scripts/dead_code_audit.py --no-cache

# Vulture mais estrito (90% confidence) para reduzir falsos positivos:
python3 scripts/dead_code_audit.py --vulture-min 90

# Via Makefile (raiz):
make dead-code-audit

# Saída:
#   docs/DEAD_CODE_AUDIT_<YYYY-MM-DD>.json   ← raw payload
#   stdout                                    ← console summary
```

---

## 6. Follow-ups (backlog)

- [ ] **F-1**: PR remove `app/services/materialized_views.py` (refactor, sem mudança de comportamento).
- [ ] **F-2**: Issue abrir com `cartorio-lgpd` — destino de `app/api/v1/lgpd_dsar.py` (registrar ou arquivar).
- [ ] **F-3**: PR cleanup `app/api/v1/router.py:1937` — remover dead `else` branch.
- [ ] **F-4**: Auditar `bot_metrics.exc_val/exc_tb` — marcar com `# noqa` se futuras lints reclamarem.
- [ ] **F-5**: Considerar rodar `dead-code-audit` em **CI** (gating opcional, não bloqueante) semanalmente.

---

## 7. Arquivos relacionados

- `scripts/dead_code_audit.py` — gerador do report (1 entry-point)
- `tests/test_dead_code_audit_g8.py` — 6 testes: cold-start, JSON shape, idempotency, summary flags, orphan detection, --no-cache bypass
- `docs/DEAD_CODE_AUDIT_<date>.json` — output gerado
- `Makefile` (raiz) — target `dead-code-audit`
- `.harness/memory/lesson-229-g8-12-t4-dead-code-audit-2026-07-18.md` — lições aprendidas

---

**Modified by Gustavo Almeida — cartorio-dev — 2026-07-18** (G8 Wave 45 / Squad 12 DRY & KISS)
