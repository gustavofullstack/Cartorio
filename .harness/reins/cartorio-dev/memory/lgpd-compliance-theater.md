---
description: Como detectar "compliance theater" — pytest verde com docstring dizendo "NAO escopo desta entrega" + backlog deferido (D3, future work, limitation). Marcadores textuais + comandos de verificacao (grep no scrub, ler docstring, verificar backlog). Ativa quando fechar ticket LGPD/PCI/HIPAA ou revisar PR com coverage supostamente completa.
---

# LGPD Compliance Theater Detection

Pytest verde NAO garante compliance real. Tests podem passar com coverage INTENCIONALMENTE incompleta, documentada em test docstring como "NAO escopo desta entrega" + backlog itemizado.

## Cenario real (cartorio-dev Sprint 1.7)

Output LLM scrub foi shipped. Tests 14/14 verde em `test_llm_output_scrub.py`. POREM test docstring documenta LIMITACOES explicitamente:

```
test_llm_output_scrub.py linhas 19-22:
'Limites documentados (NAO escopo desta entrega):
 - CNH sem regex -> nao eh redacted (D3 backlog)
 - CNS sem regex -> nao eh redacted (D3 backlog)'
```

Realidade:
- `scrub()` em `app/services/pii.py` NAO tem CNS nem CNH (grep vazio)
- output scrubber novo USA `scrub()` — portanto tambem nao pega CNS/CNH
- LGPD art. 11 (dado sensivel saude) violado na boundary 2 (output do LLM)
- Passa tests, falha na vida real = "theater of compliance"

## Trio classico de compliance fake

1. Pytest verde
2. Docstring dizendo "NAO escopo desta entrega"
3. Backlog itemizado (D3)

Se os 3 estao presentes = gap real. Reportar imediatamente.

## Marcadores textuais a procurar

Buscar com `grep -rn` em `tests/`:

| Marcador | Significado |
|----------|-------------|
| `NAO escopo` | Fora do escopo desta entrega |
| `D<X> backlog` | Backlog priorizado (D0=imediato, D3=deferido) |
| `limitation` | Limitacao conhecida |
| `future work` | Trabalho futuro |
| `will be addressed in` | Sera tratado em |
| `TODO backlog` | Backlog itemizado |
| `futura entrega` | PT-BR equivalente |
| `partial coverage` | Coverage parcial |
| `out of scope` | EN equivalente |

## Verificacao pre-"LGPD-XXX done"

```bash
# 1. Ler test docstring
cat tests/integration/test_<feature>.py | head -50

# 2. Verificar regex no scrub()
grep -E "CPF|CNPJ|RG|CNH|CNS|email|telefone" app/services/pii.py

# 3. Verificar backlog items referenciados
grep -rn "D[0-9]" app/services/ tests/integration/

# 4. Verificar TODOs explicitos no codigo
grep -rn "TODO\|FIXME\|XXX" app/services/

# 5. Confirmar com cartorio-lgpd (ou Pietra root inline) se gap esta aprovado formalmente
```

## Acao por tipo de gap

| Tipo | LGPD Art. | Prioridade |
|------|-----------|------------|
| CNS (saude) | Art. 11 | P0 imediato, NAO deferir |
| CNH | Art. 11 (categoria similar) | P1, documentar em RIPD |
| Consent gate faltando | Art. 7 I | P0 imediato |
| Retencao sem expires_at | Art. 16 | P1 |
| Audit log sem hash chain | Art. 37 | P0 imediato |
| IP em log sem truncar | Art. 37 | P1 |

## Compliance gap ≠ bug-fantasma

- **Bug-fantasma**: teste diz fail mas passa (briefing stale)
- **Compliance gap**: teste passa mas coverage eh intencionalmente incompleta e documentada (real gap)

Ambos precisam ser reportados, mas compliance gap NAO pode ser silenciado como "ja feito". Tests passando NAO sao prova de cobertura.

## Documentar gaps (quando deferido formalmente)

Quando gap eh aprovado pra deferir (por cartorio-lgpd ou Pietra root):

1. Adicionar entry em MEMORY.md com type=compliance-gap (live state)
2. Adicionar item em backlog com prioridade e prazo
3. Atualizar RIPD com limitacao explicita
4. Adicionar teste de REGRESSAO que falha quando gap NAO esta presente (anti-regression)
5. NAO remover marcadores textuais da docstring — manter como audit trail

## Licao

LGPD compliance theater eh diferente de code theater:

- **Code theater**: tests que nao testam nada (trivial assertions, mocks sempre passam)
- **Compliance theater**: tests que testam ALGO mas omitem dimensoes criticas (PII types especificos, edge cases regulatorios)

Ambos sao perigosos, mas compliance theater eh mais perigoso porque passa review superficial e vai pra producao com "100% verde" no badge de compliance.

Reutilizavel: qualquer projeto com pipeline LGPD/HIPAA/PCI onde tests tem docstring "limitation" ou backlog deferido.
