# Diagramas Mermaid dos Workflows N8N

> Indice de arquivos `.mmd` (renderizam em GitHub, VSCode, mkdocs-material).

## Indice

| # | Arquivo | Workflow | Tipo |
|---|---------|----------|------|
| 01 | [01-consulta-emolumento.mmd](01-consulta-emolumento.mmd) | Consulta Emolumento (v3) | webhook |
| 02 | [02-criar-protocolo.mmd](02-criar-protocolo.mmd) | Criar Protocolo (LGPD) | webhook |
| 03 | [03-handoff-human.mmd](03-handoff-human.mmd) | Handoff Humano (Chatwoot) | webhook |
| 11 | [11-monitor-cartorio.mmd](11-monitor-cartorio.mmd) | Monitor Cartorio | schedule+webhook |
| 12 | [12-chatbot-llm-mcp.mmd](12-chatbot-llm-mcp.mmd) | Chatbot LLM (MCP) | webhook |

## Como renderizar localmente

```bash
# Opcao 1: npx (zero install)
npx -p @mermaid-js/mermaid-cli mmdc -i diagrams/01-consulta-emolumento.mmd -o /tmp/wf01.svg

# Opcao 2: VSCode - instalar extensao "Markdown Preview Mermaid Support"

# Opcao 3: GitHub - basta comitar o .mmd; GH renderiza nativamente em .md
```
