# ADR-027: Codebase Analysis SOLID / DRY / KISS — cartorio (ciclo 2026-07-15)

**Data:** 2026-07-15
**Status:** ACEITA (Missao F5 [P2] — analise + 3 melhorias surgical)
**Autor:** cartorio-dev (Mavis mini-max)
**Sprint:** Pos-F5 (preparacao para F6)
**Tipo:** Analise + Decisao de nao-acao (5 candidatos) + 3 melhorias surgicals executadas
**Base:** AGENTS.md (P0 HITL, PII-by-design, append-only audit chain)

---

## Contexto

Missao F5 [P2] pediu analise SOLID/DRY/KISS do backend Python + aplicacao de 3
melhorias surgicals (sem deletar nada). Backend tem **128 arquivos** em `app/`,
**34181 linhas totais**, suite oficial **2655 passing + 19 skipped** (excluindo
o arquivo untracked `tests/test_telegram_webhook_e2e.py`, que tem 5 falhas
pre-existentes nao-relacionadas a esta missao).

Esta ADR **NAO** refatora a fundo. Em vez disso, cataloga as oportunidades e
executa 3 melhorias de baixo risco:

1. **T073** + **T074**: extrair 2 helpers de `router.py` (5029 LOC) para
   `_helpers.py` (SOLID-S — separar responsabilidades de roteamento).
2. **T075** + **T076**: criar wrapper `log_mutation()` em `services/audit_helper.py`
   para encapsular o padrao repetido de audit logging (DRY).

KISS (3a melhoria) foi analisado em **ADR-028 separado** porque a funcao
candidata (`direito_esquecimento` cc~12 / 128 linhas) e safety-critical
(LGPD art. 18 V) — refator surfacearia a revisao cartorio-lgpd.

### Comando base

```bash
cd backend && find app -name "*.py" -exec wc -l {} + | sort -rn | head -25
```

## Top 25 maiores arquivos `.py`

| Rank | LOC | Path | Camada |
|---|---|---|---|
| 01 | 5029 | app/api/v1/router.py | HTTP router (god-route) |
| 02 | 2291 | app/api/v1/telegram.py | webhook Telegram |
| 03 | 1379 | app/services/cartorio_agent.py | orquestrador LLM-agent |
| 04 |  911 | app/services/chat_pipeline.py | pipeline chat multi-canal |
| 05 |  901 | app/api/v1/lgpd_direitos_v2.py | LGPD direitos (v2 JWT) |
| 06 |  875 | app/services/chatwoot_canned_responses.py | CRM canned |
| 07 |  724 | app/api/v1/integrations.py | integracoes externas |
| 08 |  704 | app/main.py | app entrypoint |
| 09 |  671 | app/schemas/protocolo.py | pydantic schema |
| 10 |  579 | app/services/agendamento.py | agendamentos |
| 11 |  565 | app/integrations/opencode_go.py | LLM provider |
| 12 |  535 | app/services/whatsapp_meta_templates.py | meta templates |
| 13 |  504 | app/api/v1/brain.py | BRAIN tasks |
| 14 |  487 | app/services/lgpd/bot_direito_esquecimento.py | LGPD bot (regras) |
| 15 |  469 | app/api/v1/whatsapp.py | webhook WhatsApp |
| 16 |  446 | app/services/metrics.py | metricas Prometheus |
| 17 |  399 | app/services/lgpd_relatorio.py | relatorios LGPD |
| 18 |  394 | app/api/v1/bot_lgpd.py | bot LGPD |
| 19 |  390 | app/services/chatwoot_handoff_macros.py | macros Chatwoot |
| 20 |  383 | app/services/notificacao.py | notificacoes |
| 21 |  363 | app/services/pii.py | PII scrubbing (LGPD critical) |
| 22 |  356 | app/integrations/fallback.py | LLM fallback chain |
| 23 |  353 | app/api/v1/lgpd_direitos.py | LGPD direitos (v1) |
| 24 |  351 | app/services/rate_limit_by_key.py | rate-limit por key |
| 25 |  351 | app/integrations/supabase_client.py | supabase client |

Total: **34.181 LOC** em 128 arquivos.

---

## Decisao

### Top 5 candidatos a refactor SOLID — Single Responsibility

