---
description: Protocolo detalhado para validar briefings de parent/peer session ANTES de agir — pytest + git log + git diff + worktree checks. 4 cenaros reais documentados. Ativa quando briefing chega com claims sobre test failures, master HEAD, branch state, "work ja feito", ou diffs para review.
---

# Briefing Verification Protocol

Briefings de parent/peer session sobre test failures, master HEAD, branch state ou "work ja feito" estao stale em ~100% dos casos observados (4/4 em jun-2026). Custo de verificar: 30s. Custo de agir cego: 60-90min + possivel regressao critica assinada em review.

## Cenarios documentados (jun-2026)

### Cenario 1 — test failure phantom
Briefing dizia "246 passed, 4 FAILED" com lista de 4 testes especificos. Realidade rodada no momento: 263 passed, 0 failed. Os 4 testes PASSARAM.

Causa provavel: parent olhando output stale de console antigo ou branch diferente. Briefing herdado propagado.

### Cenario 2 — master HEAD 2 commits atras
Briefing dizia "master HEAD = X". Realidade: master HEAD avancou 2 commits durante a janela do briefing. Briefing pedia "fix de 9 fails em Y" mas Y ja tinha sido entregue em 2 commits anteriores.

### Cenario 3 — P0.1 review cego + regressao lateral
Briefing: "22 passed, 0 failed (subset)" + "cherry-pick auto-merge clean". Realidade:
- pytest full suite: 5 FAILED (NAO 0)
- master HEAD avancou 5 commits alem do briefing
- cherry-pick "clean" significa que hunk especifico aplicou sem conflito — outras mudancas paralelas NAO incluidas
- DISCOVERY CRITICO: commit bf12203 adicionou 6911 linhas de coverage data (pytest-cov output) como arquivos de codigo, 43 arquivos com suffix ",cover". Push pro origin ja feito, master poluido.

### Cenario 4 — ZCode auto-commit mid-session
Implementei endpoint + 14 testes GREEN. Descobri que:
1. origin/master JÁ TINHA commit com schema + service + tests (MAS SEM router endpoint)
2. ZCode/Mavis commitou MINHAS alteracoes uncommitted em commit proprio
3. Working tree foi resetado pra match origin/master mid-session
4. Mensagem NAO terminava com "Modified by Gustavo Almeida" (per AGENTS.md)

## Protocolo obrigatorio

### Pre-TDD (delegacao de implementacao)

```bash
git fetch origin
git log origin/master -3 --oneline
git rev-parse HEAD
git status --short
git diff backend/app/<my_domain>/ --stat
pytest tests/<affected_file> --no-cov -q
```

### Pre-review (cross-agent thumbs-up)

```bash
git rev-parse HEAD
git log master -3 --oneline
pytest tests/<affected_files> --no-cov -q --tb=no
git show <hash> --stat  # em CADA commit no range do briefing
# Opcional mas recomendado:
git worktree add /tmp/review-check <hash>
cd /tmp/review-check && pytest tests/ --no-cov -q --tb=no
```

### Output interpretation gotchas

- "X passed" pode ser subset especifico — rodar full suite pra confirmar
- "X deselected" ≠ "X failed" (sao markers excluidos por `-m 'not smoke'`)
- "auto-merge clean" no cherry-pick NAO significa identico — significa hunk especifico aplicou sem conflito
- Briefing escrito em master=X pode estar atras se master avancou 2-5 commits na janela

## Acoes quando briefing esta stale

1. Reportar discrepancia com output LITERAL do pytest + git log (sem output proprio, sem acao)
2. NUNCA inventar fix pra bug-fantasma — gastar quota em code que ja funciona quebra o master rapido
3. Se briefing pede "fix de N fails em X" e master tem commit "feat: implement X" → briefing obsoleto, so reportar
4. Se regressao lateral detectada (como cover files no Cenario 3) → reportar IMEDIATAMENTE antes de qualquer outra acao

## ZCode auto-commit detection

Sinais:
- `git log master -3 --oneline` mostra commit de "ZCode/Mavis <mavis@cartorio.local>"
- Mensagem NAO termina com "Modified by Gustavo Almeida"
- Working tree resetado mid-session

Resposta:
- Comparar seu trabalho com o commit do ZCode
- Se identico: cherry-pick ou pull fast-forward
- Se melhor/mais completo: manter o do ZCode
- Se parcial (ex: schema+service sem router): complementar com seu delta

## Reutilizavel

Qualquer task onde outro agent (ZCode, Pietra root, peer session) pode ter commitado pre-requisito ou paralelo. Verificar ANTES de TDD, nao depois.

Anti-pattern: aceitar briefing "246 passed, 4 FAILED" e sair planejando 4 fixes. Custo real = 60-90min em code que ja funciona + possiveis regressoes introduzidas.

Licao macro: output literal > narrativa propria. Copia/cola do pytest no relatorio. Sem output proprio, sem acao.
