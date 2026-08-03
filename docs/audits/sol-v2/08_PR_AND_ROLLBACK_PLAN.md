# Plano de Pull Request (PR) e Drill de Rollback (V2)

**Documento:** `docs/audits/sol-v2/08_PR_AND_ROLLBACK_PLAN.md`  

---

## 1. Estratégia de Pull Request e Commits

- **Branch Corretiva:** `codex/graph-v2-orchestration`
- **Mensagem Padrão:** Segue Conventional Commits e finaliza obrigatoriamente com:  
  `Modified by Gustavo Almeida`
- **Hook Pre-commit:** Ativo (`make pre-commit`). Nenhum commit é realizado com `--no-verify`.

---

## 2. Procedimento de Rollback de Código Local

Caso ocorra regressão durante a inclusão de novos pacotes ou testes:
1. Reverter o commit atômico específico via `git revert <SHA>`;
2. Executar `python3 scripts/sol_v2_completion_gate.py` para re-validar que os invariants V2 não foram corrompidos;
3. Atualizar o overlay em `.orchestration/cartorio-super-graph-v2/state.v2.overlay.json` marcando o nó como `ROLLED_BACK`.
