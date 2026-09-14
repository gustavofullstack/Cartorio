# N8N Orphan Audit — 2026-07-18

## Escopo

Auditoria offline da árvore `infra/n8n-workflows/`, sem chamadas ao N8N live. O detector `scripts/n8n_orphan_detector.py` procurou referências em Markdown, `Makefile`, scripts Python e shell scripts, usando `pathlib.Path.rglob` e `ThreadPoolExecutor`.

## Resultado

| Métrica | Antes | Depois | Variação |
|---|---:|---:|---:|
| JSONs na raiz | 39 | 39 | 0 |
| JSONs recursivos | 58 | 58 | 0 |
| JSONs órfãos | 0 | 0 | 0 |
| Arquivos `*.bak` / `*.json.bak` | 0 | 0 | 0 |
| Tamanho dos JSONs na raiz | 431.395 bytes | 431.395 bytes | 0 KB |
| Tamanho dos JSONs recursivos | 616.592 bytes | 616.592 bytes | 0 KB |

O inventário canônico Wave 29 continua com **38 workflows válidos / 0 quebrados** conforme `docs/N8N_WF_INVENTORY_WAVE29_G7.md`. A raiz contém um export adicional, `30-chatwoot-status-sync-g8.json`, criado para G8.03.T3; ele não foi tratado como órfão porque possui referências em `PROGRESS.md` e em `backend/tests/test_n8n_chatwoot_status_workflow_g8.py`.

## Arquivos movidos

Nenhum arquivo foi movido para `archive-2026-07-18/`. O README do diretório registra a decisão e a razão da ausência de movimentação.

## Candidatos avaliados e justificativa

- Os 38 JSONs listados no inventário Wave 29 têm referências no inventário, no `INDEX.md`, em auditorias recentes, runbooks ou documentação operacional. Foram preservados.
- `30-chatwoot-status-sync-g8.json` tem referências de tarefa e teste estrutural G8.03.T3. Foi preservado mesmo estando fora do snapshot Wave 29.
- Os dois snapshots `backups/WF03_pre_chatwoot_2026-06-29.json` e `backups/WF12_pre_mcp_2026-06-29.json` são referenciados pelo README de backups, pelos runbooks T7/T8 e por documentação de sessão. Foram preservados para rollback.
- Os 17 JSONs de `backups/legacy-v1-2026-06-23/` são descritos pelo README local, pela política de retenção até 2026-09-30 e por documentação do archive G7. Foram preservados.
- `check_all_workflows.sh`, `import_all_to_n8n.sh` e `migra-workflows-v1-to-v2.sh` possuem referências em docs, runbooks e/ou sessões. Não são órfãos.
- `11_monitor_cartorio.js` e seu README documentam o health-check standalone associado ao workflow 11. Foram preservados.
- Os READMEs, runbooks, diagramas, auditorias e relatórios têm referências operacionais ou são documentação canônica. O `README.md` raiz da pasta é reconhecidamente antigo, mas sua atualização já está registrada como follow-up fora desta task; não foi removido.
- Não foram encontrados diretórios vazios antes da criação do archive desta auditoria.

## Evidências

```text
python3 scripts/n8n_orphan_detector.py --dry-run
58 linhas de dados CSV; 0 com is_orphan=true

python3 scripts/n8n_wf_inventory.py --json
39 valid / 0 broken na árvore raiz atual

make test-fast
3851 passed, 23 skipped, 49 deselected
```

A verificação de integridade ativa permanece offline: não houve `make n8n-list`, export remoto ou qualquer chamada ao domínio do N8N. Como nenhum arquivo foi movido, nenhum workflow ativo ou standby foi afetado.

**Modified by Gustavo Almeida — G8.12.T2**
