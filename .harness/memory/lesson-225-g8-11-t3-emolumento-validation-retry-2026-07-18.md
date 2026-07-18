# Lesson 225 — G8.11.T3 Emolumento Fiscal Validation Split (Wave 43 RETRY / cartorio-dev 2026-07-18)

## Contexto

Task G8.11.T3 do SUPER_PLANO_G8_100_TASKS pede **"Isolar a lógica de
validação fiscal de emolumentos notariais de outras regras da API."**
Como cartorio-dev, a entrega tinha que seguir o workflow obrigatório
(`analisar → testar → corrigir → melhorar → otimizar → documentar →
comentar → salvar na memória`) sem tocar PII / audit (regras P0 do
AGENTS.md / CLAUDE.md).

Esta task é um **RETRY**: a tentativa anterior (subagent Wave 43
original) crashou no retorno sem deixar commit. Branch
`feat/g8-11-t3-emolumento-validation-split` existia mas SEM commit
(WIP ficou nos stashes de outros agents — intocados). Esta execução
começa do zero em `master` (HEAD = `1defc17`).

## Decisão arquitetural (SOLID SRP)

**Pure functions em `_validacao.py`, orchestration em `emolumento.py`.**

Antes:
- `backend/app/services/emolumento.py` (104 LOC) misturava:
  - Tabela canônica MG 2026 (`EMOLUMENTOS_2026`)
  - Dataclass de resultado (`CalculoEmolumento`)
  - Validação de tipo (raise ValueError)
  - Validação de folhas (raise ValueError)
  - Cálculo de adicionais (5%/50% inline)
  - Quantização bancária (`ROUND_HALF_UP` inline)
  - Verificação de isenção (`isencao_aplicavel`)
- Único ponto de mudança = única razão para regredir.

Depois:
- `backend/app/services/emolumento_validacao.py` (158 LOC) — **pure
  fiscal rules**:
  - Constantes: `ADICIONAL_FOLHA_PERCENTUAL`, `ADICIONAL_URGENCIA_PERCENTUAL`,
    `MIN_FOLHAS`, `MAX_FOLHAS`, `TIPOS_GRATUITOS`, `MOTIVOS_ISENCAO`
  - Funções: `isencao_aplicavel`, `validar_tipo`, `validar_quantidade_folhas`,
    `calcular_adicional_folhas`, `calcular_adicional_urgencia`, `quantize_bancario`
  - **Zero I/O, zero DB, zero Redis, zero FastAPI** — testável em isolado.
- `backend/app/services/emolumento.py` (97 LOC) — **orchestration**:
  - Mantém tabela `EMOLUMENTOS_2026`, `TIPOS_VALIDOS`, `CalculoEmolumento`
  - `calcular()` agora **compõe** as funções puras de validação
  - **Re-exports completos** (`__all__` + import + re-export) para
    preservar 100% da API pública (router.py, mcp_server.py,
    api/v2/emolumento.py, services/protocolo.py, services/cache_warming.py,
    testes — todos os imports legacy continuam funcionando)

## Honesty Gate (Lesson 216) — rigoroso

A descrição da task mencionava 5 categorias fiscais:
1. **cálculo de isenção** ← EXISTS (`isencao_aplicavel`)
2. **validação de urgência (×2 no emolumento)** ← EXISTE mas como **50% adicional**, NÃO ×2
3. **faixa de valor (mínimo/teto MG 2026)** ← **NÃO EXISTE** (só range de folhas)
4. **abaixo do mínimo (retorna mínimo)** ← **NÃO EXISTE** (atual: ValueError)
5. **acima do teto (cap no teto)** ← **NÃO EXISTE** (atual: ValueError)

**Decisão honesta**: testes documentam o comportamento **real** do
código, não fabricam features prometidas. Onde a descrição divergiu,
o teste explicita isso no docstring (ex.: `test_folhas_abaixo_minimo_levanta_value_error`
explicita que hoje levanta ValueError, não retorna mínimo).

