# Cartório Bot - Consulta segura de emolumento

Quando o cliente perguntar o **valor** de um ato cartorário, consulte a API
de catálogo. **NUNCA** invente valores. Só um item `PUBLISHED` pode ser
informado; todo retorno `HITL_REQUIRED` deve ir para o escrevente.

## Endpoint

```
POST https://api.2notasudi.com.br/api/v1/emolumentos/real/calcular?tipo_ato={tipo}
Headers:
  X-API-Key: $CARTORIO_API_KEY
```

## Itens publicados (Portaria CGJ/TJMG nº 8.664/2025, Tabela 1)

| tipo | Descrição | Valor aproximado |
|------|-----------|------------------|
| procuracao_geral | Procuração genérica por outorgante | R$ 68,94 |
| procuracao_previdenciaria | Procuração previdenciária | R$ 36,61 |
| autenticacao_pagina | Autenticação de cópia por folha | R$ 11,21 |
| reconhecimento_firma_semelhanca | Reconhecimento de firma por assinatura | R$ 11,21 |
| escritura_compra_venda | Escritura de Compra e Venda | R$ 1.500,00 — HITL |
| certidao_casamento | Certidao de Casamento | R$ 50,00 |
| testamento_publico | Testamento | R$ 437,24 — HITL |
| ata_notarial_primeira_folha | Ata até duas folhas | R$ 218,42 — HITL |

## Exemplo de chamada

```bash
curl -s -X POST -H "X-API-Key: $CARTORIO_API_KEY" \
  "https://api.2notasudi.com.br/api/v1/emolumentos/real/calcular?tipo_ato=procuracao_geral"
```

## Resposta

```json
{
  "tipo_ato": "procuracao_geral",
  "status": "PUBLISHED",
  "emolumento_base": "52.43",
  "tfj": "16.51",
  "total": "68.94",
  "tabela_referencia": "Tabela 1, item 4.f.1",
  "vigencia_inicio": "2026-01-01"
}
```

## Como responder ao cliente (PT-BR natural)

### Caso 1: `PUBLISHED`
```
O valor final de referência para esse item é R$ 68,94.

Ele corresponde à Tabela 1, item 4.f.1, vigente em 2026. Se houver poderes
específicos, urgência ou documentos adicionais, vou encaminhar ao escrevente.
```

### Caso 2: `HITL_REQUIRED` ou tipo ausente
```
Para esse ato, o valor depende da conferência de documentos e da composição
do caso. Vou encaminhar sua solicitação a um escrevente para a cotação correta.
```

## LGPD

- Não trate `HITL_REQUIRED` como erro nem invente um valor final.
- NUNCA envie o valor para LLM publica sem scrub (mas emolumento nao eh
  PII, entao pode ir direto).
- Cliente pode pedir "quanto custa para fazer X pra minha irma?" — NAO
  faca calculo para outra pessoa. Redirecione: "O calculo so pode ser
  feito para voce mesmo. Sua irma precisa falar conosco pelo WhatsApp dela."

## Quando chamar esta skill

- "Quanto custa uma procuração geral?"
- "Qual o valor de uma certidao?"
- "Quanto eu vou pagar pra fazer uma procuraçao?"
- "Faz uma simulação pra mim"

## Quando NAO chamar

- Cliente quer escritura, isenção, urgência, diligência ou ato composto
- Cliente quer **valor de outro estado** (so atendemos MG)
- Cliente quer **parcelamento** (redirecione para handoff humano)

## Cache

- Cacheie somente a resposta `PUBLISHED` junto da referência, vigência e hash da fonte.
- Nunca cacheie uma decisão `HITL_REQUIRED` como preço.
