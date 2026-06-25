# B14 — Macros Handoff Humano: 10 Macros Chatwoot

> Cartório 2º Notas Uberlândia — Agent AI Chatbot
> Macros para HITL (Human In The Loop) — pausar agent e transferir para humano
> LGPD: NÃO incluir PII nos templates

## Como usar

1. Acessar Chatwoot → Settings → Macros
2. Criar cada macro com nome + ação
3. Macros são acionadas pelo agent AI ou humano via Chatwoot UI

---

## 🔄 Macros de Transferência

### macro_transferir_escritor
```json
{
  "name": "Transferir para Escrevente",
  "description": "Transfere atendimento para escrivente especializado",
  "actions": [
    {"type": "assign_team", "value": "escritor"},
    {"type": "add_label", "value": "transferido-escritor"},
    {"type": "send_message", "value": "Transferindo para um escrevente especializado. Aguarde um momento."}
  ]
}
```

### macro_transferir_gerente
```json
{
  "name": "Transferir para Gerente",
  "description": "Transfere atendimento para gerente do cartório",
  "actions": [
    {"type": "assign_team", "value": "gerencia"},
    {"type": "add_label", "value": "transferido-gerente"},
    {"type": "send_message", "value": "Encaminhando para a gerência. Um atendente humano assumirá em breve."}
  ]
}
```

### macro_transferir_suporte
```json
{
  "name": "Transferir para Suporte Técnico",
  "description": "Transfere para suporte técnico do sistema",
  "actions": [
    {"type": "assign_team", "value": "suporte"},
    {"type": "add_label", "value": "transferido-suporte"},
    {"type": "send_message", "value": "Transferindo para suporte técnico. Descreva o problema que encontrou."}
  ]
}
```

---

## 🏷️ Macros de Identificação

### macro_identificar_cliente
```json
{
  "name": "Identificar Cliente",
  "description": "Solicita dados de identificação do cliente",
  "actions": [
    {"type": "add_label", "value": "identificacao-pendente"},
    {"type": "send_message", "value": "Para prosseguir, preciso identificá-lo. Por favor, informe:\n1. Nome completo\n2. CPF (últimos 4 dígitos)\n3. Data de nascimento"}
  ]
}
```

### macro_verificar_documento
```json
{
  "name": "Verificar Documento",
  "description": "Solicita envio de documento para verificação",
  "actions": [
    {"type": "add_label", "value": "verificacao-documento"},
    {"type": "send_message", "value": "Preciso verificar um documento. Por favor, envie uma foto ou PDF do documento solicitado."}
  ]
}
```

---

## 📝 Macros de Resumo

### macro_resumo_atendimento
```json
{
  "name": "Resumo do Atendimento",
  "description": "Gera resumo do atendimento para handoff",
  "actions": [
    {"type": "add_label", "value": "resumo-gerado"},
    {"type": "send_message", "value": "📋 **Resumo do Atendimento**\n\nCliente: {contact.name}\nProtocolo: {custom_attributes.protocolo}\nServiço: {custom_attributes.servico}\nStatus: {custom_attributes.status}\n\n**Histórico:**\n{conversation_messages}\n\n**Próximos passos:**\n{custom_attributes.proximos_passos}"}
  ]
}
```

### macro_resumo_rapido
```json
{
  "name": "Resumo Rápido",
  "description": "Resumo breve para transferência",
  "actions": [
    {"type": "send_message", "value": "Transferindo atendimento. Resumo:\n• Cliente: {contact.name}\n• Demanda: {last_message}\n• Tags: {conversation_labels}\n• Tempo: {conversation_duration}"}
  ]
}
```

---

## ⏸️ Macros de Pausa (HITL)

### macro_pausar_agent
```json
{
  "name": "Pausar Agent AI",
  "description": "Pausa o agent AI e aguarda humano",
  "actions": [
    {"type": "add_label", "value": "agent-pausado"},
    {"type": "send_message", "value": "Estou transferindo para um atendente humano. Aguarde um momento."}
  ]
}
```

### macro_retomar_agent
```json
{
  "name": "Retomar Agent AI",
  "description": "Retoma atendimento automático após resolução",
  "actions": [
    {"type": "remove_label", "value": "agent-pausado"},
    {"type": "add_label", "value": "agent-retomado"},
    {"type": "send_message", "value": "Atendimento retomado. Posso ajudar com mais alguma coisa?"}
  ]
}
```

### macro_encerrar_com_resumo
```json
{
  "name": "Encerrar com Resumo",
  "description": "Encerra atendimento enviando resumo final",
  "actions": [
    {"type": "send_message", "value": "✅ Atendimento encerrado.\n\nResumo final:\n• Protocolo: {custom_attributes.protocolo}\n• Status: Concluído\n• Próximos passos: {custom_attributes.proximos_passos}\n\nObrigado pelo contato! Para novas dúvidas, estou à disposição."},
    {"type": "add_label", "value": "encerrado"}
  ]
}
```

---

## 📊 Total: 10 Macros

| Categoria | Qtd | Macros |
|-----------|-----|--------|
| Transferência | 3 | escritor, gerente, suporte |
| Identificação | 2 | cliente, documento |
| Resumo | 2 | completo, rápido |
| Pausa HITL | 3 | pausar, retomar, encerrar |

**Total: 10 macros handoff humano**

---

> LGPD: Nenhuma macro contém dados pessoais reais.
> Macros usam variáveis do Chatwoot ({contact.name}, etc.)
> Labels são usados para filtrar e relatar atendimentos.
