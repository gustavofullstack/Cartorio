# Sprint Review — 2026-07-02

## Resumo da Sprint

**Tema**: Diagnóstico e correção completa da stack Docker Swarm do Cartório

**Duração**: ~2 horas (12:55 → 19:10)

**Stack corrigida**: 27/27 serviços Swarm UP no VPS `vps-cartorio` (100.99.172.84)

## Velocity

| Categoria | Planejado | Entregue | Status |
|---|---|---|---|
| Diagnóstico | 1 (read-only) | 1 (Wave 0) | ✅ |
| Correções críticas | 4 (Waves 1-4) | 4 | ✅ |
| Documentação | 1 (Wave 5) | 1 | ✅ |
| Integração | 1 (Wave 6) | 1 | ✅ |
| **Total** | **7 waves** | **7 waves** | **✅ 100%** |

## O que foi entregue (Done)

### Wave 0 — Diagnóstico
- 27 serviços Swarm identificados (JSON dizia 24)
- 8 serviços degradados mapeados
- 6 hosts fantasma descobertos (argilla-db, argilla-redis, langfuse-db, langfuse-redis, litellm-db, "db")
- 2 serviços totalmente down (chatwoot, crwal4ai)

### Wave 1 — Chatwoot fix
- `POSTGRES_HOST=db` → `cartorio_supabase` (web + sidekiq)
- `chat.2notasudi.com.br`: 502 → 302 (login)

### Wave 2 — crwal4ai imagem amd64
- Easypanel trocou `all-arm64` → `:latest` (amd64) automaticamente
- exec format error resolvido

### Wave 3 — argilla/langfuse/litellm
- **argilla-web/worker**: reuso `cartorio_supabase/argilla` + `cartorio_redis`. GRANT ALL + senha SCRAM reset.
- **langfuse-web/worker**: reuso `admin@cartorio_supabase/langfuse` + `cartorio_redis`. Prisma OK, Next.js Ready.
- **litellm-app**: reuso `admin@cartorio_supabase/litellm`. Prisma reconnect 300 retries resolvido.

### Wave 4 — zeroclaw chmod
- `chmod 600 /var/lib/docker/volumes/cartorio_zeroclaw_data/_data/.zeroclaw/config.toml`

### Wave 5 — Documentação
- `docs/SERVICE_INVENTORY.md` criado com mapa real + divergências JSON

### Wave 6 — Chatwoot bootstrap + Evolution↔Chatwoot
- ENABLE_ACCOUNT_SIGNUP=true (DB)
- Account + User SuperAdmin + Inbox API criados via rails runner
- Token Evolution↔Chatwoot: `TgSMyCg134D2GWZ38PaV3N5S`
- CHATWOOT_* envs aplicadas ao evolution-api (scale 0 → update → scale 1)

## Burn-down

```
Wave 0  ████████████████████  ✅ 100%
Wave 1  ████████████████████  ✅ 100%
Wave 2  ████████████████████  ✅ 100% (auto-fix)
Wave 3  ████████████████████  ✅ 100% (6 serviços)
Wave 4  ████████████████████  ✅ 100%
Wave 5  ████████████████████  ✅ 100%
Wave 6  ████████████████████  ✅ 100%
Sprint  ████████████████████  ✅ 100%
```

## Pendências (Backlog)

| ID | Item | Owner | Priority |
|---|---|---|---|
| PEND-001 | Reconectar WhatsApp cartorio-2notas via QR Code | Gustavo (humano) | High |
| TODO-002 | Renomear cartorio_crwal4ai → cartorio_crawl4ai (typo) | orchestrator | Low |
| TODO-003 | Auditar LiteLLM providers (10 do fallback chain) | orchestrator | Medium |
| TODO-004 | Adicionar Swarm healthchecks para detectar CrashLoop antes do 502 | orchestrator | Medium |
| TODO-005 | DBs dedicados para argilla/langfuse/litellm (separar do supabase) | orchestrator | Low |

## Lessons Learned

1. **deploy-port-conflict**: `docker service update --env-add` em serviço com port mapping host pode falhar. **Fix**: scale 0 → update → scale 1 (já documentado em AGENTS.md).
2. **alembic-grants**: GRANTs faltando em schema `public` = causa comum de CrashLoop. **Diagnóstico**: `permission denied for table alembic_version`.
3. **chatwoot-bootstrap**: Chatwoot install novo **NÃO** cria bootstrap data. **Workaround**: rails runner com `InstallationConfig.update(value: true)` + Account + User SuperAdmin + Inbox.
4. **env-vs-db**: Não confiar em env vars Docker como source of truth para config crítica de aplicação. Algumas apps só leem do DB (`InstallationConfig`).

## Métricas de saúde (pós-sprint)

- **Service availability**: 27/27 (100%)
- **Public HTTP responses**: 4/4 endpoints OK (chat 302, easypanel 200, api 200)
- **Pending integration**: 1 (WhatsApp reconnect — bloqueia fluxo end-to-end mas não causa down)
- **Logs sem erros críticos**: 8/8 serviços verificados (langfuse/argilla/litellm/evolution-api/chatwoot/anything-llm/lobechat/zeroclaw)

## Próxima Sprint (recomendação)

**Tema**: Hardening + observability + DB isolation

- Adicionar healthchecks Swarm para detectar CrashLoop rapidamente
- Adicionar Grafana/Prometheus no Easypanel para visualização de métricas
- Auditar e provisionar LiteLLM providers
- Decidir entre manter DB consolidado (mais simples) ou segregar (mais isolamento)

Modified by Gustavo Almeida