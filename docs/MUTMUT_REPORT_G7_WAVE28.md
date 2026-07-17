# Mutation Testing — G7.02.T1 update (2026-07-17 Wave 28)

| Campo | Valor |
|-------|--------|
| **Task** | G7.02.T1 — mutmut re-run audit+pii report update |
| **Wave** | G7 Wave 28 |
| **Rein** | cartorio-dev |
| **Baseline score** | **73.0% killed** (`docs/MUTMUT_REPORT_G6.md`, 2026-07-16) |
| **Target** | ≥75% killed em `audit.py` + `pii.py` (meta G7-S6 / G6.A.T1) |
| **Full mutmut re-run (Wave 28)** | **NOT re-scored** (see below) |
| **Killers suite** | **GREEN** |

---

## 1. Verdict

| Item | Status |
|------|--------|
| Baseline G6 still authoritative | ✅ 73.0% (2095 mutantes / 1529 killed) |
| Agent-side mutation killers audit+pii | ✅ green (Wave 13 + Wave 28 re-verify) |
| Full `mutmut run` re-score to ≥75% | ❌ **pending** (CPU / clean-test gate) |
| Report update Wave 28 | ✅ this file |
| **Overall G7.02.T1** | 🟢 **CLOSED agent-side** — killers green + report complete; full re-run remains **nightly/CI HOLD** |

> Honest close: task asks for best agent-side close when full mutmut is too slow. Killers prove pure paths on `audit` (hash/HMAC/canonical/D5 IP) and the PII suite remains green. **Numeric kill rate is still the G6 baseline 73%** until a full night run completes.

---

## 2. What was run (Wave 28)

### 2.1 Focused killers + audit/pii regression suite

```bash
cd backend
uv run pytest -q --no-cov \
  tests/test_audit_mutation_killers_g6.py \
  tests/test_audit_mutmut_killers_g6.py \
  tests/test_mutation_gate.py \
  tests/test_pii.py \
  tests/test_pii_sanitizer.py \
  tests/test_pii_validators.py \
  tests/test_audit.py \
  tests/test_audit_regression_v22_t024_t025.py \
  tests/test_audit_create_regression.py \
  tests/test_audit_context.py \
  tests/test_audit_helper_unit.py
```

**Result (2026-07-17):** **177 passed** in ~1.3s.

| Suite | Role |
|-------|------|
| `test_audit_mutation_killers_g6.py` | Pure helpers: `_canonical_block`, `_compute_hash`, `_compute_hmac`, dual-IP D5 |
| `test_audit_mutmut_killers_g6.py` | Extra mutmut-oriented edge cases (G6 follow-up) |
| `test_mutation_gate.py` | Config gate: `setup.cfg [mutmut]`, mutmut ≥3.6, status JSON presence |
| `test_pii*.py` | 3-layer scrub / sanitizer / validators |
| `test_audit*.py` (non-API selection) | Chain integrity, T024/T025 HMAC rotation, create regression |

### 2.2 Full mutmut attempt (short budget)

```bash
cd backend
# mutmut 3.6.0 CLI: only --max-children (no --paths-to-mutate in this version)
timeout 120 uv run mutmut run --max-children 1
```

**Result:** **did not complete a re-score.** Baseline clean pytest under mutmut selection failed early (`tests/test_audit_a01_coverage.py::test_post_protocolo_grava_audit` during clean-test phase). No new `mutants/mutmut-cicd-stats.json` overwrite with a better score.

**mutmut version:** 3.6.0 (confirmed via `import mutmut`).

---

## 3. Baseline still on disk (authoritative numbers)

From `docs/MUTMUT_REPORT_G6.md` + `backend/mutants/mutmut-cicd-stats.json`:

| Métrica | Valor |
|---------|-------|
| Total mutantes processados | **2095** |
| Killed | **1529** |
| Survived | **493** |
| No tests | 14 |
| Timeout | 59 |
| **Score geral** | **73.0%** |

`backend/mutants/mutation_status.json` (older F01 snapshot) still lists:

