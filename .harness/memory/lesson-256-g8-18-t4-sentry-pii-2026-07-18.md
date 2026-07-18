# Lesson 256 — G8.18.T4 Sentry before_send PII scrubber (2026-07-18)

## Contexto

Tarefa G8.18.T4 — estender `before_send` do Sentry para cobrir TODOS os
campos do event protocol (não só `message`/`tags`/`extra`). LGPD Art. 46
(segurança) + Art. 50 (boa-fé) — zero PII raw em vendor externo.

## Decisões arquiteturais

1. **Função `scrub_pii_from_event(event, hint)` é o hook canônico.**
   `_before_send` legado virou thin wrapper que delega + mantém a
   métrica `cartorio_pii_leak_prevented_total` (compat com tests A4).

2. **`before_send_transaction=scrub_pii_from_event`** também — Sentry
   transactions carregam breadcrumbs HTTP (headers podem vazar PII).

3. **`user.id` com PII → hash determinístico** `anon-<sha256[:16]>`,
   não `[LGPD-SCRUBBED]`. Razão: rastreabilidade cruzada (log local +
   Sentry apontam pro mesmo "user") sem expor raw. UUIDs seguros
   preservados.

4. **Helpers expostos:** `looks_like_pii(value)` (usa
   `app.services.pii.detect_only` canônico, fallback regex local) e
   `scrub_dict_inplace(d)` (recursivo para dicts/listas aninhadas).

5. **LGPD-REVIEW-PENDING** no commit — `cartorio-lgpd` precisa
   revisar antes de merge prod, conforme AGENTS.md regra de auditoria.

## Pegadinhas / armadilhas

- **Assinaturas divergentes entre `app.services.pii` e spec do harness:**
  pii module expõe `scrub(text) -> ScrubResult` (com `.text`), enquanto
  spec pedia `scrub_pii(text) -> str`. Solução: o sentry module mantém
  seu próprio `scrub_pii` local (regex direto), e `looks_like_pii`
  envolve `pii.detect_only` quando disponível.
- **Stacktrace `vars` (locals do Python) é o vetor #1 de leak** —
  PII frequentemente capturado em exceções como
  `validate_cpf("123.456.789-00")`. Scrub recursivo via
  `scrub_dict_inplace` cobre isso.
- **Breadcrumbs `.data` é vetor #2** — headers HTTP, request body,
  cookies do frontend são comuns. Mesma proteção recursiva.
- **`event == None`** é caso especial no Sentry (DropEvent) — early
  return é mandatório antes de qualquer acesso a dict.

## Resultado

- `backend/app/services/sentry.py` — `scrub_pii_from_event` cobre 6
  seções (message, exception.values, exception.stacktrace.frames,
  breadcrumbs.values, request, user) + tags/extra recursivos.
- `backend/tests/test_sentry_pii_scrub_g8.py` — **24 testes** PASS.
- `docs/SENTRY_LGPD_G8.md` — spec da configuração + checklist LGPD.
- ruff: 0 errors. mypy strict: 0 errors. sentry subset: 57 PASS, 1 skip.

## Compatibilidade

- `test_sentry_a4.py` (legado) — 100% verde após refactor.
- `_before_send` exportado ainda funciona como alias — quebra zero
  imports externos.
- `capture_exception`/`capture_message` inalterados.

## Lição reaproveitável

> Quando integrar SDK externo que recebe **qualquer** payload derivado
> de dados sensíveis, **hook genérico + função `looks_like_pii`**
> evita ter que lembrar de cada campo novo. O preço é manter o detector
> canônico (`app.services.pii`) sempre como fonte da verdade — não
> duplicar regex em cada integração.

Aplicável a: Datadog, New Relic, OpenTelemetry exporter, Sentry SaaS,
qualquer ferramenta SaaS que receba payload.
