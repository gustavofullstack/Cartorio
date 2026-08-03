# Dedupe de Eventos e Respostas no Lark · Cartório Super Graph

**Data:** 2026-08-03  
**Task ID:** G2.23  
**Status:** APROVADO (LUNA + TERRA Review)

## Evidência de Idempotência

- **Store Redis SETNX:** TTL 24h em `app/services/idempotency_store.py`.
- **Prevenção:** Eventos duplicados de retentativa no Lark são descartados silenciosamente sem gerar respostas duplicadas no chat.

