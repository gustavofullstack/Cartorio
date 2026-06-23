# CHANGELOG - Cartorio 2 Notas Uberlandia

> Documentacao de TODAS as versoes, decisoes e features desde o inicio do projeto.
> Lido por agents (Mavis) pra ter contexto rapido.

---

## v0.3.0 (2026-06-23) - SPRINT 0.5+1: Infra verde + MCP server

**Status**: Em deploy (Pietra marchando)

### Adicionado
- 6 dominios todos 200/401 (saudaveis): api, whatsapp, easypanel, agent, supbase, flow
- chatwoot + chatwoot-sidekiq deployed no Easypanel (CRM atendimento humano)
- n8n MCP server exposto em `https://cartorio-n8n.dfgdxq.easypanel.host/mcp-server/http`
- 10 workflows criados no n8n (workflows 4-10, 23/06, last update 6min ago)
- backend MCP server (`backend/mcp_server.py`): 6 tools MCP da API
- backend Postman collection (`docs/postman_collection.json`)
- backend .env.example atualizado com TODOS os providers (opencode-go, openclaw, chatwoot, n8n, supabase)
- backend config.py com novos fields (opencode_go_*, openclaw_model_*, chatwoot_*, mcp_server_*)
- Super MCP Server (Easypanel + Mavis) skeleton em `~/.mavis/mcp/easypanel-super/`
- Helbert v2.0.0 selecionado como MCP principal (unico compativel com Easypanel 2.32 RPC)

### Corrigido
- Stack Supabase antiga (4 containers sem prefixo) removida, conflito de porta resolvido
- n8n senha Supabase: ALTER USER supabase_admin + restart (200 OK)
- OpenClaw args hardcoded - precisa fix via Easypanel UI (pendente Gustavo)
- API .env nao aponta mais LiteLLM morto (apenas opencode-go + openclaw)

### Pendente (requer Gustavo via UI)
- OpenClaw port mapping fix via Easypanel UI (Service > Edit > Command `--bind auto`)
- OpenClaw LLM key (OPENAI_API_KEY ou ANTHROPIC_API_KEY)
- OpenClaw token config (rodar `openclaw doctor --generate-gateway-token` no host)
- Decisao DNS typo `supbase` vs `supabase`
- Nova Easypanel API key (a exposta 1a8ce30b... retornou 401)

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
- Skeleton + DB models + audit + PII + emolumento basico (DONE)
- DNS + HTTPS + deploy Easypanel (DONE)
- Backup automatizado Postgres (PENDENTE)
- Seed tabela emolumento MG 2026 (PENDENTE)

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
- API .env agora aponta OPENCODE_GO_BASE_URL (default https://api.opencode.ai/v1) + OPENCLAW_BASE_URL
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

---

## RISCO ATIVO

- OpenClaw ainda pedindo token na UI (precisa `openclaw doctor --generate-gateway-token` no host)
- Easypanel API key expirada (precisa regenerar)
- DNS typo `supbase` (decidir se corrige)
- 4/6 dominios ainda dependem de Gustavo via UI para config final

Modified by Gustavo Almeida