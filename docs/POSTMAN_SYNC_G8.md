# Postman Sync G8 — OpenAPI → Postman Collection v2.1

> G8.17.T1 — Script Python que regenera e sincroniza a Postman Collection a partir do Swagger/OpenAPI do backend.

## TL;DR

```bash
# 1. Regenerar collection (no-network, do codigo local)
make postman-sync

# 2. Testar
make postman-sync-test

# 3. Importar no Postman
# File > Import > Upload Files > infra/postman/cartorio-api.postman_collection.json
```

A collection gerada vive em **`infra/postman/cartorio-api.postman_collection.json`** (29 folders, 143 requests, ~218 KB).

## Por que este script?

| Antes (G7.17.T1) | Agora (G8.17.T1) |
|---|---|
| `scripts/postman_export.py` (export plano) | `scripts/postman_sync.py` (sync, folders, LGPD-safe) |
| Lista flat de requests | **29 folders por tag** (auth, lgpd, telegram, audit, brain, ...) |
| Auth `X-API-Key` + `cartorio_api_key` var | Auth `bearer` + `{{bearer_token}}` + `cartorio_api_key` var (LGPD) |
| Sem cache de fetch | **Cache local** em `.cache/postman-sync/` (TTL 5min) |
| Sem compressao | **gzip automatico** se output > 1MB |
| Sem safeguard LGPD | **`_assert_lgpd_safe()`** falha CI se token literal vazar |

## Uso

### 1. Gerar do codigo local (CI/dev — sem network)

```bash
make postman-sync
```

Equivalente a:
```bash
cd backend && uv run python ../scripts/postman_sync.py --from-app \
  --output ../infra/postman/cartorio-api.postman_collection.json \
  --base-url https://api.2notasudi.com.br
```

`--from-app` importa `app.main:app` e chama `app.openapi()` — nao precisa de servidor rodando.

### 2. Gerar de servidor live (debug)

```bash
python3 scripts/postman_sync.py --openapi-url http://localhost:8000/openapi.json \
  --output infra/postman/cartorio-api.postman_collection.json
```

Requer API rodando em `localhost:8000` (ou passar URL custom).

### 3. Offline (cached openapi.json)

```bash
make postman-sync-offline
```

Le de `backend/docs/openapi.json` (snapshot cached). Util para CI sem internet.

### 4. CLI flags

| Flag | Default | Descricao |
|---|---|---|
| `--openapi-url URL` | `http://localhost:8000/openapi.json` | URL do `/openapi.json` |
| `--from-app` | — | Carrega de `app.main` (no-network) |
| `--bypass-network` | — | Le arquivo cached (offline) |
| `--cached-openapi PATH` | `backend/docs/openapi.json` | Path do OpenAPI cached |
| `--output PATH` | `infra/postman/cartorio-api.postman_collection.json` | Output path |
| `--base-url URL` | `https://api.2notasudi.com.br` | Origin only (sem `/api/v1`) |
| `--no-cache` | — | Desabilita cache de fetch |
| `--no-compress` | — | Nao comprimir >1MB |
| `--quiet` | — | Suprime output nao-essencial |

## Estrutura da collection gerada

```json
{
  "info": {
    "name": "Cartorio API (sync)",
    "schema": "https://schema.getpostman.com/json/collection/v2.1.0/collection.json",
    "version": "0.6.0"
  },
  "auth": {
    "type": "bearer",
    "bearer": [{"key": "token", "value": "{{bearer_token}}"}]
  },
  "variable": [
    {"key": "base_url", "value": "https://api.2notasudi.com.br"},
    {"key": "bearer_token", "value": "", "type": "secret"},
    {"key": "cartorio_api_key", "value": "", "type": "secret"}
  ],
  "item": [
    {"name": "health", "description": "10 endpoints", "item": [/* requests */]},
    {"name": "cliente", "description": "4 endpoints", "item": [/* requests */]},
    ...
  ]
}
```

### Requests (v2.1)

Cada request segue o padrao:

```json
{
  "name": "GET /cliente/{cpf}",
  "request": {
    "method": "GET",
    "header": [
      {"key": "Accept", "value": "application/json"},
      {"key": "X-API-Key", "value": "{{cartorio_api_key}}"}
    ],
    "url": {
      "raw": "https://api.2notasudi.com.br/cliente/:cpf",
      "protocol": "https",
      "host": ["api", "2notasudi", "com", "br"],
      "path": ["cliente", ":cpf"],
      "variable": [{"key": "cpf", "value": "", "type": "string"}]
    },
    "description": "Buscar cliente por CPF\n\noperationId: cliente_get_by_cpf"
  },
  "response": []
}
```

POST/PUT/PATCH com `requestBody` sao hidratados com exemplo do schema OpenAPI.

## LGPD — Garantias

1. **`Authorization` sempre via `{{bearer_token}}` variable** — nunca persistido em valor literal.
2. **`bearer_token` variable com `type: "secret"`** — Postman mascara na UI.
3. **`X-API-Key` via `{{cartorio_api_key}}`** — preenchido pelo environment local.
4. **`_assert_lgpd_safe()`** — fail-fast se algum valor literal vazar para o JSON.
5. **`scripts/check_no_literal_keys.py`** — gate adicional no CI bloqueia `lin_api_*`, `sk-*`, `rnd_*`, etc.

### Como configurar o token local (DEV)

```bash
# 1. Importar environment (Postman UI)
postman/Cartorio_Env.production.postman_environment.json

# 2. Editar variaveis (olhinho ao lado do dropdown > Edit)
bearer_token = eyJhbGciOiJIUzI1NiI... (JWT real, NAO commitar)
cartorio_api_key = (32 bytes hex de `openssl rand -hex 32`)

# 3. Selecionar environment "Cartorio Env - Production"
```

## CI integration

```yaml
# .github/workflows/ci.yml (sugestao)
- name: Sync Postman collection
  run: make postman-sync
- name: Test postman_sync
  run: make postman-sync-test
- name: Verify JSON
  run: python3 -c "import json; json.load(open('infra/postman/cartorio-api.postman_collection.json'))"
```

Honesty gates:
- `make postman-sync` → exit 0, gera JSON valido
- `make postman-sync-test` → 23 tests PASS
- `cd backend && uv run ruff check ../scripts/postman_sync.py tests/test_postman_sync_g8.py` → 0 errors
- LGPD check embutido no script → exit 3 se token literal for detectado

## Estatisticas (snapshot 2026-07-18)

| Metrica | Valor |
|---|---|
| Paths OpenAPI | 141 |
| Folders (tags) | 29 |
| Requests | 143 |
| GET | 82 |
| POST | 58 |
| DELETE | 2 |
| PATCH | 1 |
| Variables | 3 (base_url, bearer_token, cartorio_api_key) |
| Output size | ~218 KB |
| Compressed (.gz) | N/A (< 1MB threshold) |

## Tests (23)

Localizados em `backend/tests/test_postman_sync_g8.py`:

- **TestConversion** (7) — minimal OpenAPI, group by tag, method mapping, path params, request body, query params, total count
- **TestLGPDAuth** (5) — no literal bearer, bearer_token is variable, assert clean, raise on literal token, raise on header token, ignores descriptions
- **TestOfflineAndCache** (3) — bypass-network file read, missing file raises, load from app
- **TestWriteAndCompress** (3) — write creates file, auto-compresses large, LGPD fail raises
- **TestStats** (1) — folder/requests/methods counts
- **TestPathConversion** (2) — params, no params

## Modified by Gustavo Almeida — G8.17.T1 (Wave 47)