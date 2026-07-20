# WORKFLOW_REGISTRY

Workflows n8n e fluxos internos (2026-07-20).

## Workflows n8n (exports em `infra/n8n-workflows/`)

| Workflow | Função | Estado |
|---|---|---|
| WF Telegram | inbound → API → resposta | ✅ ativo (substituído em grande parte pelo handler nativo da API) |
| WF WhatsApp/Evolution | inbound dual-format → API | ⏸ pronto, aguardando QR |
| WF Handoff Chatwoot | takeover humano → mute bot | ✅ ativo |
| WF Monitoramento | state Evolution → alerta Telegram | template pronto (ativar pós-QR) |

Operação: `make n8n-list` / `make n8n-export` / `make n8n-test`.

## Fluxos internos críticos (backend)

1. **Atendimento**: intake → triagem LLM → FAQ/emolumento/agendamento → (se jurídico) protocolo `DRAFT` → validação escrevente.
2. **Emolumento**: parâmetros → tabela MG 2026 → estimativa com disclaimer → nunca cálculo final sem HITL.
3. **LGPD Art. 18**: pedido → identidade → execução (acesso/correção/anonimização/portabilidade/eliminação/oposição/não-automação) → audit + resposta.
4. **CNJ massive-dump**: DPO autenticado (API key + JWT) → gate audit → streaming `yield_per(1000)` com scrub → hash do pacote.
5. **Retenção**: scheduler 03:00 BRT → anonimização/eliminação por política → métrica + audit (regressões `t036`/`t037`).

## Regras

- Todo workflow que toca PII: implementa `cartorio-n8n`, revisa `cartorio-lgpd`.
- State machines e checkpoints em `workflows/STATE_MACHINES.md` / `workflows/CHECKPOINTS.md`.
- Rollback de workflow = export anterior em `infra/n8n-workflows/` + redeploy via n8n API.
