# OpenClaw Skill Registry (G8.21.T1)

## Problema

O diretorio `.agents/skills/` cresceu para 12 skills (api, chatwoot, easypanel, hostinger, MiniMax-M3, n8n, supabase, coding-vps-21/-deploy/-monitor/-orchestrator/-tools-100) sem um mecanismo formal de descoberta, validacao e versionamento. Qualquer agente que invoca `load_skill()` precisa confiar que:

1. Toda skill tem `SKILL.md`.
2. O YAML frontmatter parseia sem erro.
3. Os campos obrigatorios `name` e `description` estao presentes.
4. Opcionalmente, um campo `version` e exposto para acompanhamento.

Sem esse contrato, uma skill nova (ou mal editada) pode quebrar o OpenClaw com erro silencioso em runtime. Esta task entrega o gate estatico offline que descobre e valida tudo isso.

## Solucao

Script CLI `scripts/openclaw_skill_registry.py` que:

- Varre `.agents/skills/**/SKILL.md` recursivamente.
- Faz parse do YAML frontmatter (delimitado por `---` na linha 1 e `---` antes do corpo).
- Valida campos obrigatorios (`name`, `description`).
- Imprime manifesto legivel OU JSON (--json).
- Retorna exit 0 se todas as skills sao validas, 1 caso contrario.

## Uso

```bash
python3 scripts/openclaw_skill_registry.py            # modo texto
python3 scripts/openclaw_skill_registry.py --json     # modo JSON (CI / agente)
make openclaw-skills-list                             # wrapper Makefile
```

Said a esperada (modo texto):

```
Found 12 skills in .agents/skills
  - api: Skill para interagir com a API FastAPI do Cartório...
  - chatwoot: Skill para interagir com o Chatwoot CRM...
  ...
```

## API

### `parse_skill(skill_md: Path) -> dict | None`

Le `SKILL.md`, devolve metadata dict quando o frontmatter e valido, ou `None` quando:

- o arquivo nao comeca com `---`;
- nao ha delimitador `---` de fechamento;
- o YAML quebra;
- o YAML parseia para algo nao-dict.

### `validate_skill(metadata: dict, name: str) -> list[str]`

Devolve lista de erros. Campo `name` ou `description` ausente / vazio e sinalizado como `f"{name}: missing required field 'X'"`.

### `discover_skills(skills_dir: Path) -> tuple[list[dict], list[str]]`

Walk recursivo, agrega skills (com campos `name`, `path`, `description` truncada em 1 linha, `version`) e erros.

### `main() -> int`

CLI argparse. Suporta `--skills-dir` e `--json`. Exit `0` somente quando `errors == []` e `skills != []`.

## Cache

A funcao privada `_cached_parse(skill_md_str)` usa `@lru_cache(maxsize=64)` indexado pelo caminho absoluto resolvido. Em uma varredura multi-skill dentro do mesmo processo, cada `SKILL.md` e parseado no maximo uma vez. Em CLI de uso unico isso nao traz beneficio visivel (cache e por-chamada), mas a funcao fica pronta para integracao em agentes que enumeram skills repetidamente (dead-man's-switch, hot-reload de manifestos).

## Testes

`backend/tests/test_openclaw_skill_registry_g8.py` — 8 testes:

| # | teste | proposito |
|---|-------|-----------|
| 1 | `test_parse_skill_returns_metadata` | frontmatter valido parseia dict |
| 2 | `test_parse_skill_invalid_yaml_returns_none` | YAML invalido + arquivo sem frontmatter |
| 3 | `test_validate_skill_missing_name` | sem `name` => erro |
| 4 | `test_validate_skill_missing_description` | sem `description` => erro |
| 5 | `test_validate_skill_complete_passes` | completa => zero erros |
| 6 | `test_main_walks_skills_dir_correctly` | walk de tmp_path; SKILL.md extra (no front) gera erro |
| 7 | `test_main_returns_0_on_valid` | `main()` retorna 0 quando tudo passa |
| 8 | `test_main_returns_1_on_errors` | `main()` retorna 1 quando ha erro |

Execucao: `cd backend && uv run pytest --no-cov -v tests/test_openclaw_skill_registry_g8.py` → 8 passed.

## Integracao

- `Makefile`: alvo `openclaw-skills-list` para uso humano e na esteira.
- Futuro: hook pre-commit falha o commit se alguma skill nao validar (ja temos `scripts/check_no_literal_keys.py`; pode ser incluido no mesmo gate).
- Futuro: --json consumido pelo agente OpenClaw para confirmar inventario antes de carregar.

## LGPD

O registry NAO le payload de execucao, nao toca Supabase, nao consulta LLM. A unica informacao publicada no manifesto e o `name` e a primeira linha da `description`. Campos sensiveis (CPF, RG, protocolo) nao podem aparecer no frontmatter de SKILL.md — gate anterior `app/services/pii.py` ja scrubbe strings que chegam a logs/LLMs publicas.

## Limites

- O registro e estatico: ele nao detecta skill duplicada por `name` (frontmatter manda, diretorio manda). Cobre-se pela revisao de PR.
- `version` nao e Obrigatorio. Quando presente, e exibido como `[vX.Y.Z]` no manifesto texto e incluido no JSON.
- O cache `lru_cache(64)` e por-path absoluto; mover o repo invalida automaticamente.

Modified by Gustavo Almeida + cartorio-dev — G8.21.T1.
