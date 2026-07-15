# ADR-029: Coverage strategy 2026-07-15 — bottom-5 surgical boost

**Data:** 2026-07-15
**Status:** ACEITA
**Autor:** cartorio-dev (Mavis mini-max)
**Vinculo:** ADR-027 (SOLID/DRY/KISS), ADR-028 (KISS opportunity), F2 ciclo 2
**Tipo:** Coverage strategy + roadmap para 97%

---

## Contexto

O backend do cartorio mantem um gate de cobertura de **90%** (failing CI
se cair), com target operacional de 95%. Apos o sprint F2, o bottom-5
era:

| Rank | Arquivo | Stmts | Miss | Cover | Tendencia |
|---|---|---|---|---|---|
| 1 | `app/api/v1/router.py` | 1170 | 226 | 81% | estavel (gate 78) |
| 2 | `app/services/audit_create.py` | 10 | 1 | 90% | regressao leve |
| 3 | `app/api/v1/bot_lgpd.py` | 120 | 9 | 92% | estavel (F5 88) |
| 4 | `app/main.py` | 160 | 13 | 92% | estavel (F5) |
| 5 | `app/services/lgpd_direito_esquecimento.py` | 72 | 6 | 92% | estavel |

Os arquivos #4 e #5 ja estavam sob controle (F5 LGPD commit). Os
arquivos #1, #2, #3 precisavam de **boost cirurgico** nesta missao G1.

## Decisao

### G1.4 — Router coverage boost

**Antes:** 81% (226 stmts nao cobertos).
**Depois:** 86% (158 stmts nao cobertos).
**Delta:** +5 pp. Stmts ainda nao cobertos concentram-se em:

- `webhook_evolution` (L753-1063) — 25%+ deste arquivo, contratos
  legados Evolution API 2.3.7 (AGENTS.md "Integration gotchas").
- `post_metrics_n8n` (L4248-4361) — ingestor N8N workflow #25; requer
  mock de MetricsStore + fixtures de payload.
- `health_backup` (L1668-1807) — branches de filesystem local
  (sem volume mount em CI, **nao coberto por design**).
- `_ingest_prometheus_text` (L4390-4441) — parser Prometheus raw; coberto
  parcialmente (5/13 stmts). Meta: 100% ate Sprint 5+.

### G1.5 — audit_create regression test

**Antes:** 90% (1 stmt nao coberto — branch `ValueError` defensivo).
**Depois:** 100%.
**Delta:** +10 pp. Tests adicionados:

- `test_create_audit_log_entry_delegates_to_audit_service`: caminho feliz
  (chain + HMAC via `AuditService.log`).
- `test_create_audit_log_entry_rejects_empty_required_values`: branch
  `ValueError` de defense in depth (Pydantic + checagem extra).

### G1.6 — bot_lgpd completion

**Antes:** 92% (9 stmts nao cobertos — branches `except Exception` em
`post_export`, `post_access`, `post_restaurar`).
**Depois:** 100%.
**Delta:** +8 pp. Tests adicionados (3 cenarios):

- audit log falha no `post_export` → resposta OK + rollback.
- audit log falha no `post_access` → resposta OK + rollback.
- audit log falha no `post_restaurar` → resposta OK + rollback.

Estes tests provam a **propriedade de fail-open** (LGPD art. 6 VIII):
"audit log indisponivel NAO pode quebrar a operacao principal do
titular". Critico para o servico do cartorio que atende 100% do
publico via WhatsApp/Telegram.

### G1.7 — Cross-cut improvements

#### DRY (T115)

**Candidatos identificados** (padrao try-AuditService.log / except-rollback
repetido 4 vezes):

- `app/api/v1/bot_lgpd.py:206-226` (post_export)
- `app/api/v1/bot_lgpd.py:280-295` (post_access)
- `app/api/v1/bot_lgpd.py:333-347` (post_restaurar)
- `app/services/lgpd/bot_direito_esquecimento.py:209-231` (solicitar)

**Decisao: HOLD para F6+.** Ja existe o helper `app.services.audit_helper.log_mutation()`
(com 0% coverage — sera alvo do proximo ciclo). Adotar o helper aqui
requer:

1. **Cross-review** `cartorio-lgpd` (touch em servico de LGPD art. 18).
2. **TDD estrito** com testes de regressao para cada um dos 4 callsites
   (RED → GREEN → commit).
3. **Auditar chain integrity** pos-refator (nao pode quebrar SHA256/HMAC).

