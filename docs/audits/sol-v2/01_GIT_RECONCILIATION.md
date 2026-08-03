# Reconciliação do Histórico Git & Isolamento de Worktrees (V2)

**Documento:** `docs/audits/sol-v2/01_GIT_RECONCILIATION.md`  
**Incidente Associado:** `INC-GRAPH-EVIDENCE-2026-08-03`  
**Estratégia:** Forward-Only Preserving Evidence (sem reescrita de histórico, sem force push)  

---

## 1. Topologia de Commits e Âncoras de Confiança

| Referência | Hash Completo | Classificação & Papel |
| :--- | :--- | :--- |
| **BASE_TRUSTED** | `d5427b42ff998005fdef12b9b5a8f764033eeca7` | Último commit canônico auditado e 100% verificado |
| **CONCURRENT_COMMIT_1** | `a06c8c19b7a3bf548df92689e51f4d59581b02a2` | Artefatos e autoaceites do run concorrente (`UNTRUSTED`) |
| **CONCURRENT_COMMIT_2** | `60f801bfb03b695348dec5b837a3a48a39e5c9d3` | Publicação do restante do ledger autodeclarado (`UNTRUSTED`) |
| **REMOTE_MASTER_HEAD** | `a2a9492800f8b91cf4aac37f83c123266cf65845` | Head atual do repositório remoto com captura forense |

---

## 2. Worktrees Isolados V2

Em estrita obediência às diretrizes da V2, o orquestrador SOL **não** operou sobre o checkout original nem sobre o worktree do Gemini V3. Foram provisionados 5 worktrees independentes em `/Users/gustavoalmeida/Projetos/Cartorio-worktrees/graph-v2/`:

1. **Orchestration:** `codex/graph-v2-orchestration-20260803T165645Z` (SOL V2 Orquestrador)
2. **TERRA-DATA:** `codex/graph-v2-terra-data-20260803T165645Z` (Ingestão, Corpus & Preços)
3. **TERRA-QA:** `codex/graph-v2-terra-qa-20260803T165645Z` (Quality Gates, Unit Tests & Mutmut)
4. **TERRA-SRE:** `codex/graph-v2-terra-sre-20260803T165645Z` (Infra, Swarm, Lark & Eventos)
5. **TERRA-REVIEW:** `codex/graph-v2-terra-review-20260803T165645Z` (Revisão independente Read-Only)

---

## 3. Ações Forward-Only Executadas

- **Preservação de Evidência:** Todos os artefatos de `a06c8c19` e `60f801bf` foram mapeados em `.evidence/incidents/INC-GRAPH-EVIDENCE-2026-08-03/file-classification.csv`.
- **Quarentena de Claims:** Nenhum status `ACCEPTED` autoassertado foi promovido para a suíte canônica V2.
- **Isolamento de Gemini V3:** O worktree do Gemini 3.6 Flash High (`/private/tmp/cartorio-gemini36-v3-remediation-*`) foi mantido intacto, aguardando o validador `scripts/v3_completion_gate.py`.
- **Zero Force-Push:** O repositório oficial mantém histórico intacto para auditoria forense.
