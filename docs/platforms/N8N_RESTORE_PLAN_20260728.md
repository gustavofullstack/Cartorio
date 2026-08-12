# Plano seguro de restauração do n8n — 2026-07-28

## Estado comprovado

- `cartorio_n8n` e `cartorio_n8n-runner`: `1/1`; `/healthz`: HTTP 200.
- Snapshot pré-restore validado:
  `n8n_pre_restore_20260728T224654Z.dump` (`375.941` bytes).
- Banco atual `cartorio_n8n-db`: `39` workflows importados, `0` ativos,
  `0` execuções, `0` credenciais e `0` API keys.
- A variável `N8N_API_KEY` ainda existe em `cartorio_system-api`, mas não
  corresponde a uma chave ativa no banco. As APIs de workflows e execuções
  rejeitam a auditoria.
- O backup diário exportou os 39 workflows pelo CLI interno, releu o JSON,
  passou `gzip -t` e preservou os dumps PostgreSQL.

Os workflows estão restaurados como inventário inerte. Isso ainda não é
automação funcional: nenhum trigger foi publicado.

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

Na importação de 28/07, os 41 arquivos canônicos foram auditados. Vinte tinham
conexões gravadas por ID em vez do nome do node, incompatíveis com n8n 2.32.5.
Uma cópia portátil de staging mapeou IDs para nomes, removeu metadados de
histórico/relacionamentos e forçou `active=false`. Dois workflows ambíguos foram
excluídos:

- `03-handoff-human-chatwoot-v3-staging.json`: nomes de nodes duplicados;
- `23-lgpd-esqueci-v2.json`: nodes e IDs de deduplicação repetidos várias vezes.

Os 39 restantes foram importados atomicamente. Duas tentativas inválidas
falharam com rollback integral e mantiveram o banco em zero antes do sucesso.

## Sequência de restauração

1. Preservar o snapshot pré-restore e o backup pós-restore.
2. Revisar cada workflow atualmente inativo:
   `active=true`, trigger, webhook, destino e referência de credencial.
3. Corrigir na fonte os dois JSONs excluídos antes de qualquer nova importação.
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

- `workflow_entity = 39`, `active = 0`, `execution_entity = 0` — aprovado.
- APIs `/workflows` e `/executions` autenticadas por chave de auditoria.
- Nenhum workflow de Chatwoot/OpenClaw ativo enquanto esses serviços estiverem
  aposentados.
- Nenhum workflow WhatsApp ativo antes de `session_connected=true`.
- Export dos 39 workflows incluído no backup e JSON relido — aprovado.
