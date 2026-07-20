# AUTONOMY

Níveis de autonomia do agente (2026-07-20).

## Níveis

| Nível | Escopo | Exemplos |
|---|---|---|
| A0 — proibido | Nunca autônomo | Rotação de chaves, decisão jurídica, emissão de certidão/escritura, isenção, aprovação de protocolo |
| A1 — com aprovação | Executa só após OK humano | Deploy prod, migration, re-sync webhook, alteração de workflow com PII |
| A2 — autônomo supervisionado | Executa e registra | Responder FAQ, calcular estimativa de emolumento, agendar, mascarar PII, retries DLQ |
| A3 — autônomo engenharia | Em branch, com gates | Rodar testes, lint, gerar docs, abrir PR (merge só humano) |

## Regras

- Toda ação A1/A2 sensível grava entrada no audit log (actor, ação, payload scrubado).
- Protocolo sempre nasce `DRAFT` — promoção a processado exige escrevente (HITL).
- Kill switch: takeover Chatwoot silencia o bot imediatamente; `autonomy/KILL_SWITCH.md`.
- Jobs agendados: retenção LGPD 03:00 BRT; dead-man's-switch audit 15min — ambos com métrica e alerta.
- Budgets: timeout LLM 45s/tentativa; máx. 2 agents simultâneos; steps por sessão conforme `.harness`.

## Condições de parada

- Falha de audit chain → fail-closed em ações sensíveis + alerta DPO.
- Esgotamento de fallback LLM → mensagem de degradação + handoff sugerido.
- Detalhes em `autonomy/STOP_CONDITIONS.md` e `autonomy/SHUTDOWN.md`.
