# Revalidação de Extração das 3 Tabelas e 79 Linhas · Cartório Super Graph

**Data:** 2026-08-03  
**Task ID:** G1.19  
**Status:** APROVADO (FLASH + TERRA Review)

## Evidência de Extração e Validação de Preços

- **Tabelas Processadas:**
  - Geral: 29 atos
  - Escrituras com Conteúdo Financeiro: 25 faixas
  - Testamentos e Alterações: 25 faixas
- **Integridade Aritmética:**
  - 79/79 totais de balcão conferem aritmeticamente.
  - 78/79 valores de ISS conferem exatamente a 5% half-up.
  - 1/79 anomalia de arredondamento de R$ 0,01 identificada no código `1606-3` (R$ 154,64 vs R$ 154,65) e registrada em `PRICE_VALIDATION_2026.json` para validação fiscal humana (HG-02).
- **Camada Dual:** Confirmada a coexistência de `REGULATORY_TJMG` e `OPERATIONAL_POS_2NOTAS`.

