# Lesson 227 — G8.12.T2 N8N orphan audit — 2026-07-18

## Resultado

A auditoria foi executada offline. Não houve acesso ao N8N live e nenhum JSON foi removido ou movido.

| Medida | Antes | Depois |
|---|---:|---:|
| JSONs do inventário canônico Wave 29 | 38 | 38 |
| JSONs na raiz no filesystem | 39 | 39 |
| JSONs recursivos, incluindo backups | 58 | 58 |
| JSONs arquiváveis encontrados | 0 | 0 |
| Tamanho dos JSONs da raiz | 431.395 kB | 431.395 kB |
| Espaço economizado | 0 kB | 0 kB |

O 39º JSON da raiz é `30-chatwoot-status-sync-g8.json`, export G8.03.T3 fora do snapshot Wave 29. Ele está referenciado por `PROGRESS.md` e pelo teste estrutural `backend/tests/test_n8n_chatwoot_status_workflow_g8.py`; por isso foi preservado.

## Workflows protegidos do inventário canônico

`00-error-handler.json`, `01-consulta-emolumento.json`, `02-criar-protocolo.json`, `03-handoff-human-chatwoot-v3-staging.json`, `04-boas-vindas-lgpd.json`, `04-consulta-protocolo.json`, `05-agendamento.json`, `06-2-via-protocolo.json`, `07-pesquisa-satisfacao.json`, `08-audit-verify-diario.json`, `10-faq-bot.json`, `11-monitor-cartorio.json`, `12-chatbot-llm-end-to-end.json`, `14-opencode-go-fallback.json`, `16-prospeccao-enrichment.json`, `18-prospeccao-followup-d7.json`, `21-backup-status-5min.json`, `22-audit-verify-6h.json`, `22-mcp-server.json`, `23-cron-stale-detector.json`, `23-lgpd-esqueci-v2.json`, `24-daily-cleanup.json`, `24-retencao-diaria.json`, `25-metrics-collector.json`, `25-protocolo-concluido-pdf.json`, `26-alerta-critico.json`, `27-welcome-first-time.json`, `28-audit-snapshot.json`, `29-rate-limit-reset.json`, `30-health-deep-check.json`, `31-telegram-listener.json`, `33-whatsapp-qr-scan-helper.json`, `34-metrics-collector-5min.json`, `35-llm-fallback-3x.json`, `36-chatwoot-telegram-sync.json`, `37-agendamento-notarial-sync.json`, `38-emolumento-calculator.json` e `evo-in.json`.

Além deles, foram preservados `30-chatwoot-status-sync-g8.json`, os 19 JSONs de backup e os scripts/documentos com referências operacionais.

## Automação criada

- `scripts/n8n_orphan_detector.py`: scanner stdlib-only, CSV, modo `--dry-run` padrão e `--apply` com confirmação explícita.
- `Makefile`: target `n8n-orphans` executa o scanner via `uv run`.
- `infra/n8n-workflows/archive-2026-07-18/README.md`: registra que o archive está vazio por decisão de segurança.
- `docs/N8N_ORPHAN_AUDIT_2026-07-18.md`: evidências e justificativas.

## Gates

- Detector `--dry-run`: CSV legível, exit 0, 0 órfãos.
- Inventário offline: JSONs válidos, nenhum quebrado.
- Baseline `make test-fast`: 3851 passed, 23 skipped, 49 deselected.

**Modified by Gustavo Almeida — G8.12.T2**
