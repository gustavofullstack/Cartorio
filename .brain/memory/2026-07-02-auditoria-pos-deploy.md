# Auditoria pós-deploy — VPS cartorio (100.99.172.84)

**Data:** 2026-07-02 ~18:30 UTC
**Método:** Somente leitura. `docker service inspect` + `docker ps/inspect/logs` + curl do host + `/proc/<pid>/net/tcp` scan.
**Veredito:** 10/11 OK, 1 quebrado.

---

## Contexto importante

O diagnóstico de hoje às 11:34 e 15:14 em `2026-07-02.md` listava env vars com nomes
errados (`db`, `cartorio_langfuse-redis`, `cartorio_langfuse-db`, `cartorio_argilla-db`,
`cartorio_argilla-redis`). **Esses nomes estão obsoletos.** O deploy de hoje corrigiu
todos eles para apontar ao `cartorio_supabase` (Postgres) e `cartorio_redis`. A
auditoria abaixo confirma que as env vars reais estão consistentes.

A única pendência ENV real é de **permissões PostgreSQL**, não de env var.

---

## Relatório por serviço

```
SERVICO: chatwoot
ESTADO: running (Up 33s, em rolling restart — segunda réplica)
ENV_FIX_AINDA_PENDENTE: nenhuma — POSTGRES_HOST=cartorio_supabase, POSTGRES_DATABASE=chatwoot, REDIS_URL=redis://default:***@cartorio_redis:6379 (todos corretos)
LOGS_DESTAQUE:
  - Booted Rails 7.1.5.2 in production environment
  - Sidekiq 7.3.1 connecting to Redis … url: redis://default:***@cartorio_redis:6379
  - TriggerScheduledItemsJob performing… (jobs normais executando)
  - Sem erros de Postgres / DNS / migrations
HTTP_CHECK: 200 (curl 127.0.0.1:3000 — servico exposto via port-mapping Swarm)
ACAO_RECOMENDADA: nenhuma. Manter monitoramento padrão.
```

```
SERVICO: chatwoot-sidekiq
ESTADO: running (Up 25s)
ENV_FIX_AINDA_PENDENTE: nenhuma (mesmas envs do chatwoot)
LOGS_DESTAQUE:
  - SidekiqAlive started with key SIDEKIQ_REGISTERED_INSTANCE::…  (healthcheck OK)
  - Filas low/scheduled executando normalmente (ReopenSnoozedConversations, TemplatesSync, SLA, etc.)
  - Nenhum erro de conexao
HTTP_CHECK: N/A (worker)
ACAO_RECOMENDADA: nenhuma.
```

```
SERVICO: langfuse-web
ESTADO: running (Up 4 min, sem healthcheck definido)
ENV_FIX_AINDA_PENDENTE: nenhuma — REDIS_HOST=cartorio_redis, REDIS_AUTH=@Techno832466, DATABASE_URL=postgresql://admin:***@cartorio_supabase:5432/langfuse, CLICKHOUSE_URL=http://cartorio_langfuse-clickhouse:8123 (todos corretos)
LOGS_DESTAQUE:
  - Prisma: 394 migrations found, no pending migrations to apply
  - Next.js 16.2.6 ready in 0ms on http://d48c207406d4:80
  - MCP feature registered: prompts
  - Sem erros de Prisma reconnect (problema antigo RESOLVIDO)
HTTP_CHECK: 200 (curl 127.0.0.1:3000)
ACAO_RECOMENDADA: nenhuma. Considerar adicionar healthcheck no Spec p/ Swarm marcar como healthy.
```

```
SERVICO: langfuse-worker
ESTADO: running (Up 4 min)
ENV_FIX_AINDA_PENDENTE: nenhuma (mesmas envs do langfuse-web)
LOGS_DESTAQUE:
  - 22 executors started: trace-upsert, ingestion-queue, dataset-*, evaluation-*, webhook-*, blobstorage-*, data-retention, etc.
  - Listening: http://9c99c33c7097:80
  - Background migrations: nothing to run
  - Finished upserting Langfuse dashboards and widgets in 1623ms
HTTP_CHECK: N/A (worker)
ACAO_RECOMENDADA: nenhuma. Filas todas subscritas e operacionais.
```

