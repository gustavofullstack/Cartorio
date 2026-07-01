# Legacy v1 Workflows — Arquivados em 2026-06-30

Pastas de workflows N8N da **versão 1** (legados do sprint 0-2) que foram
descontinuados por terem sido substituídos por versões v2/v3 oficiais ou
por não corresponderem ao estado ativo no servidor N8N remoto.

## Por que foram arquivados?

- **Duplicatas**: Cada workflow canônico tem 1-3 versões históricas (v1, v2, v3-fixed).
  Apenas a **versão canônica** (que bate 1:1 com o ID ativo em `flow.2notasudi.com.br`)
  deve ficar na raiz.
- **Substituídos**: Workflows v1 que foram **substituídos** por nós oficiais
  (`n8n-nodes-chatwoot`, `n8n-nodes-mcp`) ou por rewrite em cartorio-dev backend.
- **Morto/silencioso**: Workflows com 0 execuções em 30+ dias.

## Lista dos 17 arquivos arquivados

| # | Arquivo antigo | Substituído por |
|---|----------------|-----------------|
| 1 | `01-consulta-emolumento-v2.json` | `01-consulta-emolumento.json` (v3 com PII scrub + Audit) |
| 2 | `01-consulta-emolumento-v3-fixed.json` | `01-consulta-emolumento.json` (v3 limpo) |
| 3 | `03-handoff-human.json` | `03-handoff-human-chatwoot-v3-staging.json` (v3 com nodes oficiais Chatwoot) |
| 4 | `03-handoff-human-chatwoot.json` | mesmo acima (v2 HTTP puro) |
| 5 | `07-pesquisa-evolucao.json` | `07-pesquisa-satisfacao.json` (renomeado no v3) |
| 6 | `09-backup-status.json` | `21-backup-status-5min.json` (cron + alerta versionado) |
| 7 | `12-chatbot-llm-mcp.json` | `12-chatbot-llm-end-to-end.json` (produção) |
| 8 | `13-openclaw-chat-bridge.json` | descontinuado (openclaw agora faz fallback direto no backend) |
| 9 | `15-session-sync.json` | morto (0 exec em 30d) |
| 10 | `17-prospeccao-send-whatsapp.json` | consolidado em `16-prospeccao-enrichment.json` |
| 11 | `19-cliente-criado.json` | morto (substituído por webhook backend direto) |
| 12 | `20-protocolo-criado.json` | morto (substituído por webhook backend direto) |
| 13 | `23-lgpd-esqueci.json` | morto (LGPD esqueci agora é rota API, não workflow) |
| 14 | `27-welcome-first.json` | `27-welcome-first-time.json` (consentimento LGPD) |
| 15 | `32-alertas-telegram-pietra.json` | morto (Pietra desligada em 2026-06-15) |
| 16 | `evo-in-v2.json` | `evo-in.json` (canônico) |
| 17 | `evo-in-v3.json` | `evo-in.json` (canônico) |

## Política de retenção

- Estes arquivos **ficam aqui por 90 dias** (até 2026-09-30).
- Após 2026-09-30, podem ser removidos via `git rm`.
- Source of truth para reimportação: **remoto N8N** (`flow.2notasudi.com.br`).
- Para reverter alguma remoção prematura: `git log --diff-filter=D --summary | grep legacy-v1`.

## Rollback

Se precisar ressuscitar algum workflow:

```bash
# Reativar arquivo v1 manualmente
mv infra/n8n-workflows/backups/legacy-v1-2026-06-23/<X>.json infra/n8n-workflows/

# Importar via API:
N8N_KEY=$(grep N8N_API_KEY .secrets/api.env | cut -d= -f2-)
curl -X POST -H "X-N8N-API-KEY: $N8N_KEY" -H "Content-Type: application/json" \
  -d @infra/n8n-workflows/<X>.json \
  "https://flow.2notasudi.com.br/api/v1/workflows"
```

*Arquivado por Gustavo Almeida · 2026-06-30*
