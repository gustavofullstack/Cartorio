# Evolution API v2.3.7 — Documentação Oficial (DOCS1)

> **Versão Evolution API**: 2.3.7
> **Data download**: 2026-06-26
> **Fonte**: https://docs.evolutionfoundation.com.br (llms.txt index)
> **OpenAPI specs**: https://docs.evolutionfoundation.com.br/api-reference/openapi/Evolution-API/

API REST open-source para WhatsApp e mensageria multicanal.

---

## 📐 Arquitetura

- **Multi-provedor**: Baileys (WhatsApp Web) + WhatsApp Cloud API (Meta)
- **Chatbot Integrations**: Typebot, Chatwoot, OpenAI, Dify, Flowise, N8N
- **Event Integrations**: WebSocket, RabbitMQ, SQS, NATS, Pusher
- **Storage Integrations**: S3, MinIO
- **Stack**: Node.js 20+ | TypeScript 5+ | Express.js | Prisma ORM (PostgreSQL ou MySQL)
- **Cache recomendado**: Redis

---

## 🟢 Endpoints — Categoria Instance (14 endpoints)

| # | Endpoint | Descrição |
|---|----------|-----------|
| 1 | Create Instance | Criar nova instância WhatsApp |
| 2 | Connect Instance | Conectar instância ao WhatsApp |
| 3 | Fetch All Instances | Listar todas as instâncias |
| 4 | Delete Instance | Deletar uma instância |
| 5 | Logout Instance | Logout e desconectar instância |
| 6 | Restart Instance | Reiniciar instância WhatsApp |
| 7 | Get Connection State | Estado atual de conexão da instância |
| 8 | Get Settings | Configurações da instância |
| 9 | Set Settings | Configurar instância |
| 10 | Get Proxy | Configuração de proxy |
| 11 | Set Proxy | Configurar proxy para instância |
| 12 | Set Presence | Status de presença da instância |
| 13 | Set WebSocket | Configurar eventos WebSocket |
| 14 | Check WhatsApp Numbers | Verificar se números estão no WhatsApp |

---

## 🟢 Endpoints — Categoria Message (12 endpoints)

| # | Endpoint | Descrição |
|---|----------|-----------|
| 1 | Send Text Message | Enviar mensagem de texto |
| 2 | Send Media Message | Enviar mídia (imagem, vídeo, documento, áudio) |
| 3 | Send Buttons | Enviar mensagem com botões interativos |
| 4 | Send List | Enviar lista interativa |
| 5 | Send Poll | Enviar enquete |
| 6 | Send Contact | Enviar cartão de contato |
| 7 | Send Location | Enviar localização |
| 8 | Send Reaction | Enviar reação emoji a mensagem |
| 9 | Send Template Message | Enviar template WhatsApp Business |
| 10 | Offer Call | Iniciar chamada |
| 11 | Mark Message as Read | Marcar mensagem como lida |
| 12 | Find Messages | Buscar e filtrar mensagens |

---

## 🟢 Endpoints — Categoria Group (4 endpoints)

| # | Endpoint | Descrição |
|---|----------|-----------|
| 1 | Create Group | Criar novo grupo WhatsApp |
| 2 | Get Group Info | Informações do grupo |
| 3 | Get Participants | Listar participantes |
| 4 | Update Participant | Add, remover, promover ou rebaixar participante |

---

## 🟢 Endpoints — Categoria Chat (3 endpoints)

| # | Endpoint | Descrição |
|---|----------|-----------|
| 1 | Archive Chat | Arquivar ou desarquivar chat |
| 2 | Find Chats | Buscar e filtrar chats |
| 3 | Find Contacts | Buscar e filtrar contatos |

---

## 🟢 Endpoints — Categoria Webhook (2 endpoints)

| # | Endpoint | Descrição |
|---|----------|-----------|
| 1 | Get Webhook | Obter configuração de webhook |
| 2 | Set Webhook | Configurar webhook para eventos |

**Eventos suportados** (5 no nosso config):
- `MESSAGES_UPSERT` — Nova mensagem recebida
- `MESSAGES_UPDATE` — Mensagem atualizada (lida, etc)
- `SEND_MESSAGE` — Mensagem enviada
- `CONNECTION_UPDATE` — Status da conexão WhatsApp
- `CALL` — Chamadas

---

## 🟢 Endpoints — Categoria Profile (3 endpoints)

| # | Endpoint | Descrição |
|---|----------|-----------|
| 1 | Update Profile Name | Atualizar nome do perfil WhatsApp |
| 2 | Update Profile Picture | Atualizar foto do perfil |
| 3 | Update Profile Status | Atualizar mensagem de status |

---

## 🟢 Outros Endpoints

### Template (4)
- Create Template | Delete Template | Edit Template | Find Templates

### Label (2)
- Get Labels | Handle Label (add/remove label from chat/message)

### Business/Catalog (2)
- Get Catalog | Get Collections

---

## 📊 Total: 46 endpoints oficiais

| Categoria | Total |
|----------|-------|
| Instance | 14 |
| Message | 12 |
| Group | 4 |
| Chat | 3 |
| Webhook | 2 |
| Profile | 3 |
| Template | 4 |
| Label | 2 |
| Business/Catalog | 2 |
| **TOTAL** | **46** |

---

## 🔐 Webhook Signature Validation

Evolution API suporta validação de assinatura HMAC para webhooks externos:
- Header customizado para assinatura
- Validação server-side
- Recomendado para integrações que recebem webhooks

---

## ⚙️ Variáveis de Ambiente Essenciais

```bash
DATABASE_PROVIDER=postgresql  # ou mysql
DATABASE_CONNECTION_URI=postgres://user:pass@host:5432/db
REDIS_URI=redis://host:6379
AUTHENTICATION_API_KEY=<sua-chave-secreta>
SERVER_PORT=8080
```

---

## 🔗 Integração com nosso Sistema

| Componente | Uso |
|------------|-----|
| **Evolution API v2.3.7** | Gateway WhatsApp entrada (whatsapp.2notasudi.com.br) |
| **Webhook N8N** | /webhook/evo-in → workflow 01 (MESSAGES_UPSERT) |
| **API FastAPI** | POST /message/sendText (proxy reverso) |
| **OpenClaw** | Recebe texto via API → processa → envia resposta |

---

## 📚 Fontes Adicionais

- **OpenAPI specs**: https://docs.evolutionfoundation.com.br/api-reference/openapi/Evolution-API/{instance,message,group,chat,events,profile}.yaml
- **GitHub**: https://github.com/EvolutionAPI/evolution-api
- **llms.txt index**: https://docs.evolutionfoundation.com.br/llms.txt

---

**Modified by**: ZCode/Mavis (orquestrador)
**Próxima ação**: integrar este catálogo na skill `prompt-cartorio` para consumo por agents
**Status**: ✅ DOCS1 DONE — 46 endpoints oficiais catalogados