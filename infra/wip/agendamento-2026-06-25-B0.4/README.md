# WIP — Agendamento B0.4 Sprint 4

**Status**: Preservado como patch (NÃO mergeado)
**Descoberto em**: 2026-06-25 16:50 BRT
**Autor original**: gustavoalmeida (uid 501) — provavelmente sessão ZCode/Pietra paralela
**mtime**: 2026-06-25 13:37-13:43 BRT (~3h antes de ser descoberto)

## Contexto

Trabalho de SQUAD A (B0.4 Sprint 4 - Agendamento de Atendimentos) que ficou
em HOLD/WIP sem ser commitado. Arquivos:

- `model.py` (197L) — modelo SQLAlchemy Agendamento
- `service.py` (406L) — business logic + AuditService + LGPD hashing
- `router.py.patch` (250L) — diff para `backend/app/api/v1/router.py` (+226L)
  - 5 endpoints novos (POST /agendamento + variantes)

## Por que NÃO foi commitado

1. **SEM testes** (`test_agendamento*.py` não existe) — violação TDD strict
2. **SEM pytest run** — gate quebrado, não validável
3. **WIP sem HOLD explícito** — mtime 13:37-13:43, sessão provavelmente
   parou por timeout ou crash antes de completar

## Lição (cross-rein, cross-project)

> **"Pytest é ground truth, report de worker não"** — MEMORY.md Lesson 16/17.
> WIP sem teste = não mergeável. Preservar como patch, retomar com TDD
> RED → GREEN → commit na próxima sessão.

> **"HOLD reportado ≠ HOLD real"** — mtime files dentro do intervalo do report
> = worker agiu. Verificar `git status -sb` + `stat -f "%Sm"` ANTES de aceitar HOLD.

## Como retomar

```bash
# 1. Aplicar o patch no router.py
cd /Users/gustavoalmeida/projetos/Cartorio
patch backend/app/api/v1/router.py < infra/wip/agendamento-2026-06-25-B0.4/router.py.patch

# 2. Copiar model e service para os paths corretos
cp infra/wip/agendamento-2026-06-25-B0.4/model.py backend/app/models/agendamento.py
cp infra/wip/agendamento-2026-06-25-B0.4/service.py backend/app/services/agendamento.py

# 3. RED: escrever testes PRIMEIRO (TDD)
# backend/tests/test_agendamento.py — cobrir:
# - criar_agendamento happy path
# - conflito de horário (409)
# - cliente não existe (404)
# - protocolo não existe (404)
# - LGPD: cpf_hash presente, cpf plaintext ausente
# - Audit log registrado (LGPD art. 37)

# 4. GREEN: rodar pytest até passar
cd backend && uv run pytest tests/test_agendamento.py --no-cov -v

# 5. Commit individual (1 task = 1 commit)
git add backend/app/models/agendamento.py backend/app/services/agendamento.py \
        backend/app/api/v1/router.py backend/tests/test_agendamento.py
git commit -m "feat(agendamento): SQUAD A B0.4 - endpoints criar/listar/atualizar + testes TDD

- Model Agendamento (197L) com StatusAgendamento + TipoAtendimento enums
- Service AgendamentoService com AuditService + LGPD hashing
- 5 endpoints REST /agendamento* (+226L router.py)
- TDD strict: testes cobrem happy path + 409 conflito + 404 cliente/protocolo + LGPD

Modified by ZCode/Mavis + Gustavo Almeida"
```

## Próxima ação

Aguardando decisão Gustavo:
- (A) Retomar com TDD na próxima sessão (recomendado, preserva trabalho)
- (B) Deletar WIP e refazer do zero (mais demorado, perde 600+ linhas)
- (C) Avaliar código primeiro e decidir (mid-ground, ~30min)

Modified by ZCode/Mavis + Gustavo Almeida — 2026-06-25 16:55 BRT