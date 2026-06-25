# BRAIN Structure - Cerebro Local + Prod

**SQUAD BRAIN BRAIN1-BRAIN5** - cerebro do projeto para analise rapida, teste, correcao, melhoria, organizacao, documentacao, comentario e memoria.

## Estrutura de Diretorios

```
/Users/gustavoalmeida/projetos/Cartorio/.brain/  (LOCAL MacBook Pro)
  ├── STRUCTURE.md       (este arquivo)
  ├── index.md           (1-pagina consolidada, auto-gerada)
  ├── loop-state.json    (compact 1-pagina, current state)
  ├── tasks/             (1 arquivo por task: CAR-XXX.json)
  ├── plans/             (1 arquivo por sprint)
  ├── memory/            (1 arquivo por dia: YYYY-MM-DD.md)
  ├── lessons/           (1 arquivo por lesson: NNN-titulo-curto.md)
  ├── agents/            (1 arquivo por squad agent: S0.json, A.json, ...)
  ├── docs/              (downloads de docs externas)
  └── api-specs/         (OpenAPI specs)

/var/lib/docker/volumes/cartorio_brain/_data/  (VPS - PROD)
  └── (mesma estrutura, sync bidirecional)
```

## Schema padrao

### tasks/CAR-XXX.json
```json
{
  "id": "CAR-141",
  "squad": "S0",
  "title": "Schema public completo",
  "status": "done|pending|in_progress",
  "owner": "cartorio-supabase",
  "created_at": "2026-06-25",
  "completed_at": "2026-06-25",
  "commits": ["cf80871", "164a647"],
  "type": "infra|sec|obs|res|perf|data|api|doc|ops",
  "deps": [],
  "files_touched": ["backend/alembic/versions/0004-..."]
}
```

### plans/sprint-N.md
- Goal
- Squad distribution
- Day-by-day breakdown
- Risks
- Validators

### memory/YYYY-MM-DD.md
- TL;DR
- Commits made
- Gates status
- Decisions taken
- Lessons learned
- Next steps

### lessons/NNN-titulo.md
- Title
- Context
- Problem
- Solution
- Code reference
- Test reference

### agents/S0.json (exemplo SQUAD S0)
```json
{
  "squad": "S0",
  "name": "Supabase Foundation",
  "owner": "cartorio-supabase",
  "total_tasks": 10,
  "done": 10,
  "active": false,
  "context": "schema + RLS + cron + webhooks + storage + realtime + vault",
  "next_task": null
}
```

## index.md (auto-gerado por index.py)

```markdown
# Cartorio 2o Notas - Brain Index (2026-06-25)

## Status
- Gates: 100% GREEN
- Tasks: 50/100 (50%)

## Squads
- S0: 10/10 ✅
- A: 8/8 ✅
- B: 8/8 ✅
- ...

## Recent commits (last 10)
- a8259cd feat(openclaw): E3 skills registry auto-discovery
- c54219e feat(openclaw): E2+E4+E7+E8 registry 20 tools + thinking always-on
- ...

## Active loop
- SQUAD: J (Linear+Render+Jules)
- Last commit: c363e4c
- Next task: BRAIN1 (criar .brain/ local)
```

## loop-state.json (compact 1-pagina)

```json
{
  "session_id": "2026-06-25-pietra",
  "current_squad": "BRAIN",
  "last_task": "BRAIN1",
  "last_commit": "c363e4c",
  "next_action": "criar .brain/ tasks/ plans/ memory/ lessons/ agents/ no local",
  "gates": {"mypy": 0, "ruff": 0, "pytest": 952},
  "services": {"api": "online", "n8n": "online", "openclaw": "online", "supabase": "online"},
  "tokens_used_session": "~50k (estimado)"
}
```

## BRAIN sync VPS (BRAIN3)

```bash
# Local -> VPS (a cada commit, hook)
rsync -avz /Users/gustavoalmeida/projetos/Cartorio/.brain/ \
  cartorio@vps-cartorio.tail2fe279.ts.net:/var/lib/docker/volumes/cartorio_brain/_data/

# VPS -> Local (a cada hora, cron)
ssh cartorio@vps-cartorio.tail2fe279.ts.net \
  "rsync -avz /var/lib/docker/volumes/cartorio_brain/_data/ \
   /Users/gustavoalmeida/projetos/Cartorio/.brain/"
```

## BRAIN API endpoints (BRAIN6)

- GET /api/v1/brain/tasks?status=pending
- GET /api/v1/brain/lessons?from=2026-06-01
- POST /api/v1/brain/lesson {titulo, contexto, solucao}
- POST /api/v1/brain/sync (forca sync local <-> VPS)
- GET /api/v1/brain/loop-state

## BRAIN session memory auto (BRAIN7)

A cada commit, append 1-line em memory/YYYY-MM-DD.md:
```
[14:30] CAR-141 done (commit cf80871) - RLS policies
```

## BRAIN8 - loop-state.json

Ja documentado acima. Lido a cada turno para restaurar contexto.

## Como usar (workflow Pietra)

1. Read /Users/gustavoalmeida/projetos/Cartorio/.brain/loop-state.json
2. Read /Users/gustavoalmeida/projetos/Cartorio/.brain/index.md
3. Read /Users/gustavoalmeida/projetos/Cartorio/.brain/memory/YYYY-MM-DD.md (hoje)
4. Read /Users/gustavoalmeida/projetos/Cartorio/.harness/memory/MEMORY.md (cross-session)
5. Pick next task
6. Execute (1 commit = 1 task)
7. Update loop-state.json + memory/ + commit

Modified by Pietra + Gustavo Almeida 2026-06-25