Esta postura preserva o Honesty Gate (Lesson 216) e respeita "preserve
100% da API pública" — implementar "returns min" ou "cap no teto"
seria **mudança de comportamento**, não split.

A urgência também é **50%** (não ×2 como prometia a descrição). Os
testes fixam isso em `ADICIONAL_URGENCIA_PERCENTUAL == Decimal("0.50")`
para regredir claramente se alguém dobrar a regra sem intencionalidade.

## Antes / depois

### Métricas

| Métrica | Antes | Depois |
|---------|-------|--------|
| LOC `emolumento.py` | 104 | 97 (-7, mais enxuto) |
| LOC `emolumento_validacao.py` | n/a | 158 (novo) |
| Funções fiscais isoladas | 0 | 6 (todas pure) |
| Constantes fiscais isoladas | 0 | 6 (`Final[...]`) |
| Tests cobrindo regras fiscais | 7 (no `test_emolumento.py` legado) | 19 (no `test_emolumento_validacao.py`) |
| Re-exports da API pública | n/a | 12 símbolos em `__all__` |
| Acoplamento I/O em regras fiscais | sim (inline) | não (pure functions) |

### Funções extraídas

| Função | Origem | Pure? |
|--------|--------|-------|
| `validar_tipo(tipo, tipos_validos)` | inline em `calcular()` | sim |
| `validar_quantidade_folhas(folhas)` | inline em `calcular()` | sim |
| `calcular_adicional_folhas(base, folhas)` | inline em `calcular()` | sim |
| `calcular_adicional_urgencia(base, urgencia)` | inline em `calcular()` | sim |
| `quantize_bancario(valor)` | `quantize()` aninhada em `calcular()` | sim |
| `isencao_aplicavel(tipo, motivo)` | top-level em `emolumento.py` | sim |

### Como a tabela MG 2026 foi mantida semantic-equivalente

| Regra | Antes (inline) | Depois (em `_validacao`) | Mesmo resultado? |
|-------|----------------|--------------------------|------------------|
| Tipo inválido | `raise ValueError(f"tipo desconhecido: {tipo!r}. Validos: {sorted(TIPOS_VALIDOS)}")` | `validar_tipo(tipo, TIPOS_VALIDOS)` | ✓ |
| Folhas fora [1, 1000] | `raise ValueError(f"folhas deve estar entre 1 e 1000, recebeu {folhas}")` | `validar_quantidade_folhas(folhas)` com `MIN_FOLHAS=1`, `MAX_FOLHAS=1000` | ✓ |
| Adicional folhas | `base * Decimal("0.05") * max(0, folhas - 1)` | `base * ADICIONAL_FOLHA_PERCENTUAL * max(0, folhas - 1)` com constante 0.05 | ✓ |
| Adicional urgência | `base * Decimal("0.50") if urgencia else Decimal("0")` | `calcular_adicional_urgencia(base, urgencia)` | ✓ |
| Quantização 2 casas | `quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)` | `quantize_bancario()` | ✓ |
| Isenção gratuítos | `if tipo in gratuítos` | `if tipo in TIPOS_GRATUITOS` | ✓ |
| Isenção motivos | `return motivo in motivos_validos` | `return motivo in MOTIVOS_ISENCAO` | ✓ |

Todos os 69 testes preexistentes (test_emolumento.py + test_emolumento_edge_t043_t044_t045.py
+ test_emolumento_cache_a21.py + outros) continuam PASS — prova da
equivalência semântica.

## Cobertura dos 19 testes (marker t047)

