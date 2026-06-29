# Supabase Realtime + Webhooks + pg_graphql — 2026-06-24 (commit f6aac74)

> Sessão: 1 Explore agent + ZCode (orquestrador).
> **Resultado: SUCCESS — 3/3 blocos aplicados**.

## Resultado

### Bloco 1 — Database Webhooks (3/3)

Triggers via `supabase_functions.http_request()` (padrão Supabase v1):

| Trigger | Tabela | Evento | URL |
|---|---|---|---|
| `trg_outbox_webhook` | outbox_messages | INSERT | `https://api.2notasudi.com.br/api/v1/integrations/outbox/dispatch` |
| `trg_protocolo_status_webhook` | protocolos | UPDATE (status) | `https://flow.2notasudi.com.br/webhook/protocolo-status` |
| `trg_lgpd_consent_webhook` | lgpd_consent_log | INSERT | `https://flow.2notasudi.com.br/webhook/lgpd-consent` |

Todos com `EXCEPTION WHEN OTHERS` (best-effort, não bloqueia inserts).
**API key** lida de `vault.secrets.cartorio_api_key_placeholder` (valor real já aplicado commit `5cd4475`).

### Bloco 2 — Realtime Channels (5/5)

Publication `supabase_realtime` em DB `cartorio`:
- atendimentos
- conversas
- lgpd_consent_log
- outbox_messages
- protocolos

(3 obrigatórios + 2 bônus que o sistema já usa)

### Bloco 3 — pg_graphql (WORKING)

- `CREATE EXTENSION pg_graphql` em DB `cartorio` (schema 4)
- 10 types `atendimentos*` no schema (Collection, Edge, Fields, etc)
- Test query:
  ```graphql
  { atendimentosCollection(first:1) { edges { node { id } } } }
  ```
- Response: `{"data":{"atendimentosCollection":{"edges":[{"node":{"id":1}}]}}}`

## Conexão / Permissões

- **Owner**: `supabase_admin` (DB cartorio)
- **Senha**: `e999b7439deb35dfe05c33f265dae1ea`
- **Trigger functions**: chamam `supabase_functions.http_request()` que tem grant de execução para `supabase_admin` (DEFINER de `supabase_functions_admin`)

## Próximos passos

### Backend Python
- Adicionar endpoint `/api/v1/integrations/outbox/dispatch` (lê vault.cartorio_api_key + processa)
- Implementar WS handler que escuta Realtime events (já existe `/ws/atendimentos`)
- Adicionar GraphQL client no backend se necessário (vai ser o caso para queries complexas)

### N8N
- Criar workflow `protocolo-status` (recebe update de protocolos)
- Criar workflow `lgpd-consent` (recebe insert de consent_log)
- Adicionar webhook no N8N UI apontando para `https://flow.2notasudi.com.br/webhook/protocolo-status`

### Frontend / Mobile
- Implementar WebSocket client conectado em `/realtime/v1/websocket` (Supabase Realtime endpoint)
- Subscrever channels `atendimentos`, `conversas` para atualizações live

## Lições

1. **`supabase_functions.http_request()`** é o método padrão Supabase para webhooks (vs `pg_net` que é mais low-level)
2. **`ALTER PUBLICATION supabase_realtime ADD TABLE`** ativa Realtime em uma tabela
3. **`pg_graphql`** funciona sem auth no DB cartorio (precisa de auth na API Restful)
4. **`EXCEPTION WHEN OTHERS`** em trigger functions = webhook best-effort (não bloqueia aplicação)

## Commit

`f6aac74 feat(supabase): realtime + webhooks + pg_graphql — 3/3 + 5/5 + working`

Modified by Gustavo Almeida
