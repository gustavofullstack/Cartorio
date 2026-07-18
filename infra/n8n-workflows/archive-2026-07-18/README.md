# N8N archive — 2026-07-18

Este diretório foi criado pela auditoria G8.12.T2 para receber exports órfãos identificados offline.

## Resultado

Nenhum arquivo foi movido. O detector encontrou 58 JSONs recursivos e todos possuem ao menos uma referência em documentação, Makefile, scripts, shell scripts ou testes Python. Não havia arquivos `*.bak` ou `*.json.bak`.

Os 38 JSONs do inventário canônico Wave 29 foram preservados. O export adicional `30-chatwoot-status-sync-g8.json` também foi preservado porque é referenciado por `PROGRESS.md` e por testes de estrutura G8.03.T3. Os snapshots e legados existentes em `backups/` permanecem em seus diretórios com seus READMEs e runbooks de rollback.

A ausência de movimentações é intencional: sem acesso ao N8N live, qualquer arquivo sem confirmação documental suficiente permanece preservado.

**Modified by Gustavo Almeida — G8.12.T2**
