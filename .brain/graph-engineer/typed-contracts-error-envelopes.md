# Contratos Tipados e Envelopes de Erro (RFC 7807) · Cartório Super Graph

**Data:** 2026-08-03  
**Task ID:** G1.32  
**Status:** APROVADO (TERRA + PRO Review)

## Evidência de Contratos e Erros Tipados

- **Contratos:** Pydantic v2 schemas em `app/schemas/`.
- **Envelopes de Erro:** RFC 7807 Problem Details (`app/middleware/problem_details.py` e `app/core/exceptions.py`).
- **Retorno Limpo:** Exceções capturadas com mensagens tipadas sem vazar tracebacks ou dados sensíveis ao cliente.

