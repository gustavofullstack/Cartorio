# Postman Guide — Cartório API

Importar collection: **Postman → Import → Upload Files** → selecione `docs/POSTMAN_COLLECTION.json`.

## Variáveis
| Var | Valor | Onde |
|---|---|---|
| `cartorio_api_key` | `<64hex>` (gerado com `openssl rand -hex 32`) | Collection → Variables |
| `base_url` | `https://api.2notasudi.com.br` | já setado |

Auth padrão: **API Key** no header `X-API-Key` (editável na collection root).

## Top 10 endpoints
1. `GET /health/llm` — health do LLM
2. `GET /atendimento/list-active` — atendimentos ativos
3. `GET /protocolo/list` — protocolos
4. `GET /emolumento/calcular` — cálculo de emolumentos
5. `GET /cliente/1/lgpd/anonimizar` — anonimização LGPD
6. `POST /cliente/criar` — criar cliente
7. `GET /audit/logs` — logs auditoria
8. `POST /telegram/webhook` — webhook Telegram
9. `POST /integrations/evolution/send` — enviar msg WhatsApp
10. `GET /meta/versao` — versão da API

## Exemplo rápido
```
GET https://api.2notasudi.com.br/api/v1/health/llm
Header: X-API-Key: <sua_chave>
```
Resposta esperada: `200 {"status":"ok","model":"..."}`.

## Troubleshooting
- **401 Unauthorized**: `X-API-Key` ausente ou errada — gere nova com `openssl rand -hex 32` e atualize no painel admin.
- **404 Not Found**: endpoint/path não existe — confira `https://api.2notasudi.com.br/openapi.json`.
- **422 Unprocessable Entity**: payload inválido — valide JSON com `jq` antes de enviar.
- **429 Too Many Requests**: rate limit — aguarde 60s ou use header `Idempotency-Key` em POSTs.

## Webhooks (HMAC)
Webhooks externos usam `X-Signature: sha256=<hmac>`, não `X-API-Key`. Configure no `.env` do produtor.
