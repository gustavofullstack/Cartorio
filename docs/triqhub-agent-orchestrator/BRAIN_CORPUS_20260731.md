# Orquestração BRAIN Corpus — 2026-07-31

`correlation_id`: `corr-brain-corpus-20260731`

## Goal

Inventariar, interpretar e implementar o pipeline BRAIN local, mantendo corpus,
PII e derivados em área privada e preservando Hermes/produção integralmente.

## Tarefas e agentes reais

| Tarefa | Dono | Dependências | Resultado local |
|---|---|---|---|
| Inventário/fidelidade | `cartorio-documentos` | nenhuma | 90/90 reconciliados; limites visuais registrados |
| Arquitetura BRAIN | `cartorio-dev` | inventário lógico | 3.087/3.087 unidades; identidades e cálculo endurecidos |
| Tribunal LGPD | `cartorio-lgpd` | ingest/HITL/trace | scrub canônico, `0700/0600`, ledger encadeado |
| Integração/QA | `codex-root` | três tarefas anteriores | snapshot privado determinístico e gates consolidados |

## Gates

- T0: pass local — escopo, parede de produção e aceite definidos.
- T1: pass local — ZIP/CRC/hashes/AV, 90 fontes e staging sem overwrite.
- T2: pass de padrões — zero resíduo canônico; PII contextual permanece HITL.
- T3: parcial — código/testes locais verdes; enforcement DB/RBAC não certificado.
- T4: não declarado — corpus não indexado nem publicado.
- T5: não declarado — nenhum E2E em canal live foi autorizado ou executado.

## Parede operacional

Nenhum serviço, LaunchAgent, container, webhook, canal ou configuração Hermes foi
consultado, alterado ou reiniciado. `automatic_promotion_allowed=false` e
`published_eligible=0` permanecem obrigatórios.
