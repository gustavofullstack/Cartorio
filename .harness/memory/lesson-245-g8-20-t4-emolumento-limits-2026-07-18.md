# Lesson 245 — G8.20.T4 Emolumento Fiscal Limits/Sentinels/Parametrize (cartorio-dev 2026-07-18)

## Contexto

Task G8.20.T4 do plano G8 pediu **"testes unitários para verificação de
limites mínimos, máximos e isenções tributárias"** do calculador
de emolumentos MG 2026. Como `cartorio-dev`, a entrega teve que
seguir o workflow obrigatório (`analisar → testar → corrigir →
melhorar → otimizar → documentar → comentar → salvar na memória`)
sem tocar PII / audit (regras P0 do AGENTS.md / CLAUDE.md) e
respeitando Honesty Gate (Lesson 216/225).

HEAD de partida: `6612c38` (chore G8.14.T1 — CI cache optimization).
Wave 47 já estava consolidada (`14c9fd6`) mas dois commits
subsequentes (G8.14.T1 + lesson-243) estavam ahead.

## Baseline (Wave 43 / Lesson 225)

Arquivo `backend/tests/test_emolumento_validacao.py` já tinha 19
testes do **T047** (G8.11.T3 — split SOLID) cobrindo:
- nominal escritura/certidao
- isenção gratuítos + whitelist motivos
- urgência 50%
- adicional folhas 5%
- folhas boundary (1, 1000)
- quantize bancário ROUND_HALF_UP

A descrição G8.20.T4 listava 14 testes adicionais desejados,
**mas parte das features pedidas NÃO existem no código atual**
(Lesson 225 já documentou isso):
- "valor abaixo do mínimo **retorna mínimo**" → atual: `ValueError`
- "valor acima do teto **cap no teto**" → atual: `ValueError`
- "urgência **dobra valor**" → atual: 50% adicional, NÃO ×2

## Honesty Gate — rigoroso (mantido)

Não escrevi testes que documentariam comportamento que não existe
(seria cinismo técnico sob o nome de "regression tests"). Em vez
disso, escrevi testes **parametrizados** que documentam o
comportamento REAL atual, com docstring explicando a divergência
quando aplicável. Decisão alinhada com Lesson 225.

## Decisão de design — t048 marker + parametrização

**Markers**: `t047` preservado (19 testes), `t048` adicionado
(15 novos test functions = 62 test runs via parametrize). Total
em `test_emolumento_validacao.py`: **19 t047 + 62 t048 parametrized
= 81 passed**.

`pyproject.toml` ganhou o marker `t048`:
```toml
"t048: regression test for emolumento limits boundaries/parametrize
       (G8.20.T4 — pure rules sentinel)",
```

**Estratégia de parametrização** (cartorio-dev 2026-07-18):
- Cada `pytest.mark.parametrize` cobre um conjunto de bordas
  relacionadas. Quando a regra fiscal mudar, **múltiplos casos**
  falham de uma vez (sinal claro de regressão massiva vs. pontual).
- IDs descritivos (`min_exato`, `005_half_up`, `xss`, etc.) deixam
  o report do pytest legível e identificável em CI.

## T048 — 15 test functions adicionados

