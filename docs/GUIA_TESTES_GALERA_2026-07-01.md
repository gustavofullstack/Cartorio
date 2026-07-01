# 🚀 GUIA DE TESTES — CARTÓRIO 2º NOTAS UBERLÂNDIA (2026-07-01)

> Documento para a equipe do cartório testar TUDO do bot Telegram + WhatsApp + Chatwoot + API +43 antes da entrega oficial.

**STATUS ATUAL**: 6/6 serviços online | Telegram respondendo | WhatsApp Evolution com QR pronto para parear | Chatwoot com admin | DB PostgreSQL pgvector ativo.

---

## 1. TELEGRAM BOT ✅

### Como acessar
- Abrir Telegram
- Buscar: **`@test_cartorio_bot`** (ou `test_cartorio_bot`)
- Clicar em **Iniciar**

### 20 Cenários para testar (copie/cole cada um)

| # | Comando | Esperado |
|---|---------|----------|
| 1 | `/start` | Saudação + menu principal |
| 2 | `Ola, bom dia!` | Saudação amigável |
| 3 | `Quais servicos voces oferecem?` | Lista de serviços |
| 4 | `Quero agendar um reconhecimento de firma para amanha as 14h` | Confirma agendamento |
| 5 | `Preciso ir ao cartorio hoje para uma procuracao, qual o horario disponivel?` | Horários disponíveis |
| 6 | `Preciso da segunda via de um documento. Como faco?` | Como obter 2ª via |
| 7 | `Como consulto o andamento do meu protocolo?` | Info de protocolo |
| 8 | `Quero falar com um atendente humano` | Handoff → Chatwoot |
| 9 | `Quanto custa um reconhecimento de firma?` | Tabela emolumentos |
| 10 | `Quero exercer meu direito de portabilidade LGPD` | Passo-a-passo LGPD |
| 11 | `Onde fica o cartorio? Qual o endereco?` | Endereço + horário |
| 12 | `Qual o horario de funcionamento de voces?` | Horário |
| 13 | `Quais documentos preciso para fazer uma procuracao?` | Lista documentos |
| 14 | `Meu CPF e 111.222.333-44 e RG 12.345.678-9` | NÃO vaza PII; log seguro |
| 15 | `O cartorio faz ata notarial?` | Resposta sobre atas |
| 16 | `Quero cancelar meu agendamento` | Cancelar |
| 17 | `Estou com problema no sistema, podem me ajudar?` | Escalação |
| 18 | `Quero enviar um documento para analise` | Upload flow |
| 19 | `Muito obrigado pelo atendimento!` | Agradecimento + assinatura |
| 20 | `Tchau, ate mais!` | Despedida |

**Resultado E2E (2026-07-01 12:09 UTC)**: 20/20 processados, 0 erros 5xx. Tempo médio: 6-12s (incluindo chain LLM).

---

## 2. WHATSAPP (EVOLUTION API) ✅

### Como parear
- Acessar `http://localhost:8080/manager` (via VPS) OU abrir o **QR Code JSON** abaixo
- Instance: **`cartorio-2notas`** já criada no banco Prisma
- Status: **connecting** (espera QR escaneado)

```bash
# Pegar QR atual via API
curl -X POST -H "apikey: 429683C4C977415CAAFCCE10F7D57E11" \
  -H "Content-Type: application/json" \
  -d '{"instanceName":"cartorio-2notas"}' \
  http://localhost:8080/instance/connect/cartorio-2notas
```

### Webhook WhatsApp → API Cartório
- URL: `https://api.2notasudi.com.br/api/v1/webhook/evolution`
- Toda msg recebida no WhatsApp é roteada → API → PII scrub → OpenClaw → resposta

### Estado atual
```
instance: cartorio-2notas
state: connecting (precisa escanear QR)
db: Prisma postgresql conectado a cartorio_supabase:5432/evolution
```

---

## 3. CHATWOOT (CRM) ✅

### URL
- Frontend: `https://chat.2notasudi.com.br`
- API: `https://chat.2notasudi.com.br/api/v1/`

### Credenciais admin
- **Email**: `gustavomar.fullstack@gmail.com`
- **Password**: `@Techno832466`
- **Token API**: `X6fRdztdTA2Z2seBwm9PHJgy` (account_id=1)