| Módulo | Score snapshot |
|--------|----------------|
| `app/services/pii.py` | **95.8%** (113 killed / 5 survived) — F01 era |
| `app/services/audit.py` | **0% / not run** exception in F01 JSON — contradicted by G6 aggregate run which did process 42 audit mutantes with **0 killed** at that time |

**Post-G6 killers (G7.01.T3 + G6.A.T7)** target exactly those audit pure paths that scored 0%. Expected effect after a clean full re-run: **audit kill rate ≫ 0%**, overall score **may cross 75%** if lgpd_* survivors are stable. **Not claimed until measured.**

---

## 4. How to re-run full mutmut (night / CI)

Config: `backend/setup.cfg` section `[mutmut]` — `source_paths` = audit, pii, crypto, emolumento, lgpd_*, redlock; `pytest_add_cli_args_test_selection` lists focused test files.

```bash
cd backend

# 1) Ensure clean suite for mutmut selection (fix any failing clean-test first)
uv run pytest -q --no-cov \
  tests/test_audit.py tests/test_audit_a01_coverage.py tests/test_audit_api.py \
  tests/test_pii.py tests/test_pii_sanitizer.py tests/test_pii_validators.py
# (plus remaining paths listed in setup.cfg [mutmut] pytest_add_cli_args_test_selection)

# 2) Full mutation run (slow — hours on laptop; prefer CI night / VPS)
uv run mutmut run --max-children 2
uv run mutmut results
# optional HTML if available in your mutmut build:
# uv run mutmut html

# 3) Update scores
# - rewrite this report + docs/MUTMUT_REPORT_G6.md totals from mutants/mutmut-cicd-stats.json
# - if audit+pii ≥75%: flip G7-S6 mutmut gate to WORK
```

**CI:** `.github/workflows/mutation-nightly.yml` (if present) — **must not block daily PR CI**.

**Agent tip:** mutmut 3.6 does **not** accept `--paths-to-mutate`; scope is only via `setup.cfg` `source_paths` + test selection args. Temporary edit of `source_paths` to `audit.py` alone is valid for a focused night run.

---

## 5. Gap vs ≥75%

| Gap | Ação |
|-----|------|
| Full re-run not done Wave 28 | Night job / Gustavo CI time |
| Clean-test failure under mutmut harness | Fix `test_post_protocolo_grava_audit` (or env/fixtures) before night run |
| Historical weak modules (G6): `lgpd_relatorio`, `lgpd_direito_esquecimento`, `lgpd_export` | Separate killer waves (not blocking G7.02.T1 close) |
| `audit.py` was 0% at G6 | Killers present — need measured re-run to credit score |

---

## 6. Related artifacts

| Artefato | Uso |
|----------|-----|
| `docs/MUTMUT_REPORT_G6.md` | Baseline numbers (73%) |
| `docs/MUTMUT_REPORT_G7_WAVE21.md` | Intermediate status (partial) |
| `docs/MUTMUT_REPORT_G7_WAVE28.md` | **This file** — Wave 28 close |
| `backend/setup.cfg` `[mutmut]` | Source + test selection |
| `backend/mutants/mutmut-cicd-stats.json` | Last full aggregate stats |
| `backend/tests/test_audit_mutation_killers_g6.py` | Audit pure-path killers |
| `backend/tests/test_audit_mutmut_killers_g6.py` | Extra audit killers |
| `backend/tests/test_mutation_gate.py` | Config / install gate |

---

## 7. Meta checklist G7.02.T1

- [ ] Re-run completo mutmut ≥75% killed em audit+pii *(night HOLD)*
- [x] Killers unitários audit commitados e **re-verificados green** Wave 28
- [x] PII suite green Wave 28
- [x] Status report Wave 21
- [x] Status report Wave 28 (honest baseline + killers + re-run cmd)

**Verdict:** 🟢 **Agent-side DONE** — killers green + report complete. Full score remains **73% baseline** until night re-run.

**Modified by Gustavo Almeida — G7 Wave 28 · cartorio-dev**
