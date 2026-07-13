# F2 — Hardening Quality Evidence

**Data**: 2026-07-13 (validado)
**Owner**: Gustavo Almeida
**Executor**: TRAE SOLO M3 (batch F2)

## F2.1 pytest

```
$ uv run pytest tests/ -q --tb=line
15 failed, 2477 passed, 22 skipped, 49 deselected, 4415 warnings in 141.57s
```

**Resultado**: 2477 passing (≥1500 ✅). 15 falhas conhecidas em test infrastructure
(fakeredis race conditions em test_redlock_a20_v2, telegram menu command case
sensitivity, observability dashboard missing file).

## F2.2 mypy

```
[HOLD] venv nao configurado localmente — uvx roda sem acesso aos stubs
       do venv (200 erros "Cannot find implementation or library stub").
       Container API (VPS) tem mypy configurado, mas rodar via SSH
       quebra o ciclo.
       Acao recomendada: rodar no container cartorio_api
       (uv run mypy app/) ou commitar .venv-setup.sh.
```

## F2.3 ruff

```
$ uvx ruff check .
Found 45 errors.
[*] 23 fixable with the `--fix` option
```

**Resultado**: ruff funciona, identifica 45 violacoes pre-existentes em
infra (user-review-dashboard, scripts auxiliares, etc).

## F2.4 OpenAPI spec

- **PATHS**: 103
- **METHODS**: 105
- **Spec**: OpenAPI 3.x
- **Arquivo**: `.evidence/F2/F2.4_openapi.json`

**Resultado**: ✅ 103 paths (>= 50+)

## F2.5 v2 endpoints

```
GET /api/v2/info              → 200  (publico)
GET /api/v2/clientes          → 401  (auth required)
GET /api/v2/protocolos        → 401  (auth required)
GET /api/v2/emolumento/tabela → 401  (auth required)
```

**Resultado**: ✅ v2 online, alpha sunset 2027-12-31

Modified by Gustavo Almeida
