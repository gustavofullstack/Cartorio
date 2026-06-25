# Evolution API v2 — Documentação Consolidada

> **Fonte**: GitHub oficial `evolution-foundation/evolution-api` + site docs
> **Versão**: v2.3.7 (última release 2025-12-05)
> **Stack**: Node.js 20+, TypeScript 5+, Express.js, Prisma ORM
> **Licença**: Apache 2.0

---

## 🏗️ Arquitetura

```
Client / CRM (Chatwoot, N8N, nossa API)
     ↓
Evolution API v2
├── Channel Integrations
│   ├── Baileys (WhatsApp Web — gratuito, lib Baileys)
│   └── WhatsApp Cloud API (Meta oficial — enterprise)
├── Chatbot Integrations
│   ├── Typebot
│   ├── Chatwoot
│   ├── OpenAI
│   ├── Dify
│   ├── Flowise
│   └── N8N
├── Event Integrations
│   ├── WebSocket
│   ├── RabbitMQ
│   ├── SQS
│   ├── NATS
│   └── Pusher
└── Storage Integrations
    ├── S3
    └── MinIO
```

---

## 🔐 Autenticação

| Tipo | Como |
|------|------|
| **API key** | Header `apikey: <sua-chave>` |
| **Instance token** | Token específico por instância WhatsApp |
| **Webhook signature** | Validação de assinatura para integrações externas |

---

## 📡 Variáveis de Ambiente Importantes

Ver `.env.example` completo em: <https://github.com/evolution-foundation/evolution-api/blob/main/.env.example>

| Variável | Descrição |
|----------|-----------|
| `DATABASE_PROVIDER` | `postgresql` ou `mysql` |
| `DATABASE_*` | URL, user, senha do DB |
| `REDIS_*` | Configuração Redis (cache) |
| `AUTHENTICATION_API_KEY` | Chave mestra da API |
| `WEBHOOK_GLOBAL_URL` | URL global para webhooks |
| `WEBHOOK_GLOBAL_ENABLED` | Habilitar webhook global |
| `RABBITMQ_*` | Se usar RabbitMQ para events |
| `S3_*` | Se usar S3 para storage |
| `CHATWOOT_*` | Integração Chatwoot |
| `OPENAI_*` | Integração OpenAI |
| `TYPEBOT_*` | Integração Typebot |
| `N8N_*` | Integração N8N |

---

## 📚 Links Úteis

| Recurso | URL |
|---------|-----|
| Docs oficial | https://docs.evolutionfoundation.com.br |
| GitHub | https://github.com/evolution-foundation/evolution-api |
| Website | https://evolutionfoundation.com.br |
| Docker Hub | https://hub.docker.com/r/evoapicloud/evolution-api |
| Suporte | suporte@evofoundation.com.br |
| v2.3.7 release | https://github.com/evolution-foundation/evolution-api/releases |
| CHANGELOG | https://github.com/evolution-foundation/evolution-api/blob/main/CHANGELOG.md |

---

## 🔌 Nossa Integração (Cartório)

Nossa instância: `cartorio-2notas` (state=close, aguardando QR scan)

**Manager UI**: https://whatsapp.2notasudi.com.br/manager

**Eventos webhook configurados** (5):
- `MESSAGES_UPSERT` — Nova mensagem recebida
- `MESSAGES_UPDATE` — Mensagem atualizada (lida, etc)
- `SEND_MESSAGE` — Mensagem enviada
- `CONNECTION_UPDATE` — Status da conexão WhatsApp
- `CALL` — Chamadas

**Webhook N8N**: `https://flow.2notasudi.com.br/webhook/evo-in`

**Integração com nosso sistema**:
```
EVOLUTION-API → N8N → API → [SUPABASE + REDIS + OPENCLAW] → CHATWOOT
```

**Backup de config**: `/etc/easypanel/projects/cartorio/evolution-api/`

---

## ⚠️ Status Atual (2026-06-25)

- ✅ Evolution API UP e funcionando (v2.3.7)
- ✅ Webhook configurado para N8N
- ✅ WhatsApp TriQ Hub conectado para testes
- ⚠️ Instance `cartorio-2notas`: state=close → **Gustavo precisa escanear QR (SUI)**

---

## 🎯 Próximas Ações (Sprint 5+)

- [ ] Gustavo: escanear QR WhatsApp Business (SUI)
- [ ] Gustavo: criar DNS A records pendentes (SUI)
- [ ] Agent: configurar credential Evolution API no N8N (para WF #07)
- [ ] Agent: testar E2E WhatsApp TriQ Hub