# T8 — Ativar n8n-nodes-chatwoot em WF03 (handoff-human)

## Status: PRONTO PRA EXECUTAR (SUI 1.2 cred OK)

**Dependências verificadas:**
- [x] `CHATWOOT_API_KEY` presente em backend/.env
- [x] `CHATWOOT_ACCOUNT_ID=1` em backend/.env
- [x] `CHATWOOT_INBOX_ID=1` em backend/.env
- [x] HTTP Request nodes ativos em WF03 (backup: `backups/WF03_pre_chatwoot_2026-06-29.json`)
- [x] Node type identificado: `@devlikeapro/n8n-nodes-chatwoot.Chatwoot`

**PASSO 1 — Instalar node (se não instalado)**

No N8N UI: Settings → Community Nodes → Install
```
Package: @devlikeapro/n8n-nodes-chatwoot
```

Verificar: after install, node "Chatwoot" aparece na paleta de nodes.

**PASSO 2 — Criar Chatwoot Credential no N8N**

Settings → Credentials → New → "Chatwoot API"

| Campo | Valor |
|---|---|
| API Access Token | `d22c96d044956015643a70a0d58e2ba5a3f48f1eabfb8a6b793cafd850e0e0b3` |
| Base URL | `https://chat.2notasudi.com.br` |

Salvar como: `chatwoot-api-cartorio`

**PASSO 3 — Backup workflow atual**

```bash
# Já existe: infra/n8n-workflows/backups/WF03_pre_chatwoot_2026-06-29.json
# Garantir que está intacto antes de editar
```

**PASSO 4 — Substituir HTTP Request nodes por Chatwoot node**

No N8N UI — Workflow 03 (Handoff Humano):

1. **Chatwoot: Create Conversation (httpRequest)**
   - DELETE este node
   - ADICIONAR node "Chatwoot" (procure na paleta)
   - Config:
     - Credential: `chatwoot-api-cartorio`
     - Operation: `createConversation`
     - Inbox ID: `1`
     - Account ID: `1`
     - Source ID: `{{ $json.message_id }}`
     - Contact: Phone = `{{ $json.sender }}`

2. **Chatwoot: Send Message (httpRequest)**
   - DELETE este node
   - ADICIONAR node "Chatwoot" (procure na paleta)
   - Config:
     - Credential: `chatwoot-api-cartorio`
     - Operation: `sendMessage`
     - Conversation ID: `{{ $json.id }}` (do node anterior)
     - Message: `{{ $json.text }}`
     - Message Type: `incoming`

3. **Atualizar conexões:**
   - Normalizar Payload → Chatwoot (Create Conversation)
   - Chatwoot (Create Conversation) → Chatwoot (Send Message)
   - Chatwoot (Send Message) → Respond Handoff

4. **Atualizar Respond Handoff responseBody:**
   ```json
   {
     "status": "handoff",
     "response": "Transferi para um atendente humano.",
     "chatwoot_conversation_id": {{ $('Chatwoot: Create Conversation').item.json.id }},
     "sender": "{{ $json.sender }}",
     "transport": "n8n-nodes-chatwoot"
   }
   ```

**PASSO 5 — Testar**

1. Desativar workflow antes de editar
2. Fazer test run com payload real:
```json
{
  "body": {
    "sender": "5511999999999",
    "message": {"text": "Quero falar com atendente"},
    "reason": "duvida",
    "message_id": "test-migration-001"
  }
}
```
3. Verificar: conversa criada no Chatwoot + mensagem enviada
4. Reativar workflow

**PASSO 6 — Commit do workflow atualizado**

Salvar workflow no N8N → exportar JSON:
```bash
cp /path/to/exported.json infra/n8n-workflows/03-handoff-human-chatwoot.json
git add infra/n8n-workflows/03-handoff-human-chatwoot.json
git commit -m "feat(n8n): activate n8n-nodes-chatwoot in WF03 (T8)"
```

## Rollback

Se falhar: reimportar `backups/WF03_pre_chatwoot_2026-06-29.json` no N8N.
O backup usa HTTP Request nodes — rollback automático se o node chatwoot não funcionar.

---

*Modified by Gustavo Almeida*
*T8 Sprint 4 — M2.7 Pietra (mvs_95c881...)*
