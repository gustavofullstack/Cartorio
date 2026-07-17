# Lesson 196 — G7 Wave 24: Alembic + Backup + 502 + Coverage + Composite (2026-07-17)

Type: project + reference

## 4 slots (4 agents)

| Slot | Rein | Tasks | Entrega |
|------|------|-------|---------|
| A1 | cartorio-dev | G7.08.T1 + G7.21.T1 | Alembic head `0020` single + mypy 0/154 + gate script |
| A2 | cartorio-sre | G7.08.T2 + G7.13.T3 | Backup dry-run WORK + PLAYBOOK 502 vs NXDOMAIN |
| A3 | cartorio-dev | G7.01.T2+ | 18 tests → rate_limit/sentry/radar 100% |
| A4 | cartorio-brain/sre | G7.24.T3 + G7.23.T3 | `g7_composite_gate` exit 0/1/2 + progress append |

## Artefatos

- `docs/ALEMBIC_HEADS_REPORT_G7.md`
- `docs/MYPY_STRICT_GATE_G7.md`
- `docs/BACKUP_DRYRUN_REPORT_G7_WAVE24.md`
- `docs/PLAYBOOK_502_VS_NXDOMAIN_G7.md`
- `docs/G7_COMPOSITE_GATE_WAVE24.md`
- `docs/G7_PROGRESS_DASHBOARD.md` (Wave 24 DONE)
- `scripts/check_alembic_single_head.py`
- `scripts/g7_composite_gate.py`
- `scripts/g7_progress_append.py`
- `scripts/backup_dryrun.py` (schema-qualified CREATE TABLE fix)
- `backend/tests/test_g7_wave24_integration.py` (18 passed)
- Makefile: `g7-composite`, `g7-progress`

## Lições operacionais

1. **Alembic repo-side single head ≠ prod applied** — always HOLD `alembic current` no VPS.
2. **Backup dry-run local** prova pipeline de validação (gzip/SHA/SQLite), não restore prod.
3. **502 ≠ Traefik down** — ler access log `http-cartorio_X-0@file` (Lesson 176).
4. **Composite gate semantics**: 0 OK local+prod, 1 local fail, 2 prod HOLD (nunca 1 por rede).
5. **Coverage leverage**: 3–5 módulos médios com branch tests > tentar `router.py` 1200 LOC de uma vez.
6. **Probe live 2026-07-17**: api/agent/easypanel 200; whatsapp/chat **502**; chatwoot/n8n/supabase **NXDOMAIN**.

## Validação

```bash
cd backend && uv run pytest -q --no-cov tests/test_g7_wave24_integration.py  # 18 passed
python3 scripts/check_alembic_single_head.py  # OK 0020
python3 scripts/g7_composite_gate.py --import-only --skip-dns --skip-radar  # exit 0
```

## HOLD-GUSTAVO

DNS×3 A records · Evolution/Chatwoot DATABASE_URL · Telegram token · LobeChat key · OpenClaw scopes · redeploy radar/expanded

**Modified by Gustavo Almeida — G7 Wave 24**