```
SERVICO: argilla-web
ESTADO: DEAD — CrashLoopBackOff (4 falhas seguidas "task: non-zero exit (1)", reinicia a cada ~10s)
ENV_FIX_AINDA_PENDENTE: nenhuma nas envs do servico. O problema é permissao PostgreSQL:
  - ARGILLA_DATABASE_URL=postgresql+asyncpg://argilla_user:argillaPassword123@cartorio_supabase:5432/argilla (correto)
  - ARGILLA_REDIS_URL=redis://:%40Techno832466@cartorio_redis:6379/0 (correto)
  - ARGILLA_ELASTICSEARCH=http://cartorio_argilla-elasticsearch:9200 (correto)
LOGS_DESTAQUE:
  - ProgrammingError: (psycopg2.errors.InsufficientPrivilege) permission denied for table alembic_version
  - SQL: SELECT alembic_version.version_num FROM alembic_version
  - Alembic falha ao detectar versao do schema → exit 1 → loop
HTTP_CHECK: 000 (servico nao sobe; nao ha porta em listen)
ACAO_RECOMENDADA: GRANTs no PostgreSQL para o role argilla_user:
  PGPASSWORD=@Techno832466 docker exec cartorio_supabase.1.* psql -U admin -d argilla -c "
    GRANT USAGE ON SCHEMA public TO argilla_user;
    GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO argilla_user;
    GRANT USAGE, SELECT, UPDATE ON ALL SEQUENCES IN SCHEMA public TO argilla_user;
    ALTER DEFAULT PRIVILEGES FOR ROLE admin IN SCHEMA public GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO argilla_user;
    ALTER DEFAULT PRIVILEGES FOR ROLE admin IN SCHEMA public GRANT USAGE, SELECT, UPDATE ON SEQUENCES TO argilla_user;
  "
  (todos os 15 objetos do schema public — alembic_version, datasets, fields, questions, records, responses, suggestions, users, vectors, workspaces, etc. — estao owned por `admin` e `argilla_user` tem ZERO grants. Alembic precisa de SELECT em alembic_version pelo menos para iniciar.)
```

```
SERVICO: argilla-worker
ESTADO: running (Up 4 min)
ENV_FIX_AINDA_PENDENTE: nenhuma (mesmas envs do argilla-web)
LOGS_DESTAQUE:
  - rq.worker: rq:worker:8c2160605fb34f0f9f9c5eec2ebf38ca started with PID 12, version 1.16.2
  - Listening on default, high
  - Scheduler started; cleaning registries
  - Sem erros de conexao com Redis ou Postgres (worker não toca Alembic)
HTTP_CHECK: N/A (worker)
ACAO_RECOMENDADA: nenhuma agora. Quando argilla-web for consertado (GRANTs), o worker continuara funcional. Se quiser, rode o mesmo GRANT preventivo para o worker também acessar alembic_version.
```

```
SERVICO: litellm-app
ESTADO: running (Up 4 min)
ENV_FIX_AINDA_PENDENTE: nenhuma — DATABASE_URL=postgresql://admin:***@cartorio_supabase:5432/litellm (correto)
LOGS_DESTAQUE:
  - prisma migrate deploy completed; 122 migrations found, no pending migrations
  - LiteLLM Proxy v1 migration resolver
  - Uvicorn running on http://0.0.0.0:4000
  - Application startup complete
  - GET /health/readiness HTTP/1.1 200 OK (healthchecks respondendo)
  - Nenhum "Prisma reconnect 300 falhas consecutivas" (problema antigo RESOLVIDO)
HTTP_CHECK: 000 do host (porta 4000 NÃO está publicada no host — bind interno em 0.0.0.0:4000 dentro do container; respondendo via proxy Traefik). Verificado por /proc/<pid>/net/tcp: LISTEN=4000.
ACAO_RECOMENDADA: nenhuma operacional. O servico esta saudavel. Se quiser acesso direto do host, adicionar port mapping 4000:4000 no Spec.
```

```
SERVICO: lobechat
ESTADO: running (Up 4 min)
ENV_FIX_AINDA_PENDENTE: nenhuma (sem envs criticas para diagnostico)
LOGS_DESTAQUE:
  - Next.js 15.3.8 Ready in 622ms
  - DNS Server: 127.0.0.11 (DNS interno do Swarm — resolvendo)
  - Warnings de polyfill: DOMMatrix, ImageData, Path2D (cosméticos, não impedem boot)
  - Warning: Cannot load "@napi-rs/canvas" (PDF rendering limitado, cosmético)
HTTP_CHECK: 000 do host (porta 3210 NÃO publicada). Verificado por /proc/<pid>/net/tcp: LISTEN=3210.
ACAO_RECOMENDADA: nenhuma. Warnings de canvas/polyfill sao benignos.
```

