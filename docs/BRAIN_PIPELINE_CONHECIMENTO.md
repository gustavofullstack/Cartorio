# Pipeline BRAIN — ConhecimentoInstitucional

**Data:** 2026-07-31  
**Estado:** implementação local fail-closed; **sem T4/T5**; **Hermes/prod intocados**.  
**Correlação:** `corr-brain-corpus-20260731`

## Objetivo

Incorporar conhecimento institucional (minutas, checklists, tabelas, normativos)
ao BRAIN de forma rastreável, reversível e LGPD-by-design. O corpus bruto
permanece em `.private/` (gitignored). Somente metadados, hashes e derivados
sanitizados participam do pipeline.

## O que NÃO fazemos nesta entrega

- Não altera, reinicia ou reconfigura Hermes, Evolution, N8N, Chatwoot ou API live.
- Não publica conteúdo no índice de recuperação do BRAIN (`published_eligible=0`).
- Não envia texto bruto a LLM pública, rede externa ou storage fora da quarentena.
- Não promove automaticamente (`automatic_promotion_allowed=false` enforçado).

## Componentes

| Camada | Path | Função |
|---|---|---|
| Staging ZIP | `scripts/brain_corpus_stage_zip.py` | Valida e extrai atomicamente sem overwrite |
| Quarentena | `.private/brain-ingest-quarantine/<batch>/` | Corpus bruto + AV |
| Ingest offline | `scripts/brain_corpus_ingest.py` | Extrai DOCX/ODT/PDF/TXT → derivados sanitizados |
| Classificação | `scripts/brain_corpus_classify.py` + `app/services/conhecimento_pipeline.py` | Tipo documental local (keywords) |
| Lifecycle | `app/services/conhecimento_lifecycle.py` | Máquina de estados fail-closed |
| HITL / publish | `app/services/conhecimento_validacao.py` | Aprovação humana + publicação/revogação |
| Cálculo | `app/services/conhecimento_institucional.py` | Gramática fechada Decimal (fixed/percentage/sum) |
| Classificador | `app/services/conhecimento_classificador.py` | Catálogo fechado de tipos notariais |
| Persistência | `app/models/conhecimento_institucional.py` + Alembic `0030` | Tabelas `knowledge_*` |
| Trace agentes | `scripts/brain_agent_trace.py` | Ledger encadeado e tamper-evident em `.evidence/brain-corpus/` |

## Ciclo de vida

```text
INGESTED
  → EXTRACTED
  → CLASSIFIED
  → PENDING_HUMAN_VALIDATION   ← ponto atual do corpus 2026-07-31
  → APPROVED                   ← somente humano
  → PUBLISHED                  ← único estado consumível pelo BRAIN
  → SUPERSEDED | REVOKED
```

Qualquer salto (ex.: CLASSIFIED → PUBLISHED) é rejeitado. Terminais
(REJECTED/REVOKED/SUPERSEDED) não reabrem.

## Gates T0–T5 (estado factual)

| Gate | Estado | Evidência |
|---|---|---|
| T0 escopo | **pass local** | objetivo, limites, donos, tarefas e aceites registrados |
| T1 integridade | **pass local** | 90/90 hashes, CRC, AV local `rc=0`, sem traversal/link/criptografia |
| T2 privacidade | **pass de padrões / HITL contextual** | 3.087 units, resíduo canônico 0, `0700/0600`; nomes/endereço livre exigem humano |
| T3 controle | **parcial** | lifecycle/HITL/identidades/cálculo/testes verdes; enforcement DB/RBAC ainda pendente |
| T4 integração | **não declarado** | sem indexação/publicação em ambiente de atendimento |
| T5 operação | **não declarado** | sem consulta real no canal |

## Como rodar (somente local)

```bash
# 0) Validar staging existente sem sobrescrever
uv run --project backend python scripts/brain_corpus_stage_zip.py \
  /caminho/privado/corpus.zip --destination \
  .private/brain-ingest-quarantine/<batch>

# 1) Ingestão offline (quarentena já populada)
uv run --project backend python scripts/brain_corpus_ingest.py
# stdout: {"is_blocked": false, "sources_discovered": 90, ...}

# 2) Classificação offline (lê só derived/)
uv run --project backend python scripts/brain_corpus_classify.py
# stdout: histogram de tipos + published_eligible=0

# 3) Trace de agente (metadados opacos)
uv run --project backend python scripts/brain_agent_trace.py \
  --agent codex-root --action classify --gate T3 \
  --result ok --evidence-ref derived/classification.sanitized.json

# 4) Testes do bounded context
cd backend && uv run pytest -q --no-cov \
  tests/test_conhecimento_*.py tests/test_brain_corpus_ingest.py
```

## HITL — publicação bloqueada nesta entrega

1. Escrevente/DPO revisa `classification.sanitized.json` (códigos + hashes).
2. Registrar aprovação humana da versão e sign-off separado DPO/LGPD.
3. `publicar_versao` exige as duas decisões, `t4_authorized=true` e ambiente `isolated`.
4. Somente então o BRAIN pode recuperar via `e_consumivel(PUBLISHED)`.
5. Rollback: `revogar_publicacao` ou flag de recuperação desligada — audit preservado.

## Rastreabilidade de agentes

| Agente | Papel nesta entrega |
|---|---|
| `codex-root` | integração, staging, publicação fail-closed, testes e docs |
| `cartorio-documentos` | reconciliação 90/90 e auditoria de fidelidade estrutural |
| `cartorio-dev` | classificador integral, identidade, schema lógico e cálculo |
| `cartorio-lgpd` | scrub canônico, permissões, HITL, trace e tribunal independente |
| Hermes | **intocado** — runtime prod preservado |

Ledger: `.evidence/brain-corpus/agent-trace.jsonl` (hash-chain, `flock`, `fsync`, `0600`).

## PII e segredos

- Corpus bruto: somente `.private/` (gitignored).
- Ingest aplica máscaras específicas e o scrubber canônico completo; remove URLs.
- A varredura final encontrou zero padrões canônicos residuais nas 3.087 unidades.
- Nome e endereço livre não são decidíveis só por regex; o corpus continua privado e sob HITL.
- Classificador recusa texto com CPF formatado cru.
- Trace bloqueia PII, paths e padrões de segredo, inclusive códigos OAuth.
- Cálculos usam só `Decimal` — sem `eval`, float ou I/O.

## Critério de não-regressão

- `automatic_promotion_allowed` permanece `false` no manifest e no classify.
- `published_eligible == 0` após classify offline.
- Tentativa de CLASSIFIED→PUBLISHED falha.
- Tentativa de calcular regra não-PUBLISHED falha.
- Coverage gate do backend permanece ≥ 90% no CI completo.

---

## Fila HITL

```bash
uv run --project backend python scripts/brain_corpus_hitl_queue.py
```

Gera `derived/hitl_queue.sanitized.json` (prioridade P0–P3, sem texto/PII).
Checklist operacional: `docs/BRAIN_HITL_CHECKLIST.md`.

Próximo passo autorizado: revisão HITL humana + sign-off `cartorio-lgpd`
antes de qualquer publicação ou recuperação live (T4/T5).
