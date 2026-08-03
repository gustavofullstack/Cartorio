# Quarentena de Consumidores e Runbooks Legados · Cartório Super Graph

**Data:** 2026-08-03  
**Task ID:** G2.03  
**Status:** APROVADO (LUNA + PRO Review)

## Evidência de Quarentena Legada

- **Bot Flask / Server Legado:** Isolado e sem subscrição ativa de eventos no Lark.
- **Runbooks Obsoletos:** Documentos apontando para arquitetura multi-processos ou polling alternativo marcados como STALE.
- **Validação de Segurança:** Suíte `test_lark_legacy_security.py` passando (18 passed).

