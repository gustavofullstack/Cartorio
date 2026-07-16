# Mutation Testing Report — G6 Wave 1 (2026-07-16)

**Tool**: mutmut 3.6.0
**Config**: `backend/setup.cfg [mutmut]` — 10 source paths (audit/pii/crypto/emolumento/lgpd_*/redlock)
**Date**: 2026-07-16 09:50 BRT
**Run by**: Pietra orquestrador (cartorio-dev, G6.A.T1)
**Status**: 🟡 **PARTIAL** — score 73.0% killed (target ≥75%)

---

## 📊 Resumo agregado

| Métrica | Valor |
|---|---|
| Total mutantes processados | **2095** |
| Killed (detectados pelos testes) | **1529** |
| Survived (não detectados) | **493** |
| No tests | 14 |
| Timeout | 59 |
| **Score geral** | **73.0% killed** |

## 📊 Por arquivo (top problemáticos)

| Arquivo | Killed | Survived | No tests | Timeout | Score |
|---|---|---|---|---|---|
| app.services.lgpd_export | 65 | 114 | 0 | 40 | **28.6%** ⚠️ |
| app.services.lgpd_direito_esquecimento | 30 | 100 | 0 | 9 | **20.5%** ⚠️ |
| app.services.lgpd_consent | 32 | 32 | 0 | 10 | 43.2% |
| app.services.lgpd_relatorio | 0 | 149 | 0 | 0 | 0.0% ⚠️ |
| app.services.audit | **0** | **42** | 0 | 0 | **0.0%** ⚠️ |
| app.services.pii | 18 | 25 | 0 | 0 | 41.9% |
| app.services.redlock | 14 | 12 | 0 | 0 | 53.8% |
| app.services.lgpd_anonimizacao | 78 | 7 | 0 | 0 | 91.8% |
| app.services.emolumento | 14 | 8 | 0 | 0 | 63.6% |
| app.services.crypto | 41 | 4 | 0 | 0 | 91.1% |

**Piores**: `audit.py` (0%), `lgpd_relatorio.py` (0%), `lgpd_direito_esquecimento.py` (20%), `lgpd_export.py` (29%)

**Melhores**: `crypto.py` (91%), `lgpd_anonimizacao.py` (92%), `pii.py` (42% mas melhor que audit), `redlock.py` (54%)

## 🎯 Conclusão vs meta G6.A.T1

**Meta**: ≥75% killed em `audit.py` + `pii.py`.
**Resultado parcial**:
- ❌ `audit.py`: **0%** (42 mutantes sobreviveram, ZERO killed)
- ❌ `pii.py`: **42%** (25 survived de 43 mutantes)

**Comparação com baseline 2026-07-02** (`mutants/mutation_status.json`):
- `audit.py`: 0/0 → 0/42 (REGRESSÃO, era "not run yet")
- `pii.py`: 113/5 → 18/25 (regressão leve)
- `crypto.py`: 41/5 → 41/4 (estável)
- `lgpd_consent.py`: 125/58 → 32/32 (REGRESSÃO forte, ou config mudou)
- `lgpd_anonimizacao.py`: 85/8 → 78/7 (estável)
- `emolumento.py`: 14/1 → 14/8 (regressão)

**Hipótese da regressão**: a config do `setup.cfg [mutmut]` mudou ou pytest_add_cli_args `--cov-fail-under=0` está fazendo mutmut rodar testes demais (full suite) mas em paralelo perdeu accuracy. Investigar.

## 🔴 Ação próxima wave (G6.A.T1.1)

1. **Investigar por que `audit.py` 42/42 sobreviveram** — pode ser:
   - Testes não estão sendo descobertos para mutantes do `audit.py` (paths_to_mutate errado?)
   - Mutations são todas "equivalentes" (não afetam comportamento observável)
   - Tests do audit usam fixtures que bypassam a lógica mutada
2. **Adicionar `assume(d5 >= d_inativo)` nos Hypothesis tests** (paralelo)
3. **Re-rodar mutmut 3.6 com `--max-children 1`** (serial, mais lento mas mais preciso)
4. **Reescrever testes específicos em `test_audit.py` para matar mutantes específicos** (boundary conditions)

## 📁 Artefatos

- `mutants/mutmut-cicd-stats.json` — stats agregados JSON
- `mutants/mutmut-stats.json` — mapping test → function (172KB)
- `mutants/.coverage` — coverage cache da run
- `mutants/.pytest_cache/` — pytest cache da run
- Esta report: `docs/MUTMUT_REPORT_G6.md`

---

**Modified by Gustavo Almeida + Pietra orquestrador — 2026-07-16 09:55 BRT**
