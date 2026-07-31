# Pipeline BRAIN — ConhecimentoInstitucional

**Data:** 2026-07-31  
**Estado:** implementação local fail-closed; **sem T4/T5**; **Hermes/prod intocados**.  
**Assinatura:** @Codex/brain_pipeline + revisão planejada @Grok/@cartorio-lgpd

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
| Quarentena | `.private/brain-ingest-quarantine/<batch>/` | Corpus bruto + AV |
| Ingest offline | `scripts/brain_corpus_ingest.py` | Extrai DOCX/ODT/PDF/TXT → derivados sanitizados |
| Classificação | `scripts/brain_corpus_classify.py` + `app/services/conhecimento_pipeline.py` | Tipo documental local (keywords) |
| Lifecycle | `app/services/conhecimento_lifecycle.py` | Máquina de estados fail-closed |
| HITL / publish | `app/services/conhecimento_validacao.py` | Aprovação humana + publicação/revogação |
| Cálculo | `app/services/conhecimento_institucional.py` | Gramática fechada Decimal (fixed/percentage/sum) |
| Classificador | `app/services/conhecimento_classificador.py` | Catálogo fechado de tipos notariais |
| Persistência | `app/models/conhecimento_institucional.py` + Alembic `0030` | Tabelas `knowledge_*` |
| Trace agentes | `scripts/brain_agent_trace.py` | Ledger append-only em `.evidence/brain-corpus/` |

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
| T0 escopo | parcial | Super plano + este doc |
| T1 integridade | parcial | 90 fontes, hash, AV PASS, extract 3083 units, `is_blocked=false` |
| T2 privacidade | parcial | PII scrub no ingest; classificador rejeita CPF bruto; derivados sem nomes |
| T3 controle | parcial | lifecycle + HITL + schema + testes unitários |
| T4 integração | **não declarado** | sem indexação/publicação em ambiente de atendimento |
| T5 operação | **não declarado** | sem consulta real no canal |

## Como rodar (somente local)

```bash
# 1) Ingestão offline (quarentena já populada)
uv run --project backend python scripts/brain_corpus_ingest.py
# stdout: {"is_blocked": false, "sources_discovered": 90, ...}

# 2) Classificação offline (lê só derived/)
uv run --project backend python scripts/brain_corpus_classify.py
# stdout: histogram de tipos + published_eligible=0

# 3) Trace de agente (metadados opacos)
uv run --project backend python scripts/brain_agent_trace.py \
  --agent codex --action classify --gate T3 \
  --result ok --evidence-ref derived/classification.sanitized.json

# 4) Testes do bounded context
cd backend && uv run pytest -q --no-cov \
  tests/test_conhecimento_*.py tests/test_brain_corpus_ingest.py
```

## HITL — como publicar (futuro, após T4 autorizado)

1. Escrevente/DPO revisa `classification.sanitized.json` (códigos + hashes).
2. `registrar_decisao_humana(... APPROVED ...)` por versão.
3. `publicar_versao(... APPROVED → PUBLISHED ...)`.
4. Somente então o BRAIN pode recuperar via `e_consumivel(PUBLISHED)`.
5. Rollback: `revogar_publicacao` ou flag de recuperação desligada — audit preservado.

## Rastreabilidade de agentes

| Agente | Papel nesta entrega |
|---|---|
| @Codex / implementer | lifecycle, classificador, pipeline, testes, docs |
| @Grok | liderança de revisão (parecer de risco — pendente sign-off) |
| @Terra | schema/RBAC/PII (modelo + migration 0030 pré-existente) |
| @Kimi | execução local assistida (opcional) |
| @AGY | coordenação preservada; sem takeover de runtime |
| Hermes | **intocado** — runtime prod preservado |

Ledger: `.evidence/brain-corpus/agent-trace.jsonl` (append-only, sem PII).

## PII e segredos

- Corpus bruto: somente `.private/` (gitignored).
- Ingest substitui CPF/CNPJ/email/telefone/CEP/RG e remove URLs.
- Classificador recusa texto com CPF formatado cru.
- Trace/agent ledger bloqueia padrões de chave (`sk-`, `ghp_`, etc.) e CPF/email.
- Cálculos usam só `Decimal` — sem `eval`, float ou I/O.

## Critério de não-regressão

- `automatic_promotion_allowed` permanece `false` no manifest e no classify.
- `published_eligible == 0` após classify offline.
- Tentativa de CLASSIFIED→PUBLISHED falha.
- Tentativa de calcular regra não-PUBLISHED falha.
- Coverage gate do backend permanece ≥ 90% no CI completo.

---

Próximo passo autorizado (fora desta entrega): revisão HITL humana + sign-off
`cartorio-lgpd` antes de qualquer merge que toque publicação ou recuperação live.
