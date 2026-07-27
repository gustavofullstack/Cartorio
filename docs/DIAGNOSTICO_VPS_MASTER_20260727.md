# Diagnóstico Master — VPS Agent AI Cartório (2º Ofício Uberlândia)

**Data:** 2026-07-27 08:43 BRT | **Auditor:** Gustavo Almeida + Antigravity (Claude Opus 4.6)
**VPS:** `187.77.236.77` (público) / `100.99.172.84` (Tailscale) | **EasyPanel + Docker Swarm**

> **Veredito Geral: `OPERACIONAL_PARCIAL` — serviços-base disponíveis, mas o
> bot multicanal não está certificado para produção. Consulte a matriz viva em
> `docs/PRONTIDAO_VPS_AGENT_AI_20260727.md`; HTTP 200 não substitui E2E.**

---

## 1. HERMES (Agent AI Gateway) — `NOT_DEPLOYED` 🔴

### O que é
Agent AI baseado em Nous Research Hermes que orquestra conversas, chama ferramentas MCP e responde via múltiplos canais (iMessage/Photon, API interna).

### Estado atual
- **Serviço Docker:** NÃO EXISTE na VPS (zero containers)
- **Stack pronto:** `infra/hermes/docker-stack.yml` (imagem fixada `sha256:6df245c...`)
- **Config:** `infra/hermes/config.cartorio.yaml` (modelo via env, MCP via URL interna)
- **4 Docker Secrets PENDENTES:**
  - `hermes_api_server_key` — autenticação API interna
  - `hermes_llm_api_key` — autenticação LLM (MiniMax Coding Plan)
  - `hermes_mcp_cartorio_api_key` — autenticação MCP contra FastAPI
  - `hermes_photon_project_secret` — autenticação Photon/iMessage

### O que falta para 100%
1. Criar os 4 Docker Secrets no EasyPanel/Swarm (NUNCA em .env ou repositório)
2. Configurar `HERMES_LLM_BASE_URL` = URL do MiniMax/LiteLLM
3. Configurar `HERMES_LLM_MODEL` = modelo MiniMax aprovado
4. Configurar `PHOTON_PROJECT_ID` + `PHOTON_ALLOWED_USERS` (E.164)
5. `docker stack deploy -c infra/hermes/docker-stack.yml cartorio`
6. Validar `cartorio_hermes` 1/1, health 200, MCP handshake

### Sequência de deploy

Criar os quatro secrets somente no gerenciador de secrets da VPS, configurar
os valores não secretos no Easypanel e executar
`infra/hermes/preflight-vps.sh`. O deploy só pode seguir após
`HERMES_PREFLIGHT=PASS`; o runbook canônico é
`docs/HERMES_VPS_DEPLOYMENT.md`.

---

## 2. FASTAPI (Backend Principal) — `OPERATIONAL` 🟢

### O que é
Backend Python FastAPI que serve a API REST, endpoints MCP, dashboard, webhooks Telegram/WhatsApp, LGPD e auditoria.

### Estado atual
- **URL:** `https://api.2notasudi.com.br`
- **Endpoints:** 220+ rotas em `backend/app/api/v1/router.py` (219KB)
- **MCP Server:** 15 ferramentas registradas em `backend/mcp_server.py`, montado em `/mcp`
- **Dashboard:** `https://api.2notasudi.com.br/dashboard` (Dark Mode Premium)
- **Health Radar:** `https://api.2notasudi.com.br/api/v1/health/radar` → `GREEN` 🟢
- **Swagger:** `https://api.2notasudi.com.br/docs` → 200 OK

### Serviços internos críticos (111 arquivos em `app/services/`)
| Serviço | Arquivo | Função |
|---------|---------|--------|
| Audit Chain | `audit.py` + `audit_integrity.py` | SHA256 chain + HMAC append-only |
| PII Scrubbing | `pii.py` + `pii_unified.py` | 3 camadas: input/pre-LLM/output |
| Emolumentos | `emolumento_real_djalma.py` | Tabela MG 2026 TJMG |
| LGPD | `lgpd/` + 8 arquivos | Art. 18 completo |
| CNJ Export | `cnj_export.py` | Streaming + PII scrub |
| Rate Limit | `rate_limit.py` + `rate_limit_by_key.py` | Sliding window 60/min |
| Idempotência | `idempotency_store.py` | Redis SETNX TTL 24h |
| Chat Pipeline | `chat_pipeline.py` | Orquestração de conversas |
| Agent Cartório | `cartorio_agent.py` (58KB) | Agente IA principal |

