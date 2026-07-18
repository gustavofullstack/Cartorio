# Otimização de CI — G8.14.T1

## Objetivo

Reduzir o tempo de preparação e execução dos jobs `lint` e `test` sem alterar os gates de
Ruff, mypy, pytest, cobertura ou Codecov.

## Antes e depois

| Área | Antes | Depois |
|---|---|---|
| uv | `setup-uv@v3` + cache manual | `setup-uv@v4` com cache nativo |
| Python/pip | instalação via `uv python install` | `setup-python@v5`, cache pip por `uv.lock` |
| ambiente virtual | `backend/.venv` compartilhada no cache | não cacheada; recriada pelo uv a partir dos artefatos |
| chave do lint | usava `matrix.python-version` sem matrix ativa | usa `env.PYTHON_VERSION` |
| dependências | `uv sync --all-extras` instalava também E2E | `uv sync --frozen --extra dev` |
| mypy | apagava `.mypy_cache` em cada run | cache incremental versionado por lock/config/fontes |
| pytest | somente `xdist -n auto` | `xdist` mantido + `.pytest_cache` e `htmlcov` cacheados |

O cache de dependências usa `backend/uv.lock` como fonte de invalidação. Os caches de
qualidade e teste ficam separados: mudanças no código não descartam wheels já baixados, e
mudanças no lockfile invalidam todos os caches relevantes.

## Métricas e honestidade

- `backend/uv.lock`: 3.182 linhas e 568.382 bytes no baseline.
- Testes de contrato do workflow: 3 testes em 0,20 s no ambiente local inicial.
- Suíte completa sem cobertura: 4.094 passaram, 23 ignorados e 49 desmarcados em 99,31 s.
- Paralelismo pytest já existente: redução histórica local de cerca de 67 s para 21 s com
  `pytest-xdist`; essa melhoria antecede G8.14.T1 e não é atribuída a este cache.
- Tempo real do GitHub Actions antes/depois: não medido, pois a task proíbe disparar CI real.

Após o merge, comparar a mediana de cinco runs frios e cinco runs quentes. Registrar por job:
`Install uv with dependency cache`, `Install dependencies`, `Mypy typecheck` e `Run pytest`;
também conferir `cache-hit` nos logs das actions.

## Decisões

Não foi adicionada matrix de pytest. O workflow já usa `xdist -n auto`; dividir em runners
duplicaria o startup de Postgres/Redis e exigiria combinar cobertura, podendo aumentar custo e
tempo total. Também não foi usado `-p no:cacheprovider`, porque o cache de pytest deve
continuar disponível em CI e desenvolvimento.

O workflow não possui job de produção. Em imagens de produção, a recomendação permanece
`uv sync --frozen --no-dev`; o CI usa o extra `dev` porque Ruff, mypy, pytest e xdist são gates
obrigatórios.

Modified by Gustavo Almeida
