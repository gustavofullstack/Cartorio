# Lesson 229 — G8.12.T4: Dead Code Audit estático (Wave 45)

## Contexto

Gustavo Almeida pediu em Wave 45 (cartorio-dev) a execução de **G8.12.T4 —
"Validar ausência de código morto no diretório `/app` via análise estática"**.

> **P0 rule (HITL):** "NÃO deletar código automaticamente. Apenas REPORTAR
> achados para revisão manual. Decisão de remoção é humana (HITL)."

Output esperado: tooling consolidado + report JSON + top-N achados + follow-ups.
Remoção zero automatizada.

## Decisões técnicas

1. **Script na raiz** (`scripts/dead_code_audit.py`), não em `backend/scripts/`.
   Mesmo padrão de `scripts/stability_report.py` e `scripts/postman_export.py`:
   auto-detecta REPO_ROOT via `Path(__file__).parent.parent`, e roda via
   `subprocess` a partir de `BACKEND_DIR`. Stdlib + `uv run` para invocar
   linters — zero deps externas obrigatórias além das que o `uv` resolve.

2. **4 linters consolidados num só entry-point**:
   - `ruff --select F401,F841` (gate CI já passa: 0 findings).
   - `pyflakes app/` (broad unused import/variable scan).
   - `vulture --min-confidence 80` (unused functions/classes, unreachable code).
   - `coverage json --data-file=.coverage --omit=...` (zero/partial coverage).
   Cada um com timeout duro (60s pyflakes, 180s vulture, 60s coverage) e
   tratamento de `subprocess.TimeoutExpired`/`FileNotFoundError`.

3. **Cache 1h TTL por data** (`docs/DEAD_CODE_AUDIT_<YYYY-MM-DD>.json`).
   Se a run atual produz o mesmo path e o mtime < 3600s, retorna o payload
   cacheado. Bypass via `--no-cache`. Cache HIT é evidenciado em stdout com
   `[cache] report re-usado (age=Xs, ttl=3600s)`.

4. **Proteção de paths críticos**: `FALSE_POSITIVE_GLOBS = (
   'app/audit*', 'app/pii.py', 'app/audit_context.py')`. Mesmo se vulture
   marcar (p.ex. `unused function`), `select_top_candidates` ignora. Reforça
   o rule G8 P0: "mudança em audit/pii exige review `cartorio-lgpd`".

5. **vulture ≥80 confidence é o sweet spot**. Com `--min-confidence 60`,
   vulture emite 60+ findings, mas 80% são falsos positivos (FastAPI endpoints
   registrados via `app.include_router`, Pydantic `model_config = ConfigDict()`,
   etc. que ferramenta não detecta). Já com ≥80, sobram 8 achados reais
   (1 unreachable branch + 7 unused vars estilísticas/assinaturas).

6. **`coverage report --format=json` é desconhecido** em `coverage 7.14`.
   Forma correta: `coverage json -o arquivo.json` (sub-comando separado).
   Bug do `idempotency` na API antiga vs nova.

7. **DETECÇÃO de orphan_modules via coverage gaps**: arquivos com
   `summary_pct == 0.0` no JSON de coverage são módulos totalmente
   descobertos pelos testes. Cruzando com `grep` por imports do módulo,
   confirmei 2 candidatos reais:

   - `app/api/v1/lgpd_dsar.py` — router completo, schemas referenciados
     em testes (Pydantic strict), mas **nunca importado** em `main.py`
     nem em `app/api/v1/router.py`. Schema sibling `app/schemas/lgpd_dsar.py`
     **é** usado (test_pydantic_strict_g7/g8.py) para validar DSAR Pydantic
     strict. Decisão: decidir com cartorio-lgpd se arquivar ou registrar.
   - `app/services/materialized_views.py` — 14 LOC stub, **zero importers**.
     Candidato limpo a remoção.

8. **6 testes pytest** cobrindo: cold-start (`--no-cache`), JSON shape,
   idempotência (cache hit em 2a run), summary flags booleanos, orphan
   detection, `--no-cache` bypass. Rodam em <6s end-to-end porque o
   subprocess só invoca `python3 + script.py` (lê coverage existente
   ou cache).

## Achados baseline (2026-07-18)

| Ferramenta | Findings | Status |
|---|---|---|
| ruff F401/F841 | 0 | **CLEAN** (gate CI passa) |
| pyflakes | 0 | **CLEAN** |
| vulture ≥80 | 8 | CHECK (decisão humana) |
| coverage <100% | 86 arquivos | (informational) |
| zero-coverage | 2 orfãos | CHECK (LGPD clearance) |

Top-2 achados (HITL):
1. `app/api/v1/lgpd_dsar.py` (27 stmts, 0% cov, never imported)
2. `app/services/materialized_views.py` (14 stmts, 0% cov, never imported)

Top-1 unreachable:
- `app/api/v1/router.py:1937` `else: json_error = None` (try sempre retorna)

## Lições reutilizáveis

1. **Orphan modules = cobertura 0% + zero importers**. União dos dois sinais
   (coverage `summary_pct == 0.0` ∧ `grep -r "from app.X.<module>"` retorna
   vazio) é a melhor heurística para detectar código órfão sem false positives.

2. **vulture ≥80 vs ≥60**: 80% confidence remove os falsos positivos do
   FastAPI/Pydantic. Use ≥80 como default; ≥90 só se quiser relatório ultra-clean
   (e ignorar `__exit__` exc_val/exc_tb que vulture classifica como unused).

3. **HITL-by-design em auditorias**: o script explicitamente NUNCA remove.
   `--delete` flag foi ativamente descartada pra forçar revisão humana
   via PR separado. Decisão humana via `docs/DEAD_CODE_AUDIT_<date>.md`
   seção "Recomendação para próximas waves".

4. **Cache de saída estruturada**: 1h TTL em path com data (`<YYYY-MM-DD>`)
   elimina overhead em CI (cada run não precisa rerodar 4 linters), mas
   `--no-cache` permite forçar quando código mudou.

5. **vulture / pyflakes / ruff cobrem espectros complementares**:
   - ruff F401/F841: imports/vars (rápido, gate).
   - pyflakes: same + `undefined name` (semantic).
   - vulture: funções/classes (cross-module, requer AST walking).
   - coverage: behavioral (roda test suite).

   Os 4 juntos cobrem "dead" em 4 sentidos diferentes.

## Anti-patterns evitados

- ❌ Auto-deletar órfãos (HITL violation).
- ❌ Hard-coded "key literal" no script (passa pelo `check_no_literal_keys.py`).
- ❌ Toque em `app/audit*`, `app/pii.py`, `app/audit_context.py`
  (cross-rein P0 — cartorio-lgpd review).
- ❌ Rodar contra serviços externos (subprocess é local-only).

## Modified by

Gustavo Almeida + cartorio-dev · G8 Wave 45 / Squad 12 DRY & KISS cleanup · 2026-07-18