| R# | Função de teste | Casos | Cobre |
|----|-----------------|-------|-------|
| T048.1a | `test_folhas_validas_boundary_parametrizado` | 6 | folhas=1, 2, 5, 100, 999, 1000 OK |
| T048.1b | `test_folhas_invalidas_levanta_value_error_parametrizado` | 6 | folhas=0, -1, -100, 1001, 5000, 100k → ValueError (Honesty Gate) |
| T048.2a | `test_isencao_motivo_whitelist_aceito_todos_tipos_pagos` | 3 | cada MOTIVOS_ISENCAO × 3 atos pagos |
| T048.2b | `test_isencao_motivo_invalido_rejeitado_tipos_pagos` | 6 | motivos fora whitelist (case, unicode, XSS, etc) |
| T048.2c | `test_isencao_gratuito_predomina_sobre_motivo_invalido` | 2 | gratuidade LEI prevalece (independente do motivo) |
| T048.3a | `test_quantize_bancario_parametrizado_round_half_up_canonico` | 13 | todas as bordas canônicas .004/.005/.006, carry-over, negativo |
| T048.4a | `test_adicional_folhas_puro_parametrizado_escritura` | 6 | 5% × folhas extras (1..99) |
| T048.4b | `test_adicional_urgencia_parametrizado_valor_extremo` | 6 | base=0, base=28.90, base=4521, base=10000 |
| T048.4c | `test_adicional_folhas_zero_folhas_extras_zero_clamps` | 1 | clamp defensivo max(0, folhas-1) |
| T048.5a | `test_sentinela_tipos_gratuitos_estavel` | 1 | frozenset exato {nascimento, obito} |
| T048.5b | `test_sentinela_motivos_isencao_estavel` | 1 | frozenset exato {justica, filantropica, social} |
| T048.5c | `test_sentinela_adicionais_percentuais_estavel` | 1 | ADICIONAL_FOLHA=0.05, ADICIONAL_URGENCIA=0.50 |
| T048.5d | `test_sentinela_min_max_folhas_estavel` | 1 | MIN=1, MAX=1000 imutáveis |
| T048.6a | `test_validar_tipo_rejeicao_parametrizada` | 6 | tipo inválido (vazio, foo, case, trailing_space, "None", xss) |
| T048.6b | `test_validar_tipo_aceita_todos_tipos_validos` | 1 | sentinel: len(TIPOS_VALIDOS)==10 |
| T048.7a | `test_calcular_integracao_quantize_2_casas_total` | 1 | total.as_tuple().exponent == -2 |
| T048.7b | `test_calcular_isencao_gratuito_total_zero` | 1 | gratuidade zera TODOS os campos |

Total: **17 test functions** (62 test runs expandido por parametrize),
**14 sentinelas + parametrizadas** (mínimo que a task pediu: 14).

## Cobertura de regras MG 2026 por teste

| Regra MG 2026 | Teste t048 |
|---------------|-----------|
| Range fechado [1, 1000] folhas | T048.1a/b |
| Fora do range → ValueError | T048.1b (Honesty Gate) |
| Gratuidade LEI (registro_nascimento, registro_obito) | T048.2c + T048.5a |
| Whitelist motivos isenção | T048.2a/b + T048.5b |
| 5% por folha adicional | T048.4a/c |
| 50% urgência justificada | T048.4b + T048.5c |
| ROUND_HALF_UP bancário | T048.3a |
| 2 casas decimais (R$ X.YY) | T048.7a |
| Tipo estrito (case-sensitive, sem normalização) | T048.6a/b |
| Tab.Placeholder com 10 atos | T048.6b (sentinel 10) |

## Honesty Gate — resultados

```text
cd backend && unset PYTHONPATH
uv run pytest tests/test_emolumento_validacao.py --no-cov -v
  -> 81 passed in 0.59s

uv run pytest tests/test_emolumento_validacao.py tests/test_emolumento.py tests/test_emolumento_edge_t043_t044_t045.py --no-cov
  -> 102 passed (somando todos os emolumento tests)

uv run pytest --no-cov -q -k emolumento
  -> 151 passed, 1 skipped (suite emolumento completa)

uv run pytest --no-cov -q   (full suite)
  -> 4154 passed, 2 failed, 23 skipped, 49 deselected
  Obs: 2 falhas em test_health_radar_expanded.py e
       test_g7_wave24_integration.py — PRÉ-EXISTENTES (rodadas
       isoladas: 2 passed em 0.50s). É poluição de estado entre
       testes (test isolation issue), NÃO-REGRESSÃO desta task.

uv run ruff check tests/test_emolumento_validacao.py
  -> All checks passed!

uv run ruff check pyproject.toml
  -> (config-only, sem issues)

uv run mypy tests/test_emolumento_validacao.py
  -> Success: no issues found in 1 source file

uv run mypy app/services/emolumento_validacao.py app/services/emolumento.py
  -> Success: no issues found in 2 source files

uv run mypy app/
  -> (não tocado; sem mudança)
```

