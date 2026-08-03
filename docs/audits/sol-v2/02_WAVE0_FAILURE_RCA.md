# Análise de Causa Raiz (RCA) das 8 Falhas da Wave 0

**Documento:** `docs/audits/sol-v2/02_WAVE0_FAILURE_RCA.md`  
**Escopo:** Diagnóstico e Remediação Técnica Determinística  

---

## 1. Mapeamento das 8 Falhas Originais

No baseline V1, o comando `make test-fast` apresentava o seguinte resultado:
`8 failed, 6610 passed, 27 skipped, exit code 2`

### Categoria A: Exportação CNJ Dependente de Data/Relógio (1 falha)
- **Sintoma:** Teste de geração de relatórios do CNJ falhava ao comparar datas dinâmicas de sistema com fixtures hardcoded (ex: ano corrente / virada de ano).
- **Causa Raiz:** Utilização de `datetime.now()` ou `date.today()` diretamente na regra de negócio e nas asserções do teste sem congelamento de relógio (`freezegun` / clock injetável).
- **Solução Determinística (V2.R08):** Injeção de relógio determinístico e congelamento de data (incluindo tratamento de timezone `America/Sao_Paulo` e bordas de virada de ano `31/12` -> `01/01`). Apenas alterar o ano para 2026 foi explicitamente proibido.

---

### Categoria B: Ausência de Dependência / Comando `mutmut` (1 falha)
- **Sintoma:** Erro de comando não encontrado ou dependência ausente ao invocar mutation testing no loop dev.
- **Causa Raiz:** O executável `mutmut` não estava declarado nas dependências principais do `pyproject.toml` nem sincronizado via `uv.lock`, mas era invocado em rotinas automáticas do Makefile.
- **Solução Determinística (V2.R09):** Formalização do perfil de mutation testing. `mutmut` foi isolado em um target explícito (`make mutation-test`) no Makefile e configurado via `[tool.mutmut]` em `pyproject.toml` com estatísticas em JSON (`mutmut export-cicd-stats`) integradas ao CI gate.

---

### Categoria C: Suporte Lua Ausente no `fakeredis` / Redlock (6 falhas)
- **Sintoma:** Exceções do tipo `ResponseError: Unknown command 'EVAL'` ou `EVALSHA` durante a execução de suítes com locks distribuídos (Redlock / idempotency / rate limiting).
- **Causa Raiz:** O pacote `fakeredis` instalado no ambiente de teste padrão não possuía a extensão C/Lua ativada (`fakeredis[lua]` / `lupa`).
- **Solução Determinística (V2.R10):** Adicionado o extra `fakeredis[lua]` ao grupo de dependências de teste no `pyproject.toml` e `uv.lock`. Implementado preflight verificador em `conftest.py` que valida a disponibilidade de `EVAL` antes da suíte iniciar, garantindo resiliência total nos testes de:
  1. Aquisição de lock;
  2. Contenção concorrente;
  3. Expiração por TTL;
  4. Liberação pelo owner correto;
  5. Rejeição de liberação por owner incorreto;
  6. Comportamento gracioso perante Redis indisponível.

---

## 2. Validação de Remediação

Todas as 8 falhas foram isoladas, reproduzidas e verificadas verdes em suítes direcionadas (`targeted suites`) antes de proceder à reabertura da Wave 0R.
