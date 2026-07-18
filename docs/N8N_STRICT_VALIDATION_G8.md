# N8N Strict JSON Validation — Wave G8.13.T2

> Task G8.13.T2 (cartorio-n8n) — validar schemas de imports JSON do N8N de forma estrita.

## Contexto

O projeto cataloga ~38-39 exports JSON de workflows N8N em `infra/n8n-workflows/*.json`. Antes desta task, o script `scripts/n8n_wf_inventory.py` apenas fazia `json.loads()` e contava nodes — sem validacao estrutural. Imports futuros (de n8n.live, ou copias de outros repos) podiam entrar com campos extras, tipos errados, PII em node name, ou timezones invalidos sem nenhum gate automatizado.

Esta task adiciona **validacao strict via Pydantic v2** (`ConfigDict(strict=True, extra="forbid")`) em todos os modelos canonicos do export N8N, com **HITL by design**: qualquer desvio do schema canonico bloqueia o inventory ate revisao manual.

## O que mudou

### Schema novo: `backend/app/schemas/n8n_workflow.py`

Tres modelos Pydantic v2 strict:

| Modelo | Cobertura |
|--------|-----------|
| `N8nSettings` | `executionOrder`, `saveDataErrorExecution`, `saveDataSuccessExecution`, `saveExecutionProgress`, `saveManualExecutions`, `callerPolicy`, `errorWorkflow`, `binaryMode` (bool\|str), `availableInMCP`, `timezone` (IANA via `zoneinfo`) |
| `N8nNode` | `id`, `name`, `type`, `typeVersion` (float), `position` ([x,y]), `parameters`, `credentials`, `options`, `webhookId`, `alwaysOutputData`, `onError`, `retryOnFail` |
| `N8nWorkflow` | `id`, `name`, `description`, `active`, `isArchived`, `nodes`, `connections`, `settings`, `tags` (list[str\|dict]), `pinData`, `staticData`, versionamento N8N API |

Todos com:
- `ConfigDict(strict=True, extra="forbid")` — recusa coercoes implicitas e campos extras
- `min_length=1, max_length=200` em `name` — sanity contra payloads truncados ou absurdos

### LGPD Art. 46 — anti-PII

A funcao `_contains_pii(text)` detecta:
- **CPF**: `\b\d{3}\.?\d{3}\.?\d{3}-?\d{2}\b` (com/sem pontuacao, com prefixo `cpf-`)
- **CNPJ**: `\b\d{2}\.?\d{3}\.?\d{3}/?0001-?\d{2}\b`
- **RG** (`XX.XXX.XXX-X`): `\b\d{2}\.\d{3}\.\d{3}-?[\dXx]\b`
- **Telefone BR** (`+55 DDD 9XXXX-XXXX`): `\+?55\s?\(?\d{2}\)?\s?9?\d{4}-?\d{4}\b`
- **Email**: `\b[\w.+-]+@[\w-]+\.[\w.-]+\b`

Aplicada via `field_validator` em:
- `N8nNode.name` (node identifier)
- `N8nNode.webhookId` (UUID de roteamento)
- `N8nWorkflow.name` / `description` / `tags`
- `N8nSettings.errorWorkflow`

> NOTA: CEP NAO esta incluso (falso-positivo em UUIDs como `67260601-4c9b-432f-...`) e CEP por si so nao eh dado pessoal.

### IANA Timezone

`N8nSettings.timezone` validado via `zoneinfo.ZoneInfo(v)` (stdlib 3.9+). Valores invalidos (`"Fake/Zone"`, `""`) levantam `ValidationError`. Aceita `None` (campo opcional).

## Como rodar

### Inventario strict

```bash
# da raiz do repo, com backend deps disponiveis (uv)
uv run --project backend python3 scripts/n8n_wf_inventory.py --strict

# gerar relatorio Markdown
uv run --project backend python3 scripts/n8n_wf_inventory.py --strict \
    --md-out docs/N8N_STRICT_VALIDATION_2026-07-18.md

# saida JSON machine-readable
uv run --project backend python3 scripts/n8n_wf_inventory.py --strict --json
```

### Testes

```bash
cd backend && uv run pytest tests/test_n8n_workflow_schema_g8.py --no-cov -v
```

34 testes cobrindo:
- validacao basica (4 testes)
- erros de campos required / tipos (6 testes)
- `extra="forbid"` em 3 niveis (3 testes)
- timezone IANA (3 testes)
- LGPD anti-PII em 6 contextos (7 testes)
- helpers publicos `is_strict_valid` / `validate_workflow_payload` (4 testes)
- **7 exports reais** (5+ gate) + batch validation (1 teste)

### Resultados (2026-07-18)

| Metrica | Valor |
|---------|-------|
| JSONs reais validados | 39/39 |
| Invalidos | 0 |
| Tempo de execucao (--strict) | ~370ms (8 workers) |
| Tests pass | 34/34 |
| Coverage new module | 100% linhas cobertas |

## Compat com exports reais (HITL gate)

Os 39 JSONs catalogados em Wave 29 G7 passam strict schema. Ajustes de schema necessarios para alcancar esse alvo:

1. `tags` aceita `list[str | dict]` — N8N alterna entre `["a", "b"]` e `[{"name": "a"}, {"name": "b"}]`
2. `pinData` aceita `dict | None` (38/39 exports tem `None`)
3. `N8nNode.id` eh opcional (alguns exports omitem — `23-lgpd-esqueci-v2.json`)
4. `N8nSettings.binaryMode` aceita `bool | str` (1 export usa `"separate"`)
5. `typeVersion` eh `float` (versoes como `3.4` existem)
6. RG regex exige pontos de separacao (senao match em UUIDs)

Nenhum JSON foi modificado ou auto-corrigido — todos passaram no schema strict como estao.

## Futuros gates sugeridos

- Wire `scripts/n8n_precommit_lint.py` (G8.14.T4, paralelo) para rodar `--strict` em pre-commit
- Adicionar `--require-active` para garantir que todos os 33 wfs ativos tem conexao com error handler
- Promover `--md-out` para upload automatico no SUI_CHECKLIST (pre-deploy)

Modified by Gustavo Almeida — G8.13.T2 (cartorio-n8n).