### O que validar
```bash
# Test login
curl -H "api_access_token: X6fRdztdTA2Z2seBwm9PHJgy" \
  https://chat.2notasudi.com.br/api/v1/accounts

# Account info
curl -H "api_access_token: X6fRdztdTA2Z2seBwm9PHJgy" \
  https://chat.2notasudi.com.br/api/v1/accounts/1
```

### Estado atual
- ✅ Conta `Cartorio 2notas` ativa (id=1)
- ✅ User `Gustavo` (administrator)
- ❌ 0 contatos (criar manualmente OU via WhatsApp/Telegram inbound)
- ❌ 0 inboxes (criar WhatsApp inbox via Settings → Inboxes → Add → API)

---

## 4. API CARTÓRIO ✅

### Swagger / Documentação
- **`https://api.2notasudi.com.br/docs`** (FastAPI auto-generated)

### 99 endpoints agrupados:

#### Health
```
GET /health                                # health
GET /api/v1/health/live                    # liveness probe
GET /api/v1/health/ready                   # readiness (db+redis)
GET /api/v1/health/db                      # postgres status
GET /api/v1/health/redis                   # redis status
GET /api/v1/health/llm                     # LLM provider status
GET /api/v1/health/integracoes             # ALL integrations
GET /api/v1/health/backup                  # backup status
GET /api/v1/health/lgpd                    # LGPD compliance
```

#### Cliente
```
GET  /api/v1/cliente/{cliente_id}
GET  /api/v1/cliente/{cliente_id}/historico
POST /api/v1/cliente/{cliente_id}/lgpd/anonimizar
POST /api/v1/cliente/{cliente_id}/lgpd/optout
GET  /api/v1/cliente/{cliente_id}/lgpd/portabilidade/download
```

#### Agendamento
```
POST /api/v1/agendamento                   # CRIAR agendamento
GET  /api/v1/agendamento/{id}/confirmar
GET  /api/v1/agendamento/{id}/cancelar
GET  /api/v1/agendamento/disponibilidade
GET  /api/v1/agendamento/pendentes
GET  /api/v1/agendamento/proximos
```

#### Protocolo
```
POST /api/v1/protocolo                     # criar
GET  /api/v1/protocolo/{numero}
GET  /api/v1/protocolo/recentes-concluidos
```

#### Telegram (webhook + info)
```
POST /api/v1/telegram/webhook              # Telegram → API (bot entry)
GET  /api/v1/telegram/webhook/info         # status
```

#### WhatsApp / Evolution (webhook)
```
POST /api/v1/webhook/evolution             # Evolution → API
POST /api/v1/webhook/chatwoot              # Chatwoot → API
```

#### Emolumento / Documento
```
POST /api/v1/emolumento/calcular
POST /api/v1/documento/segunda-via
POST /api/v1/documento/upload
```

#### Atendimento (com WebSocket)
```
POST /api/v1/atendimento                     # iniciar sessão
GET  /api/v1/atendimento/list-active
GET  /api/v1/atendimento/ultimas-24h
GET  /api/v1/atendimento/{id}/historico
WS   /api/v1/atendimento/ws/{session_id}    # WebSocket
```

#### LGPD
```
POST /api/v1/lgpd/consent
POST /api/v1/lgpd/revogar-consent
GET  /api/v1/lgpd/export/{cliente_id}
GET  /api/v1/lgpd/dashboard
POST /api/v1/lgpd/oposicao
GET  /api/v1/admin/lgpd/relatorio-anual
```

#### Admin
```
GET  /api/v1/admin/pool                    # DB pool stats
GET  /api/v1/admin/locks                   # lock status
GET  /api/v1/admin/slow-queries            # slow queries
POST /api/v1/admin/audit/check-now
GET  /api/v1/admin/audit/health
POST /api/v1/admin/retencao/run
```

#### MCP / Integrações
```
GET  /mcp-servers                          # lista MCP servers
GET  /api/v1/integrations/openclaw        # OpenClaw status
GET  /api/v1/integrations/opencode/test   # OpenCode fallback
POST /api/v1/integrations/outbox/dispatch
POST /api/v1/integrations/n8n/error       # legacy
```

