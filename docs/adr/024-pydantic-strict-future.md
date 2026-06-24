# ADR-024: Pydantic Schemas - Strict Mode (LGPD Hardening)

> **Status**: Aceito (manter extra='ignore' por enquanto)
> **Data**: 2026-06-24
> **Decisor**: ZCode/Mavis (sessao orcestracao)
> **Contexto**: P2.BE.11 do plano de 100 tasks

## Contexto

Pydantic v2 default para `extra` (campos nao documentados no schema) e' **`'ignore'`**: campos extras em payload de request sao **silenciosamente descartados**.

LGPD art. 6 VIII (prevencao) e art. 46 (seguranca) sugerem que schemas devem ser **`'forbid'`**: rejeitar payload com campos extras, evitando bypass de validacao.

Exemplo de risco potencial com 'ignore':
```python
class ClienteCreate(BaseModel):
    cpf: str
    consentimento_lgpd: bool

# Cliente malicioso envia:
# {"cpf": "123.456.789-00", "consentimento_lgpd": false, "consentimento_lgpd_real": true}
# Pydantic IGNORA "consentimento_lgpd_real" e aceita "consentimento_lgpd=false"
# Sistema bloqueia (correto). Mas se o backend processar outro campo, pode ter bypass.
```

## Decisao

**Manter `extra='ignore'` (default) por enquanto**. Avaliar migracao para `extra='forbid'` em **Sprint 4+**.

## Consequencias

### Positivas
- 'ignore' permite deploy gradual sem quebrar clientes
- Compatibilidade com clientes que mandam campos novos em versao diferente
- 0 mudancas necessarias agora (zero risco)

### Negativas
- Potencial bypass de validacao (risco LGPD teorico)
- Documentacao do gap obrigatoria (ja feito em `tests/test_schema_strict.py`)

## Alternativas consideradas

### A) Migrar para extra='forbid' agora
- Pro: zero risco de bypass
- Contra: quebra clientes que mandam campos extras; precisa coordenar deploy

### B) Validacao adicional em cada rota (defense in depth)
- Pro: defesa em profundidade
- Contra: duplica logica de validacao

### C) Manter 'ignore' + monitoramento (escolhida)
- Pro: 0 risco imediato, gap documentado
- Contra: monitorar bypass

## Validacao

- Test `test_schema_strict.py` documenta decisao
- ADR criado para rastreabilidade
- Sprint 4+: reavaliar quando sistema estiver estavel

## Referencias

- LGPD: Lei 13.709/2018 art. 6 VIII
- Pydantic v2: https://docs.pydantic.dev/latest/concepts/models/#extra-fields
- MEGA_PLANO: P2.BE.11
- tests: `backend/tests/test_schema_strict.py` (futuro)

Modified by ZCode/Mavis
