# Lesson 221 — G8.11.T4 Architecture Coupling Tests (Wave 43 / cartorio-dev 2026-07-17)

## Contexto

Task G8.11.T4 do SUPER_PLANO_G8_100_TASKS pediu uma suite de testes
arquiteturais que falhe se alguem quebrar o desacoplamento Clean
Architecture esperado entre as camadas `api / services / models / core
/ schemas`. Como cartorio-dev, a entrega tinha que seguir o workflow
obrigatorio (`analisar -> testar -> corrigir -> melhorar -> otimizar
-> documentar -> comentar -> salvar na memoria`) sem tocar PII / audit
(regras P0 do AGENTS.md / CLAUDE.md).

## Decisao

**AST estatico, sem pylint nem import-linter.** Justificativa:

- pytest-only (sem dependencia externa alem do stdlib `ast`).
- Suite roda em ~0.5s (cached `lru_cache` em `_parse_file`).
- Diff legivel em CI: cada violacao imprime `filepath: imports 'app.X'`.
- Honesty Gate compativel com o policy atual: testes estrictos apenas
  para regras que o codebase ja respeita (e que falhariam se alguem
  regredisse no futuro).

Tambem escolhi registrar o marker `pytest.mark.coupling` em
`pyproject.toml` para permitir `pytest -m coupling` em CI dedicado de
guardioes arquiteturais.

## Achados (baseline Wave 43, hoje)

Auditoria via grep antes de escrever o teste:

| Regra | Estado hoje | Como o teste trata |
|-------|-------------|--------------------|
| `app.services.*` importa `app.api.*` | **0 violacoes** | enforce strict |
| `app.models.*` importa `app.api.*`     | **0 violacoes** | enforce strict |
| `app.core.*` importa `app.api/services` | **0 violacoes** | enforce strict |
| `app.schemas/*` importa `sqlalchemy`   | **0 violacoes** | enforce strict |
| `require_*` gates espalhados fora de deps.py | **0 violacoes** | enforce strict |
| `app.models/*` importa business services | **1 violacao** (`models/agendamento.py -> services.pii.hash_pii`) | whitelist explicita para `app.services.pii` |
| `app.services/*` chama business services | 32 violacoes (composition legitima) | fora do escopo do R5; testes futuros podem adicionar regra opcional |
| `app.services/*` importa `fastapi` / `starlette` | 8 violacoes (legado antes de HITL/PII framework split) | fora do escopo; tocaria `audit_context.py`, `rate_limit.py`, etc |
| `app.api/*` importa `app.services.*` direto | 32 matches via 14 router files | fora do escopo (deps.py + composition) |

**imports_violations_found**: 8 (acumulado das 8 regras strict enforced, nao-violacoes hoje) + 1 violacao whitelist (models.agendamento -> services.pii) = **0 violations enforced failing**.

## Antes / depois

Antes:

- Sem suite de guardioes arquiteturais.
- Regressao de camada nao detectada ate build break (runtime ImportError).
- Multiplos PRs podem inverter dependencia sem levantar alerta.

Depois:

- `backend/tests/test_architecture_coupling.py` (542 linhas, 10 testes, 0.5s).
- Cada regra documentada com R-codigo + comentario + allowed-exceptions
  no topo do arquivo (Clean Architecture / DRY / SOLID).
- Constantes `LAYER_DIRS`, `FORBIDDEN_UPWARD_IMPORTS`,
  `BUSINESS_SERVICE_MODULES`, `PII_PRIMITIVE_ALLOWLIST` em um unico
  ponto de evolucao.
- Helpers `_collect_imports`, `_iter_python_files`, `_violations`,
  `_format_violations` reusaveis via `lru_cache(maxsize=4096)`.
- Fixture `scope="module"` para evitar re-listar diretorios por teste.
- Marker `coupling` registrado em `pyproject.toml`.

## Cobertura das 10 regras

| R# | Teste | Camada guardada | Hoje |
|----|-------|-----------------|------|
| R1 | `test_services_layer_must_not_import_app_api` | services x api | 0 viol. |
| R2 | `test_core_layer_must_not_import_high_layers` | core x api/services | 0 viol. |
| R3 | `test_schemas_layer_must_not_instantiate_db_sessions` | schemas x sqlalchemy | 0 viol. |
| R4 | `test_dependencies_module_concentrates_di_providers` | api/deps.py como DI bridge | 0 viol. |
| R5 | `test_models_must_not_reach_into_business_services` | models x services (whitelist pii) | 0 viol. enforced |
| R6 | `test_models_layer_dependency_graph_is_dag` | models como leaf do DAG | 0 viol. |
| R7 | `test_routers_use_depends_for_di` | routers usam `Depends()` | positivo |
| R8 | `test_pydantic_schemas_use_from_attributes_for_orm_mapping` | schemas ORM-independent | positivo |
| R9 | `test_layer_packages_have_init_files` | packaging | sanity |
| R10 | `test_layer_file_counts_within_bounds` | code smell smeller | sanity |

## Honesty Gate

```text
pytest tests/test_architecture_coupling.py --no-cov -v
  -> 10 passed in 0.51s
ruff check tests/test_architecture_coupling.py
  -> All checks passed!
ruff format --check tests/test_architecture_coupling.py
  -> 1 file already formatted
mypy tests/test_architecture_coupling.py
  -> Success: no issues found in 1 source file
```

## Pendencias conhecidas (futuras waves)

- Services importando `fastapi`/`starlette` (8 arquivos) — sairiam com
  um refactor `framework-agnostic` em `audit_context`, `rate_limit`,
  `agendamento`, `lgpd.bot_direito_esquecimento`,
  `websocket_manager`. Provavelmente wave cartorio-dev + cartorio-lgpd
  (afeta `audit/` indiretamente).
- `app.schemas.agendamento.py` re-exporta enums de `app.models` — fica
  OK pelo pattern `ConfigDict(from_attributes=True)` mas quer registrar
  ADR-019 explicando porque eh OK.
- Composition de services (32 violations em R5-extended) deve virar uma
  ferramenta visual (gerada de AST) para code review futuro — nao eh
  regra strict pois ciclios de composition sao detectados em runtime.

## Modified by Gustavo Almeida + cartorio-dev agent (Wave 43 2026-07-17)
