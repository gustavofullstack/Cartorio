# Cartório Bot - Handoff Trigger (escalação humana)

Esta skill nao chama API. **Define REGRAS** de quando o OpenClaw deve
transferir o atendimento para um escrevente humano via Chatwoot.

## Quando fazer handoff (OBRIGATORIO)

Handoff eh **OBRIGATORIO** quando QUALQUER destas condicoes for verdadeira:

1. **PII detectado** - cliente mandou CPF/RG/documento no chat
   (ja eh bloqueado por `pii_block_on_detect=true` na API)
2. **Cliente pediu para falar com humano** - "Quero falar com alguem",
   "Me passa para o escrevente", "Vou ligar"
3. **Cliente expressou frustracao/insatisfacao** - "Nao resolve nada",
   "Pessimo atendimento", "Vou reclamar", "Ja tentei varias vezes"
4. **LLM errou 2+ vezes** - mesma pergunta do cliente retornou resposta
   quebrada/incorreta consecutivamente
5. **Pedido juridico complexo** - "Preciso de advice juridico",
   "Tenho duvida legal sobre", "Pode me orientar sobre o caso?"
6. **Coisas que o bot NAO sabe fazer**:
   - Cancelar protocolo (LGPD art. 7 V - revogacao so via DPO)
   - Reembolso / devolucao de emolumento
   - Agendamento de casamento (civil - requer comparecimento)
   - Reconhecimento de firma por semelhanca (escrevente valida)
7. **Cliente eh idoso, PCD, ou tem dificuldade tecnica** - redundancia
   de tentativas, fala truncada, sem aceno

## Como fazer o handoff

### Via Chatwoot (oficial, recomendado)

```bash
# 1. Criar conversa (se nao existir)
curl -X POST -H "api_access_token: $CHATWOOT_BOT_TOKEN" \
     -H "Content-Type: application/json" \
     -d "{\"source_id\": \"$SESSION_ID\", \"contact\": {\"phone_number\": \"$PHONE\"}}" \
     https://chatwoot.2notasudi.com.br/api/v1/accounts/1/conversations

# 2. Criar mensagem como bot com handoff reason
curl -X POST -H "api_access_token: $CHATWOOT_BOT_TOKEN" \
     -H "Content-Type: application/json" \
     -d "{\"content\": \"$HANDOFF_MESSAGE\", \"message_type\": \"outgoing\"}" \
     https://chatwoot.2notasudi.com.br/api/v1/accounts/1/conversations/$CONV_ID/messages

# 3. Marcar conversa como "open" + assign a um agent humano
curl -X POST -H "api_access_token: $CHATWOOT_BOT_TOKEN" \
     -H "Content-Type: application/json" \
     -d "{\"status\": \"open\", \"assignee_id\": $ESCREVENTE_ID}" \
     https://chatwoot.2notasudi.com.br/api/v1/accounts/1/conversations/$CONV_ID
```

### Mensagem padrao de handoff (PT-BR natural)

```
Vou transferir seu atendimento para um dos nossos escreventes
especializados. Eles vao te ajudar melhor com isso.

⏱️ Tempo medio de resposta: 5-10 minutos
📋 Ja passei o historico da nossa conversa.

Aguarde um instante, ok?
```

Adicionar motivo do handoff em uma segunda mensagem (interna, nao pro cliente):

```
[HANDOFF] motivo=PII detectado | confianca=alta | sessao_id=$SESSION_ID
```

## Audit log (LGPD art. 37)

Apos handoff bem-sucedido, registrar no audit log da API:

```bash
curl -X POST -H "apikey: $CARTORIO_API_KEY" \
     -H "X-Canal: openclaw" \
     -H "Content-Type: application/json" \
     -d "{
       \"actor_id\": \"openclaw:handoff:$SESSION_ID\",
       \"action\": \"atendimento.handoff\",
       \"resource\": \"atendimento:$ATENDIMENTO_ID\",
       \"payload\": {
         \"motivo\": \"$MOTIVO\",
         \"confianca\": \"alta\",
         \"destino\": \"chatwoot:conversa:$CONV_ID\"
       }
     }" \
     https://api.2notasudi.com.br/api/v1/audit/log
```

(Mesma rota `POST /audit/log` que adicionamos no v0.5.2)

## NAO fazer handoff (continuar bot)

- Duvida simples sobre horarios / endereco / documentos necessarios
- Pedido de orcamento (skill `cartorio-emolumento-calc`)
- Consulta de status de protocolo (skill `cartorio-protocolo-tracker`)
- Saudacao inicial

## Retry policy (handoff falhou?)

Se o POST pro Chatwoot retornar 5xx, **tentar ate 3x** com backoff 1s/3s/9s.
Se apos 3x ainda falhar:

1. Logar erro no audit com `action=atendimento.handoff.failed`
2. Mandar mensagem direta ao cliente: "Tivemos uma instabilidade. Vou te chamar no WhatsApp em 5 min. Pode me enviar seu telefone?"
3. Alertar o escrevente via Telegram (Sprint 4)

## LGPD

- Mensagem de handoff NAO pode conter PII (mesma regra do bot em geral)
- Auditoria de handoff deve registrar `actor_id=openclaw` (sempre, mesmo ID)
- Chatwoot tem sua propria auditoria (LGPD cartorio config)
- Cliente pode revogar consentimento a qualquer momento - nesse caso, **encerrar handoff** e apagar conversa

## Cache

- TTL: 0 (handoff eh evento unico, NAO cachear)
- Armazenamento: N8N workflow #03 (handoff) tem logica propria de retry