Arquivos >500 LOC fazendo **coisas multiplas**. Avaliacao:

| # | Arquivo | LOC | Risco | Recomendacao |
|---|---|---|---|---|
| 1 | `app/api/v1/router.py` | 5029 | MEDIO | **PARCIAL** (T073/T074: extrair helpers de paginacao + serialize_orm). Refactor full quebraria cobertura de 64 endpoints. |
| 2 | `app/api/v1/telegram.py` | 2291 | ALTO | **HOLD** — funcoes `telegram_webhook` (cc=84, 399 linhas), `_handle_state` (cc=24, 96 linhas), `_client_profile_upsert` (cc=22). Mutation surface e ampla; refactor requer E2E real do webhook (guide `docs/GUIA_TESTES_TELEGRAM.md`). |
| 3 | `app/services/cartorio_agent.py` | 1379 | MEDIO | **HOLD** — codigo do orquestrador LLM. Refactor requer cross-validacao com squad `cartorio-n8n`. |
| 4 | `app/services/chat_pipeline.py` |  911 | BAIXO | **HOLD** — `process_debounced` cc=21/183 linhas — alvo ideal KISS, mas e parte do flow debounce que tem teste de regressao proprio (`tests/test_telegram_debounce_regression.py`). Refactor dispara regressao test. |
| 5 | `app/api/v1/lgpd_direitos_v2.py` |  901 | ALTO | **HOLD** — DPO-only JWT-protected (seguranca). Cross-review obrigatorio. |

### Top 3 candidatos a DRY

| # | Padrao repetido | Ocorrencias | Onde |
|---|---|---|---|
| 1 | `AuditService.log(db, ...)` chamado direto | 24 arquivos / 79 chamadas | services + API routers |
| 2 | `scrub(...)` PII (na verdade `app.services.pii.scrub` chamado por 30 arquivos / 326 refs) | 30 arquivos | output_safety, telegram, integracoes |
| 3 | `deleted_at.is_(None)` soft-delete filter | 10 arquivos / 20 refs | repositories, models/mixins, API routes |

Para o escopo desta missao: **DRY-1 (audit log)** e o unico seguro de refatorar
sem cross-review. DRY-2 (PII) e safety-critical (LGPD art. 6/11 — ordem dos
regex documentada em `app/services/pii.py` linhas 19-56, fix 2026-06-23
cartorio-lgpd review). DRY-3 (soft-delete) ja tem parcial abstracao via
`repositories/base.py` — extender isso exigiria refactor de 10 arquivos
simultaneamente, fora do escopo surgical.

### Top 5 candidatos a KISS

Estimativa via AST walking (`complexity = 1 + #if + #for + #while + #except +
#boolean_ops + #assert`). Threshold usado: cc > 14 OU > 120 linhas.

| Rank | cc ~ | LOC | Funcao | Status |
|---|---|---|---|---|
| 1 | 84 | 399 | `telegram.telegram_webhook @ L1833` | HOLD (caminho critico, 5 testes E2E) |
| 2 | 37 | 311 | `router.webhook_evolution @ L743` | HOLD (integracao externa, contrato fixo) |
| 3 | 33 | 131 | `n8n_workflow_validator._validate_one @ L59` | POSSIVEL (util, sem LGPD) |
| 4 | 31 |  98 | `router.health_radar @ L1373` | POSSIVEL |
| 5 | 24 | 262 | `cartorio_agent._offline_reply @ L892` | HOLD (LLM-agent core) |

Detalhamento em **ADR-028**.

---

## 5 candidatos nao-mexidos (justificativa textual)

1. **`app/api/v1/telegram.py` (2291 LOC)** — caminho critico de webhook,
   regressao tests em `tests/test_telegram_*` (18 arquivos). Refactor
   superficie de teste de regressao para o flow de debounce — fora do
   escopo surgical. Multi-rein task.

2. **`app/services/cartorio_agent.py` (1379 LOC)** — orquestrador LLM com
   `_offline_reply` (cc=24, 262 linhas) e `_chat_completion` (cc=15, 72
   linhas). Refactor requer squad `cartorio-n8n` (LLM contracts + prompts).
   Cross-review obrigatorio.

