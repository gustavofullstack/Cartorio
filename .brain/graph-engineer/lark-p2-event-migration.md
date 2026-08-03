# Migração de Assinatura para im.message.receive_v1 P2 · Cartório Super Graph

**Data:** 2026-08-03  
**Task ID:** G2.06  
**Status:** APROVADO (LUNA + PRO Review)

## Evidência de Evento P2

- **Evento Alvo:** `im.message.receive_v1` (Mensagem P2 modernizada).
- **Descontinuação:** Eventos legados P1 (`message`, `message_read`) inativados na configuração do tenant.
- **Validador de Runtime:** `scripts/verify_hermes_lark_p2.sh` preparado como gate de execução P2.