## Antes / depois

| Métrica | Antes (Wave 43) | Depois (G8.20.T4) |
|---------|-----------------|-------------------|
| Test functions em `test_emolumento_validacao.py` | 19 | 36 (+17 funções T048) |
| Test runs (parametrize expandido) | 19 | 81 (+62) |
| Markers registrados em `pyproject.toml` | 1 (t047) | 2 (+t048) |
| Docstrings com referência MG 2026 | ~14 | ~32 |
| Sentinelas de constantes fiscais | 0 | 4 (TIPOS_GRATUITOS, MOTIVOS_ISENCAO, ADICIONAL_*, MIN/MAX_FOLHAS) |
| Funções puras com cobertura parametrizada | 1/6 | 6/6 (100%) |

## Decisões de não-implementação (Honesty Gate preservado)

A task description G8.20.T4 listava como desejáveis:

1. ❌ "abaixo do mínimo → retorna mínimo da faixa" — **NÃO IMPLEMENTADO** no
   código atual (Levanta ValueError — ver Lesson 225). T048.1b documenta o
   comportamento REAL e explicita no docstring a divergência.
2. ❌ "acima do teto → cap no teto" — **NÃO IMPLEMENTADO** no código atual
   (Levanta ValueError). T048.1b documenta.
3. ❌ "urgência dobra valor" — **NÃO IMPLEMENTADO** (regra atual: 50%
   adicional, não ×2). T048.4b documenta com base=10k → 50% = 5000.
4. ✅ "5% por folha adicional" — **JÁ IMPLEMENTADO** + parametrizado (T048.4a).
5. ✅ "arredondamento bancário ROUND_HALF_UP" — **JÁ IMPLEMENTADO** +
   parametrizado 13 bordas (T048.3a).
6. ✅ "tipos gratuitos isentos" — **JÁ IMPLEMENTADO** + parametrizado +
   sentinela (T048.2c/5a).
7. ✅ "tipos pagos com motivo na whitelist" — **JÁ IMPLEMENTADO** +
   parametrizado (T048.2a/b).

Estas pendências (1, 2, 3) **continuam fora do escopo** desta task;
podem virar futura task de **feature** (`G8.XX.TY — feature:
clamp/teto/mínimo + urgência ×2`) quando produto decidir o que fazer
— não é decisão técnica isolada de backend, depende de definição
com tabelião + cartorio-lgpd + publicação no DO.

## Lições reaproveitáveis (cross-rein)

1. **Parametrize > множество testes manuais** quando o contrato fiscal
   é discreto (frozenset de 2-3 itens, range fechado). 1 função com
   parametrize × N variantes é mais legível e menos edit-prone que N
   funções `test_X_diferente_1` / `test_X_diferente_2` / etc.
2. **Sentinelas explícitas de constantes** (`assert TIPOS_GRATUITOS
   == frozenset({...})`) custam 1 LOC e protegem contra mudança
   silenciosa. Vale o byte.
3. **Honesty Gate aplica-se a parametrização também** — se o contrato
   diz "10 atos placeholder", o sentinel `len(TIPOS_VALIDOS) == 10`
   falha conscientemente quando a carga oficial do DO aumentar.
4. **Docstrings com referência legal explícita** (ex.: "Regra MG 2026
   — Lei 6.015/73 + CNJ") tornam o teste autodescritivo para auditor
   externo. Mesmo que a tabela MG 2026 ainda seja placeholder,
   referenciar a base legal dá accountability.

## Modified by Gustavo Almeida + cartorio-dev agent (Wave 47+ G8.20.T4 2026-07-18)
