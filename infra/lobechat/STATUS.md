# LobeChat — STATUS SNAPSHOT (2026-07-15 14:45 BRT — F4 [P1] RETRY)

> Snapshot operacional do container LobeChat. Sub-agent `cartorio-evolution` na missão F4 [P1] RETRY.
> Documentação + templates (sem alterar backend code). Cross-refs:
> - Lesson 170 (`lesson-170-lobechat-agent-fix-2026-07-14.md`) — root cause + fix CORS/timeout
> - Lesson 177 (`lesson-177-openclaw-e8-finalize-2026-07-14.md`) — OpenClaw catalog E8
> - Lesson 179 (`lesson-179-dns-cloudflare-fixos-2026-07-15.md`) — DNS runbook (F4 SRE)
> - Lesson 178 (`lesson-178-lobechat-telegram-snapshot-2026-07-15.md`) — esta missão

---

## Estado do container (validado 2026-07-15)

| Item | Valor | Evidência | Status |
|------|-------|-----------|--------|
| Container | **UP (1/1 replicas)** | F4 SRE confirmou EasyPanel dashboard | [WORK] |
| Imagem | `lobehub/lobe-chat` (v1.143+) | `docker inspect` | [WORK] |
| Memória alocada | ~512 MB | docker stats | [WORK] |
| CPU alocada | 0.5 core | docker stats | [WORK] |
| Porta interna | 3210 (TCP) | docker compose | [WORK] |
| Health endpoint | `/api/health` 200 (interno) | `curl http://localhost:3210/api/health` | [WORK] |
| URL funcional | `https://cartorio-lobechat.dfgdxq.easypanel.host` | EasyPanel wildcard | [WORK] |
| URL branded | `https://lobe.2notasudi.com.br` | **PENDING** (Traefik router YAML HOLD-GUSTAVO) | [HOLD-GUSTAVO] |

---

## DNS público (situação 2026-07-15)

| Domínio | Status | Próxima ação |
|---------|--------|--------------|
| `cartorio-lobechat.dfgdxq.easypanel.host` | UP (EasyPanel wildcard) | funcional, sem branding |
| `lobe.2notasudi.com.br` (A record → 187.77.236.77) | **PENDING** | Traefik router YAML ainda não commitado; A record Cloudflare não criado |
| `lobechat.2notasudi.com.br` (variante) | **NÃO configurado** | Gustavo decidir entre `lobe` / `lobechat` |

**Status DNS**: [HOLD-GUSTAVO] — decisão DNS + Cloudflare A record + Traefik router.

> **Cross-ref DNS**: Lesson 179 (`lesson-179-dns-cloudflare-fixos-2026-07-15.md`) — runbook UI 5min para criar A records no Cloudflare. Padrão para chatwoot/n8n/supabase já documentado; mesma técnica vale para `lobe`/`lobechat`.

---

## Variáveis de ambiente (atuais em prod)

| Var | Valor atual | Esperado produção | Status |
|-----|-------------|-------------------|--------|
| `OPENAI_API_KEY` | `sk-xxxx` (placeholder) | bearer do OpenClaw (operator token rotacionável) | [HOLD-GUSTAVO] |
| `OPENAI_PROXY_URL` | (vazio) | `https://agent.2notasudi.com.br/v1` | [HOLD-GUSTAVO] |
| `OPENAI_MODEL_LIST` | (não definido) | `openclaw,openclaw/default,openclaw/main` | [HOLD-GUSTAVO] |
| `CUSTOM_OPENAI_BASE_URL` | (vazio) | `https://agent.2notasudi.com.br/v1` | [TODO] |
| `ACCESS_CODE` | (não definido) | opcional — gate de login | [OPTIONAL] |
| `DATABASE_URL` | postgres interno (EasyPanel volume) | mesmo | [WORK] |
| `AUTH_SECRET` | (gerado pelo EasyPanel) | secret 32+ chars | [WORK] |

**Status `OPENAI_API_KEY=sk-xxxx`**: placeholder significa que o LobeChat hoje roteia chamadas OpenAI reais (que vão falhar com 401) OU retorna mensagem "API key inválida". **Não está usando OpenClaw Gateway ainda.**

> **CORS do OpenClaw (target)**: já configurado para `.2notasudi.com.br`/`.trycloudflare.com`/localhost (Lesson 170 fix). Após Gustavo apontar DNS para `lobe.2notasudi.com.br`, OpenClaw já vai aceitar o origin.

---

## Quem autentica no LobeChat?