KISS prefere **NAO** antecipar refator em codigo safety-critical.
Decisao registrada para a proxima missao.

#### KISS (T116)

**Top 5 funcoes complexas** (cyclomatic complexity via AST-walk, +
re-confirma contra ADR-028):

| Funcao | cc | Justificativa do HOLD |
|---|---|---|
| `router.webhook_evolution` | 29 | Contrato Evolution 2.3.7 fixo (legacy + nested payload) |
| `router.health_radar` | 23 | Densidade e a feature (6 servicos) |
| `router.post_metrics_n8n` | 18 | N8N workflow #25 contract, cross-review `cartorio-n8n` |
| `router._ingest_prometheus_text` | 13 | Parser Prometheus, sem LGPD coupling, **alvo F6** |
| `router.health_backup` | 15 | Filesystem branches **nao cobriveis em CI** |

**Decisao: HOLD em todos.** Mesmo racional do ADR-028: densidade e
dominio, nao bug. KISS prefere **NAO mexer**.

## Metricas finais (G1)

### Suite pytest

```
============================= 2816 passed, 19 skipped, 5 failed in 68.47s
```

5 falhas pre-existentes **sem relacao** com esta missao (test_telegram_webhook_e2e
precisa de `app.services.fallback` que ainda nao foi commitado em master).

### Coverage por arquivo alvo

| Arquivo | Antes | Depois | Delta | Meta | Status |
|---|---|---|---|---|---|
| `app/api/v1/router.py` | 81% | 86% | +5pp | >=85% | ATINGIDA |
| `app/services/audit_create.py` | 90% | 100% | +10pp | 100% | ATINGIDA |
| `app/api/v1/bot_lgpd.py` | 92% | 100% | +8pp | >=95% | ATINGIDA |
| TOTAL backend | 95% | 96% | +1pp | >=95% | MANTIDA |

### Quality gates

- `mypy app/`: 0 errors (141 arquivos commitados).
- `ruff check .`: 0 violations.
- 0 mypy regressions nos 3 arquivos novos.

## Roadmap para 97%

### F6 (proximo ciclo)

- **+0.5pp** — Cobertura do `audit_helper.log_mutation` (25 stmts).
  Ja existe a funcao, so precisa de testes. **Quick win**.
- **+0.3pp** — Cobertura completa de `_ingest_prometheus_text` (8 stmts).
  Parser puro, sem LGPD coupling.
- **+0.2pp** — Mover padrao try-AuditService.log dos 4 callsites LGPD
  para `log_mutation` (com cross-review `cartorio-lgpd`).

### Sprint 5+

- **+0.5pp** — `main.py` lifespan + scheduler (8 stmts nao cobertos;
  requer E2E ou refator com TestClient + lifespan mocking).
- **+0.3pp** — `health_radar` parametrized mocks de httpx (4 servicos
  externos).
- **+0.2pp** — webhook_evolution edge cases (payload invalido,
  idempotency race, fallback LLM rate-limited).

Total estimado: **+2pp** no F6, **+1pp** no Sprint 5 = **99%** estavel
em 2-3 ciclos.

## Consequencias

### Positivas

- 3 arquivos do bottom-5 saem da lista de risco.
- bot_lgpd atinge 100% — LGPD-safe bot endpoints 100% testados.
- audit_create 100% — chain adapter LGPD art. 37 coberto.
- 5 testes novos (40 passed incluindo os pre-existentes).
- ADR documenta explicitamente o **stop**: 4 candidatos a DRY estao
  em HOLD, com motivo, para a proxima missao.

### Negativas

- router.py ainda 86% — webhook_evolution + n8n_ingest dominam as 158
  stmts remanescentes. **Esperado**: contrato externo fixo.
- main.py continua em 92% — lifespan 8 stmts nao cobriveis sem E2E
  (decisao consciente).

## Compliance

- LGPD: zero impacto em codigo de tratamento (LGPD review nao necessario
  — nenhum arquivo de dominio LGPD foi modificado).
- HITL: zero impacto.
- Conventional Commits: commit `test(quality): coverage boost...`
  com mensagem terminando em `Modified by Gustavo Almeida`.
- Branch: `master` (padrao AGENTS.md).

---

## Referencias

- ADR-027: codebase analysis SOLID/DRY/KISS.
- ADR-028: KISS opportunity analysis (mesmo racional).
- AGENTS.md: secao "Tests" + "Code style" + regras P0.
- F2 sprint bottom-5 (commit 6116a60).
- F5 SOLID commit (4b8dce7) + F5 LGPD commit (55fde90).
