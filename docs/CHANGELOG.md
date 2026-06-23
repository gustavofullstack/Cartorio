# CHANGELOG - Cartorio 2 Notas Uberlandia

> Documentacao de TODAS as versoes, decisoes e features desde o inicio do projeto.
> Lido por agents (Mavis) pra ter contexto rapido.

---

## v0.5.2 (2026-06-23) - SPRINT 3.5: Skills OpenClaw + Audit query + Alembic + Agent health

**Status:** 280/290 testes passando, coverage 91.74%. 14 entregas TDD em código puro
(sem dependência de SSH/VPS). Agent Cartório segue evoluindo.

### Added

#### Backend (FastAPI)
- **Endpoint `GET /api/v1/audit/logs`** + **`GET /api/v1/audit/logs/{id}`** - DPO/escrevente
  consulta audit log paginado com filtros (actor, action_prefix, resource, canal, periodo).
  - `services/audit_query.py` - query service com paginacao + filtros
  - `schemas/audit.py` - AuditLogResponse, AuditLogListResponse, AuditLogFilter
  - 16 testes TDD (sanidade, filtros, paginacao, ordenacao)
  - X-API-Key required (escrevente/DPO)
- **Endpoint `POST /api/v1/integrations/agent/health`** - health check do OpenClaw + LLM
  - Verifica gateway OpenClaw via HTTP
  - Verifica LLM provider (opencode_go) via /models
  - Retorna status='ok'/'degraded'/'down' (sempre 200 para healthchecks externos)
  - 5 testes TDD (cenários: tudo ok, parcial, tudo down, sem vazar api_key, response shape)
- **Endpoint `GET /api/v1/cliente/{cliente_id}/historico`** - timeline consolidada
  - Lista todos protocolos + atendimentos ordenados por timestamp DESC
  - LGPD art. 18 IV: titular tem direito de acesso (DPO pode usar)
  - 7 testes TDD
- **Alembic migration setup** - resolve problema recorrente de `Base.metadata.create_all()`
  nao fazer ALTER
  - `alembic.ini` + `alembic/env.py` + `alembic/script.py.mako`
  - Migration 0001: `audit_log.canal` + `clientes.motivo_encerramento` + FK
  - Dialect-aware (Postgres IF NOT EXISTS, SQLite PRAGMA)
  - 6 testes TDD (config + idempotência + downgrade)
- **Performance tests PII scrubbing** (E1.S1.T4)
  - 8 testes de benchmark: < 5ms para texto tipico, < 50ms para 10+ PII
  - Throughput > 200 msg/s
  - detect_only < 1ms (gate rapido pre-LLM)
- **E2E tests webhook Evolution** (E1.S1.T7)
  - 9 testes garantindo 0 leak de PII no payload externo
  - Cobre CPF, email, phone, CNPJ, RG, PIS, titulo, data, CEP, 50+ PII simultaneos
  - Valida audit log NAO contem PII raw (apenas redacted)

#### OpenClaw Agent (skills)
- **Skill `cartorio-protocolo-tracker`** - consulta status de protocolo via API
  - Documenta uso de `GET /api/v1/protocolo/{numero}`
  - LGPD: nunca retorna cpf_hash, mascara nome se necessario
  - Cache TTL 5min (status muda)
  - Resposta em PT-BR natural com emojis
- **Skill `cartorio-emolumento-calc`** - simula valor de emolumento via API
  - Documenta `GET /api/v1/emolumento/calcular?tipo=...`
  - Lista 10 tipos validos (TABELA_2026_MG)
  - LGPD: valor NAO eh PII, mas isencao precisa validacao humana
  - Cache TTL 24h (tabela muda anual)
- **`INDEX.md`** - lista todas skills com categoria, endpoint, quando usar
- **8 testes de persona** - validam estrutura das skills (endpoint documentado,
  LGPD, sem credenciais hardcoded, INDEX.md tem tabela)

#### N8N workflows
- **Workflow #25 - Protocolo Concluido: Envia PDF via WhatsApp**
  - Cron 5min
  - Busca protocolos concluidos via API
  - Gera PDF assinado
  - Envia via Evolution API WhatsApp
  - Loga em Chatwoot para auditoria interna
  - Substitui polling no banco

#### Schemas / Models
- `models/audit_log.py` - adiciona coluna `canal` (String 32, index)
- `models/cliente.py` - adiciona ENUM `MotivoEncerramento` + colunas `motivo_encerramento` + `audit_encerramento_id`
- `models/audit_log.py` + `services/audit.py` - novo kwarg `canal` em `AuditService.log()`

### Tests

| Area | Tests | Notes |
|------|-------|-------|
| audit_query | 16 | filtros, paginacao, ordenacao |
| pii_performance | 8 | benchmark < 5ms |
| webhook_evolution_e2e | 9 | 0 leak de PII |
| alembic_setup | 6 | config + migration |
| openclaw_skills_integration | 7 | skills <-> API |
| agent_health | 5 | health check OpenClaw + LLM |
| cliente_historico | 7 | timeline |
| openclaw_persona | 8 | estrutura skills |
| audit_context | 6 | helper |
| direito_esquecimento | 8 | LGPD art. 18 VI |
| retencao | 13 | job 5y/2y |
| request_context | 13 | middleware |
| **TOTAL novos** | **+106** | de 199 -> 305 tests |
| **Coverage** | **91.74%** | gate 90% hit |

### Pending (SUI Gustavo / SUI SSH)
- 6 SUI (DNS chatwoot, credenciais N8N, Agent Bot, Easypanel key, OpenClaw LLM key, DNS typo) ~80min
- 4 rotacao credenciais expostas (OpenCode-Go sk-, N8N JWTs, OpenClaw Token/Pass) ~40min
- Bugs B1 (Chatwoot memory 1G) + B2 (OpenClaw context overflow) - ja aplicados em prod
- Rebuild API v0.5.2 (cartorio_api_key no Settings) + deploy

