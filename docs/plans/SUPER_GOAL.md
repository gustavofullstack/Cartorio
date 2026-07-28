# SUPER GOAL — 2026-07-27 (Sessão de Fechamento Operacional)

> **Origem:** consolidação da pasted-text #1 (IMENSAGER master prompt), pasted-text #2 (P0 IDENTITY_HERMES_LEAK investigation), AGENTS.md, STATUS.md, GOALS.md, .brain/memory/2026-07-27.md e output da Fase 1 (git reconciliation).
>
> **Modified by Gustavo Almeida · 2026-07-27**

---

## 🎯 SUPER META ÚNICA

**Achar e zerar todos os blockers Agent-doable que impedem o canal iMessage (PIETRA · MINIMAX M3 1M XMAX) de sair de `IMESSAGE_REQUIRES_FIX` → `IMESSAGE_FELIPE_ACCEPTED`, commitar tudo limpo, atualizar memória + STATUS + GOALS com números honestos, e entregar relatório final verificado.**

---

## 📋 CHECKLIST DE EXECUÇÃO SEQUENCIAL (13 passos)

| # | Passo | Status | Gate |
|---|---|---|---|
| 1 | Criar SUPER_GOAL.md (este arquivo) | 🟡 in_progress | Arquivo presente |
| 2 | Commitar dirty files (`AGENTS.md`, `.brain/memory/2026-07-27.md`, `prompts/*.md`) | ⬜ pending | `git status` limpo |
| 3 | Verificar hipótese MCP endpoint (paste #2 §4) — config check no Mac | ⬜ pending | Evidência de path correto/errado |
| 4 | `make lint` (ruff + mypy) | ⬜ pending | 0 errors |
| 5 | `make test-fast` (sem coverage) | ⬜ pending | PASS |
| 6 | Focal: `pytest backend/tests/test_retry_envelope_3x20s.py -v` | ⬜ pending | 15/15 PASS |
| 7 | `scripts/check_no_literal_keys.py` (secret scan) | ⬜ pending | 0 violations |
| 8 | Implementar defesa-em-profundidade (paste #2 §3.3): filtro hard-stop + counter Prometheus | ⬜ pending | Código + test PASS |
| 9 | Adicionar regression test que FALHA se identity leak voltar | ⬜ pending | test FAIL → fix → test PASS |
| 10 | Atualizar `.harness/memory/MEMORY.md` com Lesson 282 | ⬜ pending | Append-only, número novo |
| 11 | Atualizar `STATUS.md` + `GOALS.md` com números honestos | ⬜ pending | Sem claim inflado |
| 12 | Gerar `REPORT_2026-07-27.md` consolidando tudo | ⬜ pending | Arquivo presente |
| 13 | **Completion audit final** — verificar todo requirement satisfeito | ⬜ pending | Checklist 13/13 |

---

## 🚦 REGRAS INEGOCIÁVEIS

- **HITL obrigatório**: protocolo nasce DRAFT, bot nunca decide sozinho.
- **PII nunca raw**: 3 camadas (Pydantic → Sentry → log MaskingFilter).
- **Audit append-only**: SHA256 + HMAC, qualquer mudança exige sign-off `cartorio-lgpd`.
- **Sem secrets commitados**: `.env` no `.gitignore`, `check_no_literal_keys.py` gate.
- **Conventional Commits** + `Modified by Gustavo Almeida` no trailer.
- **YOLO mode** = continuar sem input, exceto destrutivo (`rm`, `drop`, `force push`).
- **NÃO inventar PASS**: CONNECTED ≠ OPERATIONAL, harness ≠ real transport.

---

## 🛑 SUI (humanos) — fora do escopo desta sessão

- **B1** Audit 0028 + legacy sign-off → `cartorio-lgpd`
- **B2** WhatsApp QR scan → Gustavo
- **B3** Secrets rotation (n8n, openclaw) → Gustavo (NUNCA sob pressão)
- **Felipe** confirmação visual no iPhone dele → Felipe

---

## 📊 ESTADO INICIAL DO REPO (2026-07-27 21:25 BRT)

| Item | Valor |
|---|---|
| Branch | `master` |
| HEAD | `cfefa9e8` — feat(llm): 3x20s retry envelope |
| Working tree dirty | `AGENTS.md` (memória ZCode), `.brain/memory/2026-07-27.md` (+1) |
| Working tree untracked | `prompts/` (2 arquivos novos) |
| Tests totais | 1648+ (meta antiga superada) |
| Coverage | ~91% (gate 90%) |
| Lint | 0 errors esperado |
| Mypy | 0 errors esperado |
| P0 ativo | IDENTITY_HERMES_LEAK (iMessage 30% Hermes em N=10) |
| Gate canal | `IMESSAGE_REQUIRES_FIX` |

---

## 🎯 CRITÉRIO DE DONE

Todos os 13 passos acima com status ✅, mais:
- Working tree limpo (`git status` = nada ou só mudanças intencionais commitadas)
- Report final presente e verificado
- Sem claim inflado em STATUS/GOALS
- Lição reaproveitável salva em `.harness/memory/MEMORY.md`