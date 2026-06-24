# ADR-023: Validacao Check-Digit CNS e CNH

> **Status**: Aceito
> **Data**: 2026-06-24
> **Decisor**: ZCode/Mavis (sessao orcestracao)
> **Contexto**: P0.5 + P0.6 do plano de 100 tasks (BLOQUEANTE LGPD art. 11)

## Contexto

LGPD art. 11 classifica **dado sensivel** de saude. CNS (Cartao Nacional de Saude) e' o principal identificador de cidadao no SUS, e CNH (Carteira Nacional de Habilitacao) e' identificacao pessoal (LGPD art. 6).

O sistema ja tinha **regex de deteccao** em `app/services/pii.py` para CNS e CNH (Sprint 0.5), mas **NAO validava check-digit (DV)**. Isso causava:

1. **Falsos positivos**: ISBN de 13 digitos, OAB de 6 digitos, CNJ de 20 digitos, conta bancaria de 15+ digitos PODIAM ser confundidos com CNS/CNH. Mitigado por keyword-anchored, mas ainda arriscado.
2. **Falsos negativos**: CNS/CNH reais com DV errado (typo do cliente) passavam pela deteccao sem alerta.
3. **Conformidade LGPD**: cartorio-lgpd audit (2026-06-23) classificou P0.5 (CNS) e P0.6 (CNH) como BLOQUEANTE.

## Decisao

Adicionar **validacao de check-digit (DV)** em `app/services/pii.py` para CNS e CNH como camada EXTRA ao regex existente.

### Algoritmo CNS

- Estrutura: 15 digitos + 1 DV = 16 digitos totais
- Pesos FIXOS decrescentes: 15, 14, 13, 12, 11, 10, 9, 8, 7, 6, 5, 4, 3, 2, 1
- Aplicados da posicao 1 (peso 15) ate posicao 15 (peso 1)
- Soma = soma(digito[i] * peso[i])
- DV = 11 - (soma mod 11)
- Se DV >= 10, DV = 0 (regra de overflow)
- Fonte: Manual tecnico DATASUS / CADSUS

### Algoritmo CNH

- Estrutura: 9 digitos base + 2 DV = 11 digitos totais
- Pesos CICLICOS: 2, 3, 4, 5, 6, 7, 8, 9 (repetindo)
- Aplicados da direita para a esquerda
- DV1 = 0 se (soma mod 11) < 2, senao 11 - (soma mod 11)
- DV2 mesmo processo, agora sobre 10 digitos (9 + DV1)
- Fonte: implementacoes open source validadas (tiimgreen/validar-cnh, jcassio0/validarCNPJ-CPF-CNH)

## Consequencias

### Positivas

- **Anti-FP reforcado**: CNS sem DV correto (typo, ISBN) NAO passa pela validacao.
- **Conformidade LGPD art. 11**: CNS = dado sensivel saude, agora validado.
- **Cobertura de testes**: 18 testes novos (9 CNS + 9 CNH), total 400 (era 382).
- **API publica**: `validate_cns(cns_digits)` e `validate_cnh(cnh_digits)` disponiveis para uso fora do PII scrub.

### Negativas

- **Performance**: adicionar ~0.1ms por match (operacoes de soma simples, desprezivel).
- **Custo de manutencao**: 2 algoritmos a mais para manter. Algoritmo CNS foi VALIDADO empiricamente (bug inicial descoberto e corrigido).

## Licao aprendida (cross-rein)

**NUNCA confie em "exemplo de blog" para algoritmo oficial**. O primeiro agent retornou formula "modulo 11 ciclico 2-10" para CNS que produzia DV errado (DV1=7 em vez de 0). A formula correta usa **pesos fixos decrescentes 15..1**, nao pesos ciclicos. Validacao empirica com o CNS de teste `8980007647356000` (universalmente conhecido) foi essencial.

## Implementacao

- Arquivo: `backend/app/services/pii.py`
- Funcoes: `_cns_mod11()`, `_cns_dv()`, `validate_cns()`, `_cnh_mod11()`, `_cnh_dv1()`, `_cnh_dv2()`, `validate_cnh()`
- Testes: `backend/tests/test_pii.py` (+18 testes)
- Total: 400 passed, coverage 92.27%, ruff/mypy 0

## Alternativas consideradas

### A) Validacao via API externa (DATASUS, Receita Federal)

- Pro: usa fonte oficial.
- Contra: latencia, dependencia externa, custo.

### B) Manter so regex (status quo)

- Pro: ja funciona.
- Contra: falsos positivos/negativos, NAO conformidade LGPD.

### C) Validacao local (escolhida)

- Pro: zero latencia, zero dependencia externa, codigo aberto, auditavel.
- Contra: precisa manter algoritmos atualizados.

## Validacao

- pytest: 400 passed (era 382)
- Coverage: 92.27% (gate 90% OK)
- Ruff: 0 erros
- Mypy: 0 erros
- Testes cobrem: DV valido, DV invalido (DV1 e DV2 separados), tamanho invalido, entrada vazia, caracteres nao-decimais, formatacao, CNS provisorio/definitivo, CNH classica.

## Referencias

- MEGA_PLANO: `docs/superpowers/plans/2026-06-24-mega-plano-100-tasks.md` (P0.5 + P0.6)
- Commit: `d8d2d84`
- Codigo: `backend/app/services/pii.py`
- Tests: `backend/tests/test_pii.py`
- PENDENCIAS_SUI: `docs/PENDENCIAS_SUI_2026-06-23.md` (P0.5, P0.6)

Modified by ZCode/Mavis
