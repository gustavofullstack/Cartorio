# Schema Dual-Layer Regulatório vs Operacional · Cartório Super Graph

**Data:** 2026-08-03  
**Task ID:** G1.21  
**Status:** APROVADO (TERRA + PRO Review)

## Evidência de Schema Dual

- **Pydantic / SQLAlchemy Schema:**
  - `REGULATORY_TJMG`: `emolumento_bruto` + `tfj` = `valor_total_regulatorio`
  - `OPERATIONAL_POS_2NOTAS`: `emolumento_liquido` + `recompe` + `fundos` + `iss` + `tfj` = `valor_total_balcao`
- **Validação de Transparência:** Zero sobreposição silenciosa. Fonte e vigência explicitadas.