```
SERVICO: crwal4ai
ESTADO: running (healthy — 5 healthchecks consecutivos, Up 4 min)
ENV_FIX_AINDA_PENDENTE: nenhuma (nenhuma env relevante para diagnostico)
LOGS_DESTAQUE:
  - supervisord started redis (in-container) and gunicorn (127.0.0.1:11235)
  - Crawl4AI 0.9.0, FastAPI server started
  - CRAWL4AI_API_TOKEN não setado — bind loopback only (127.0.0.1:11235). Esperado para uso interno.
  - Secret key efêmero (esperado sem SECRET_KEY)
HTTP_CHECK: N/A (servico bind em loopback; healthcheck proprio retornando healthy)
ACAO_RECOMENDADA: nenhuma. Plataforma/arch não interfere (o aviso sobre arm64 em x86_64 do diagnóstico anterior era enganoso; healthcheck está passando).
```

```
SERVICO: evolution-api
ESTADO: running (Up 30 horas — não foi reiniciado pelo deploy de hoje)
ENV_FIX_AINDA_PENDENTE: nenhuma — CHATWOOT_ENABLED=false (intencional? ver abaixo)
LOGS_DESTAQUE:
  - [cartorio-2notas] v2.3.7 — ChannelStartupService Wed Jul 01 09:41:54 — Browser: Evolution API / Chrome / Baileys 2.3000.1042466098
  - WAMonitoringService: Instance "cartorio-2notas" - NOT CONNECTION  (desde Wed Jul 01 09:41:55)
  - Sem logs de tentativa de reconexao depois disso
HTTP_CHECK: 200 (curl 127.0.0.1:8080)
ACAO_RECOMENDADA:
  1. A instância WhatsApp `cartorio-2notas` está NOT CONNECTED há ~33 horas. Provavelmente
     o QR code expirou ou sessão Baileys perdeu. Se for instancia real de cliente,
     é necessário reabrir a instancia via API do Evolution (POST /instance/restart/
     cartorio-2notas) e re-escanear QR. Nao fazer automaticamente — depende do
     uso real.
  2. CHATWOOT_ENABLED=false. Se a intenção era integrar com chatwoot (que agora
     está saudavel), setar para "true" e reiniciar. Confirmar com o usuario.
```

```
SERVICO: zeroclaw
ESTADO: running (Up 3 horas)
ENV_FIX_AINDA_PENDENTE: nenhuma (sem envs criticas)
LOGS_DESTAQUE:
  - WARN: Config file "/zeroclaw-data/.zeroclaw/config.toml" is world-readable (mode 644)
  - ZeroClaw Gateway listening on http://[::]:42617
  - Web Dashboard: http://[::]:42617/
  - PAIRING REQUIRED — code 456630
  - Scheduler: no overdue jobs to catch up
HTTP_CHECK: 000 do host (bind em [::]:42617 dentro do container, sem port mapping para o host). Verificado por /proc/<pid>/net/tcp: LISTEN=42617.
ACAO_RECOMENDADA:
  1. Security: chmod 600 /etc/easypanel/projects/cartorio/zeroclaw/volumes/data/.zeroclaw/config.toml
     (aviso continua aparecendo no startup; config.toml contem credenciais).
  2. Se quiser acessar o dashboard/agent de fora do container, adicionar port
     mapping 42617:42617 no Spec.
```

---

## Veredito final

**10 de 11 serviços saudaveis.** Apenas **1 quebrado**:

```
argilla-web  — CrashLoopBackOff (4 falhas seguidas)
              Causa raiz: GRANTs PostgreSQL faltando para argilla_user
              Solução minima (sem restart dos demais):
                docker exec cartorio_supabase.1.<cid> psql -U admin -d argilla -c "
                  GRANT USAGE ON SCHEMA public TO argilla_user;
                  GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO argilla_user;
                  GRANT USAGE, SELECT, UPDATE ON ALL SEQUENCES IN SCHEMA public TO argilla_user;
                "
              Após o GRANT, Swarm vai detectar exit 1 e tentar novamente (ou
              forçar `docker service update --force cartorio_argilla-web`).
```

**Pendencias nao-bloqueantes (ordenadas por prioridade):**

1. `evolution-api` instancia `cartorio-2notas` NOT CONNECTED ha 33h — verificar
   se é intencional ou precisa restart + re-QR.
2. `zeroclaw` config.toml mode 644 world-readable — chmod 600.
3. `chatwoot/chatwoot-sidekiq` rolling restarts visíveis durante a auditoria —
   provavelmente normal (deploy rolling), mas investigar se for recorrente.
4. `langfuse-web/worker`, `litellm-app`, `lobechat`, `zeroclaw`, `crwal4ai`
   não tem healthcheck no Spec — adicionar para Swarm marcar como healthy.
5. Se `chatwoot<->evolution-api` deve estar integrado, setar
   `CHATWOOT_ENABLED=true` no evolution-api e reiniciar.

**NÃO foram feitas alterações durante a auditoria.** Apenas leituras.