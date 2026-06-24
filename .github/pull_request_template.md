# Pull Request

> **Obrigatorio preencher TODAS as secoes. PRs sem checklist completo serao rejeitados.**

## Resumo

<!-- 1-3 frases: o que esta PR faz e por que -->

## Tipo de mudanca

<!-- Marque com [x] -->

- [ ] `feat:` Nova funcionalidade
- [ ] `fix:` Correcao de bug
- [ ] `docs:` Apenas documentacao
- [ ] `test:` Apenas testes
- [ ] `refactor:` Mudanca de codigo sem mudanca de comportamento
- [ ] `chore:` Manutencao (deps, configs, etc)
- [ ] `perf:` Melhoria de performance

## Issue / Task

<!-- Link para issue, task do TASKS.md, ou Sprint -->

- Issue: #___
- Task: `E_.S_.T_` (de `.harness/TASKS.md`)
- Sprint: ___

## Mudancas

<!-- Lista das mudancas principais. Para cada arquivo: o que mudou e por que. -->

- `path/file.py`: descricao
- `path/other.py`: descricao

## Quality gates (VERIFICAR antes de pedir review)

<!-- TODOS devem ser ✅. Se algum falhar, NAO abra PR. -->

- [ ] `make lint` passa (ruff + mypy)
- [ ] `make test` passa (400+ testes, coverage >= 90%)
- [ ] `make qa` passa (gate completo)
- [ ] `pre-commit run --all-files` passa
- [ ] Sem warnings no output
- [ ] Sem `print()` deixado no codigo
- [ ] Sem `TODO` sem issue linkada
- [ ] Sem credenciais ou secrets commitados

## LGPD (OBRIGATORIO se tocar audit, pii, conversa, cliente)

<!-- Se sua PR toca QUALQUER um desses, marque TODOS os itens. -->

- [ ] Mudanca em `audit/` revisada por `cartorio-lgpd`
- [ ] Mudanca em `pii/` revisada por `cartorio-lgpd`
- [ ] Mudanca em `cliente/` (LGPD art. 18) revisada por `cartorio-lgpd`
- [ ] Mudanca em `conversa/` (HITL) revisada por `cartorio-lgpd`
- [ ] Documento legal (RIPD, DPA, consent) atualizado se necessario
- [ ] Audit log registra a mudanca (LGPD art. 37)

## Testes

<!-- Descreva o que foi testado -->

- [ ] Testes unitarios adicionados/atualizados
- [ ] Testes cobrem caso nominal + 2-3 casos de borda
- [ ] Teste E2E adicionado (se aplicavel)
- [ ] Coverage nao caiu (rodar `make test-cov`)

## Documentacao

- [ ] Docstrings em funcoes publicas
- [ ] `docs/API.md` atualizado (se novo endpoint)
- [ ] `docs/CHANGELOG.md` atualizado
- [ ] `docs/FAQ.md` atualizado (se bug fix)
- [ ] ADR novo em `docs/adr/` (se decisao arquitetural)
- [ ] `.harness/memory/MEMORY.md` atualizado (se licao cross-rein)

## Rollback plan

<!-- O que fazer se der merda em prod? -->

- [ ] Rollback via `git revert <commit>` + redeploy
- [ ] Migration Alembic reversivel (`alembic downgrade -1`)
- [ ] Sem destruicao de dados (soft delete apenas)
- [ ] Backup pre-deploy feito (N8N workflow #09)

## Screenshots / Logs

<!-- Se UI, anexar screenshots. Se backend, colar logs de teste. -->

```bash
# Output de make qa
$ make qa
...
```

## Reviewers sugeridos

<!-- Quem deve revisar? @username -->

- @___ (cartorio-dev, se backend)
- @___ (cartorio-n8n, se workflow)
- @___ (cartorio-lgpd, se LGPD)

## Checklist final

- [ ] Branch atualizada com `master` (`git rebase master` ou `git merge master`)
- [ ] Sem commits `WIP`, `fix typo`, `debug` ou `console.log`
- [ ] Mensagem de commit segue Conventional Commits
- [ ] PR description tem link para issue/task
- [ ] Auto-review feito (voce mesmo revisou seu codigo)
- [ ] CI local passou (`make ci`)

---

**Modified by**: Gustavo Almeida
**Sprint**: ___
**Tempo gasto**: ___h

<!-- Apos merge, lembrar de:
1. Atualizar .harness/TASKS.md (marcar task como done)
2. Atualizar docs/CHANGELOG.md (adicionar entrada)
3. Se for deploy em prod, rodar SMOKE_TEST_REPORT.md
-->