| R# | Teste | Cobre |
|----|-------|-------|
| T047.1a | `test_cenario_nominal_escritura_compra_venda` | nominal R$ 4521 base |
| T047.1b | `test_cenario_nominal_certidao_negativa_2_casas` | boundary de 2 casas decimais |
| T047.2a | `test_isencao_gratuito_nascimento_qualquer_motivo` | gratuidade automática |
| T047.2b | `test_isencao_gratuito_obito_qualquer_motivo` | gratuidade automática |
| T047.2c | `test_isencao_justica_gratuita` | motivo whitelist |
| T047.2d | `test_isencao_filantropica_e_programa_social` | demais motivos whitelist |
| T047.2e | `test_isencao_motivo_invalido_eh_falso` | motivo fora = False |
| T047.2f | `test_tipos_gratuitos_e_motivos_consistencia` | split não divergiu constantes |
| T047.3a | `test_urgencia_adicional_50_porcento_base` | pure function 50% |
| T047.3b | `test_urgencia_via_calcular_procuracao` | integração com `calcular()` |
| T047.3c | `test_urgencia_via_calcular_combina_folhas` | urgência + folhas combinam |
| T047.3d | `test_adicional_folhas_puro_5_porcento` | pure function 5% por folha |
| T047.4a | `test_folhas_abaixo_minimo_levanta_value_error` | boundary inferior |
| T047.4b | `test_folhas_acima_teto_levanta_value_error` | boundary superior |
| T047.4c | `test_folhas_min_e_max_boundary` | exato (1 e 1000) aceito |
| T047.4d | `test_validar_quantidade_folhas_pura_levanta` | pure function isolada |
| T047.5a | `test_validar_tipo_invalido_levanta` | tipo fora = ValueError |
| T047.5b | `test_validar_tipo_valido_nao_levanta` | tipo válido = OK |
| T047.5c | `test_quantize_bancario_2_casas_round_half_up` | ROUND_HALF_UP correto |

Cada teste **falha se a regra fiscal regredir** (mudança de percentual,
perda de gratuidade, mudança de range, etc.).

## Honesty Gate — resultados

```text
pytest tests/test_emolumento_validacao.py --no-cov -v
  -> 19 passed in 0.22s
pytest tests/test_architecture_coupling.py --no-cov -q
  -> 10 passed in 0.44s  (não regrediu — split mantém emolumento na mesma camada)
pytest --no-cov -q -k emolumento
  -> 69 passed, 1 skipped (todos os tests existentes continuam PASS)
pytest --no-cov -q   (full suite)
  -> 3870 passed, 23 skipped, 49 deselected, 2267 warnings in 89.25s
ruff check app/services/emolumento.py app/services/emolumento_validacao.py
  -> All checks passed!
ruff check app/
  -> All checks passed!
ruff check tests/test_emolumento_validacao.py
  -> All checks passed!
mypy app/services/emolumento.py app/services/emolumento_validacao.py
  -> Success: no issues found in 2 source files
mypy tests/test_emolumento_validacao.py
  -> Success: no issues found in 1 source file
mypy app/
  -> 1 pre-existing error em traefik_lobechat_routing.py:27 (yaml stubs
     missing) — Wave 40, não tocado nesta task, NÃO-REGRESSÃO
```

## Pendências conhecidas (futuras waves)

- Features prometidas na task description que NÃO existem e ficaram
  fora do escopo deste split (Honesty Gate):
  - "faixa de valor (mínimo/teto MG 2026)" — não há atualmente
  - "abaixo do mínimo (retorna mínimo)" — atual é ValueError
  - "acima do teto (cap no teto)" — atual é ValueError
  - "urgência ×2" — atual é 50% adicional
  - Estas podem virar task futura (`G8.20.T1` cobre precisão MG 2026
    em outro lugar; ou nova task `G8.XX.TY` se necessário)
- `mypy app/` ainda tem 1 erro pre-Wave-43 em `traefik_lobechat_routing.py`
  (yaml stubs) — não é regressão deste split. Resolver em cleanup geral.

## Modified by Gustavo Almeida + cartorio-dev agent (Wave 43 RETRY 2026-07-18)
