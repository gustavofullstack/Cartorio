# Validador Declarativo de Fórmulas · Cartório Super Graph

**Data:** 2026-08-03  
**Task ID:** G1.22  
**Status:** APROVADO (TERRA + PRO Review)

## Evidência de Validador de Fórmulas

- **Validação com Decimal:** Operações de emolumento e ISS utilizam `Decimal` com arredondamento estrito `ROUND_HALF_UP` a 2 casas decimais.
- **Fórmula Operacional:** `total = round(emolumento_liquido * 1.05 + recompe + fundos + tfj, 2)`.

