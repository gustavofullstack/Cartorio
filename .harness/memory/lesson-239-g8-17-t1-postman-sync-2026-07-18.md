# Lesson 239 — G8.17.T1 Postman OpenAPI Sync (2026-07-18)

## Contexto

Wave 47 task G8.17.T1: regenerar Postman Collection v2.1 a partir do OpenAPI.
Existia `scripts/postman_export.py` (G7.17.T1) — flat list, sem folders, sem
LGPD-safe guard, sem cache. Task era evoluir para sync version.

## O que foi entregue

1. `scripts/postman_sync.py` (430 LOC) — conversor melhorado
2. `backend/tests/test_postman_sync_g8.py` (270 LOC) — 23 tests
3. `backend/tests/fixtures/minimal_openapi.json` — fixture OpenAPI 3.0.3
4. `infra/postman/cartorio-api.postman_collection.json` — gerado (218 KB, 29 folders, 143 requests)
5. `docs/POSTMAN_SYNC_G8.md` — documentação 1 pagina
6. Makefile: `postman-sync`, `postman-sync-offline`, `postman-sync-test`

## Decisoes criticas

### 1. Folder grouping por tag (vs flat list)

G7.17.T1 exportava items flat no root. Postman UI fica inutil com 143 items
sem agrupamento. G8 agrupa por `op.tags[0]` em folders (29 tags detectadas
no OpenAPI real). Side-benefit: discoverability + Newman `--folder LGPD` flag.

### 2. LGPD guard com escopo cirurgico

Implementacao inicial: regex `(?:Bearer|Token)\s+\w{8,}` no blob inteiro.
**Falhou em CI**: descricoes PT-BR dos endpoints tem "refresh token JWT",
"token rotation", etc. Solucao: walk cirurgico em campos sensiveis:
- `auth.bearer[].value`
- `auth.apikey[].value`
- `variable[].value`
- `request.header[].value` (somente keys authorization/*token*)

Descricoes/`name`/`description` nao sao auditadas (false positives).

### 3. `_BEARER_LITERAL_RE` ignora placeholders

`_PLACEHOLDER_RE.sub("", value)` antes do match remove `{{bearer_token}}` etc
para nao matchar valor placeholder.

### 4. Cache de OpenAPI fetch

`.cache/postman-sync/<sha256(url)>.json` com TTL 300s. CIs rodando em loop
(fanout) nao fazem refetch. Override via `POSTMAN_SYNC_CACHE` env.

### 5. Compressao gzip transparente

Output > 1MB → gera `.json.gz` adicional (CI artifact menor). Threshold em
`COMPRESS_THRESHOLD_BYTES`. Para 143 requests da API real (~218 KB), nao
dispara.

### 6. Co-existencia com G7.17.T1

`scripts/postman_export.py` (G7) NAO foi removido — preserva backward
compat para scripts externos que consomem `docs/postman_collection.generated.json`.
Novo `scripts/postman_sync.py` (G8) gera `infra/postman/cartorio-api.postman_collection.json`
no novo formato (folders + bearer auth).

## Test coverage (23 tests, 100% pass)

| Suite | Tests | Cobre |
|---|---|---|
| TestConversion | 7 | Conversion base, group by tag, method map, path params, body, query, count |
| TestLGPDAuth | 5 | Sem literal bearer, bearer_token placeholder, clean pass, raise on literal, raise on header, **ignores descriptions** |
| TestOfflineAndCache | 3 | bypass-network file read, missing file raises, load from app |
| TestWriteAndCompress | 3 | write creates file, auto-compress large, LGPD fail raises |
| TestStats | 1 | folder/requests/methods counts |
| TestPathConversion | 2 | path com/sem params |

## Pitfalls aprendidos

1. **f-string sem placeholder** → ruff F541. Auto-fix com `ruff check --fix`.
2. **Makefile `\` + indent tab** → Make nao reconhece target. Fix: linha unica.
3. **System Python 3.9** → script roda via `cd backend && uv run python ../scripts/...`
4. **datetime.UTC ausente em 3.9** → app.main falha em 3.9, exige Python 3.11+
5. **E402 import apos sys.path.insert** → usar `# noqa: E402` (intencional)
6. **`output.with_suffix(suffix + '.gz')` so adiciona 1 suffix** → usar
   `output.with_name(output.name + '.gz')` para preservar `.json` no path.

## Output estatistico (real OpenAPI)

```
paths:      141
folders:    29
requests:   143
methods:    {'GET': 82, 'POST': 58, 'DELETE': 2, 'PATCH': 1}
variables:  ['base_url', 'bearer_token', 'cartorio_api_key']
output:     infra/postman/cartorio-api.postman_collection.json (223077 bytes)
```

## LGPD compliance checklist

- [x] Authorization via `{{bearer_token}}` variable, NUNCA hardcoded
- [x] `_assert_lgpd_safe()` fail-fast em LGPD violation
- [x] `scripts/check_no_literal_keys.py` gate adicional
- [x] Nenhum secret real no collection (3 vars todas `value=""`)
- [x] Nenhum fetch contra prod — `--from-app` ou localhost dev only

## Honest count update

Wave 47 task G8.17.T1 → **54 → 55/100** (+1 task done).

## Refs

- Script: `scripts/postman_sync.py`
- Tests: `backend/tests/test_postman_sync_g8.py`
- Fixture: `backend/tests/fixtures/minimal_openapi.json`
- Doc: `docs/POSTMAN_SYNC_G8.md`
- Output: `infra/postman/cartorio-api.postman_collection.json`
- Anterior (G7): `scripts/postman_export.py`, `docs/postman_collection.generated.json`

Modified by Gustavo Almeida + cartorio-dev agent — Wave 47 closeout.