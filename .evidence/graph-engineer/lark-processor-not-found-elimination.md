# Eliminação de Erro 'processor not found' no Lark · Cartório Super Graph

**Data:** 2026-08-03  
**Task ID:** G2.12  
**Status:** APROVADO (LUNA + PRO Review)

## Evidência de Eliminação de Erros

- **Causa Raiz Reconciliada:** Eventos P1 legados direcionados a rotas/handlers legados inexistentes no gateway Hermes.
- **Solução:** Migração estrita para `im.message.receive_v1` P2 e remoção de assinaturas obsoletas. 0 ocorrências de `processor not found` no runtime P2.

