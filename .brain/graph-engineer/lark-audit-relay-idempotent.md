# Relay de Auditoria Idempotente (Lark) · Cartório Super Graph

**Data:** 2026-08-03  
**Task ID:** G2.24  
**Status:** APROVADO (TERRA + PRO Review)

## Evidência de Audit Relay

- **Chain Tamper-Evident:** Todas as requisições e respostas no Lark geram evento no `audit_log` (SHA256 chain + HMAC).
- **Idempotência:** Garantia de registro único por evento de mensagem recebida.

