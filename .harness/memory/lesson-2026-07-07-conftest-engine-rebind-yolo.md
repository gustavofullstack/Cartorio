---
name: conftest-engine-rebind-yolo-2026-07-07
description: Fix para "from app.db import engine" snapshot no import time — autouse re-bind via sys.modules
type: project
---

# conftest autouse _rebind_engine_pattern (2026-07-07)

## Contexto
Tests que fazem `from app.db import engine` no top-level do modulo snapshotam
a engine no import time. Quando o conftest autouse cria engine SQLite por test
(setup isolated), o `app.db.engine` global eh reatribuido mas os modulos ja
importados continuam com a engine antiga em `mod.engine`.

## Sintoma
- test v2_clientes faz INSERT via session_scope (visivel)
- endpoint client.get chama Depends(get_db) que usa engine diferente
- result: 0 edges retornados mesmo com 5 clientes inseridos
- ERRO: `OperationalError: no such table: audit_log` durante lifespan/audit

## Solucao
Adicionar re-bind em TODOS modulos `app.*` no conftest autouse:

```python
rebound: list[tuple[object, str, object]] = []
for mod_name, mod in list(sys.modules.items()):
    if mod is None or not mod_name.startswith("app"):
        continue
    if not hasattr(mod, "__dict__"):
        continue
    for attr_name, new_value in (
        ("engine", eng),
        ("session_scope", patched_scope),
        ("get_db", patched_get_db),
        ("SessionLocal", NewSL),
    ):
        current = mod.__dict__.get(attr_name)
        if current is None or current is new_value:
            continue
        try:
            setattr(mod, attr_name, new_value)
            rebound.append((mod, attr_name, current))
        except (AttributeError, TypeError):
            pass

try:
    yield
finally:
    appdb.session_scope = original_scope
    appdb.get_db = original_get_db
    appdb.SessionLocal = original_sessionlocal
    appdb.engine = original_engine
    for mod, attr, old in rebound:
        try: setattr(mod, attr, old)
        except Exception: pass
```

## Bonus 1: JWT_SECRET autouse
Tests como `test_auth_jwt::test_settings_jwt_secret_min_length_32_validated`
mutam env var + chamam `get_settings.cache_clear()` deixando singleton com
secret curto. Autouse que resset pra "a"*64 antes de CADA test:

```python
@pytest.fixture(autouse=True)
def _reset_jwt_secret(monkeypatch):
    monkeypatch.setenv("JWT_SECRET", "a" * 64)
    from app.config import get_settings, settings
    get_settings.cache_clear()
    settings.jwt_secret = "a" * 64
    yield
```

## Bonus 2: LGPD A19 — usar `deleted_at` (nao motivo_encerramento)
test_v2_clientes usava `motivo_encerramento` pra excluir, mas endpoint em
`/api/v2/clientes` filtra por `deleted_at IS NULL`. Padrao correto:

```python
cliente.deleted_at = datetime.now(timezone.utc)  # soft-delete
# Query: ?include_deleted=true (EXIGE JWT dpo=True)
```

## Bonus 3: JWT ISSUER padrao
`settings.jwt_issuer` default = `"cartorio-api"` (NAO `"cartorio-test"`).
JWT sem `iss` claim ou iss errado = 401 Token invalido.

## Resultado
- 1211 -> 2042 tests passing (+831)
- 0 ruff, 0 mypy, 86.19% coverage (gate 90% via F5 follow-up)
- 3 commits pushed (28098d3 + 174c0bc + ...)

## Modified by Gustavo Almeida + Antigravity (YOLO loop)
