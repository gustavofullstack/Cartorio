# Menor Privilégio de Scopes no Lark · Cartório Super Graph

**Data:** 2026-08-03  
**Task ID:** G2.05  
**Status:** APROVADO (PRO + LUNA Review)

## Evidência de Scopes Restritos

- **Eventos:** Restrito estritamente ao evento `im.message.receive_v1` (mensagens diretas e menções @ em grupos).
- **Permissões de Escrita / Leitura Sensível:** Bloqueadas (zero leitura de todos os canais, zero acesso a anexos/Drive/Docs, zero tokens de usuário).
- **MCP Server Profile:** Exposta exclusivamente a tool determinística `cartorio_calcular_emolumento`.