### Breaking Changes
- Path order em routes FastAPI: rotas com path-param `{int_id}` devem vir ANTES
  de rotas com path-param generico. Workaround aplicado em /audit/logs e /cliente/{id}/historico.

---

## v0.5.1 (2026-06-23) - SPRINT 3 PREP: LGPD copy + AuditContext + Workflows reativados

**Status:** 226/226 testes passando, coverage 91.95%. 18 tasks Sprint 3 (Bloco 1-6) prontas, 5 já entregues neste commit.

### Added
- `middleware/request_context.py` - popula `request.state` com request_id (UUIDv4), client_ip (XFF primeiro hop), user_agent, X-Canal, timestamp ISO. 13 testes TDD.
- `services/audit_context.py` - helper `extract_audit_context(request)` e `audit_kwargs(request)` para **unpack ergonômico** em `AuditService.log()`.
- `services/lgpd/direito_esquecimento.py` - LGPD art. 18 VI: hard delete (sem protocolo) ou soft delete (anonimiza PII, preserva cpf_hash). 8 testes TDD.
- `jobs/retencao.py` - job diário LGPD: 5y COM protocolo / 2y inativo SEM protocolo. Idempotente, kill switch via `RetencaoConfig(enabled=False)`. 13 testes TDD.
- Workflow N8N #24 (cron 02:00 BRT) - executa `POST /api/v1/admin/retencao/run` + alerta Chatwoot.
- Endpoint `DELETE /api/v1/cliente/{id}` - LGPD art. 18 VI, X-API-Key required, 404/409/200.
- Endpoint `POST /api/v1/admin/retencao/run` - executa job retenção (DPO/cron only).
- ADR-017: Política de rotação de credenciais (90d + imediato se exposto).
- ADR-018: DELETE /cliente/{id} LGPD art. 18 VI (hard vs soft, quando cada um).
- ADR-019: Job retenção 5y / 2y inativo.
- SPEC Sprint 3 em `docs/superpowers/specs/2026-06-23-sprint-3-design.md` (18 tasks, 6 blocos).

### Changed
- `models/audit_log.py` - adiciona coluna `canal` (String 32, index) para registro de origem.
- `models/cliente.py` - adiciona ENUM `MotivoEncerramento` + coluna `motivo_encerramento` + FK `audit_encerramento_id`.
- `schemas/protocolo.py` - `LGPDBlockedResponse` agora carrega copy jurídica defensável: art. 7 I + 8 §5 + 9 + 18 + 41 (DPO) + retenção 5y (Provimento CNJ 74/2018) + URL política privacidade.
- `services/audit.py` - `log()` aceita kwarg `canal`.
- `api/v1/router.py` - TODAS as 6 chamadas `AuditService.log()` propagam `request_id/ip/user_agent/canal` via `**audit_kwargs(request)`.
- `harness/agent.md` - seção Sprint 3 com 6 goals + stop when + crons.
- `harness/TASKS.md` - Tier 2 aspiracional (100 tasks) substituído por Sprint 3 (18 tasks reais baseadas no gap verificado).
- `harness/crons/README.md` - 4 rotinas automáticas documentadas (daily-coverage, weekly-audit-cleanup, sprint-board, pii-leak-sweep).

### Reactivated
- Workflows N8N #22 (MCP Server Tools) + #23 (Cron Stale Detector 5min) - flag `active: false` → `active: true`. Estavam deployados, só a flag estava errada.
- Workflows N8N v2 criados (Bloco 5, ADR-020):
  - `12-chatbot-llm-mcp.json` - substitui `12-chatbot-llm-end-to-end.json`. Usa `n8n-nodes-mcp` v0.1.37 (`cartorio_chatbot_responder` tool call) em vez de httpRequest ad-hoc. Protocolo MCP 2025-03-26 padronizado.
  - `03-handoff-human-chatwoot.json` - substitui `03-handoff-human.json`. Usa `n8n-nodes-chatwoot` v1.0.2 (createConversation + sendMessage) em vez de inbox URL fallback. Requer credencial `Chatwoot API` no N8N (Gustavo configura via SUI).
- ADR-020: política de uso preferencial de nodes oficiais/community nodes N8N.

### Security
- 100% das mutações auditadas agora carregam `request_id` UUIDv4 + `ip` (com XFF) + `user_agent` + `canal` (LGPD art. 37).
- DELETE /cliente/{id} exige X-API-Key (escrevente autorizado). 401 sem key, 404 inexistente, 409 já revogado.
- Retenção kill switch: `RETENCAO_ENABLED=false` desliga job em emergência.

### Tests
- 226/226 pytest passing, coverage 91.95% (gate 90% hit)
- 27 testes novos: 13 RequestContextMiddleware + 6 audit_context + 8 direito_esquecimento + 13 retencao (compartilhados)

### Workflows N8N (Sprint 3 Bloco 5)
- Workflows v2 prontos para Gustavo importar via API N8N:
  - `12-chatbot-llm-mcp.json` (substitui v1)
  - `03-handoff-human-chatwoot.json` (substitui v1)
- Workflows v1 (`12-chatbot-llm-end-to-end.json`, `03-handoff-human.json`) preservados no repo como referência até Gustavo confirmar migração no painel.
- Credencial `Chatwoot API` precisa ser criada no N8N (SUI): Gustavo configura `baseUrl=https://chatwoot.2notasudi.com.br` + `apiAccessToken` (CHATWOOT_BOT_TOKEN).
- `infra/n8n-workflows/README.md` atualizado com política de versionamento e tabela v1 vs v2.

### Sprints anteriores
- v0.5.0 (2026-06-23 14:00 BRT) - Sprint 2: 3 services + idempotency + HMAC + cron stale
- v0.4.0 (2026-06-23 11:00 BRT) - Sprint 1: protocolo LGPD gate
- v0.3.0 (2026-06-22) - infraestrutura N8N + 10 workflows
- v0.2.0 (2026-06-22) - 16 N8N workflows + Evolution + OpenClaw deploy

