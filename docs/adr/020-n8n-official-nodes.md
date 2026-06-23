# ADR-020: Uso preferencial de nodes oficiais N8N (community nodes)

**Data:** 2026-06-23
**Status:** APROVADA (Sprint 3, Bloco 5)
**Autor:** ZCode (Mavis)

## Contexto

O projeto tem 4 community nodes N8N instalados mas **nenhum** estava sendo usado
ativamente (ver Sprint 0 spec §3 "Notable absence"):

- `n8n-nodes-chatwoot` v1.0.2 — instalado, não usado (workflow #03 usava HTTP ad-hoc com inbox URL fallback)
- `n8n-nodes-minio` v1.3.0 — instalado, não usado
- `n8n-nodes-evolution-api` v1.0.4 — instalado, não usado
- `n8n-nodes-mcp` v0.1.37 — instalado, não usado (workflow #12 usava HTTP ad-hoc)
- `n8n-nodes-pdfkit` v0.1.2 — instalado, não usado

Resultado: integrações dependem de chamadas `httpRequest` frágeis, sem tipagem,
sem retry nativo, sem schema validation, e sem padronização.

## Decisão

**Preferência por nodes oficiais/community nodes** quando:

1. O node está **instalado** no N8N (verificado em `~/.n8n/nodes/`)
2. Cobre **≥80%** do caso de uso (sem precisar de workarounds)
3. O node tem **versionamento ativo** (release nos últimos 6 meses)

**Manter `httpRequest` ad-hoc** quando:

1. Não existe node community oficial
2. O node é deprecated/abandonado
3. O node requer credentials extras que não temos (ex: node Evolution
   precisa de URL + apikey locais; já temos via env, então podemos usar)

## Aplicação no Sprint 3

| Workflow | Antes (httpRequest) | Depois (Bloco 5) | Benefício |
|----------|---------------------|------------------|-----------|
| #12 (chatbot LLM) | HTTP: OpenCode-Go | `n8n-nodes-mcp` (cartorio_chatbot_responder) | Protocolo MCP padronizado, retry nativo, schema validation |
| #03 (handoff humano) | HTTP: Chatwoot com inbox URL fallback | `n8n-nodes-chatwoot` (criar conversation + message) | Auth oficial, retries, suporte a multi-inbox |

## Consequências

**Positivas**
- Reduz superfície de manutenção: cada node é mantido pelo vendor
- Padroniza erros e timeouts
- Permite uso de N8N UI pra debugar (em vez de curl manual)
- Facilita onboarding de novos devs (idioma N8N, não httpRequest ad-hoc)

**Negativas**
- Vendor lock-in parcial (se um node quebrar, dependemos do mantenedor)
- Upgrade de node pode quebrar workflows (mitigação: testar em staging)
- Alguns nodes são "thin wrappers" em torno de HTTP (não muito ganho)
- Necessidade de credentials no N8N (não só env vars)

## Não-objetivos

- Migrar **TODOS** os 16 workflows (apenas os com nó community equivalente)
- Adicionar novos community nodes (já temos o que precisa)
- Escrever nodes custom em TypeScript (overkill p/ 4 integrações)

## Workflows do Sprint 3 Bloco 5

- `12-chatbot-llm-mcp.json` (novo, substitui `12-chatbot-llm-end-to-end.json`)
- `03-handoff-human-chatwoot.json` (novo, substitui `03-handoff-human.json`)

Os workflows antigos ficam no repo como referência histórica; Gustavo pode
decidir via N8N UI qual fica ativo.

## Referências

- N8N community nodes registry: https://www.npmjs.com/search?q=n8n-nodes
- MCP protocol 2025-03-26
- Sprint 0 spec §3 ("notable absence" de nodes usados)
