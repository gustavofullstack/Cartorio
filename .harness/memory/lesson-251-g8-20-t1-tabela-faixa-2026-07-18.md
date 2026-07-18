# Lesson 251 — G8.20.T1 faixas placeholder MG 2026 (2026-07-18)

## Contexto

A calculadora já usava `Decimal` e `ROUND_HALF_UP`, mas não expunha uma função pura para validar valores contra faixas mínimas e máximas. Como emolumento é regra jurídica com HITL obrigatório, esta task não altera `calcular()` nem aplica limites automaticamente.

Os valores de `FAIXAS_EMOLUMENTO_2026` são placeholders. O escrevente deve validar a tabela antes de qualquer uso em produção, e a substituição definitiva depende de carga automatizada do Diário Oficial.

## Decisão

- Manter `EMOLUMENTOS_2026` e a regra final de `calcular()` inalteradas.
- Declarar `FAIXAS_EMOLUMENTO_2026` separadamente, com `Decimal` para todos os limites.
- Implementar `aplicar_limite_faixa(tipo, valor)` como função pura, sem I/O e sem side effects.
- Preservar valores de tipos desconhecidos para compatibilidade.
- Demonstrar composição explícita com `calcular(tabela=...)`, sem transformar o clamp em decisão jurídica automática.

## Precisão matemática

Um valor positivo de `Decimal("0.01")` não está abaixo de um mínimo `Decimal("0.00")`. O caso de regressão correto para `certidao_negativa` usa `Decimal("-0.01")` e espera `Decimal("0.00")`.

Esta distinção evita criar um teste que contradiga o contrato `valor < min` e garante que a função preserve `Decimal("0.01")` quando ele estiver dentro da faixa.

## Testes

```text
pytest tests/test_emolumento_validacao.py --no-cov -v
  -> 86 passed (81 existentes + 5 novos)
ruff check app/services/emolumento*.py
  -> All checks passed!
mypy app/services/
  -> Success: no issues found in 103 source files
pytest --no-cov -q
  -> 4220 passed, 23 skipped, 49 deselected, 1 falha fora do escopo
```

A falha global ocorreu em `test_openapi_security_scheme_defined`, da task anterior G8.17.T4. O mesmo teste passou isoladamente (`1 passed`), indicando contaminação de estado/ordem do cache OpenAPI e não regressão de emolumentos.

## Lição reutilizável

Em validações monetárias, os casos de borda devem ser derivados formalmente das desigualdades do contrato. Quando o mínimo é zero, o menor valor positivo não é caso "abaixo do mínimo". Para regras jurídicas, uma função pura pode documentar e testar limites sem conectá-los automaticamente ao fluxo decisório; a integração final continua sujeita a HITL e tabela oficial.

## Modified by Gustavo Almeida + cartorio-dev agent (G8.20.T1 2026-07-18)