### O que falta
- Rollout controlado para publicar o health Hermes corrigido.
- Alinhar a credencial OpenClaw configurada na API: o gateway está acessível,
  mas a credencial atual recebe 401 no endpoint de modelos.

---

## 3. REDIS 8 — `OPERATIONAL` 🟢

### Estado atual
- Serviço `cartorio_redis` no Swarm, 1/1 réplicas
- Usado para: cache de sessões, rate limiting, idempotência, redlock, DLQ

### Serviços que dependem do Redis
| Serviço | Uso |
|---------|-----|
| `rate_limit.py` / `rate_limit_by_key.py` | Sliding window por IP/API key |
| `idempotency_store.py` | Dedupe webhook 24h |
| `redlock.py` | Distributed lock |
| `redis_bus.py` | Pub/sub events |
| `redis_ttl_inventory.py` | Inventário de TTLs |
| `dlq.py` | Dead Letter Queue 3x backoff |

### O que falta
- ✅ Operacional. Nada bloqueante.

---

## 4. POSTGRES 16 (Supabase) — `OPERATIONAL` 🟢

### Estado atual
- Serviço `cartorio_supabase-db-1` no Swarm
- 15 models SQLAlchemy 2.0 em `backend/app/models/`
- Alembic migrations (head: 0015)
- Pool tuned: 20 + 10 overflow, recycle 1h, pre-ping

### Models do banco
| Model | Arquivo | Função |
|-------|---------|--------|
| Cliente | `cliente.py` | Dados de clientes (PII protegido) |
| Conversa | `conversa.py` | Histórico de conversas |
| Protocolo | `protocolo.py` | Protocolos jurídicos (DRAFT → validado) |
| Documento | `documento.py` | Documentos notariais |
| Agendamento | `agendamento.py` | Sistema de agendamentos |
| Atendimento | `atendimento.py` | Atendimentos em andamento |
| AuditLog | `audit_log.py` | Log imutável SHA256+HMAC |
| Emolumento | `emolumento_catalogo.py` | Catálogo de emolumentos |
| WebhookEvent | `webhook_event.py` | Eventos de webhook |
| OutboxMessage | `outbox_message.py` | DLQ com retry |
| LGPDConsent | `lgpd_consent.py` | Consentimentos LGPD |
| CNJExportRequest | `cnj_export_request.py` | Requisições CNJ |

### O que falta
- ✅ Operacional. Nada bloqueante.
- P1: LGPD-0028 migration pendente de sign-off

---

## 5. CHATWOOT CRM (Omnichannel) — `DEGRADED` 🟡

### O que é
CRM que centraliza atendimento de TODOS os canais (Telegram, WhatsApp, iMessage, Web Chat) com hand-off humano para atos jurídicos.

### Estado atual
- **URL:** `https://chatwoot.2notasudi.com.br` → processo saudável
- **Health:** UP no radar
- **API:** ⚠️ Credencial retornando 401 — chave precisa rotacionar/reconciliar
- **Inbox Telegram:** ID 1
- **Account:** ID 1

### Integração no código
| Arquivo | Função |
|---------|--------|
| `chatwoot_handoff.py` (17KB) | Hand-off para humano |
| `chatwoot_handoff_macros.py` (15KB) | Macros de atendimento |
| `chatwoot_canned_responses.py` (30KB) | Respostas pré-definidas |
| `chatwoot_lgpd_erasure.py` | Erasure LGPD |

### O que falta para 100%
1. **P0:** Rotacionar/reconciliar credencial de API no secret manager
2. **P0:** Validar hand-off real: bot → humano → retorno ao bot
3. P1: Certificar que logs não contêm PII raw

---