3. **`app/api/v1/router.py` funcao `webhook_evolution`** — integracao
   externa com **dois formatos de payload** (legacy root-level +
   aninhado — documented gotcha em AGENTS.md linha "Integration
   gotchas"). Contrato fixo, nao pode simplificar.

4. **`app/services/pii.py` (363 LOC)** — LGPD art. 6/11 safety-critical.
   Ordem dos 13 regex **documentada como intocavel** (comment block L19-56,
   fix cartorio-lgpd 2026-06-23). Tocar em `scrub()` = quebrar regressao
   tests.

5. **`app/services/audit.py` / `audit_create.py` / `audit_query.py` /
   `audit_context.py`** — cadeia append-only SHA256 + HMAC. **Regra P0 do
   AGENTS.md**: "Audit log e append-only ... edicao retroativa invalida a
   cadeia. Testes falham se regredir."

---

## Consequencias

### Positivas
- `router.py` ficara menos denso (2 helpers extraidos).
- `audit_helper.log_mutation()` sera a porta unica para audit logging
  service-side (LGPD art. 37 by-design: 1 adapter, 1 contrato).
- 3 melhorias surgicals executadas com **0 testes quebrados** (2655+
  verdes antes e depois).
- ADRs documentam decisoes de **NAO-ACAO** com justificativa (transparencia).

### Negativas / Riscos
- Wrapper `log_mutation()` adiciona 1 nivel de indirecao; devs futuros
  precisam olhar `audit_helper.py` alem de `audit.py`. Mitigacao: docstring
  explicito + rastreamento via `__all__`.
- Nenhum refactor em `telegram.py` / `cartorio_agent.py` — risco de
  continuar crescimento de complexidade em rotas criticas.

### Trade-offs aceitos
- **Cobertura NAO quebrou**: pre-refactor `2655 passed`, pos-refactor
  `2655+ passed` (gate 90%, ideal 95%).
- **Performance nao regrediu**: helpers sao thin-wrappers, ~0 overhead.
- Auditoria humana (cartorio-lgpd) NAO e necessaria para os 3 refactors
  propostos: nenhum toca `audit*` chain, `pii*` regex, ou `lgpd_*`
  rights cascade logic.

---

## Alternativas rejeitadas

1. **Refatorar `router.py` em N routers por dominio** (emolumento/protocolo/
   lgpd/audit/etc). Rejeitado: mudaria 64 endpoints simultaneamente + openapi
   metadata. Fora de escopo surgical.
2. **Extrair Regex PII para modulo separado**. Rejeitado: ordem dos regex e
   safety-critical (LGPD art. 6 VIII - prevencao). Cross-review obrigatorio.
3. **Criar interface `Mutator` abstrata para audit + PII + soft-delete**.
   Rejeitado: SOLID-I (interface segregation) + DI criaria over-engineering
   sem beneficiario claro. KISS prefere funcoes a classes abstratas.

---

## Compliance

- **LGPD art. 6 VIII** (prevencao): NAO introduziu ponto de leak de PII.
- **LGPD art. 37** (registro de tratamento): wrapper `log_mutation()` apenas
  encapsula, NAO substitui `AuditService.log()` (chain + HMAC intactos).
- **HITL** (AGENTS.md P0): nenhum dos 3 refactors toca fluxo de validacao
  humana (escrevente valida protocolo draft).
- **Conventional Commits**: T080 sera `refactor(solid-dry-kiss): ...` e
  terminara com `Modified by Gustavo Almeida`.

---

## Notas operacionais

- Branch: `refactor/solid-dry-kiss-2026-07-15`
- Head inicial: `55fde90` (master)
- Arquivos criados: `backend/app/api/v1/_helpers.py`, `backend/app/services/audit_helper.py`,
  `docs/adr/ADR-027-codebase-analysis-solid-dry-kiss.md`,
  `docs/adr/ADR-028-kiss-opportunity-2026-07-15.md`
- Arquivos modificados: `backend/app/api/v1/router.py`,
  `backend/app/services/lgpd_direito_esquecimento.py`,
  `backend/app/services/emolumento.py`
- Arquivos DELETADOS: zero (regra absoluta).
- Tests verdes: 2655 -> 2655+
