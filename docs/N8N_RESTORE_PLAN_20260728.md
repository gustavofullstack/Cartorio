# Plano seguro de restauração do n8n — 2026-07-28

## Estado comprovado

- `cartorio_n8n` e `cartorio_n8n-runner`: `1/1`; `/healthz`: HTTP 200.
- Banco atual `cartorio_n8n-db`: `0` workflows, `0` execuções, `0`
  credenciais e `0` API keys.
- A variável `N8N_API_KEY` ainda existe em `cartorio_system-api`, mas não
  corresponde a uma chave ativa no banco. As APIs de workflows e execuções
  rejeitam a auditoria.
- O backup diário dos bancos voltou a funcionar. A exportação n8n por API
  falhou corretamente sem invalidar os dumps PostgreSQL.

Isso é disponibilidade de processo, não recuperação funcional do n8n.

## Inventário versionado

Leitura recursiva de `infra/n8n-workflows/`:

| Evidência | Quantidade |
| --- | ---: |
| JSONs de workflow válidos | 61 |
| Marcados `active=true` no arquivo | 41 |
| Cópias em diretórios `backups/` | 20 |
| Referenciam Chatwoot | 19 |
| Referenciam OpenClaw | 4 |
| Referenciam WhatsApp | 27 |
| Referenciam Telegram | 9 |
| Contêm referências a credenciais n8n | 8 |

As categorias se sobrepõem. Não importar todos os 61: isso duplicaria backups
e poderia reativar fluxos ligados a Chatwoot/OpenClaw aposentados ou ao
WhatsApp ainda desconectado.

## Sequência de restauração

1. Preservar um dump do banco n8n vazio atual e registrar o digest.
2. Selecionar somente workflows canônicos fora de `backups/`; revisar cada
   `active=true`, trigger, webhook, destino e referência de credencial.
3. Importar inicialmente como inativos. Não executar nem publicar durante a
   importação.
4. Recriar credenciais exclusivamente pela UI/secret manager; nunca inserir API
   key ou credential blob diretamente no Postgres.
5. Criar pela UI uma API key dedicada à observabilidade, de menor privilégio,
   e atualizar o secret manager consumido pelo `cartorio_system-api`.
6. Executar lint/teste de cada workflow com dados sintéticos.
7. Ativar um workflow por vez e provar trigger → execução → efeito esperado →
   auditoria, com rollback conhecido.
8. Somente depois habilitar export automático. O backup usa API quando
   autorizada e CLI interno como contingência.

## Gates

- `workflow_entity > 0` e inventário reconciliado sem duplicatas.
- APIs `/workflows` e `/executions` autenticadas por chave de auditoria.
- Nenhum workflow de Chatwoot/OpenClaw ativo enquanto esses serviços estiverem
  aposentados.
- Nenhum workflow WhatsApp ativo antes de `session_connected=true`.
- Export do n8n incluído no backup e JSON relido com sucesso.
