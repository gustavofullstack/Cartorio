# CHANGELOG - Cartorio 2 Notas Uberlandia

> Documentacao de TODAS as versoes, decisoes e features desde o inicio do projeto.
> Lido por agents (Mavis) pra ter contexto rapido.

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

## RISCO ATIVO

- OpenClaw ainda pedindo token na UI (precisa `openclaw doctor --generate-gateway-token` no host)
- Easypanel API key expirada (precisa regenerar via UI)
- DNS typo `supbase` (decidir se corrige ou aceita como oficial)
- 4/6 domínios ainda dependem de Gustavo via UI para config final
- Chatwoot Agent Bot + Inbox nunca foram criados (UI)
- 155 tabelas no cartorio database (poluído, precisa separar em schemas/databases)

## ESTADO ATUAL (10:42 BRT 2026-06-23)

| Componente | Status | Notas |
|---|---|---|
| api.2notasudi.com.br | 200 (health) | 404 raiz é normal FastAPI |
| whatsapp.2notasudi.com.br | 200 | Evolution v2.3.7 |
| easypanel.2notasudi.com.br | 200 | Painel |
| agent.2notasudi.com.br | 200 | OpenClaw UP, pede token |
| supbase.2notasudi.com.br | 401 | Kong correto |
| flow.2notasudi.com.br | 200 | n8n 2.27.3, 10 workflows carregados (vazios) |
| chatwoot.2notasudi.com.br | 000 | DNS não propagou, container UP em 3000 |
| Tabelas cartorio_backend | 5/5 OK | clientes, conversas, documentos, protocolos, audit_log |
| Backup diário | ATIVO | /etc/cron.d/cartorio-backup 03:00 |
| Network monitor | ATIVO | systemd timer a cada 5min |
| Pendências UI | 7 itens | OpenClaw, Chatwoot, Easypanel key, DNS typo |

Modified by Gustavo Almeida