# Execução BRAIN (offline) — Lote `2026-07-31-ce236ba32b01-run-batch`

## Escopo
- Arquivo origem: `/Users/gustavoalmeida/Downloads/Cartorio-20260731T144042Z-1-001.zip`
- Objetivo: extrair, inventariar, classificar e preparar fila HITL em modo **offline**, **fail-closed** e sem exposição de PII.
- Restrições respeitadas: runtime Hermes e serviços live não foram reiniciados/alterados.

## Resultado operacional
- **Batch criado**: `.private/brain-ingest-quarantine/2026-07-31-ce236ba32b01-run-batch`
- **Arquivos no lote**: 90
- **Tamanho não compactado total**: 17.505.807 bytes

### 1) Stage do ZIP
- Comando: `python scripts/brain_corpus_stage_zip.py`
- SHA256 do ZIP: `ce236ba32b01e11139052867d189ce76ce14bf9d9030d9a24512ebdba2252efb`
- `manifest`: `MANIFEST.private.json`

### 2) Ingestão de origem para derivados sanitizados
- Comando: `python scripts/brain_corpus_ingest.py`
- Artefato: `.private/brain-ingest-quarantine/2026-07-31-ce236ba32b01-run-batch/derived/manifest.sanitized.json`
- **is_blocked**: `false`
- `sources_discovered`: 90
- `sources_extracted`: 90
- `units_written`: 3.087

### 3) Classificação offline
- Comando: `python scripts/brain_corpus_classify.py`
- Artefato: `.private/brain-ingest-quarantine/2026-07-31-ce236ba32b01-run-batch/derived/classification.sanitized.json`
- **is_blocked**: `false`
- `automatic_promotion_allowed`: `false`
- `published_eligible`: `0`
- `sources_classified`: 90

#### Distribuição por tipo
- ATA_NOTARIAL: 1
- DIVORCIO_UNIAO_ESTAVEL: 3
- EMOLUMENTOS: 1
- ESCRITURA_COMPRA_VENDA: 1
- ESTREMACAO: 4
- INVENTARIO_PARTILHA: 5
- LISTA_DOCUMENTOS: 5
- NORMATIVO_CNJ: 5
- OUTROS_ATOS: 26
- PROCURACAO: 8
- RECONHECIMENTO_FIRMA: 3
- RECONHECIMENTO_PATERNIDADE: 1
- SUCESSOES_HERANCA: 5
- TESTAMENTO: 18
- USUCAPIAO: 4

### 4) Geração de fila HITL
- Comando: `python scripts/brain_corpus_hitl_queue.py`
- Artefato: `.private/brain-ingest-quarantine/2026-07-31-ce236ba32b01-run-batch/derived/hitl_queue.sanitized.json`
- **is_blocked**: `false`
- `state`: `PENDING_HUMAN_VALIDATION`
- `total_items`: 90
- `ambiguous`: 16
- `ocr_flagged`: 1
- `published_eligible`: `0`
- `automatic_promotion_allowed`: `false`

### 5) Rastreabilidade por agente
- Ledger: `.evidence/brain-corpus/agent-trace.jsonl`
- Entradas adicionadas nesta execução: 5
- Linhas totais no ledger: 15
- Ações registradas: `extract`, `classify`, `review`, `test`, `document`
- Agentes usados: `cartorio-documentos`, `cartorio-dev`, `cartorio-lgpd`, `codex-root`

### 6) Validação de testes
- Comando: `uv run pytest tests/test_brain_corpus_ingest.py tests/test_conhecimento_pipeline.py tests/test_brain_agent_trace.py -q --no-cov`
- Resultado: `32 passed`
- Nota: execução com cobertura padrão (`--cov`) falha por threshold global 90% do projeto, não por regressão dos fluxos BRAIN.

## Evidências adicionais
- JSON de resumo técnico: `.evidence/brain-corpus/goal-2026-07-31-ce236ba32b01-run-batch.json`
