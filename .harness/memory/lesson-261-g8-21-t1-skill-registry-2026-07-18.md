# Lesson 261 — G8.21.T1 OpenClaw skill registry + validator (2026-07-18)

## Contexto

O diretorio `.agents/skills/` ja abrigava 12 skills (api, chatwoot, easypanel, hostinger, MiniMax-M3, n8n, supabase + 5 skills coding-vps_*), todas seguindo o mesmo formato de SKILL.md com YAML frontmatter, mas o OpenClaw e os agentes locais nao tinham um mecanismo offline para descobrir e validar esse catalogo. Sem gate estatico, uma skill com frontmatter mal-formado entraria no ar e quebraria o `load_skill()` em runtime.

## Decisao

Foi criado `scripts/openclaw_skill_registry.py`, CLI stdlib-only + PyYAML (ja nas deps do projeto). O script:

- varre `.agents/skills/**/SKILL.md` recursivamente;
- faz parse seguro do YAML frontmatter (delimitado por `---` na linha 1 e `---` antes do corpo);
- valida presenca de `name` e `description`;
- imprime manifesto legivel OU JSON (--json);
- retorna exit 0 quando tudo passa, 1 quando ha erros ou nenhuma skill for encontrada.

A funcao `_cached_parse` usa `@lru_cache(maxsize=64)` indexado pelo caminho absoluto, preparando o terreno para integracoes que enumerem skills repetidamente (dead-man's-switch, hot-reload). Cache e deterministico: o path resolve e estavel dentro do mesmo repo HEAD; mover o repo ou trocar de branch nao compartilha chaves.

## Testes

`backend/tests/test_openclaw_skill_registry_g8.py` — 8 testes passam:

- `parse_skill` retorna metadata dict, ou None em YAML invalido / sem frontmatter;
- `validate_skill` exige `name` e `description`;
- `discover_skills` caminha SKILL.md corretamente e reporta erros;
- `main()` retorna 0 / 1 conforme o caso.

Suite completa do backend continua com apenas as 2 falhas pre-existentes ja mapeadas nas Lessons 250-252 e 260 (`test_scrub_response_nao_altera_audit_metadata` reproduz isolada; `test_openapi_security_scheme_defined` passa isolada). Esta task nao introduziu regressao.

## LGPD

O registry NAO le payloads de execucao, NAO consulta Supabase, NAO chama LLM. Apenas expoe `name`, primeira linha da `description`, `path`, e quando presente `version`. Campos sensiveis (CPF/RG/protocolo) nunca devem aparecer no frontmatter de SKILL.md; o gate anterior `app/services/pii.py` ja scrubbe tudo que segue pra logs/LLMs publicas.

## Operacao

Novo alvo Makefile:

```makefile
openclaw-skills-list:  ## Lista + valida skills em .agents/skills/ (G8.21.T1)
    python3 scripts/openclaw_skill_registry.py
```

Modo texto imprime uma linha por skill; modo JSON retorna `{count, errors, skills[]}` para CI / agente.

## Validacao

- `python3 scripts/openclaw_skill_registry.py` -> 12 skills encontradas, exit 0;
- `cd backend && uv run pytest --no-cov -v tests/test_openclaw_skill_registry_g8.py` -> 8 passed;
- `uv run --project backend ruff check scripts/openclaw_skill_registry.py backend/tests/test_openclaw_skill_registry_g8.py` -> All checks passed;
- `uv run --project backend ruff format --check ...` -> 2 already formatted;
- `cd backend && uv run pytest --no-cov -q` -> 4327 passed (2 falhas pre-existentes ja documentadas em Lessons 250-252 e 260).

## Proximo passo

- Adicionar `openclaw-skills-list` ao `make pre-commit` (junto com outros gates estruturais);
- Hook pre-commit falha o commit se uma nova skill entrar sem `name`+`description`;
- Quando o OpenClaw estiver em versao estavel, expor o inventario via endpoint MCP / tool `list_skills`.
