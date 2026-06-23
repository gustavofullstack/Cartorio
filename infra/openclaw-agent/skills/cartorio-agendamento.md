# Cartório Bot - Agendamento de Atendimento

Quando o cliente quiser agendar um atendimento presencial no cartório, consulte
a API de disponibilidade e ofereça os slots.

## Endpoints

### 1. Consultar disponibilidade

```
GET https://api.2notasudi.com.br/api/v1/agendamento/disponibilidade
Headers:
  X-API-Key: $CARTORIO_API_KEY
```

Response 200:
```json
{
  "data": "2026-06-25",
  "slots": [
    {"hora": "09:00", "disponivel": true, "escrevente": "Maria Souza"},
    {"hora": "10:30", "disponivel": false, "escrevente": "Maria Souza", "motivo": "ocupado"},
    {"hora": "14:00", "disponivel": true, "escrevente": "João Silva"},
    {"hora": "15:30", "disponivel": true, "escrevente": "Maria Souza"}
  ],
  "atendimento_tipo_disponivel": ["escritura", "procuracao", "reconhecimento_firma"]
}
```

### 2. Criar agendamento (Sprint 3.5+)

```
POST https://api.2notasudi.com.br/api/v1/agendamento
Headers:
  X-API-Key: $CARTORIO_API_KEY
  X-Canal: openclaw
Body:
{
  "cliente_id": 42,
  "data": "2026-06-25",
  "hora": "09:00",
  "tipo": "escritura",
  "canal_origem": "whatsapp",
  "observacoes": "Cliente ja enviou documentos por email"
}
```

## Como responder ao cliente (PT-BR natural)

### Passo 1: entender o que o cliente precisa

Antes de oferecer slots, **sempre perguntar o tipo de atendimento**:
- "Voce quer agendar para que tipo de atendimento? (escritura, procuraçao, reconhecimento de firma, etc.)"

### Passo 2: oferecer slots

```
Para [tipo], temos estes horarios disponiveis nos proximos dias:

📅 Hoje, [data]:
- ⏰ 09:00 (Maria Souza)
- ⏰ 14:00 (João Silva)
- ⏰ 15:30 (Maria Souza)

📅 Amanha, [data]:
- ⏰ 09:30
- ⏰ 10:00
- ⏰ 16:00

Qual horario eh melhor para voce?
```

### Passo 3: confirmar agendamento

```
Perfeito! Vou agendar:

📅 Data: [data]
⏰ Horario: [hora]
👤 Escrevente: [nome]
📋 Tipo: [tipo]

Voce recebera a confirmacao por WhatsApp 24h antes. 
Precisa de mais alguma coisa?
```

## Quando NAO agendar (handoff humano)

- Cliente quer cancelar agendamento existente - handoff (sistema tem confirmacao manual)
- Cliente quer remarcar - handoff
- Cliente tem < 18 anos sem responsavel - handoff
- Tipo de ato exige comparecimento de mais pessoas (ex: casamento civil) - handoff

## LGPD

- NAO exibir nome completo do escrevente em chat publico (usar so primeiro nome)
- Horarios vazam padrao de trabalho (pouco PII, mas documentar)
- Confirmacao de agendamento: cliente_id eh hash, NAO mostrar

## Cache

- TTL: 5 min (disponibilidade pode mudar)
- Storage: in-memory
- Invalida: em qualquer criacao de agendamento

## Edge cases

- Sem slots disponiveis no dia: oferecer proximo dia util
- Cliente pede horario especifico ja ocupado: oferecer alternativos
- Cliente fora do horario comercial: "Atendemos seg-sex 09h-17h. Posso sugerir amanha as 09h?"
