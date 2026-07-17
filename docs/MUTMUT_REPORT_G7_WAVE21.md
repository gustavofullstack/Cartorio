# Mutation Testing — G7.02.T1 status update (2026-07-16 Wave 21)

**Baseline:** `docs/MUTMUT_REPORT_G6.md` (Wave 1) — **73.0% killed** (target ≥75%)  
**Melhorias desde baseline (sem re-run full mutmut nesta wave):**

| Entrega | Efeito esperado em mutantes |
|---------|----------------------------|
| G6.A.T7 / G7.01.T3 `test_audit_mutation_killers_g6.py` | matar `_compute_hash` / `_compute_hmac` / canonical / verify edges |
| G6/G7 IP truncation + D5 tests | matar mutantes em `truncate_ip` / dual IP log |
| Rate-limit metrics + redlock peer tests | cobertura redlock/rate paths |

## Como re-rodar (staging/CI night)

```bash
cd backend
# setup.cfg [mutmut] já lista audit/pii/crypto/emolumento/lgpd_*/redlock
uv run mutmut run --max-children 2
uv run mutmut results
uv run mutmut html  # se disponível
# atualizar docs/MUTMUT_REPORT_G6.md com novo score
```

**CI:** `.github/workflows/mutation-nightly.yml` (se presente) — não bloquear PR diário.

## Meta G7.02.T1

- [ ] Re-run completo mutmut ≥75% killed em audit+pii
- [x] Killers unitários audit commitados no worktree G7
- [x] Este status report Wave 21

**Verdict:** 🟡 PARTIAL — full re-run ainda pendente (custo CPU alto); baseline + killers documentados.

**Modified by Gustavo Almeida — G7 Wave 21**
