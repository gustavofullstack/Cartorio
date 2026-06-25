# Architecture Decision Records (ADRs) — Cartório Chatbot

> Registro de decisões arquiteturais importantes do projeto.
> Última atualização: 2026-06-26.

## O que são ADRs?

**Architecture Decision Records** são documentos curtos que capturam decisões arquiteturais importantes:
- **Contexto**: Por que precisamos decidir?
- **Decisão**: O que decidimos?
- **Consequências**: Prós e contras.
- **Alternativas**: O que mais consideramos?

**Regra**: Toda decisão importante vira um ADR. Formato: `NNN-titulo-curto.md`.

---

## Índice de ADRs

| # | Título | Status | Data |
|---|--------|--------|------|
| [001](#adr-001) | Stack principal (FastAPI + N8N + Supabase) | Aceito | 2026-06-22 |
| [002](#adr-002) | Multi-provider LLM | Aceito | 2026-06-22 |
| [003](#adr-003) | OpenClaw como Agent AI | Aceito | 2026-06-23 |
| [004](#adr-004) | Evolution API como gateway WhatsApp | Aceito | 2026-06-23 |
| [005](#adr-005) | Chatwoot como CRM | Aceito | 2026-06-23 |
| [006](#adr-006) | Traefik como reverse proxy | Aceito | 2026-06-23 |
| [007](#adr-007) | Tailscale como VPN | Aceito | 2026-06-23 |
| [008](#adr-008) | Docker Swarm como orquestrador | Aceito | 2026-06-23 |
| [009](#adr-009) | Easypanel como UI de deploy | Aceito | 2026-06-23 |
| [010](#adr-010) | Isolamento de DB por serviço | Aceito | 2026-06-24 |
| [011](#adr-011) | Scripts de backup no VPS (não no Mac) | Aceito | 2026-06-24 |
| [012](#adr-012) | API como MCP server | Aceito | 2026-06-24 |
| [013](#adr-013) | Backup mount durability | Aceito | 2026-06-25 |
| [014](#adr-014) | Branch master exclusiva | Aceito | 2026-06-25 |
| [015](#adr-015) | OpenClaw 1M context + thinking adaptive | Aceito | 2026-06-25 |
| [016](#adr-016) | Pydantic V2 ConfigDict (não V1 Config) | Aceito | 2026-06-25 |
| [017](#adr-017) | Nunca rotacionar chaves | Aceito (Inviolável) | 2026-06-25 |
| [018](#adr-018) | Trigger updated_at automático | Aceito | 2026-06-25 |
| [019](#adr-019) | Soft delete (deleted_at) | Aceito | 2026-06-25 |
| [020](#adr-020) | /api/v1 + /api/v2 dual versioning | Aceito | 2026-06-25 |
| [021](#adr-021) | RFC 7807 Problem Details | Aceito | 2026-06-25 |
| [022](#adr-022) | Redlock distribuído via Redis | Aceito | 2026-06-25 |
| [023](#adr-023) | Outbox pattern + pg_notify | Aceito | 2026-06-25 |
| [024](#adr-024) | PII Scrub antes de logar | Aceito | 2026-06-25 |
| [025](#adr-025) | RLS em tabelas com PII | Aceito | 2026-06-25 |
| [026](#adr-026) | OpenAPI spec validation no CI | Aceito | 2026-06-25 |

---

## ADR-001: Stack Principal (FastAPI + N8N + Supabase)

**Status**: Aceito
**Data**: 2026-06-22

### Contexto

Precisamos definir a stack tecnológica principal do sistema. Considerações:
- Atendimento via WhatsApp (integração fácil)
- Agent AI para respostas automáticas
- Banco de dados confiável para documentos jurídicos
- Workflows de automação
- Deploy e manutenção simples

### Decisão

Adotamos a stack:
- **API**: FastAPI (Python) - backend central
- **Workflows**: N8N - automação
- **DB**: Supabase (PostgreSQL 15+)
- **Agent AI**: OpenClaw Gateway (deepseek-v4-flash)
- **WhatsApp**: Evolution API v2.3.7
- **CRM**: Chatwoot

### Consequências

**Positivas**:
- Python ecosystem maduro
- N8N low-code (rápido para prototipar)
- Supabase tem Auth, Storage, Realtime, RLS, Vault inclusos
- OpenClaw 1M context (suficiente para conversas longas)
- Tudo self-hosted (controle total)

**Negativas**:
- Muitas peças para manter
- Documentação às vezes escassa
- Dependência de múltiplos fornecedores (apesar de self-hosted)

**Riscos**:
- Complexidade operacional (8+ serviços)
- Mitigação: monitoring, runbooks, postmortems

---

## ADR-002: Multi-Provider LLM

**Status**: Aceito
**Data**: 2026-06-22

### Contexto

Não queremos ficar presos a um único provedor LLM (OpenAI, Anthropic, Google). Precisamos:
- Trocar facilmente entre provedores
- Testar diferentes modelos
- Usar modelos gratuitos quando possível
- Ter fallback se um provedor falhar

### Decisão

Integrações LLM devem ser **agnósticas de provider**:
- Abstração em camada de configuração
- URLs, models, API keys via `.env`
- Suporte para 10+ provedores (OpenAI, Claude, Gemini, DeepSeek, Kimi, etc)

### Consequências

**Positivas**:
- Flexibilidade
- Custo otimizado (modelos grátis para tarefas simples)
- Resiliência (fallback)

**Negativas**:
- Mais código de abstração
- Cada provider tem peculiaridades (tokens, pricing, rate limits)

---

## ADR-003: OpenClaw como Agent AI

**Status**: Aceito
**Data**: 2026-06-23

### Contexto

Precisamos de um Agent AI que:
- Tenha 1M+ tokens de contexto (conversas longas)
- Suporte thinking/chain-of-thought
- Tenha WebSocket (baixa latência)
- Seja self-hosted
- Suporte tools/MCP

### Decisão

**OpenClaw Gateway** (open source) com modelo `deepseek-v4-flash` via OpenCode-Go API.

Configuração:
- Context: 1M tokens
- Thinking: adaptive ON
- Tools: MCP + custom functions

### Consequências

**Positivas**:
- 1M tokens (10x mais que GPT-3.5)
- Thinking melhora qualidade das respostas
- WebSocket = baixa latência
- Self-hosted = controle total

**Negativas**:
- Setup inicial complexo (configuração do agent)
- 1M context custa mais (mitigação: cache, summarization)

---

## ADR-004: Evolution API como Gateway WhatsApp

**Status**: Aceito
**Data**: 2026-06-23

### Contexto

Precisamos de um gateway para WhatsApp Business API. Opções:
- Evolution API (open source, self-hosted)
- Baileys (lib Node.js)
- Twilio (pago, hospedado)
- Z-API (pago, hospedado)

### Decisão

**Evolution API v2.3.7** (self-hosted, open source).

### Consequências

**Positivas**:
- Open source
- Self-hosted
- API REST completa
- Suporta múltiplas instâncias
- Webhooks configuráveis

**Negativas**:
- Dependência de QR scan para conectar
- Documentação às vezes escassa

---

## ADR-005: Chatwoot como CRM

**Status**: Aceito
**Data**: 2026-06-23

### Contexto

CRM para gerenciar conversas, HITL (Human In The Loop), automações:
- Hubspot (pago)
- Salesforce (pago, complexo)
- Chatwoot (open source, self-hosted)
- Pipefy (pago)

### Decisão

**Chatwoot** (self-hosted).

### Consequências

**Positivas**:
- Open source
- HITL built-in
- Canned responses, macros, labels
- API REST completa
- Integração WhatsApp via Evolution

**Negativas**:
- Setup inicial
- UI às vezes lenta

---

## ADR-006: Traefik como Reverse Proxy

**Status**: Aceito
**Data**: 2026-06-23

### Contexto

Reverse proxy com SSL automático para 7+ domínios:
- Nginx (tradicional)
- Caddy (Go, simples)
- Traefik (cloud-native, auto-discovery)
- HAProxy (avançado)

### Decisão

**Traefik** (cloud-native, Docker integration).

### Consequências

**Positivas**:
- Auto-discovery de containers
- SSL automático via Let's Encrypt
- Dashboard built-in
- Cloud-native (nascido para Docker/K8s)

**Negativas**:
- Configuração via labels (não arquivo único)
- Logs às vezes verbosos

---

## ADR-007: Tailscale como VPN

**Status**: Aceito
**Data**: 2026-06-23

### Contexto

Acesso seguro à VPS para o time:
- WireGuard puro (manual)
- Tailscale (gerenciado, zero-config)
- OpenVPN (tradicional)
- SSH com bastion (complexo)

### Decisão

**Tailscale** (zero-config, MagicDNS, ACLs).

### Contexto

**Positivas**:
- Zero-config
- MagicDNS (resolve `vps-cartorio.tail2fe279.ts.net`)
- WireGuard (criptografia moderna)
- Multi-platform (Mac, iOS, Linux)

**Negativas**:
- Dependência do serviço Tailscale (mitigação: SSH direto como fallback)

---

## ADR-008: Docker Swarm como Orquestrador

**Status**: Aceito
**Data**: 2026-06-23

### Contexto

Orquestração de containers:
- Docker Compose (simples, single host)
- Docker Swarm (built-in, simples)
- Kubernetes (poderoso, complexo)
- Nomad (HashiCorp)

### Decisão

**Docker Swarm** (built-in, simples para 1 VPS).

### Consequências

**Positivas**:
- Built-in no Docker
- Mais simples que K8s
- Suficiente para 1 VPS (26 containers)
- Rolling updates

**Negativas**:
- Menos features que K8s
- Comunidade menor

---

## ADR-009: Easypanel como UI de Deploy

**Status**: Aceito
**Data**: 2026-06-23

### Contexto

UI para gerenciar deploys na VPS:
- Portainer (UI Docker genérica)
- Easypanel (Swarm-focused, simples)
- Yacht (UI Docker)
- DIY (scripts bash)

### Decisão

**Easypanel**.

### Consequências

**Positivas**:
- Específico para Swarm
- UI intuitiva
- Git integration (CI/CD built-in)
- Traefik integrado

**Negativas**:
- Vendor lock-in leve (mitigação: API documentada)

---

## ADR-010: Isolamento de DB por Serviço

**Status**: Aceito
**Data**: 2026-06-24

### Contexto

Cada serviço (Cartório, N8N, Chatwoot, Evolution) precisa de banco de dados. Opções:
- 1 DB único (schemas separados)
- Múltiplos DBs no mesmo Postgres
- DBs em servidores diferentes

### Decisão

**Múltiplos DBs no mesmo Postgres** (1 cluster, 4 DBs: cartorio, n8n, chatwoot, evolution).

### Consequências

**Positivas**:
- Isolamento lógico
- Backup independente
- Permissões granulares por DB
- Mais simples que múltiplos servidores

**Negativas**:
- Compartilham recursos (CPU, RAM, disco)
- 1 cluster = 1 ponto de falha (mitigação: backup + replicação)

---

## ADR-011: Scripts de Backup no VPS

**Status**: Aceito
**Data**: 2026-06-24

### Contexto

Onde armazenar scripts de backup (pg_dump, tar, etc)?
- Repositório Git (versionado)
- VPS diretamente (/usr/local/bin)
- Ambos (sync)

### Decisão

**Scripts no repositório** (`backend/scripts/`, `infra/backup/`) **+ deploy no VPS** (`/usr/local/bin/`).

### Consequências

**Positivas**:
- Versionado
- Auditável
- Fácil de atualizar

**Negativas**:
- Deploy step necessário

---

## ADR-012: API como MCP Server

**Status**: Aceito
**Data**: 2026-06-24

### Contexto

Agents externos (Claude, OpenCode, Minimax, etc) precisam acessar funcionalidades do sistema:
- Cada agent tem sua própria forma
- MCP é o padrão emergente

### Decisão

**API FastAPI exposta como MCP Server via FastMCP 3.x** (164 tools).

### Consequências

**Positivas**:
- Padrão universal
- Qualquer agent MCP-compatible usa
- Tools versionadas
- Discovery via `/mcp-servers`

**Negativas**:
- Mais um protocolo para manter
- FastMCP ainda evoluindo

---

## ADR-013: Backup Mount Durability

**Status**: Aceito
**Data**: 2026-06-25

### Contexto

Volume de backup pode ser perdido após `docker service update`. Devemos:
- Recriar volume automaticamente
- Validar em cada deploy
- Alertar se falhar

### Decisão

Volume de backup é montado como **bind mount** do host (`/var/backups/cartorio/`) ao invés de volume Docker (durabilidade).

### Consequências

**Positivas**:
- Sobrevive a qualquer operação Docker
- Acessível direto do host para restore
- Backup scripts rodam fora do Docker

**Negativas**:
- Não-portável entre hosts (mitigação: rsync + S3)

---

## ADR-014: Branch Master Exclusiva

**Status**: Aceito (Regra absoluta)
**Data**: 2026-06-25

### Contexto

Git workflow:
- master only
- feature branches
- gitflow

### Decisão

**Apenas branch `master`**. Nenhuma feature branch. Jules configurado para não criar branches automáticas.

### Consequências

**Positivas**:
- Simples
- Sem merge hell
- Sempre deployável

**Negativas**:
- Risco de quebrar master (mitigação: gates mypy+ruff+pytest)
- Sem code review formal (mitigação: postmortem + testes E2E)

---

## ADR-015: OpenClaw 1M Context + Thinking Adaptive

**Status**: Aceito
**Data**: 2026-06-25

### Contexto

OpenClaw originalmente vinha com contexto 131k tokens (não 1M como documentado). Thinking estava desativado.

### Decisão

Corrigir:
- `models.json`: `contextWindow: 1048576` (1M)
- `agent.json`: `thinking.enabled: true`, `mode: adaptive`, `budget: 10000`

### Consequências

**Positivas**:
- Contexto 8x maior (conversas longas sem perder info)
- Thinking melhora qualidade em tarefas complexas
- Adaptive = só pensa quando necessário (performance)

**Negativas**:
- 1M context = mais memória no LLM provider
- Thinking = mais tokens consumidos

---

## ADR-016: Pydantic V2 ConfigDict

**Status**: Aceito
**Data**: 2026-06-25

### Contexto

Pydantic V1 (`class Config`) está deprecated. V2 usa `model_config = ConfigDict(...)`.

### Decisão

**Pydantic V2 com `ConfigDict`** em todos schemas. Nunca `class Config`.

### Consequências

**Positivas**:
- Sem warnings de deprecation
- Performance 2-50x melhor
- Type hints corretos

**Negativas**:
- Algumas libs externas ainda usam V1 (mitigação: pydantic-compat)

---

## ADR-017: Nunca Rotacionar Chaves

**Status**: Aceito (Inviolável)
**Data**: 2026-06-25

### Contexto

Gustavo (CEO) proibiu terminantemente rotação de chaves. Apenas ele e o agent têm acesso.

### Decisão

**NUNCA rotacionar chaves** (API keys, tokens, senhas, JWTs, etc).

**Única exceção**: chave comprometida por incidente de segurança (decisão do Gustavo).

### Consequências

**Positivas**:
- Sistema sempre funcional (chaves estáveis)
- Sem lock-out acidental
- Conformidade com regra do chefe

**Negativas**:
- Risco teórico de chave exposta (mitigação: audit log + monitoramento)

---

## ADR-018: Trigger Updated_at Automático

**Status**: Aceito
**Data**: 2026-06-25

### Contexto

Coluna `updated_at` em quase todas tabelas. Quem atualiza?

### Decisão

**Trigger automático `BEFORE UPDATE` em TODAS as tabelas** (função `fn_set_updated_at`).

### Consequências

**Positivas**:
- Impossível esquecer
- Consistente
- Auditing simplificado

**Negativas**:
- Pequeno overhead por write (desprezível)

---

## ADR-019: Soft Delete (deleted_at)

**Status**: Aceito
**Data**: 2026-06-25

### Decisão

**Soft delete** (campo `deleted_at`) ao invés de hard delete. Queries padrão filtram `WHERE deleted_at IS NULL`.

### Consequências

**Positivas**:
- Recuperação possível
- Audit trail completo
- LGPD compliance (anonimização posterior)

**Negativas**:
- Tabelas "crescem" (mitigação: vacuum + cleanup job)

---

## ADR-020: /api/v1 + /api/v2 Dual Versioning

**Status**: Aceito
**Data**: 2026-06-25

### Contexto

API v1 estável, mas queremos evoluir. Como versionar?

### Decisão

**Dual versioning**: `/api/v1/*` (estável) + `/api/v2/*` (alpha, sunset 2027).

### Consequências

**Positivas**:
- v1 sempre funcional
- v2 para novos features/testes
- Migração gradual

**Negativas**:
- Manter 2 versões (mitigação: sunset em 2027)

---

## ADR-021: RFC 7807 Problem Details

**Status**: Aceito
**Data**: 2026-06-25

### Contexto

Formato de resposta de erro HTTP:
- JSON customizado
- RFC 7807 (Problem Details for HTTP APIs)
- Problem+JSON (RFC 9457 - update)

### Decisão

**RFC 7807 / 9457 Problem Details** em todos 4xx/5xx.

```json
{
  "type": "https://api.2notasudi.com.br/errors/invalid-cpf",
  "title": "CPF inválido",
  "status": 400,
  "detail": "CPF 12345678900 não passa na validação de dígitos verificadores",
  "instance": "/api/v1/clientes",
  "correlation_id": "abc-123"
}
```

### Consequências

**Positivas**:
- Padrão
- Extensível
- UI consegue parsear consistentemente

---

## ADR-022: Redlock Distribuído via Redis

**Status**: Aceito
**Data**: 2026-06-25

### Contexto

Lock distribuído para migrations, seed, e operações críticas:
- DB advisory locks
- Redis SET NX EX
- Redlock (algorithm)
- ZooKeeper/etcd (overkill)

### Decisão

**Redis SET NX EX + Lua script para safe-release**.

### Consequências

**Positivas**:
- Simples
- Suficiente para nosso caso (1 VPS, 1 Redis)
- Atomic (Lua)

**Negativas**:
- Não é Redlock "full" (5 instâncias Redis)
- Suficiente para 1 Redis

---

## ADR-023: Outbox Pattern + pg_notify

**Status**: Aceito
**Data**: 2026-06-25

### Contexto

Comunicação assíncrona entre API e N8N:
- Direct webhook (pode falhar)
- Polling (ineficiente)
- pg_notify + LISTEN/NOTIFY (Postgres nativo)
- Outbox pattern + N8N DB webhook

### Decisão

**Outbox pattern** (tabela `outbox_messages`) + **pg_notify trigger** + **N8N DB webhook** (escuta mudanças).

### Consequências

**Positivas**:
- Reliable (outbox garante persistência)
- Realtime (pg_notify notifica N8N)
- Standard pattern

**Negativas**:
- Complexidade (mais uma tabela + trigger)

---

## ADR-024: PII Scrub Antes de Logar

**Status**: Aceito (LGPD)
**Data**: 2026-06-25

### Contexto

LGPD art. 37: precisamos rastrear ações mas não vazar PII em logs.

### Decisão

**Middleware de PII Scrub** que substitui CPF, RG, telefone, email, CNS por `[REDACTED-TIPO]` ANTES de logar.

### Consequências

**Positivas**:
- LGPD compliant
- Logs compartilháveis sem risco
- Audit log preserva PII (separado, com RLS)

**Negativas**:
- Logs menos úteis para debug (mitigação: log debug com PII, mas com flag)

---

## ADR-025: RLS em Tabelas com PII

**Status**: Aceito (LGPD)
**Data**: 2026-06-25

### Contexto

Defense in depth: além de auth no app, RLS no DB.

### Decisão

**RLS ativo** em `clientes`, `protocolos`, `documentos`, `audit_log`.

Policies por role:
- `anon`: nada
- `authenticated`: apenas seus próprios dados
- `service_role`: tudo (admin)

### Consequências

**Positivas**:
- DB-level security
- Bypass impossível sem service_role
- Compliance LGPD

**Negativas**:
- Queries mais complexas
- Testes precisam considerar contexto

---

## ADR-026: OpenAPI Spec Validation no CI

**Status**: Aceito
**Data**: 2026-06-25

### Contexto

OpenAPI spec pode ficar desatualizada/inconsistente com código real.

### Decisão

**Middleware valida OpenAPI spec** no CI usando `openapi-spec-validator`. Falha o build se inválida.

### Consequências

**Positivas**:
- Spec sempre válida
- Documentação confiável
- Schema detectado cedo

**Negativas**:
- Mais um check no CI (rápido, < 1s)

---

## Template para Novos ADRs

```markdown
# ADR-NNN: Título Curto

**Status**: Proposto | Aceito | Depreciado | Superseded
**Data**: YYYY-MM-DD
**Decisor(es)**: @autor

## Contexto

[Por que precisamos decidir? Qual o problema?]

## Decisão

[O que decidimos?]

## Consequências

### Positivas
- [Benefício 1]
- [Benefício 2]

### Negativas
- [Trade-off 1]
- [Trade-off 2]

## Alternativas Consideradas

### [Alternativa 1]
[Prós e contras, por que rejeitada]

### [Alternativa 2]
[Prós e contras, por que rejeitada]

## Referências

- [Link 1]
- [Link 2]
```

---

**Mantido por**: Pietra (orquestrador)
**Próxima revisão**: 2026-07-02
**Versão**: 1.0.0
