# Migration Guide - Workflows N8N v1 -> v2

> Guia para upgrade de versao major (breaking change) em workflows N8N.
> Mantido por `cartorio-n8n` rein.

## Politica de Versionamento (semver)

- **major** (v1 -> v2): breaking change, requer MIGRATION
- **minor** (v1.0 -> v1.1): adicao nao-breaking
- **patch** (v1.0.0 -> v1.0.1): bugfix

## Breaking Changes Conhecidas

| Workflow | De -> Para | Trigger mudou? | Auth mudou? | Schema mudou? | Migration necessaria |
|----------|-----------|----------------|-------------|---------------|---------------------|
| 00-error-handler | v3 -> v4 | nao | sim (env-only) | nao | setar env CARTORIO_API_KEY |
| 03-handoff-human | v1 -> v2 | nao | sim (credencial renomeada) | sim (conversation_id opcional) | recriar credencial Chatwoot |
| 12-chatbot-llm | v1 -> v2 | nao | nao | sim (tool MCP) | subir backend MCP (wf22) |
| 01-consulta-emolumento | v1 -> v3 | nao | nao | sim (PII + audit) | re-importar WF |
| 27-welcome-first-time | v1 -> v2 (27-welcome-first) | nao | nao | sim (adiciona respond) | re-importar WF |

## Script de Migracao Automatica

`migra-workflows-v1-to-v2.sh` aplica migracoes idempotentes:
1. Re-export workflow do repo
2. Cria novo workflow no N8N (POST)
3. Ativa novo workflow
4. Desativa v1 antigo
5. Arquiva v1 antigo (soft delete)

## Pre-Migration Checklist

- [ ] 1. Backup completo: `bash scripts/backup_n8n_workflows.sh`
- [ ] 2. Conferir credenciais N8N: `Chatwoot API`, `cartorio-api-key`, `evolution-api-cartorio`
- [ ] 3. Ler CHANGELOG.md para entender diff
- [ ] 4. Validar env vars no N8N: `CARTORIO_API_KEY`, `OPENCODE_GO_KEY`, etc
- [ ] 5. Smoke test: `python3 scripts/n8n_workflow_test.py` (gera report)
- [ ] 6. Verificar webhook URLs (Evolution apontando para v2 path)
- [ ] 7. Subir backend MCP se migrar wf12 -> v2
- [ ] 8. Rodar `migra-workflows-v1-to-v2.sh` em horario de baixo trafego (00:00-04:00 BRT)

## Pos-Migration Checklist

- [ ] 1. Verificar execution history no N8N (ultimas 24h sem erro)
- [ ] 2. Conferir `wf11-monitor-cartorio` reports "All OK"
- [ ] 3. Testar webhook com curl: ver `README.md` secao "Como importar"
- [ ] 4. Re-executar test runner: `python3 scripts/n8n_workflow_test.py`
- [ ] 5. Verificar `docs/n8n-workflows-test-report.md` - zero FAIL/ERROR
- [ ] 6. Conferir audit log: `wf08-audit-verify-diario` (cron 03:30)
- [ ] 7. Verificar Chatwoot nao recebeu alertas spurios
- [ ] 8. Conferir metricas Prometheus: `wf25-metrics-collector`
- [ ] 9. Snapshot S3 foi gerado: `wf28-audit-snapshot` (cron 04:00)
- [ ] 10. Commit do CHANGELOG atualizado + tag `n8n-v2.0.0`
- [ ] 11. Comunicar stakeholders via Chatwoot `#cartorio-tech`
- [ ] 12. Atualizar docs/CHANGELOG.md raiz

---

Modified by ZCode/Mavis + Gustavo Almeida — 2026-06-24
