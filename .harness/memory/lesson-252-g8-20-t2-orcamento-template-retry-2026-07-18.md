# Lesson 252 — G8.20.T2 template workflow orçamento + fix openapi merge (2026-07-18)

## Contexto

Construção do primeiro **template offline** de workflow N8N (`template-orcamento-escritura.json`)
no projeto: 6 nodes lineares `Webhook → Validar → Calc Emolumento → Format Response DRAFT →
Audit LGPD Art.37`, com flag `draft: true` explícita para HITL (escrevente valida) e node
final de auditoria apontando para `/api/v1/audit` (LGPD Art. 37).

A workdir master já tinha um **merge conflict não resolvido** no `openapi_enhancer.py`
(4 blocos `<<<<<<< Updated upstream` / `>>>>>>> Stashed changes` deixados pelo Wave 47
consolidator). O conflito deixava o módulo sintaticamente inválido e quebrava a suíte de
testes mesmo antes do trabalho novo começar.

## Decisão

- Optar por **template estático + runbook Markdown + suite de validação estrutural** em vez
  de importar contra o N8N live (Wave 49 ainda não tem TLS contra `flow.2notasudi.com.br`
  revisado nesta sprint e tasks G8.20+2 estavam marcadas `NÃO rodar contra N8N live`).
- Schema strict Pydantic v2 (`app.schemas.n8n_workflow.N8nWorkflow`) já aceita campos
  `executionOrder: "v1"` em `settings` com `extra=forbid` — fornece defaults razoáveis
  para os outros campos, então passar `{"executionOrder": "v1"}` é suficiente.
- `typeVersion: int` (ex.: `1`) é promovido automaticamente para `float` pelo Pydantic
  v2 mesmo em `strict=True` (via validador `lax` para `float`). `position: list[float]`
  aceita ints. Isso simplifica o template: números JSON crus funcionam.
- Não incluir nó de validação por escrevente (HITL WebSocket) — ele pertence a G8.20.T3,
  e o template é o **bloco de cálculo + audit** consumido pelo workflow pai
  (`01-consulta-emolumento` / `02-criar-protocolo`).
- Resolver o merge conflict pré-existente do `openapi_enhancer.py` via
  `git checkout HEAD -- backend/app/middleware/openapi_enhancer.py`. A versão HEAD
  contém tudo que importa (a função `_register_webhook_schemas` e o SECURITY_SCHEMES
  com 3 chaves: `ApiKeyAuth`, `BearerAuth`, `TelegramWebhookSecret`). A side "Stashed
  changes" só adicionava comentários extras — sem novo código.

## Validação

```text
python3 scripts/n8n_wf_inventory.py                  # count: 40  valid: True
APP_ENV=development uv run python3 ../scripts/n8n_wf_inventory.py --strict
                                                    # count: 40  valid: 40  invalid: 0
                                                     # template-orcamento-escritura.json: status=valid  nodes=5
APP_ENV=development uv run pytest --no-cov -q \
    tests/test_orcamento_template_validation_g8.py  # 12 passed in 0.24s
APP_ENV=development uv run ruff check \
    tests/test_orcamento_template_validation_g8.py  # All checks passed!
APP_ENV=development uv run pytest --no-cov -q       # 4220 passed, 1 FLAKY pré-existente
```

## Honestidade (Honesty Gate)

| Métrica | Baseline | Esperado | Observado |
|---------|----------|----------|-----------|
| `n8n_wf_inventory.py` count | 39 | 40 (era 38) | **40** |
| Novos tests | 0 | 5+ | **12** (5 obrigatórios + 7 hardening) |
| Ruff | 0 | 0 | **0** |
| Full pytest | 4215 passed, 1 flaky | passa | 4220 passed, 1 flaky (mesmo teste, pré-existente) |

> **Nota crítica:** o Honesty Gate indicava "39 wfs (era 38)" e "pytest --no-cov -q →
> continua PASS". Observação: o baseline real do workdir já era **39** (Wave 49 parcial
> já havia commitado outras tasks) e o teste `test_openapi_security_scheme_defined`
> **já falhava pré-existente** quando roda após 3663+ outros tests — falha de ordering
> entre testes que mutam `app.openapi_schema`. Não é regressão deste trabalho. Foi
> reproduzido sem qualquer mudança nova (`git stash --include-untracked` +
> `pytest --no-cov -q` → mesmo FAIL idêntico).

## Lições aprendidas

1. **Validar pré-condições antes do Honesty Gate.** O gate literal não bate porque o
   workdir master recebeu merges parciais com conflitos. Stash limpo + rerun puro é o
   caminho pra distinguir regression de pré-existente.
2. **`git checkout HEAD -- <file-unmerged>` é a saída mais barata** quando a side
   "Stashed changes" não traz código novo (só comentários). Confirmar via
   `git show HEAD:<file>` antes de descartar a WIP side.
3. **Templates N8N no schema strict aceitam `list[int]` em `position`** porque Pydantic
   v2 strict coerce-soft em containers built-in. Mesmo em `float`-typed, `1` é
   aceito e promovido. Isso simplifica authoring manual.
4. **`tags: list[str | dict]` aceita duas formas** — `["emolumento", "orcamento"]` é
   canônico; `[{"name": "..."}]` (versão da API N8N) também passa. Templates podem
   usar uma ou outra.
5. **Schema strict vs basic no inventário.** O modo `basic` (padrão `python3`) só
   checa JSON parseável; o modo `strict` (sob `uv run` + `APP_ENV=development`)
   carrega `app.schemas.n8n_workflow.N8nWorkflow` e valida Pydantic v2 strict + LGPD
   anti-PII regex. Um template `active: false` ainda é contado.

## Pendências para G8.20.T3+

- G8.20.T3: nó de validação por escrevente (HITL WebSocket + Chatwoot signal).
- G8.20.T4: label Chatwoot `orcamento_draft` + handoff para dashboard escrevente.
- G8.20.T5: persistir `orcamento` table com snapshots MG tabela referência.
- G8.20.T6: RIPD específico do fluxo (cartorio-lgpd revê).
- Investigar a flakiness do `test_openapi_security_scheme_defined` (provavelmente
  cache de `app.openapi_schema` poluído por `test_openapi_validator.py` /
  `test_webhook_schemas_g8.py`). Out of scope desta task.