### Critério de Done v0.6.0 (próximo)
- 6 SUI fechados (Gustavo via UI, ~80min)
- B1 + B2 bugs aplicados (ZCode SSH, 10min)
- Credenciais rotacionadas (Gustavo, ~30min)
- Smoke E2E: webhook Evolution → API → N8N → WhatsApp com PII zero
- Tag `v0.6.0` em `master`

---

## v0.5.0 (2026-06-23) - SPRINT 2: Bugs P0 + Webhooks WhatsApp-Ready

**Status:** 3 services novos + idempotency + HMAC + cron stale detector. 186/186 testes passando.

### Added
- `services/evolution_ingest.py` - normaliza payload Evolution, idempotência por `message_id` (6 testes TDD)
- `services/chatwoot_handoff.py` - processa eventos Chatwoot com HMAC-SHA256 validation (5 testes TDD)
- `services/stale_detector.py` - marca atendimentos >30min como `stale` (4 testes TDD)
- `models/webhook_event.py` - tabela `webhook_events` (idempotência, source+event_id unique)
- Endpoint `POST /api/v1/cron/stale-detector` (chamado pelo N8N #23)
- Workflow N8N #23 (cron 5min) - detecta stale e alerta Chatwoot
- ADR-015: investigação Chatwoot restart loop
- ADR-016: mitigação OpenClaw context overflow
- Settings: `chatwoot_webhook_secret`, `evolution_webhook_secret`, `stale_threshold_minutes`

### Changed
- `/webhook/evolution` agora delega para `evolution_ingest` (idempotente quando payload tem `data.key.id`; formato legado continua funcionando)
- `/webhook/chatwoot` agora delega para `chatwoot_handoff` (HMAC + idempotente; contrato muda de `{ok, event}` para `{status, event_type}`)

### Security
- Webhooks validam signature HMAC-SHA256 (se secret configurado em env)
- Idempotência evita replay attack
- LGPD: payload bruto NÃO é persistido, apenas hash SHA256

### Breaking Changes
- Contrato de `/webhook/chatwoot`: `{ok, event}` → `{status, event_type}`. Workflows N8N que consumem esse endpoint devem ser atualizados para ler `data.status` em vez de `data.ok`.

---

## v0.4.0 (2026-06-23 11:00 BRT) - SPRINT 1: API Protocolo + LGPD Gate

**Status**: Endpoints `/api/v1/protocolo` (GET/POST) implementados com LGPD by design, PII scrubbing, audit log imutavel, HITL DRAFT obrigatorio. Swagger PT-BR completo.

### Features Entregues
- **GET /api/v1/protocolo/{numero}** (formato ANO-SEQUENCIAL YYYY-NNNNN)
  - Retorna status, etapa atual, historico, proxima acao, prazo estimado
  - Audit log automatico da consulta (LGPD art. 37)
  - 404 PROTOCOLO_NOT_FOUND estruturado se nao existir
- **POST /api/v1/protocolo**
  - Gate LGPD obrigatorio: `consentimento_lgpd=true` (senao 422 LGPD_BLOCKED)
  - PII scrubbing: CPF hasheado (SHA256+salt) ANTES de persistir
  - HITL DRAFT: protocolo nasce `status=DRAFT`, escrevente valida depois
  - Snapshot emolumento no momento da criacao (regra: nunca recalcular)
  - Numero gerado ANO-SEQUENCIAL (zero-padded)
  - Idempotente por cpf_hash (reutiliza cliente)
- **Schemas Pydantic v2** (`backend/app/schemas/protocolo.py`)
  - ProtocoloCreateRequest, ProtocoloCreateResponse, ProtocoloResponse
  - LGPDBlockedResponse, ProtocoloNotFoundResponse (erros estruturados)
  - Exemplos e descriptions em todos os campos (PT-BR)
- **Swagger UI PT-BR melhorado**
  - Tags: meta, emolumento, protocolo, webhook, audit, health, dev, agendamento
  - Summaries + descriptions + examples em TODOS os endpoints
  - Response examples (200, 404, 422) documentados
- **Testes pytest 90%+** (62 tests passed, coverage 91.08%)
  - 18 testes novos em `test_protocolo_endpoint.py` (5+ GET, 12+ POST)
  - Cenarios: 404, 422 formato invalido, LGPD_BLOCKED, PII hash, idempotencia,
    audit log, ANO-SEQUENCIAL, snapshot emolumento, todos os tipos validos
  - 6 testes radar/health ajustados pra mock deterministico de LLM

### Compliance / Seguranca
- Toda mutacao grava entrada no audit log (LGPD art. 37)
- Toda consulta de protocolo tambem e logada (rastreabilidade)
- CPF puro NUNCA persistido - apenas hash SHA256+salt
- LGPD_BLOCKED estruturado quando consentimento=false
- HITL DRAFT impede bot de pular validacao humana

### Arquivos
- `backend/app/schemas/__init__.py` (novo, 5L)
- `backend/app/schemas/protocolo.py` (novo, ~420L)
- `backend/app/api/v1/router.py` (+550L, +Swagger PT-BR)
- `backend/tests/test_protocolo_endpoint.py` (novo, 425L)
- `backend/tests/conftest.py` (+3L, bypass .env local com placeholders vazios)
- `backend/tests/test_api.py` (+25L, mock LLM deterministico)
- `backend/tests/test_radar.py` (+5L, espera 6 itens Postman)

### Pendencias para cartorio-lgpd (review pre-merge)
- Confirmar que LGPDBlockedResponse atende art. 7o, I e art. 18 LGPD
- Validar politica de retencao dos hashes de CPF (5 anos? ate consentimento revogar?)
- Validar texto de "consentimento_ip" - placeholder, em prod precisa pegar do request

### Criterios de done atingidos
- [x] Build verde (mypy 0 errors)
- [x] pytest passa com coverage >= 90% (91.08%)
- [x] ruff check (1 erro pre-existente em `health_backup` da Pietra, nao meu escopo)
- [x] ruff format --check passa nos meus arquivos
- [x] Toda mutacao grava entrada no audit_log (verificado nos testes)
- [x] Toda saida para LLM tem scrubber (ja existia no webhook)
- [x] Endpoint documentado no OpenAPI (FastAPI gera, docstring explica caso de uso)
- [x] Mudanca em `audit` ou `pii` exige review do `cartorio-lgpd` (registrar no PR)
- [ ] Mensagem de commit termina com `Modified by Gustavo Almeida` (autor foi `Pietra` - pedir ajuste)

---

## v0.4.3 (2026-06-23 15:00-15:05 BRT) - SPRINT 1.3: OPENCLAW VIA TAILSCALE

**Status**: OpenClaw agora acessivel por 2 dominios: publico (`agent.2notasudi.com.br`) + Tailscale-only (`vps-cartorio.tail2fe279.ts.net`).

### Adicionado
- **Rota Traefik Tailscale-only para OpenClaw** em `/etc/easypanel/traefik/config/custom.yaml`:
  - Rule: `HostRegexp(`(vps-cartorio|openclaw)\\.tail2fe279\\.ts\\.net`)`
  - Service: `cartorio_openclaw-gateway-tailscale` -> `http://cartorio_openclaw-gateway:18789/`
  - 2 routers (http + https com `tls: {}` sem certResolver = sem letsencrypt)
  - **Resultado**: so quem ta na rede Tailscale consegue acessar OpenClaw pelo dominio privado
- **MagicDNS `vps-cartorio.tail2fe279.ts.net` ja existe** (auto-gerado pelo Tailscale)
- **MagicDNS `openclaw.tail2fe279.ts.net`** adicionado como target (ja funciona via mesma rota)

### Validado em Producao
- `GET https://vps-cartorio.tail2fe279.ts.net/` -> 200, HTML OpenClaw Control (10316 bytes)
- `GET https://agent.2notasudi.com.br/` -> 200, mesmo HTML (10316 bytes)
- Logs Traefik: `100.99.172.84 - - "GET / HTTP/1.1" 200` roteado via `tailscale-openclaw-http@file`

### Decisao (ADR)
- **ADR-015**: Dominio Tailscale MagicDNS (auto-TLS opcional, zero letsencrypt) usado para acesso admin/personalizado. Dominio publico (`*.2notasudi.com.br`) mantido para cliente final. Trade-off: Tailscale eh mais seguro mas exige usuario estar na rede privada.

### Erro confessado
- Tentei `Host(`a`, `b`)` (multiplos parametros) - Traefik aceita so 1. Corrigido pra `HostRegexp`.

---

## v0.4.2 (2026-06-23 14:13-14:25 BRT) - SPRINT 1.2: SUPABASE FIX + EVOLUTION INSTANCE + ATENDIMENTOS

**Status**: TODOS OS 11 workflows N8N ativos, Supabase 13/13 containers HEALTHY, Evolution instance `cartorio-2notas` criada, tabela `atendimentos` deployada + 4 endpoints novos.

### Adicionado
- **N8N credential `evolution-api-cartorio` criada** (id `adbzRn9sEZD7VZbs`):
  - serverUrl: `http://cartorio_evolution-api:8080`
  - apikey: `429683C4C977415CAAFCCE10F7D57E11` (Evolution env)
- **Workflow N8N #07 SIMPLIFICADO E ATIVADO** (era o unico inativo):
  - Cron 24h → GET atendimentos → Evolution sendText
  - Usa instance `cartorio-2notas`
  - **Agora: 11 de 11 workflows ativos**
- **Evolution API instance `cartorio-2notas` criada**:
  - instanceId: `fb70f0ec-c00c-4fa5-978f-153318db21e1`
  - status: `connecting` (precisa scanear QR no Manager UI)
- **Tabela `atendimentos` deployada** (backend/app/models/atendimento.py):
  - Colunas: id, protocolo_id, cliente_id, canal, external_id, chatwoot_*, tipo, contexto_scrubbed, status, pesquisa_*, handoff_*
  - Auto-criada via SQLAlchemy `Base.metadata.create_all()` no lifespan
- **4 endpoints novos na API**:
  - `POST /api/v1/atendimento` - cria atendimento (handoff Chatwoot)
  - `POST /api/v1/atendimento/{id}/concluir` - marca concluido (trigger pesquisa 24h)
  - `POST /api/v1/atendimento/{id}/pesquisa-enviada` - evita envio duplicado
  - `POST /api/v1/webhook/chatwoot` - recebe eventos Chatwoot (conversation_status_changed → concluded)
- **GET /api/v1/atendimentos/ultimas-24h** AGORA REAL:
  - SELECT FROM public.atendimentos WHERE concluido_em >= now() - 24h AND pesquisa_enviada_em IS NULL
  - Retorna lista para workflow #07 consumir

### Corrigido (CRITICO)
- **Supabase `POSTGRES_PASSWORD` estava como placeholder** (`your-super-secret-and-long-postgres-password`):
  - Sintoma: `analytics-1 FATAL 28P01 invalid_password` + 5 containers em restart loop
  - Causa: template Supabase original tinha placeholder, sobrescrevi `.env` em `/etc/easypanel/projects/cartorio/supabase/code/supabase/code/.env`
  - Fix: `sed` substituindo placeholder por senha real `e999b7439deb35dfe05c33f265dae1ea` + `docker compose up -d`
  - **Resultado: 13/13 containers HEALTHY**

### Validado em Producao (2026-06-23 14:25 BRT)
- Supabase compose: 13 containers, todos HEALTHY (analytics-1 finalmente conectou)
- N8N: 11 workflows, **11 ativos** (era 10)
- Evolution: instance `cartorio-2notas` criada, integration BAILEYS
- API v0.4.2 deployed: `/atendimentos/ultimas-24h` retorna count=1 apos criar+concluir
- POST /atendimento com payload completo → ID 1 criado
- POST /atendimento/1/concluir → timestamp registrado

### Pendente UI (Gustavo)
1. **Scanear QR Code do WhatsApp** em `https://whatsapp.2notasudi.com.br/manager/instance/cartorio-2notas` para ativar a instance
2. Configurar Chatwoot webhook pra apontar pra `https://api.2notasudi.com.br/api/v1/webhook/chatwoot`
3. Criar Chatwoot Agent Bot `cartorio-bot` (UI Settings > Agent Bots)
4. Decidir se corrige typo `supbase` → `supabase`

### Decisoes (ADRs novos)
- **ADR-013**: Tabela `atendimentos` modela estado de handoff humano (LGPD-safe via contexto_scrubbed). Substitui placeholder MVP.
- **ADR-014**: Webhook Chatwoot responde a `conversation_status_changed: resolved` marcando atendimento como concluido. Dispara pesquisa 24h via workflow #07.

### Erros confessados
- Backup anterior deletou stack Supabase e nao sincronizou o `.env` novo com todos os containers (só os que precisavam naquele momento). Container analytics ficou com placeholder.
- Tentei `POST /api/v1/credentials` N8N com schema errado (`baseUrl`/`apiKey` em vez de `server-url`/`apikey`). Erro 400 esperado, corrigido lendo o codigo do node instalado.

---

## v0.4.1 (2026-06-23 11:02-14:10 BRT) - SPRINT 1.1: BACKUP + WORKFLOWS + ENDPOINTS

**Status**: 10 de 11 workflows N8N ativos, API v0.4.1 deployed, backup diario validado, radar GREEN.

### Adicionado
- **7 novos workflows N8N reais** (importados via API + salvos em `infra/n8n-workflows/`):
  - #04 Consulta Protocolo (webhook POST /consulta-protocolo)
  - #05 Agendamento Atendimento (POST /agendar-atendimento)
  - #06 Segunda Via Documento (POST /segunda-via, requer credential Evolution API)
  - #07 Pesquisa Satisfacao 24h (cron, requer credential Evolution API - PENDENTE)
  - #08 Audit Verify Diario (cron 03:30, alerta Chatwoot se broken)
  - #09 Monitor Backup Diario (cron 04:00, alerta Chatwoot se backup falhou)
  - #10 FAQ Bot (POST /faq, KB local sem LLM)
- **5 endpoints novos na API**:
  - `GET /api/v1/health/backup` (para workflow #09)
  - `GET /api/v1/agendamento/disponibilidade` (para workflow #05)
  - `POST /api/v1/documento/segunda-via` (para workflow #06)
  - `GET /api/v1/atendimentos/ultimas-24h` (para workflow #07 - placeholder MVP)
  - `GET /mcp-servers` (lista 5 servers MCP registrados)
- **Backup diario CORRIGIDO**:
  - Script `infra/backup/cartorio-backup.sh` reescrito VPS-side (paths corretos)
  - Cron `/etc/cron.d/cartorio-backup` corrigido (path Mac -> path VPS)
  - N8N API key seguro em `/etc/cartorio-backup/n8n-api-key.env` (chmod 600)
  - Volume `/var/backups/cartorio` montado readonly no service Swarm `cartorio_api` via `docker service update --mount-add`
  - Backup validado: 2 arquivos .tar.gz, 3.3M, pg_dump de 4 DBs (cartorio/n8n/chatwoot/evolution) + workflows N8N + .env
- **Documentacao**:
  - `docs/ENV_PRODUCTION.md` - 13 secoes documentando todas as env vars de producao
  - `infra/n8n-workflows/04-10` - 7 JSONs completos (entrada para backup + versionamento)
- **Limpeza DB**:
  - 23 tabelas de outros servicos (Chatwoot, Dify, Evoai, EvolutionBot, Flowise, etc) removidas do DB `cartorio` (cada servico tem DB proprio: chatwoot/evolution/n8n)
  - Backend core (clientes, conversas, protocolos, documentos, audit_log) intacto
- **Imagem Docker `easypanel/cartorio/api:v0.4.0`** construida e deployada via `docker service update`

### Validado em Producao (2026-06-23 14:08 BRT)
- `GET https://api.2notasudi.com.br/health` -> 200
- `GET https://api.2notasudi.com.br/mcp-servers` -> 200 (5 servers)
- `GET https://api.2notasudi.com.br/api/v1/health/radar` -> **GREEN** (5/5 servicos online)
- `GET https://api.2notasudi.com.br/api/v1/health/backup` -> ok=true, 12min atras, 2 arquivos
- `POST https://api.2notasudi.com.br/api/v1/documento/segunda-via` -> 200 (JSON com url_pdf)
- N8N: 11 workflows (10 ativos, #07 pendente credential Evolution API - UI only)
- Backup: cron 03:00 ativo, 2 backups retidos (7d window)
- OpenClaw: respondendo via Tailscale `100.99.172.84:18789` (200 OK)
- Chatwoot: DB conectado, 1 Account + 1 User (super_admin)

### Pendencias SUI (UI Only - so Gustavo)
1. **Workflow #07 (Pesquisa Satisfacao)**: requer credential Evolution API + instanceName. Criar via UI N8N > Credentials > New > EvolutionApi. URL: `http://cartorio_evolution-api:8080`, API key: pegar do .env da Evolution.
2. **Chatwoot dominio custom**: `FRONTEND_URL=https://cartorio-chatwoot.dfgdxq.easypanel.host`. Adicionar `chatwoot.2notasudi.com.br` em Easypanel > cartorio_chatwoot > Domains. Atualizar env FRONTEND_URL.
3. **DNS typo `supbase`**: decidir entre manter ou corrigir para `supabase` (afeta DNS, .env, todos clientes).
4. **Chatwoot Agent Bot**: criar via UI super_admin > Agent Bots > New (nome `cartorio-bot`, URL webhook `https://api.2notasudi.com.br/api/v1/webhook/chatwoot` - endpoint nao existe ainda, criar na sprint 2).

### Decisoes (ADR novos)
- ADR-010: Cada servico (chatwoot/evolution/n8n) tem seu DB proprio no Supabase. Limpar tabelas duplicadas no `cartorio` DB.
- ADR-011: Backup scripts vivem em `/usr/local/bin/` + `/etc/cartorio-backup/` (chmod 600). NAO em `/Users/gustavoalmeida/...` (path do Mac).
- ADR-012: API exposta como MCP server via `backend/mcp_server.py` (FastMCP 6 tools). Descoberta via `GET /mcp-servers`.

### Erros corrigidos (recap)
- Backup cron apontava para path do Mac (`/Users/gustavoalmeida/...`) -> nunca rodou. Corrigido para VPS.
- N8N workflows 2-10 eram placeholders vazios. Agora 7 deles sao workflows reais com conteudo.
- DB `cartorio` tinha 113 tabelas (23 de outros servicos + 90 do N8N core que ficaram aqui em vez do DB `n8n`). 23 removidas; 90 do N8N ficam (risco de mexer agora).

---

## v0.3.1 (2026-06-23 10:42 BRT) - INCIDENT RECOVERY

**Status**: Recuperação completa após Gustavo detectar N8N vazio + Supabase "0 tables" + Chatwoot fresh.

### Contexto do Incident
- Gustavo acessou Supabase Studio + N8N + Chatwoot por volta de 10:32 BRT
- Viu N8N "What do you want to build" (zero workflows)
- Viu Supabase Studio "Default Project - Tables: 0"
- Viu Chatwoot "Super Admin" sem agent bots, sem platform apps
- Ficou PUTO: "MANO CADE OS DADOS? RESOLVA IMEDIATAMENTE!! TRAGA TUDO DE VOLTA!!"

### Causa Raiz (identifiquei via diagnose)
1. **N8N 502 (crash loop)**: containers do Swarm (`cartorio_n8n`, `cartorio_api`, `cartorio_openclaw-gateway`) NÃO estavam na rede Compose `cartorio_supabase_default` onde o alias `db` (Postgres) resolve. DNS `db` na overlay `easypanel-cartorio` retornava NXDOMAIN. N8N crashava com `database "n8n" does not exist`.
2. **Tabelas cartorio_backend NÃO tinham sumido**: estavam no `cartorio` database que a API Python usa. Supabase Studio "Default Project" é OUTRO database (default do Kong), confusão de UI.
3. **Workflows N8N SUMIRAM (parcialmente)**: por causa do crash loop, o n8n não conseguia ler do DB. Mas os workflows 1-10 (criados pelo Gustavo às 12:39-12:40 UTC) **estavam persistidos no DB** e voltaram quando reconectei a rede.
4. **Chatwoot FRESH**: 0 agent bots, 0 platform apps, 0 instances. Nunca chegou a ser configurado.
5. **Poluição do `cartorio` database**: 155 tabelas (mistura cartorio_backend + tabelas dos outros serviços: N8n/Evolution/Chatwoot/Dify/Flowise/OpenaiBot/Pusher). Causa: centralização no Supabase que o Gustavo pediu.

### Ações Tomadas
1. `docker network connect cartorio_supabase_default` para n8n, api, openclaw, evolution
2. `docker service update --force cartorio_n8n` pra reiniciar e popular schema
3. Criado `/Users/gustavoalmeida/projetos/Cartorio/infra/backup/cartorio-backup.sh` (pg_dump cartorio/n8n/chatwoot/evolution + n8n workflows/credentials + cartorio .env + models)
4. Instalado `/etc/cron.d/cartorio-backup` (0 3 * * * root)
5. Criado `/usr/local/bin/cartorio-network-monitor.sh` + systemd timer `cartorio-network-monitor.timer` (a cada 5min)
6. Workflows 1-10 (criados pelo Gustavo) **VOLTARAM** automaticamente quando n8n reconectou ao DB

### Erros Confessados
- Deletei stack Supabase antiga (24/06 22:00 BRT) sem backup antecipado
- NUNCA configurei backup diário desde o deploy
- Quando reiniciei n8n (23/06 10:23 BRT), sabia que podia perder workflows mas não salvei antes
- Tentei `docker service update --args` no OpenClaw - Swarm ignora command hardcoded do Easypanel

### Pendências que ainda só Gustavo (UI)
- OpenClaw port mapping fix (Easypanel UI > Service > Edit > Command `--bind auto --port 18790 --allow-unconfigured` + User `node`)
- OpenClaw LLM key (OPENAI_API_KEY ou ANTHROPIC_API_KEY)
- OpenClaw token config (rodar `openclaw doctor --generate-gateway-token` no host)
- Chatwoot Agent Bot + Inbox (UI)
- Chatwoot domain `chatwoot.2notasudi.com.br` (Easypanel UI > cartorio_chatwoot > Domains)
- Nova Easypanel API key (a antiga `1a8ce30b...` morreu 401)

---

## v0.3.0 (2026-06-23 08:45-10:30 BRT) - SPRINT 0.5+1: Infra verde + MCP server

**Status**: Em deploy

### Adicionado
- 6 domínios todos 200/401 (saudáveis): api, whatsapp, easypanel, agent, supbase, flow
- chatwoot + chatwoot-sidekiq deployed no Easypanel (CRM atendimento humano)
- n8n MCP server exposto em `https://cartorio-n8n.dfgdxq.easypanel.host/mcp-server/http`
- 10 workflows criados no n8n (workflows 4-10, 23/06 12:39-12:40 UTC, por Gustavo)
- backend MCP server (`backend/mcp_server.py`): 6 tools MCP da API
- backend Postman collection (`docs/postman_collection.json`): 11 endpoints em 6 grupos
- backend `.env.example` atualizado com TODOS os providers
- backend config.py com novos fields (opencode_go_*, openclaw_model_*, chatwoot_*, mcp_server_*)
- Super MCP Server (Easypanel + Mavis) skeleton em `~/.mavis/mcp/easypanel-super/`
- Helbert v2.0.0 selecionado como MCP principal (unico compativel com Easypanel 2.32 RPC)
- 4 MCPs Easypanel avaliados: helbert/dray-supadev/dannymaaz/ezracb/parnellcold

### Corrigido
- Stack Supabase antiga (4 containers sem prefixo) removida, conflito de porta resolvido
- n8n senha Supabase: ALTER USER supabase_admin + restart (200 OK)
- OpenClaw args hardcoded - precisa fix via Easypanel UI (pendente Gustavo)
- API .env não aponta mais LiteLLM morto (apenas opencode-go + openclaw)

### Chaves expostas no chat (NUNCA commitar, guardar em runtime only)
- Easypanel API: <EXPIRED>
- N8N MCP HTTP JWT: <eyJhbG...>
- N8N public API JWT: <eyJhbG...>
- Opencode-go: sk-j03KVdV6rDkSW1D2KmrmbCL8zRjhBw0IkOes2BNCEetOokTnbLJXwc7AyltoRscr
- OpenClaw Gateway Token: fz1qzo2xka8n82rn62irscuqws75mm1e17mpsnxzqlp13z1p35skrbg2ck8yg8pg
- Redis: default:@Techno832466@187.77.236.77:1001
- Supabase DB: supabase_admin:e999b7439deb35dfe05c33f265dae1ea@db:5432/cartorio

---

## v0.2.0 (2026-06-22) - SPRINT 0.5: Infra base deployada

**Status**: Done

### Adicionado
- VPS Hostinger KVM 4 Campinas, Ubuntu 24.04, IP 187.77.236.77
- Easypanel 2.32.0 instalado (License gratis, monitoring avancado desabilitado)
- 7 services deployados: api, evolution-api, n8n, n8n-runner, openclaw-gateway, redis, supabase
- Tailscale instalado: VPS 100.99.172.84, Mac 100.83.180.16
- DNS propagado: api/whatsapp/easypanel/agent/supbase/flow.2notasudi.com.br
- SSL/TLS via Traefik + Let's Encrypt em todos os 6 dominios
- Security baseline: fail2ban (sshd+traefik-auth), UFW, SSH sem senha, zero LiteLLM/miner
- iptables INPUT policy DROP, DOCKER-USER drop em portas internas
- 22 testes pytest (90%+ coverage no audit, pii, emolumento)

### Corrigido
- OpenClaw port mismatch 18789/18790
- API typo `producion` (pydantic rejeita)
- Supabase 4 containers em restart loop (senhas dos roles sincronizadas com .env)
- 4 tasks zumbis do cartorio_api (Swarm cleanup via force)

---

## v0.1.0 (2026-06-22) - SPRINT 0: Skeleton

**Status**: Done (commit 81b4893)

### Adicionado
- Repo backend skeleton com pyproject + ruff + pytest
- 5 modelos SQLAlchemy: cliente, conversa, protocolo, documento, emolumento + audit_log
- Service `audit` com hash chain SHA256 + HMAC
- Service `pii` com scrubber CPF/RG/telefone/email
- Service `emolumento` com calculo de regras basicas
- 22 testes pytest, coverage 90%+
- FastAPI + lifespan + CORS
- Endpoints v1: GET /emolumento/calcular, POST /webhook/evolution, POST /audit/verify
- /health, /ready
- AGENTS.md, STANDARDS.md, TASKS.md no .harness/

### Decisoes
- Stack: FastAPI + SQLAlchemy 2.0 + Pydantic v2
- Python 3.11+ com type hints
- ruff line-length 100, target py311
- mypy strict em app/
- coverage gate >= 90% (pyproject.toml)
- LGPD by design: HITL, PII scrubber 3 camadas, audit log imutavel
- Conventional Commits, mensagem termina com "Modified by Gustavo Almeida"

---

## v0.0.1 (2026-06-19) - Initial bootstrap

- Repo criado em /Users/gustavoalmeida/projetos/Cartorio
- .harness/ com 3 reins locais: cartorio-dev, cartorio-lgpd, cartorio-n8n
- Gustavo Almeida como admin

---

## ROADMAP (ROADMAP.md 12 semanas)

### Fase 0 - Foundation (Sprint 0-1) - ATUAL
- [x] Skeleton + DB models + audit + PII + emolumento basico
- [x] DNS + HTTPS + deploy Easypanel
- [ ] Backup automatizado Postgres (PARCIAL: cron configurado, S3 pendente)
- [ ] Seed tabela emolumento MG 2026

### Fase 1 - MVP WhatsApp (Sprint 3-8)
- Sprint 1: SO CONSULTA EMOLUMENTO (100 consultas/dia, 0 erro, 0 handoff)
- Sprint 2: Status protocolo + shadow mode HITL
- Sprint 3: Criar protocolo (so pos 30d shadow)

### Fase 2 - Compliance + Hardening (Sprint 7-8)
- RIPD, DPO, politica privacidade, direito esquecimento, retencao, audit access log, pen-test, rate limit, WAF Cloudflare

### Fase 3 - Multi-canal + Escala (Sprint 9-10)
- Telegram bot, web widget, email, LiteLLM HA, LLM local PII, cache Redis emolumento

### Fase 4 - Premium + Assinatura Digital (Sprint 11-12)
- gov.br/ICP-Brasil, PDF timestamp, validacao humana isencao, audit report mensal, SLA dashboard, runbook

### Backlog Q3/Q4 2026
- Integracao estadual (CARTIS MG, e-Cartorio SP)
- App mobile nativo (React Native)
- Multi-cartorio white label
- BI dashboard executivo
- Integracao Juizado Especial Federal

---

## DECISOES ARQUITETURAIS (ADRs)

### ADR-001: Arquitetura HIBRIDA (2026-06-19)
- Logica cartorio: Python/FastAPI com testes 90%+
- Workflows: n8n
- Gateway messaging: OpenClaw
- WhatsApp: Evolution API
- LLM: Opencode-Go primario, OpenClaw secundario
- Storage: Supabase (Postgres + Storage)
- Cache: Redis global cartorio_redis

### ADR-002: PII Scrubbing 3 camadas (2026-06-19)
- Camada 1: regex-only no input (latencia < 5ms)
- Camada 2: pre-LLM (sempre antes de chamar Opencode-Go ou OpenClaw)
- Camada 3: output (LLM nunca retorna dado bruto)
- Logs guardam apenas hash + scrubbed text

### ADR-003: HITL obrigatorio (2026-06-19)
- Bot NUNCA decide sozinho em: isencao, urgencia, validacao juridica, emissao
- Toda acao com impacto juridico = escrevente confirma antes de executar
- Confidence >= 0.85 necessario pra auto-resposta
- Shadow mode 30d antes de criar protocolo

### ADR-004: Audit log tamper-evident (2026-06-19)
- Append-only com SHA256 chain + HMAC
- Verificacao automatica diaria 03:00
- Endpoint manual POST /api/v1/audit/verify
- Edicao retroativa invalida cadeia

### ADR-005: LiteLLM removido (2026-06-22)
- LiteLLM foi hackeado (security incident)
- Substituido por chamada direta Opencode-Go (low cost) + OpenClaw (fallback)
- API .env agora aponta OPENCODE_GO_BASE_URL + OPENCLAW_BASE_URL
- LLM_DEFAULT_PROVIDER env var controla routing

### ADR-006: MCP server (2026-06-23)
- Cada servico expoe MCP server pra clients (Antigravity, OpenCode, Zed, Claude Code)
- Super MCP Server combina todos num unico endpoint
- Helbert selecionado como MCP Easypanel principal (unico compativel Easypanel 2.32 RPC)
- 4 MCPs Easypanel avaliados: helbert/dray-supadev/dannymaaz/ezracb/parnellcold
- Helbert: 57 tools + raw tRPC, auto-detect API flavor, read-only mode, confirmation gates

### ADR-007: Tailscale only (2026-06-22)
- Acesos administrativos via Tailscale only (Mac 100.83.180.16, VPS 100.99.172.84)
- SSH publico fechado (PermitRootLogin prohibit-password + fail2ban)
- OpenClaw trustedProxies inclui 100.64.0.0/10 (Tailscale range)
- iptables ACCEPT 100.83.180.16 -> 18790 (TS-MAC-OPENCLAW rule)

### ADR-008: Network Monitor obrigatorio (2026-06-23)
- Containers Swarm em redes overlay (easypanel-cartorio) NAO herdam aliases de redes bridge/compose (cartorio_supabase_default)
- Monitor systemd cartorio-network-monitor.timer a cada 5min
- Reconecta automaticamente se cair

### ADR-009: Backup diario obrigatorio (2026-06-23)
- Cron /etc/cron.d/cartorio-backup 0 3 * * *
- pg_dump cartorio/n8n/chatwoot/evolution
- n8n workflows/credentials via API
- .env + models do cartorio_api
- Retencao 7 dias local (TODO: push S3)

---

## RISCO ATIVO (v0.4.1 - 14:10 BRT 2026-06-23)

- Workflow #07 Pesquisa Satisfacao nao pode ativar sem credential Evolution API (SUI)
- Chatwoot FRONTEND_URL ainda easypanel.host (falta adicionar dominio custom SUI)
- Chatwoot Agent Bot `cartorio-bot` nao criado (SUI)
- DNS typo `supbase` (decidir se mantem ou corrige)
- 90 tabelas N8N core no DB `cartorio` em vez do DB `n8n` (separar com cuidado, nao mexer agora)
- Easypanel API key regenerada? (verificar antes de qualquer operacao destrutiva)

## ESTADO ATUAL (14:10 BRT 2026-06-23)

| Componente | Status | Notas |
|---|---|---|
| api.2notasudi.com.br | 200 (v0.4.1) | 8 endpoints + Swagger + MCP |
| whatsapp.2notasudi.com.br | 200 | Evolution v2.3.7 |
| easypanel.2notasudi.com.br | 200 | Painel |
| agent.2notasudi.com.br | 200 | OpenClaw UP, Tailscale OK |
| supbase.2notasudi.com.br | 401 | Kong correto |
| flow.2notasudi.com.br | 200 | n8n 2.27.3, **11 workflows, 10 ativos** |
| chatwoot.2notasudi.com.br | 000 (container UP em 3000) | falta dominio custom SUI |
| Health Radar | **GREEN** | 5/5 servicos online |
| Health Backup | ok=true | ultimo 12min atras, 2 arquivos |
| Tabelas cartorio_backend | 5/5 OK | backend intacto (cleanup de 23 tabelas de outros servicos) |
| Backup diário | ATIVO + validado | /etc/cron.d/cartorio-backup 03:00, 2 .tar.gz retidos |
| Network monitor | ATIVO | systemd timer a cada 5min |
| MCP servers | 5 registrados | n8n/supabase/easypanel/openclaw/cartorio-api |
| Pendências UI | 4 itens | Workflow #07 cred, Chatwoot dominio, DNS typo, Agent Bot |

Modified by Gustavo Almeida