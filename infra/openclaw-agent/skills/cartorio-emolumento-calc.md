# Cartório Bot - Cálculo de Emolumento

Quando o cliente perguntar o **valor** de um ato cartorário, consulte a API
de cálculo. **NUNCA** invente valores — emolumento é regulado pela
TABELA_2026_MG e tem valores oficiais. Inventar = responsabilidade legal.

## Endpoint

```
GET https://api.2notasudi.com.br/api/v1/emolumento/calcular?tipo={tipo}
Headers:
  X-API-Key: $CARTORIO_API_KEY
```

## Tipos válidos (TABELA_2026_MG)

| tipo | Descrição | Valor aproximado |
|------|-----------|------------------|
| certidao_negativa | Certidão negativa de propriedade | R$ 87,50 |
| certidao_positiva | Certidão positiva de propriedade | R$ 87,50 |
| certidao_casamento | Certidão de casamento | R$ 105,40 |
| escritura_compra_venda | Escritura de compra e venda de imóvel | R$ 350,00+ (varia) |
| escritura_doacao | Escritura de doação | R$ 280,00+ |
| procuracao | Procuração | R$ 156,40 |
| autenticacao | Autenticação de cópia | R$ 5,50 / folha |
| reconhecimento_firma | Reconhecimento de firma | R$ 8,90 |
| registro_nascimento | Registro de nascimento | R$ 0 (gratuito) |
| registro_obito | Registro de óbito | R$ 0 (gratuito) |

## Exemplo de chamada

```bash
curl -s -H "X-API-Key: $CARTORIO_API_KEY" \
  "https://api.2notasudi.com.br/api/v1/emolumento/calcular?tipo=escritura_compra_venda"
```

## Resposta (sucesso 200)

```json
{
  "tipo": "escritura_compra_venda",
  "valor_base": 350.00,
  "valor_adicional": 35.00,
  "valor_total": 385.00,
  "tabela_referencia": "TABELA_2026_MG",
  "prazo_dias": 5,
  "detalhes": {
    "isencao": false,
    "observacoes": "Valor base pode variar conforme complexidade do imovel."
  }
}
```

## Como responder ao cliente (PT-BR natural)

### Caso 1: valor retornado com sucesso
```
Simulei aqui o valor para você! 💰

📄 Tipo: escritura_compra_venda
💵 Valor base: R$ 350,00
💵 Adicional: R$ 35,00
💵 **Total: R$ 385,00**
⏰ Prazo: 5 dias úteis
📋 Tabela: TABELA_2026_MG

⚠️ Esse valor é uma SIMULAÇÃO. O valor final é confirmado pelo escrevente
no momento do atendimento, após análise do caso.

Quer que eu agende um horário para você vir ao cartório?
```

### Caso 2: tipo invalido
```
Hmm, não reconheço esse tipo de ato. Você quis dizer:

- escritura_compra_venda
- escritura_doacao
- procuracao
- certidao_casamento
- autenticacao
- reconhecimento_firma

Qual desses é o que você precisa?
```

## LGPD

- NUNCA persista o valor calculado. Cliente pode ter isencao (idoso, doador
  de orgaos, etc) que altera o valor final.
- NUNCA envie o valor para LLM publica sem scrub (mas emolumento nao eh
  PII, entao pode ir direto).
- Cliente pode pedir "quanto custa para fazer X pra minha irma?" — NAO
  faca calculo para outra pessoa. Redirecione: "O calculo so pode ser
  feito para voce mesmo. Sua irma precisa falar conosco pelo WhatsApp dela."

## Quando chamar esta skill

- "Quanto custa uma escritura?"
- "Qual o valor de uma certidao?"
- "Quanto eu vou pagar pra fazer uma procuraçao?"
- "Faz uma simulação pra mim"

## Quando NAO chamar

- Cliente quer **calcular isento** (precisa ir ao balcao, escrevente valida)
- Cliente quer **valor de outro estado** (so atendemos MG)
- Cliente quer **parcelamento** (redirecione para handoff humano)

## Cache

- TTL: 24 horas (valores raramente mudam, so anual)
- Storage: in-memory no OpenClaw
- Invalida em: 1o dia util de cada ano (atualizacao da tabela MG)
