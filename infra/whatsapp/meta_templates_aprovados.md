# B15 — Templates WhatsApp Meta Aprovados: 11 Templates

> Cartório 2º Notas Uberlândia — Agent AI Chatbot
> Templates para WhatsApp Business API (Evolution API)
> Aprovação: Meta Business Manager → Message Templates
> LGPD: NÃO incluir PII nos templates

## Como submeter para aprovação

1. Acessar Meta Business Manager → Message Templates
2. Criar template com categoria + linguagem
3. Enviar para aprovação (24-48h)
4. Após aprovação, usar via Evolution API

---

## 📋 CATEGORIA: UTILITY (Uso geral)

### cartorio_protocolo_novo
```
Nome: cartorio_protocolo_novo
Categoria: Utility
Idioma: pt_BR
Body:
Olá {{1}}! Seu protocolo foi criado com sucesso.

📋 Protocolo: {{2}}
📅 Data: {{3}}
⏰ Prazo estimado: {{4}}

Para acompanhar, acesse nosso canal ou digite /consultar.

Cartório 2º Notas de Uberlândia
```
**Variáveis**: nome, protocolo, data, prazo

### cartorio_protocolo_status
```
Nome: cartorio_protocolo_status
Categoria: Utility
Idioma: pt_BR
Body:
Olá {{1}}! Status do seu protocolo:

📋 Protocolo: {{2}}
📊 Status: {{3}}
📝 Detalhes: {{4}}

Próximos passos: {{5}}

Cartório 2º Notas de Uberlândia
```
**Variáveis**: nome, protocolo, status, detalhes, proximos_passos

### cartorio_documento_pronto
```
Nome: cartorio_documento_pronto
Categoria: Utility
Idioma: pt_BR
Body:
Olá {{1}}! Seu documento está pronto para retirada.

📄 Documento: {{2}}
📋 Protocolo: {{3}}
📍 Local: Cartório 2º Notas de Uberlândia
🕐 Horário: seg-sex 8h-17h, sáb 8h-12h

Traga documento de identidade com foto.

Cartório 2º Notas de Uberlândia
```
**Variáveis**: nome, documento, protocolo

### cartorio_agendamento_confirmado
```
Nome: cartorio_agendamento_confirmado
Categoria: Utility
Idioma: pt_BR
Body:
Olá {{1}}! Seu agendamento foi confirmado.

📅 Data: {{2}}
⏰ Horário: {{3}}
📍 Local: Cartório 2º Notas de Uberlândia
📄 Serviço: {{4}}

Chegue 15 minutos antes com todos os documentos.

Cartório 2º Notas de Uberlândia
```
**Variáveis**: nome, data, horario, servico

---

## 📋 CATEGORIA: MARKETING (Comunicação)

### cartorio_boas_vindas
```
Nome: cartorio_boas_vindas
Categoria: Marketing
Idioma: pt_BR
Body:
Olá {{1}}! 👋

Bem-vindo ao Cartório 2º Notas de Uberlândia!

Sou seu assistente virtual e posso ajudar com:
📋 Protocolos e atendimentos
💰 Tabelas de emolumentos
📅 Agendamentos
📜 Informações sobre serviços

Como posso ajudar?

Cartório 2º Notas de Uberlândia
```
**Variáveis**: nome

### cartorio_promocao
```
Nome: cartorio_promocao
Categoria: Marketing
Idioma: pt_BR
Body:
Olá {{1}}! 📢

{{2}}

Para mais informações, acesse nosso canal ou entre em contato.

Cartório 2º Notas de Uberlândia

Para não receber mais mensagens, responda SAIR.
```
**Variáveis**: nome, mensagem

### cartorio_lembrete
```
Nome: cartorio_lembrete
Categoria: Marketing
Idioma: pt_BR
Body:
Olá {{1}}! 🔔

Lembrete: {{2}}

Se precisar reagendar, estou à disposição.

Cartório 2º Notas de Uberlândia

Para não receber mais, responda SAIR.
```
**Variáveis**: nome, lembrete

---

## 📋 CATEGORIA: TRANSACTIONAL (Transações)

### cartorio_pagamento_confirmado
```
Nome: cartorio_pagamento_confirmado
Categoria: Transactional
Idioma: pt_BR
Body:
Olá {{1}}! Pagamento confirmado.

💰 Valor: R$ {{2}}
📋 Protocolo: {{3}}
📅 Data: {{4}}
💳 Forma: {{5}}

Seu atendimento prosseguirá normalmente.

Cartório 2º Notas de Uberlândia
```
**Variáveis**: nome, valor, protocolo, data, forma_pagamento

### cartorio_nfe_recebida
```
Nome: cartorio_nfe_recebida
Categoria: Transactional
Idioma: pt_BR
Body:
Olá {{1}}! Nota fiscal emitida.

📄 NF-e: {{2}}
💰 Valor: R$ {{3}}
📅 Data: {{4}}

Acesse: {{5}}

Cartório 2º Notas de Uberlândia
```
**Variáveis**: nome, nfe, valor, data, link

### cartorioErro_no_servico
```
Nome: cartorio_erro_servico
Categoria: Transactional
Idioma: pt_BR
Body:
Olá {{1}}! Occorreu um erro no processamento.

📋 Protocolo: {{2}}
⚠️ Erro: {{3}}

Nosso time já foi notificado.
Tente novamente em alguns minutos ou entre em contato.

Cartório 2º Notas de Uberlândia
```
**Variáveis**: nome, protocolo, erro

### cartorio_satisfacao
```
Nome: cartorio_satisfacao
Categoria: Transactional
Idioma: pt_BR
Body:
Olá {{1}}! Como foi seu atendimento?

⭐⭐⭐⭐⭐ (responda com 1-5 estrelas)

Sua opinião nos ajuda a melhorar!

Cartório 2º Notas de Uberlândia
```
**Variáveis**: nome

---

## 📊 Total: 11 Templates

| Categoria | Qtd | Templates |
|-----------|-----|-----------|
| Utility | 4 | protocolo_novo, status, doc_pronto, agendamento |
| Marketing | 3 | boas_vindas, promocao, lembrete |
| Transactional | 4 | pagamento, nfe, erro, satisfacao |

**Total: 11 templates WhatsApp Business API**

---

## ⚠️ Regras Meta

- Templates precisam de aprovação (24-48h)
- Variáveis `{{1}}`, `{{2}}` etc. são preenchidas via API
- Categoria deve ser precisa (utility/marketing/transactional)
- Não incluir links externos não verificados
- Não incluir PII (CPF, RG, etc.)
- Opt-out obrigatório para marketing: "Para não receber, responda SAIR"

## 🔧 Envio via Evolution API

```json
{
  "number": "5534999999999",
  "template": {
    "name": "cartorio_protocolo_novo",
    "lang": "pt_BR",
    "components": [{
      "type": "body",
      "parameters": [
        {"type": "text", "text": "João Silva"},
        {"type": "text", "text": "PROTO-2026-001234"},
        {"type": "text", "text": "25/06/2026"},
        {"type": "text", "text": "3 dias úteis"}
      ]
    }]
  }
}
```
