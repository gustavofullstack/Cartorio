# Decisões de Perfis de Dependência & Lockfiles (V2)

**Documento:** `docs/audits/sol-v2/03_DEPENDENCY_PROFILE_DECISIONS.md`  
**Escopo:** `pyproject.toml`, `uv.lock` e Alvos do Makefile  

---

## 1. Separação de Perfis de Execução

Para garantir reprodutibilidade e evitar que testes de mutação de longa duração desacelerem o ciclo de desenvolvimento rápido (`make test-fast`), estabeleceram-se dois perfis claros:

### Perfil A: QA Canônico Padrão (`make test-fast` / `make qa`)
- **Ferramentas:** `pytest`, `pytest-asyncio`, `pytest-cov`, `fakeredis[lua]`, `respx`.
- **Propósito:** Execução ultra-rápida de testes unitários e de integração sem chamadas LLM externas.
- **Requisito de Bloqueio:** Exit code 0 e cobertura mínima de 90%.

### Perfil B: Testes de Mutação (`make mutation-test`)
- **Ferramentas:** `mutmut`, `mutmut-json-reporter`.
- **Configuração:** `[tool.mutmut]` em `pyproject.toml` (desativando `use_setproctitle` no macOS).
- **Relatórios:** Exportação via `mutmut export-cicd-stats` para geração de relatórios estruturados de CI.

---

## 2. Invariantes de Segurança e Lockfile

- **Nenhuma chave literal:** Validado via `scripts/check_no_literal_keys.py`.
- **Gerenciamento `uv`:** Uso exclusivo do `uv` (`uv sync --frozen`).
- **Resolução de Conflitos:** `uv.lock` verificado e mantido sincronizado na raiz do backend.