## 6. TELEGRAM — `CONNECTED` 🟢/🟡

### Estado atual
- **Bot:** `@test_cartorio_bot`
- **Webhook:** Configurado em `api.2notasudi.com.br`
- **Handler:** `backend/app/api/v1/telegram.py` (109KB — mega handler)
- **Pending queue:** 0
- **Secret:** OK

### O que falta
- **P1:** Executar E2E real com cenários do guia (`docs/GUIA_TESTES_TELEGRAM.md`)
- P1: Conversa privada + grupo real certificada

---

## 7. WHATSAPP (Evolution API) — `DEGRADED` 🔴

### Estado atual
- **Evolution API 2.3.7:** ONLINE em `https://whatsapp.2notasudi.com.br`
- **Sessão `cartorio-2notas`:** `status: close` ❌ — DESCONECTADA
- **Handler:** `backend/app/api/v1/whatsapp.py` (30KB)
- **Ingest:** `backend/app/services/evolution_ingest.py` (7KB)

### O que falta para 100%
1. **P0:** Parear novamente via QR Code no celular do cartório
   - Acessar `https://flow.2notasudi.com.br` → Evolution → Instância → QR Code
   - Escanear com WhatsApp Business do celular autorizado
2. **P0:** Após pareamento, enviar mensagem teste e verificar resposta do bot
3. P1: Templates de WhatsApp Business API (`whatsapp_meta_templates.py`)

---

## 8. EVO-HUB / WA-CLI — `NOT_IMPLEMENTED` ⚪

### Estado atual
- **Evo-Hub:** Não encontrado no projeto
- **WA-CLI:** Não encontrado no projeto
- **Avaliação:** Evolution API 2.3.7 é suficiente para o caso de uso atual

### Recomendação
- Se Evolution API atende, Evo-Hub/WA-CLI são desnecessários
- Se precisar automação avançada (envio em massa, multi-sessão), avaliar Evo-Hub

---

## 9. iMESSAGE (Photon) — `NOT_DEPLOYED` 🔴

### Estado atual
- **Depende do Hermes** (sidecar Photon na porta 8793)
- **Spectrum Gateway:** `services/spectrum-gateway/` (contratos tipados, scaffold)
- **Config:** `infra/hermes/config.cartorio.yaml` → `gateway.platforms.photon.enabled: true`

### O que falta para 100%
1. Hermes precisa estar deployed primeiro
2. Configurar `PHOTON_PROJECT_ID` e `PHOTON_ALLOWED_USERS` (E.164)
3. Round-trip real: iPhone autorizado → Photon → Hermes → resposta

---

## 10. SUPABASE (PostgREST/Auth/Storage) — `OPERATIONAL` 🟢

### Estado atual
- **URL:** `https://supbase.2notasudi.com.br`
- **PostgREST:** 200 OK
- **Client:** `backend/app/integrations/supabase_client.py` (12KB)

### O que falta
- ✅ Operacional

---

## 11. N8N (Workflow Engine) — `PARTIALLY_INTEGRATED` 🟡

### Estado atual
- **URL:** `https://flow.2notasudi.com.br`
- **Workflows:** 32 listados, 31 ativos
- **Exports:** `infra/n8n-workflows/`
- **Problem:** Chave de API sem permissão para consultar execuções

### Integração no código
| Arquivo | Função |
|---------|--------|
| `n8n_token_router.py` (10KB) | Roteamento de tokens |
| `n8n_workflow_validator.py` (7KB) | Validação de workflows |
| `n8n_meta_triggers.py` (8KB) | Meta-triggers |
| `n8n_error.py` | Error handler |

### O que falta
- **P1:** Rotacionar chave N8N com permissão de leitura de execuções
- P1: Exportação de workflows no backup automatizado

---

## 12. EXPORT CNJ — `IMPLEMENTED` 🟢

### Estado atual
- **Backend:** `backend/app/services/cnj_export.py` (11KB) + `cnj_protecao.py` (8KB)
- **Endpoint:** `backend/app/api/v1/cnj_export.py` (12KB)
- **Features:** Streaming + PII scrub + JWT DPO + gate de audit
- **Docs:** `docs/CNJ_LGPD_REPORT.md`, `docs/CNJ_PROTECAO_DADOS.md`

