# Perfil público MCP

`MCP_PUBLIC_API_KEY` é uma credencial independente de `MCP_API_KEY`. No endpoint
`/mcp`, ela permite somente `tools/list` com `cartorio_calcular_emolumento` e a
chamada dessa tool. Qualquer outra `tools/call` retorna `403`; ausência,
formato inválido ou credencial incorreta não recebe acesso.

O perfil interno continua sendo destinado exclusivamente a integrações controladas.
Não reutilize a chave pública como credencial interna: uma configuração igual falha
o perfil público. A publicação, rotação e qualquer ampliação de escopo exigem
revisão `cartorio-lgpd` e validação E2E autorizada.
