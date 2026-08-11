# Lesson 302 — Pietra WhatsApp P0: orquestracao + guardrails (auditoria 41/100)

Data: 2026-08-11
Reins: cartorio-dev, cartorio-lgpd, cartorio-n8n
Status: codigo na branch `fix/pietra-whatsapp-p0-audit-20260811` (sem deploy, sem QR, sem DB real)

## Sintoma

Bateria real no WhatsApp: nota 41/100, NO-GO. Duplicidade, resposta apos 52min10s, rajada fora de ordem, pergunta perdida, testamento com 4 testemunhas, PDF no celular a R$ 11,21, ITBI 2–3%, “pedra do cartorio”, protocolo virando catalogo.

## Causas raiz (codigo, nao “falta de Redis”)

1. **`resume_burst` descartava a 1a de 2 msgs** (`len <= 2 → texts[-1]`). Rajada de 2 perdia pergunta.
2. **`process_debounced` nao dormia** a janela de 1.2s — debounce era so documentacao.
3. **Rate-limit DROP** em vez de esperar — pergunta sumia.
4. **Sem lock por conversa e sem idempotencia de saida** — respostas duplicadas/fora de ordem.
5. **Sem expiry de evento antigo** — fila/reprocessamento gerava resposta 52min depois.
6. **`_wants_catalog_continue` casava `proximo`** → “proximos horarios” virava `catalogo_serie` hard-offline.
7. **WhatsApp nao passava** por `guard_identity` nem allowlist de e-mail institucional.
8. **Fatos juridicos nao estavam no path de saida** — so no prompt, o LLM ignorava.

## Fix (TDD, local)

- `whatsapp_orchestration.py`: stale 300s, lock SETNX 90s, burst numerado, output idempotency 24h (hash na chave Redis).
- `pietra_legal_guardrails.py`: 2 testemunhas, legitima, PDF R$ 12,99, semelhanca=cartao da serventia, ITBI 2%, procuracao publica, ata constata, protocolo≠catalogo, pedra→Pietra, LGPD DRAFT+DPO.
- `outbound_scrub.py`: dpo@ / contato@ nao viram `[EMAIL_REDACTED]`.
- `chat_pipeline.process_debounced`: sleep + lock + stale + guardrails + identity + outbound + skip send duplicado.
- Catalogo: autenticacao eletronica R$ 12,99 + cartao autografo R$ 11,21. Intent protocolo composto responde as 3 perguntas.

## Replay

`tests/test_pietra_whatsapp_audit_replay.py`: 10/10 casos sanitizados = 100/100 no gate deterministico. Rajada preserva 10 entradas. Nao substitui bateria live no WhatsApp (ainda P1 apos merge).

## Nao fazer

- Nao deployar esta branch sem `make qa` + review cartorio-lgpd (toca PII outbound + identidade).
- Nao afrouxar HITL: protocolo continua DRAFT.
- Nao voltar `resume_burst` para “fica so a ultima”.
