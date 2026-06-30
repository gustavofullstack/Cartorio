# T7 — Ativar n8n-nodes-mcp em WF12 (chatbot-llm)

## Status: PRONTO PRA EXECUTAR (verificar package install)

**Contexto:**
- `12-chatbot-llm-end-to-end.json` (ATIVO): HTTP Request → `api.2notasudi.com.br/api/v1/integrations/opencode/test`
- `12-chatbot-llm-mcp.json` (PARALELO): usa `n8n-nodes-mcp.mcpClient` com tool `cartorio_chatbot_responder`

**PASSO 1 — Verificar se n8n-nodes-mcp está instalado**

No N8N UI: Settings → Community Nodes
Se `@nicktorn89/n8n-nodes-mcp` não aparecer → instalar.

**PASSO 2 — Configurar MCP Server URL no N8N**

O MCP server é o próprio N8N (n8n acts as MCP client). Configurar:
- Settings → MCP → Add Server
- Server URL: `http://localhost:5678` (ou URL interna do N8N)
- Auth: same credentials as N8N

**PASSO 3 — Comparar parâmetros antes de migrar**

| Parâmetro | HTTP Request (atual) | MCP node (mcp.json) |
|---|---|---|
| prompt | `{{ $json.scrubbed }}` | `{{ $json.scrubbed }}` |
| model | `deepseek-v4-flash-free` | `deepseek-v4-flash` |
| consent_granted | sim | sim |
| use_fallback | `true` | ❌ NÃO tem |
| session_id | `n8n-{{ $json.session_id }}` | ❌ NÃO tem |

**ATENÇÃO:** O HTTP Request tem `use_fallback: true` e `session_id`. O MCP node não expõe esses parâmetros diretamente. Se o chatbot precisar de fallback ou session management, KEEP HTTP Request como está.

**PASSO 4 — Se gap acima for aceitável: migrar**

1. Desativar WF12 antes de editar
2. Backup JSON atual
3. Substituir node HTTP Request pelo MCP node de `12-chatbot-llm-mcp.json`
4. Testar: mandar mensagem real → verificar resposta LLM
5. Reativar

**PASSO 5 — Se gap for problemático: manter HTTP Request**

O HTTP Request atual funciona. O MCP node é "nice to have" mas não crítico se:
- O endpoint `/api/v1/integrations/opencode/test` está estável
- O rate limit é aceitável

**DECISÃO:** Gustavo decide. Se quiser ativar MCP, fazer em staging primeiro.

---

## Alternativa: Ativar WF12-mcp como PRINCIPAL

O `12-chatbot-llm-mcp.json` já está pronto com o MCP node. Pode ser importado no N8N como workflow separado e ativado como "v2" do chatbot.用户提供中文：

*Modified by Gustavo Almeida*
*T7 Sprint 4 — M2.7 Pietra (mvs_95c881...)*
