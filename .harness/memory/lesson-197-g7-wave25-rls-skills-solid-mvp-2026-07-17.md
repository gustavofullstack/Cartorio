# Lesson 197 — G7 Wave 25: RLS + Skills + SOLID + MVP cut (2026-07-17)

Type: project + reference

## 4 slots

| Slot | Tasks | Entrega |
|------|-------|---------|
| A1 | G7.08.T3 + T4 | RLS audit + connection pool report + `pool_config_inventory_g7.py` |
| A2 | G7.15.T2–T4 | Skills smoke 6/6 + SKILLS-MAP 12 + `skills_smoke.py` |
| A3 | G7.20.T1/T3 + G7.21.T3 | Dead code audit (−11 LOC) + Any hotspots + Mapped 100% |
| A4 | G7.22.T2 + G7.23.T4 + G7.13.T1 | CD EasyPanel + MVP cut-line + LE cert monitor |

## Achados críticos

1. **RLS migration 0004** vs `schema.sql` drift: dump tem policies `USING (true)` que anulam “own” — validar prod com `pg_policies`.
2. **DB_POOL_SIZE default código = 20**, não 25 (docs v22 desatualizados). Cap 30/worker × 4 = 120.
3. **Skills core 6/6 PASS**; alguns SKILL.md ainda têm **API keys literais** (follow-up secrets scrub, não T3).
4. **Mapped 100%** — zero `Column(` legado nos models.
5. **MVP cut-line canônico**: só consulta emolumento WA + read protocolo + HITL; sem emissão auto.
6. **CD EasyPanel**: auto-git nem sempre ON; `scripts/deploy.sh` EasyPanel API ainda TODO.

## Validação

```bash
python3 scripts/skills_smoke.py          # PASS 6/6
python3 scripts/pool_config_inventory_g7.py
python3 scripts/g7_orchestrator.py status
```

**Modified by Gustavo Almeida — G7 Wave 25**
