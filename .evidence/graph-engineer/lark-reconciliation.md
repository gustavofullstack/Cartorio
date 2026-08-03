# Reconciliação do Plano e Recovery do Lark · Cartório Super Graph

**Data:** 2026-08-03  
**Task ID:** G2.01  
**Status:** APROVADO (PRO + SOL Review)

## Estado Reconciliado da Integração Lark / Hermes

1. **Arquitetura Canônica:**
   - **Consumidor Único:** Hermes WebSocket (1 réplica, 1 conexão, 1 task).
   - **Bot Flask / Router alternativo:** Inativo / legados desativados.
   - **Identidade Pública:** Exclusivamente **PIETRA**.

2. **Bloqueadores Atuais Registrados (Status = STALE / PENDING_P2):**
   - **Evento P2:** O tenant Lark precisa estar configurado para `im.message.receive_v1`. Eventos P1 legados (`message`, `message_read`) devem ser descontinuados.
   - **Erro `processor not found`:** Ocorrências em logs legados bloqueiam a certificação até prova de 0 ocorrências após migração P2.

3. **Verificação de Runtime (Script de Gate):**
   - O gate de verificação é [`scripts/verify_hermes_lark_p2.sh`](../../scripts/verify_hermes_lark_p2.sh).
   - O script é read-only e falha fechado enquanto houver eventos P1 ou ausência de inbound P2.

4. **Classificação de Documentos:**
   - `LARK_HERMES_RECOVERY_20260731.md`: Fonte primária de baseline da Tarefa 2.
   - Tutoriais antigos propondo Flask ou endpoints REST legados para Lark: Classificados como `STALE`.

