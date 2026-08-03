# Retrieval Somente de Estado PUBLISHED · Cartório Super Graph

**Data:** 2026-08-03  
**Task ID:** G1.39  
**Status:** APROVADO (TERRA + PRO Review)

## Evidência de Retrieval Restrito

- **Lifecycle Enforcement:** `app/services/conhecimento_lifecycle.py` valida `e_consumivel(state)`.
- **Regra:** Somente registros com `state == "PUBLISHED"` são disponibilizados para consulta por RAG ou MCP tools. Registros em quarentena ou `PENDING_HUMAN_VALIDATION` são filtrados out.

