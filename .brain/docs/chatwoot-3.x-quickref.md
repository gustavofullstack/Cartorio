# Chatwoot 3.x — Quick Reference

**Source**: https://www.chatwoot.com/developers/api/
**Versao em uso**: 3.x (chat.2notasudi.com.br, DNS_LOST externo / online interno)
**Atualizado**: 2026-06-25

## 1. Autenticacao

Header: `api_access_token: <CHATWOOT_API_KEY>`

```bash
# API key (a ser gerada via Rails console)
docker exec cartorio_chatwoot-1 bash -c "\
  bundle exec rails runner 'User.first.accounts.first.access_tokens.create(name: \"cartorio-api\").save_token'"
```

## 2. Endpoints Principais

```bash
CHATWOOT_URL="https://chat.2notasudi.com.br"  # ou http://cartorio_chatwoot:3000 interno
TOKEN="<api_access_token>"

# Listar accounts
GET /api/v1/accounts

# Listar inboxes
GET /api/v1/accounts/{account_id}/inboxes

# Listar conversas
GET /api/v1/accounts/{account_id}/conversations?status=open

# Listar contacts
GET /api/v1/accounts/{account_id]/contacts

# Criar/atualizar contact
POST /api/v1/accounts/{account_id}/contacts
Body: {"name": "Joao", "email": "...", "phone_number": "+5534..."}

# Enviar mensagem
POST /api/v1/accounts/{account_id}/conversations/{cid}/messages
Body: {"content": "Ola!", "message_type": "outgoing", "private": false}

# Toggle status (pausar agente IA)
POST /api/v1/accounts/{account_id}/conversations/{cid}/toggle
Body: {"status": "resolved" | "open" | "pending" | "snoozed"}

# Adicionar label
POST /api/v1/accounts/{account_id}/conversations/{cid}/labels
Body: {"labels": ["novo", "protocolo"]}

# Canned responses
GET /api/v1/accounts/{account_id]/canned_responses
POST /api/v1/accounts/{account_id]/canned_responses
```

## 3. Webhook Events

Configuraveis em Settings -> Webhooks:

| Evento | Quando | Payload |
|---|---|---|
| `message_created` | msg recebida/enviada | {id, content, conversation, sender} |
| `message_updated` | msg editada | {id, content} |
| `conversation_created` | nova conversa | {id, status, contact} |
| `conversation_status_changed` | status mudou | {id, status} |
| `webwidget_triggered` | usuario abriu chat | {contact, ...} |
| `contact_created` | novo contact | {id, name, email} |
| `contact_updated` | contact editado | {id, ...} |

## 4. Custom Attributes (H2)

```bash
# Criar definicao
POST /api/v1/accounts/{account_id}/custom_attribute_definitions
Body: {
  "attribute_display_name": "CPF/CNPJ hash",
  "attribute_key": "cpf_cnpj_hash",
  "attribute_model": "contact",  # ou "conversation"
  "attribute_display_type": "text"
}

# Setar valor em contact
POST /api/v1/accounts/{account_id}/contacts/{cid}/custom_attributes
Body: {"cpf_cnpj_hash": "abc123..."}
```

Atributos H2 (8 total):
- cpf_cnpj_hash (text, contact)
- protocolo_id (number, conversation)
- emolumento_total_centavos (number, conversation)
- lgpd_consent_granted (checkbox, contact)
- lgpd_consent_at (date, contact)
- servico_interesse (list, conversation)
- canal_origem (list, contact)
- agente_ia_pausado (checkbox, conversation)

## 5. Canned Responses (H4)

52 templates em `docs/canned-responses-chatwoot.json` (B13).
Categorias: saudacao, info, servico, valor, agendamento, feedback, juridico, restricao, lgpd, acessibilidade, protocolo, transfer.

## 6. Macros (H3)

10 macros M-H01 a M-H10 (docs/chatwoot-setup-2026-06-25.json):
- M-H01: Pausar agente IA
- M-H02: Reabrir com agente IA
- M-H03: Atribuir a escrevente
- M-H04: Adicionar label juridico
- M-H05: Adicionar label LGPD-pendente
- M-H06: Escalar supervisor
- M-H07: Aplicar macro + nota privada
- M-H08: Marcar como resolvido
- M-H09: Snooze 1h
- M-H10: Transferir para setor

## 7. Labels (H5)

10 labels canonicos: novo, protocolo, emolumento, documento, concluido, pausado, urgente, lgpd-pendente, lead-frio, vip.

## 8. Gotchas

- API key NAO vem em /api/v1/accounts (precisa criar via Rails console)
- Webhook signature eh HMAC-SHA256
- Custom attributes sao por-account (precisa criar em cada account)
- Labels sao globais por account (compartilhadas)
- Conversation status: open/resolved/pending/snoozed

## 9. Integracao com N8N + Cartorio

```
[WhatsApp] -> [Evolution API] -> [N8N WF] -> [Chatwoot API] -> [Chatwoot UI]
                                              (cria contact, conversation)
[HUMANO]   <- [Chatwoot UI]  <- [Chatwoot API] <- [N8N WF] <- [API Cartorio]
```

N8N WF 03-handoff-human-chatwoot.json faz a ponte.

## 10. Backup

```bash
docker exec cartorio_chatwoot-1 bash -c "\
  bundle exec rails runner 'puts Account.first.to_json'"
# Salvar saida em /var/backups/chatwoot/YYYYMMDD.json
```

Modified by Pietra + Gustavo Almeida 2026-06-25