### O que falta
- ✅ Implementado. Validação em produção pendente.

---

## 13. TAILSCALE/SSH — `OPERATIONAL` 🟢

### Estado atual
- **VPS Tailscale:** `100.99.172.84` (conectada)
- **VPS Público:** `187.77.236.77` (SSH root)
- **MacBook:** `100.83.180.16` (UI/cliente apenas)
- **Código:** `ssh_tailscale_acl.py` (7KB) + `tailscale_probe.py` (7KB)
- **Regra SSH:** `-o ConnectTimeout=8 -o BatchMode=yes`, bounded

### O que falta
- ✅ Operacional

---

## 14. MINIMAX CODING PLAN — `CONFIGURADO` 🟡

### Estado atual
- **Provider:** MiniMax.io Coding Plan
- **Model:** MiniMax-M3 XMax Thinking
- **Credencial:** configurada no ambiente de produção; não é exibida nem usada
  por este diagnóstico.
- **Integração:** Via LiteLLM proxy ou direto (`https://api.minimaxi.com/v1`)

### Configuração para Hermes
```
HERMES_LLM_BASE_URL=https://api.minimaxi.com/v1
HERMES_LLM_MODEL=MiniMax-M3
# Key vai no Docker Secret 'hermes_llm_api_key'
```

### O que falta
- Executar inferência sintética, sem PII, somente após autorização explícita de
  custo. Presença de variável não prova resposta do provider.

---

## RESUMO EXECUTIVO

### Componentes com evidência técnica atual
| # | Pilar | Status |
|---|-------|--------|
| 2 | FastAPI / MCP | 🟢 API, handshake e tool pública validados |
| 3 | Redis 8 | 🟢 online pelo radar e pela API |
| 4/10 | Postgres / Supabase | 🟢 backup e restore isolado validados |
| 12 | Export CNJ | 🟢 contratos locais de segurança validados |
| 13 | Tailscale/SSH | 🟢 conectividade VPS validada |
| 8 | Evo-Hub/WA-CLI | ⚪ não implantados; decisão arquitetural pendente |

### Componentes ainda sem aceite operacional
| # | Pilar | Status | Bloqueio |
|---|-------|--------|----------|
| 1 | Hermes | 🔴 NOT_DEPLOYED | 4 Docker Secrets + deploy |
| 5 | Chatwoot | 🟡 DEGRADED | API 401 — credencial |
| 7 | WhatsApp | 🔴 DEGRADED | Sessão close — QR Code |
| 9 | iMessage | 🔴 NOT_DEPLOYED | Depende do Hermes |
| 11 | N8N | 🟡 PARTIAL | snapshot de workflows funciona; falta observabilidade de execuções |
| 6 | Telegram | 🟡 HANDSHAKE | falta conversa privada/grupo E2E |
| 14 | MiniMax | 🟡 CONFIGURADO | falta inferência sintética autorizada |
| — | OpenClaw | 🟡 DEGRADED | API → gateway recebe 401 |

### Sequência de Resolução (ordem obrigatória)
1. **WhatsApp QR Code** — pareamento pelo celular do cartório (Gustavo executa)
2. **Chatwoot credencial** — rotacionar no secret manager (Gustavo executa)
3. **N8N observabilidade** — criar credencial somente leitura para execuções
4. **Hermes deploy** — criar 4 secrets + stack deploy (Gustavo executa na VPS)
5. **iMessage/Photon** — configura junto com Hermes
6. **Telegram E2E** — rodar cenários reais após Hermes

### Topologia Definitiva

| Nó | IP | Papel |
|----|-----|-------|
| **VPS Hostinger** | `187.77.236.77` / `100.99.172.84` | **TUDO** — produção, dev, testes, Docker Swarm |
| **MacBook Pro** | `100.83.180.16` | **Somente cliente SSH/UI** |

**Nenhuma máquina local externa faz parte deste projeto.**

---

Modified by Gustavo Almeida — 2026-07-27