#### Auth
```
POST /api/v1/auth/login
GET  /api/v1/auth/me
POST /api/v1/auth/refresh
```

#### Brain / Lessons
```
GET  /api/v1/brain/sessions
GET  /api/v1/brain/snapshots
GET  /api/v1/brain/context/current
GET  /api/v1/brain/tasks
POST /api/v1/brain/lesson
GET  /api/v1/brain/lessons
```

---

## 5. BANCO DE DADOS (Postgres + pgvector) ✅

### Conexão canônica
```
postgres://admin:@Techno832466@cartorio_supabase:5432/supabase?sslmode=disable
```

### Stats
- **121 tabelas** no schema `public`
- **Extensão pgvector instalada** (`CREATE EXTENSION vector`)
- **7 conexões ativas** atuais
- **DBs**: `supabase` (principal), `evolution` (WhatsApp), `chatwoot` (usa a mesma)

### Acessos
- Via **DbGate** (UI): `http://vps-cartorio:3000` (via Tailscale)
- Via **dbgate**: porta interna 3000
- Via `psql`: `docker exec cartorio_supabase.1 psql -U admin -d supabase`

---

## 6. REDIS ✅

```
redis://default:@Techno832466@cartorio_redis:6379/0
```

- **709 keys** armazenadas (Sidekiq, rate-limit, sessions, WebSocket pubsub)
- **TTL ativo** (`avg_ttl=4357807177` = ~50 dias)
- Redis Commander UI: `http://vps-cartorio:8081` (via Tailscale)

---

## 7. OPENCLAW GATEWAY (LLM Fallback) ✅

- `http://cartorio_openclaw-gateway:18789` (interno)
- Modelo principal: **`minimax-m3`** (MiniMax)
- `/health`, `/status`, `/v1/models` — todos online
- Usado como fallback quando OpenCode Go falha (`Insufficient balance`)

---

## 8. STATUS DE INTEGRAÇÕES

| Integração | Status | Detalhes |
|------------|--------|----------|
| database | ✅ online | 0ms |
| redis | ✅ online | 2ms |
| **n8n** | ⚠️ DESLIGADO | Service removido do swarm a pedido (volumes mantidos) |
| openclaw | ✅ online | `minimax-m3` reachable |
| evolution | ✅ online | v2.3.7, instance `cartorio-2notas` connecting (aguardando QR) |
| chatwoot (health URL) | ⚠️ URL externa | usar token novo `X6fRd...` |
| supabase | ✅ online | pgvector + 121 tabelas |
| opencode_go | ✅ online | 200 OK (mas com `Insufficient balance` no billing) |

---

## 9. SCRIPTS ÚTEIS

```bash
# Health check completo
curl -sS https://api.2notasudi.com.br/api/v1/health/integracoes | jq

# Listar contatos Chatwoot
curl -sS -H "api_access_token: X6fRdztdTA2Z2seBwm9PHJgy" \
  https://chat.2notasudi.com.br/api/v1/accounts/1/contacts | jq

# Telegram webhook info
curl -sS https://api.telegram.org/bot8859206262:AAHNZ1a5L9O0U_4sXXTWQAVtEI4BnQjPH_Q/getWebhookInfo | jq

# Evolution instances
curl -sS -H "apikey: 429683C4C977415CAAFCCE10F7D57E11" \
  http://localhost:8080/instance/fetchInstances | jq
```

---

## 10. PENDÊNCIAS ANTES DA ENTREGA

- [ ] **Escanear QR** do WhatsApp Evolution (instance `cartorio-2notas`)
- [ ] **Criar Inbox WhatsApp** no Chatwoot (Settings → Inboxes)
- [ ] **(Opcional) Reativar N8N**: Gustavo pediu desligamento. Subir com chatwoot-node + mcp-node via `infra/n8n-workflows/import_all_to_n8n.sh`

---

**Commit final**: `1c48347 fix(telegram): sanitize LLM output + remove bad-gateway middleware`

**Memória atualizada**: `~/.claude/projects/-Users-gustavoalmeida-projetos-Cartorio/memory/`
- `validation-2026-07-01-services.md` (snapshot completo)
- `lesson-110-chatwoot-pgvector.md` (pgvector)
- `lesson-111-telegram-parse-mode.md` (think tag fix)
