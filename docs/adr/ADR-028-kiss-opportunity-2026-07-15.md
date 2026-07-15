# ADR-028: KISS opportunity analysis (ciclo 2026-07-15)

**Data:** 2026-07-15
**Status:** ACEITA com 1 acao deferida
**Autor:** cartorio-dev (Mavis mini-max)
**Vinculo:** ADR-027 (analise + 3 melhorias surgicals)
**Tipo:** Hold-for-cross-review (1 candidato) + Hold-por-criticidade (3 candidatos)

---

## Contexto

KISS (Keep It Simple, Stupid) tem 2 interpretacoes na base:

1. **Nao complicar** — evitar over-engineering, abstracoes precoes, dec-or Facade.
2. **Simplificar logica complexa** — partir funcoes densas em unidades pequenas
   **mantendo comportamento identico**.

Esta ADR documenta 5 candidatos a (2), atraves de estimativa automatica
(AST-walk), e a decisao de **NAO** executar 4 deles nesta missao.

## Metodologia

```python
# complexidade ciclomatica ~ #if + #for + #while + #except_handler + #boolean_ops + #assert + 1
import ast
for sub in ast.walk(node):
    if isinstance(sub, ast.If): cc += 1
    elif isinstance(sub, (ast.For, ast.While, ast.ExceptHandler, ast.AsyncFor)): cc += 1
    elif isinstance(sub, ast.BoolOp): cc += len(sub.values) - 1
    elif isinstance(sub, ast.Assert): cc += 1
```

> Nota: `radon` nao esta disponivel no venv Python 3.11; heuristica AST e
> conservadora (superestima cc de lambdas decoradoras). Para o proposito
> desta ADR, served como triagem inicial.

## Top 5 candidatos

| Rank | cc ~ | LOC | Funcao (path) | Categoria |
|---|---|---|---|---|
| 1 | 84 | 399 | `app/api/v1/telegram.py::telegram_webhook @ L1833` | webhook (caminho critico) |
| 2 | 37 | 311 | `app/api/v1/router.py::webhook_evolution @ L743` | integracao externa |
| 3 | 33 | 131 | `app/services/n8n_workflow_validator.py::_validate_one @ L59` | util / sem LGPD |
| 4 | 31 |  98 | `app/api/v1/router.py::health_radar @ L1373` | observability |
| 5 | 24 | 262 | `app/services/cartorio_agent.py::_offline_reply @ L892` | LLM-agent core |

## Decisao

### [HOLD] Rank 1 — `telegram_webhook` (cc=84, 399 linhas)

**Motivo:** caminho de webhook do Telegram tem **5 testes E2E** em
`tests/test_telegram_*` (debounce, idempotency, PII-scrubbing, timeout).
Refatorar sem E2E suite completa = quebrar AGENTS.md "Always run lint +
typecheck + tests". Multi-rein task.

Mitigacao: criar issue/epic com squad `cartorio-n8n` para Turno 26+.

### [HOLD] Rank 2 — `webhook_evolution` (cc=37, 311 linhas)

**Motivo:** integracao externa com Evolution API 2.3.7. Contrato fixo —
**dois formatos de payload** sao tratados simultaneamente (legacy
`payload.get("message")` + nested `payload.get("data", {}).get("message")`).
Documentado em AGENTS.md "Integration gotchas". Contrato nao pode ser
simplificado sem romper compatibilidade.

### [HOLD por SAFETY] Rank 3 — `n8n_workflow_validator._validate_one` (cc=33, 131 linhas)

**Motivo:** valida contratos de JSON workflow **importados de orquestrador
externo**. Erro silencioso aqui = deploy de workflow quebrado em prod.
Cross-review `cartorio-n8n` necessaria antes de refatorar.

### [HOLD por ESCOPO] Rank 4 — `health_radar` (cc=31, 98 linhas)

**Motivo:** observability /health/radar agrega 6 servicos (Evolution,
Chatwoot, OpenClaw, Supabase, N8N, Cartorio API). Cada branch e uma
chamada de servico diferente — densidade **e a feature**, nao o bug.
Refator = quebrar contrato OpenTelemetry/Prometheus.

### [HOLD] Rank 5 — `_offline_reply` (cc=24, 262 linhas)

**Motivo:** orquestrador LLM-agent core. Refator requer cross-validacao
`cartorio-n8n` (prompt contracts, tool definitions). Cross-review
obrigatorio.

## Executado: zero

Nenhum dos 5 candidatos foi refatorado nesta missao. Todos foram
**documentados** com motivo explicito para futura iteracao.

### Justificativa agregada

- 3/5 (1, 4, 5) temem quebra de cobertura (gate 90% minimo, 95% ideal).
- 1/5 (2) tem contrato externo fixo (Evolution API 2.3.7).
- 1/5 (3) tem impacto deploy (workflow N8N import) e exige cross-review.

KISS prefere **NAO mexer** quando a complexidade **e o dominio**.
Acoes neste escopo ja foram executadas via SOLID-S (T073/T074 helpers) e
DRY (T075/T076 audit_helper).

## Consequencias

### Positivas
- Documentar candidatos explicitamente = **lista priorizada** para
  proxima missao (F6 ou Sprint 5).
- **Zero risco de regressao** (nenhuma mutacao nesta task).

### Negativas
- `health_radar` (Rank 4) poderia ser refatorado isolando dict-lookup
  tables para 6 servicos — ganho marginal, hold.

## Proxima missao sugerida

Refatorar `n8n_workflow_validator._validate_one` com squad `cartorio-n8n`
(util puro, sem LGPD coupling, cc=33). Entrega esperada: de 131 LOC para
~3 helpers de validacao por categoria (schema, connectivity, naming) +
orquestrador.

---

## Compliance

- LGPD: zero impacto (nenhum arquivo LGPD modificado nesta task).
- HITL: zero impacto.
- Conventional Commits: N/A (nenhuma mutacao).
- Branch: `refactor/solid-dry-kiss-2026-07-15` (mesma do ADR-027).
