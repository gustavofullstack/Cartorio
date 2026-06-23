# Cartório Bot - Pesquisa de Satisfação (Pós-Atendimento)

Quando um atendimento e CONCLUIDO no Chatwoot (workflow N8N #07 ja faz isso),
o bot envia uma pesquisa curta para o cliente medir qualidade do atendimento.

## Endpoint

### 1. Marcar pesquisa como enviada (no CRM)

```
POST https://api.2notasudi.com.br/api/v1/atendimento/{atendimento_id}/pesquisa-enviada
Headers:
  X-API-Key: $CARTORIO_API_KEY
```

(Pesquisa ja foi enviada pelo N8N #07. Este endpoint apenas MARCA no DB.)

### 2. Resposta esperada

Se o cliente responder a pesquisa (1-5 estrelas), o OpenClaw
**nao processa** - vai via Chatwoot, que ja tem painel proprio.

## Quando o cliente responde "Como foi o atendimento?"

Voce pode oferecer a pesquisa **se**:

1. Cliente acabou de concluir um atendimento (status="concluido")
2. Cliente NAO respondeu pesquisa nos ultimos 30 dias
3. Cliente NAO e reincidente (3+ pesquisas no mes = spam)

Voce pode oferecer a pesquisa **mesmo que nao atenda esses criterios**, mas marque como "concierge" e NAO salve.

## Mensagem template (PT-BR)

```
Ola [nome]! Tudo bem?

Voce acabou de ser atendido pelo cartorio. Pode nos ajudar
a melhorar com uma avaliacao rapidinha?

⭐⭐⭐⭐⭐ Otimo
⭐⭐⭐⭐ Bom
⭐⭐⭐ Regular
⭐⭐ Ruim
⭐ Pessimo

Responde com o numero de estrelas (1 a 5) e a gente
encaminha para o escrevente responsavel. Obrigado!
```

## Quando NAO oferecer

- Cliente pediu cancelamento (LGPD art. 7 V - revogacao)
- Cliente ja reclamou (handoff ja escalado)
- Cliente com menos de 18 anos (LGPD)
- Emojis ja vieram (cliente ta bravo, NAO manda pesquisa)

## LGPD

- Pesquisa e opcional, **cliente pode recusar** sem perder atendimento
- NAO persistir respostas da pesquisa no OpenClaw (vai pro Chatwoot)
- Se cliente responder 1 ou 2 estrelas: handoff automatico pro escrevente
- Resposta 3+ estrelas: agradece e encerra
- Retencao da resposta: 90 dias (anonimizada, so estrelas agregadas)

## Cache

- TTL: 24h (cliente que respondeu nao recebe de novo)
- Storage: in-memory
- Invalida: 30 dias (depois cliente pode receber de novo)

## Edge cases

- Cliente responde com emoji diferente: tentar normalizar (🌟 = 1⭐, ⭐ = 1, etc)
- Cliente responde com texto livre: agradeca, NAO classifique (handoff)
- Cliente ja enviou: "Obrigado, ja respondi" - agradecer e NAO enviar de novo