| Auth method | Status | Notas |
|-------------|--------|-------|
| **NEXT_AUTH providers** | EasyPanel env `AUTH_SECRET` (cookie session) | [WORK] |
| SSO Google | NÃO configurado | [OPTIONAL] |
| SSO GitHub | NÃO configurado | [OPTIONAL] |
| Email + password (local Postgres) | UP | [WORK] |
| Anonymous access | DESABILITADO por padrão | [WORK] |

**Gustavo e escreventes** acessam com email/senha local criado no primeiro boot do container.

---

## Health & métricas

| Probe | Endpoint | Esperado |
|-------|----------|----------|
| Liveness | `GET /api/health` | 200 |
| Models list (interno LobeChat) | `GET /api/v1/models` | 200 (lista providers configurados) |
| OpenClaw upstream | `GET https://agent.2notasudi.com.br/v1/models` (Bearer) | 200 com lista `openclaw`, `openclaw/default`, `openclaw/main` |

---

## Gap list (ações pendentes)

| # | Ação | Owner | Blocker? |
|---|------|-------|----------|
| 1 | Decidir DNS final (`lobe.2notasudi.com.br` vs `lobechat.2notasudi.com.br`) | Gustavo | sim |
| 2 | Criar A record Cloudflare `lobe → 187.77.236.77` (proxy DNS only) | Gustavo | sim |
| 3 | Commitar Traefik router YAML para branded lobe domain em `infra/traefik/dynamic/lobe.yml` | Gustavo/dev | após #1 e #2 |
| 4 | Gerar operator token OpenClaw (revogar `@Techno832466`) | Gustavo | opcional |
| 5 | Atualizar `OPENAI_API_KEY` no `.env` EasyPanel com operator token | Gustavo | sim |
| 6 | Atualizar `OPENAI_PROXY_URL` → `https://agent.2notasudi.com.br/v1` | Gustavo | sim |
| 7 | Definir `OPENAI_MODEL_LIST=openclaw,openclaw/default,openclaw/main` | Gustavo | sim |
| 8 | Restart container LobeChat (pegar novas envs) | Gustavo | sim |
| 9 | Importar `infra/lobechat/agent_cartorio_import.json` via LobeChat UI (5 cliques) | Gustavo | sim |
| 10 | Validar agente "Cartório 2º Notas de Uberlândia" aparece + responde `oi` | Gustavo | smoke |
| 11 | Ativar monitor Uptime Kuma (`infra/lobechat/monitors.json`) | dev (auto) | já integrado |

---

## Próximos passos (3 ações Gustavo)

1. **DNS + A record + Traefik**: decidir subdomínio + criar A record no Cloudflare (`lobe → 187.77.236.77` proxy DNS only) + commitar router YAML em `infra/traefik/dynamic/lobe.yml` (template em `infra/lobechat/README.md`).
2. **Env OpenClaw**: gerar novo operator token (revoga `@Techno832466`), atualizar `OPENAI_API_KEY` + `OPENAI_PROXY_URL` + `OPENAI_MODEL_LIST` no EasyPanel env do serviço `lobechat`, restart.
3. **Import agente via UI**: seguir `infra/lobechat/SETUP.md` passo-a-passo (5 cliques) e validar smoke `oi → saudação cartorária`.

---

## Cross-refs (mapa de navegação)

- `infra/lobechat/README.md` — runbook de produção (3 passos Gustavo)
- `infra/lobechat/SETUP.md` — passo-a-passo UI (5 cliques) para importar agente
- `infra/lobechat/agent_cartorio_import.json` — schema v1 export
- `infra/lobechat/monitors.json` — Uptime Kuma monitor
- `infra/openclaw-agent/workspace/SOUL.md` — persona source
- `infra/dns/CLOUDFLARE_RUNBOOK.md` — DNS runbook (F4 SRE, Lesson 179)
- `infra/traefik/ROUTERS_PENDENTES.yaml` — Traefik routers template (F4 SRE)
- `.harness/memory/lesson-170-lobechat-agent-fix-2026-07-14.md` — fix CORS+timeout
- `.harness/memory/lesson-177-openclaw-e8-finalize-2026-07-14.md` — catalog E8
- `.harness/memory/lesson-178-lobechat-telegram-snapshot-2026-07-15.md` — esta missão
- `.harness/SUI_CHECKLIST.md` — go-live checklist

---

Modified by Gustavo Almeida — 2026-07-15 14:45 BRT — F4 [P1] RETRY