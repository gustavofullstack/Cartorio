# SUPER PLANO 100 TASKS - CARTÓRIO 2º NOTAS INTEGRAÇÃO GERAL

> **Foco:** Melhoria contínua, integração completa (Evolution -> API -> N8N -> Chatwoot -> Redis -> Supabase), documentação e estabilização.

## SQUAD A - CORE API E BACKEND (cartorio-dev)

- [ ] **T001** A1. Fix 100% test coverage timeout na suíte completa (`test_e2e_health.py` e full suite rodando isolado no CI).
- [ ] **T002** A2. Padronizar todos os routers para usar `hmac.compare_digest` onde há verificação de webhooks secret (Evo, Chatwoot, Telegram).
- [ ] **T003** A3. Auditar hardcoded tokens: garantir que configs fallback sejam puramente baseadas em env vars referenciadas, prevenindo leaks.
- [ ] **T004** A4. Expandir Swagger UI customizado: injetar examples JSON reais p/ todos os endpoints POST/PATCH.
- [ ] **T005** A5. Implementar Prometheus /metrics custom counters p/ taxa de erro LLM e N8N timeouts.
- [ ] **T006** A6. Configurar uvicorn worker timeout (prevent hanging connections do gateway).
- [ ] **T007** A7. Refatorar `_send_message` no telegram/whatsapp para usar fila async p/ alta escala, aliviando request cycle time.
- [ ] **T008** A8. Centralizar constants de TTL Redis p/ sessions em `backend/app/core/config.py`.
- [ ] **T009** A9. Otimizar contagem de queries SQLAlchemy: forçar uso de `db.scalar(select(func.count()).select_from(model))` onde há `len(db.execute(stmt).scalars().all())`.
- [ ] **T010** A10. Testes paramétricos pytest p/ scrubber de PII: expandir de 5 para 50 variações de máscaras (CPF, RG, CNH).
- [ ] **T011** A11. CI/CD Pre-commit checks: rodar `uv run ruff format --check` explicitamente apenas nos arquivos difados.
- [ ] **T012** A12. Adicionar health checks profundos para Redis sentinel/cluster connections.
- [ ] **T013** A13. Substituir requests síncronos na inicialização de webhooks do Telegram pelo client assíncrono httpx configurado com retry.
- [ ] **T014** A14. Validar e restringir `CORS_ORIGINS` para rejeitar origens com trailing slashes no setup de produção.
- [ ] **T015** A15. Otimizar `_get_tg_pool()` e equivalentes WhatsApp para reaproveitar TCP connections (Connection Pooling).
- [ ] **T016** A16. Implementar Pydantic strict flags e forward-refs em models de Supabase responses.
- [ ] **T017** A17. Mapear explícito `/api/v2` endpoints alpha em blueprint isolado para migração 2027.
- [ ] **T018** A18. Criar endpoint `/health/dependencies` p/ verificar especificamente binários host como `pdftotext`.
- [ ] **T019** A19. Auditoria de Exceptions em middlewares: evitar que falhas no audit log mascarem a resposta de negócio, logando graceful fallback.
- [ ] **T020** A20. Revisar injeção de dependências (`Depends`) para garantir que sessões do DB sejam fechadas corretamente no teardown assíncrono.

## SQUAD B - SUPABASE INTEGRAÇÃO AVANÇADA (cartorio-dba)

- [ ] **T021** B1. Ativar Supabase Cron para limpeza de sessões mortas no Redis (edge function rodando a cada 1h).
- [ ] **T022** B2. Configurar Database Webhooks: disparar evento p/ webhook N8N ao atualizar `status` na tabela de protocolo.
- [ ] **T023** B3. Migrar tokens sensíveis não-rotacionáveis para Supabase Vault (encryption at rest).
- [ ] **T024** B4. Ativar e documentar introspecção Supabase GraphQL para uso pelo dashboard analytics.
- [ ] **T025** B5. Implementar pg_cron para refresh da Materialized View de emolumentos no DB diretamente.
- [ ] **T026** B6. Configurar Supabase Queues (pgmq) para processamento pesado offload (ex: geração de PDF assinado em background).
- [ ] **T027** B7. Validar Row Level Security (RLS) policies p/ tenant isolation em ambiente multi-cartório.
- [ ] **T028** B8. Escrever documentação canônica (docs/platforms/supabase.md) detalhando setup de Vault/Cron/Webhooks/GraphQL.
- [ ] **T029** B9. Criar dashboard metrics (grafana) alimentado diretamente pelas views do pg_stat_statements.
- [ ] **T030** B10. Otimizar índices DB (B-tree) em colunas frequently queried: `cpf_hash`, `protocolo_id`.
- [ ] **T031** B11. Setup de Logical Replication para read replica ou fallback (preparação HA).
- [ ] **T032** B12. Revisar constraints de deleção (Cascade) vs Soft Delete pattern para LGPD.
- [ ] **T033** B13. Otimizar connection pool Supavisor, alinhando max_connections da API.
- [ ] **T034** B14. Implantar scripts de DB migration CI-tested via CLI do Supabase localmente.
- [ ] **T035** B15. Auditar logs do Kong API Gateway no Supabase para detecção de anomalias (rate limits).
- [ ] **T036** B16. Estabelecer backup rules (WAL archiving) validáveis via Supabase restore test.
- [ ] **T037** B17. Implementar schema migrations reversíveis para todos models SQLAlchemy novos.
- [ ] **T038** B18. Testar fallback em caso de falha de RPC do Supabase.
- [ ] **T039** B19. Integrar MCP cartorio_mcp_supabase para habilitar consultas avançadas via Supabase REST no agent AI.
- [ ] **T040** B20. Configurar triggers de notificação via Supabase Realtime para dashboard admin UI.

## SQUAD C - N8N WORKFLOWS E INTEGRAÇÕES (cartorio-n8n)

- [ ] **T041** C1. Testar todos 12 Workflows ativos e documentar gargalos de falha no README do N8N.
- [ ] **T042** C2. Substituir expressions `$env` inseguras por Data Tables nativas do N8N p/ variáveis persistentes.
- [ ] **T043** C3. WF03 (Handoff Humano): Revisar webhook de callback do Chatwoot p/ evitar loop infinito de update status.
- [ ] **T044** C4. WF04 (Boas-vindas LGPD): Integrar API Supabase direta via webhook para persistir aceite de consentimento.
- [ ] **T045** C5. WF05 (Agendamento): Otimizar node de calendário para fuso horário de Uberlândia explícito (America/Sao_Paulo).
- [ ] **T046** C6. WF06 (2ª via protocolo): Adicionar fallback via e-mail caso PDF falhe envio via Evolution API.
- [ ] **T047** C7. Implementar Global Error Handler Workflow p/ disparar alertas Telegram ao grupo Mavis em qualquer falha crítica N8N.
- [ ] **T048** C8. Revisar configuração de Retry (3x com exp backoff) em todos HTTP Request nodes conectando a API Cartório.
- [ ] **T049** C9. Atualizar docs/platforms/n8n.md ensinando a ler execuções passadas p/ debug.
- [ ] **T050** C10. Ativar node n8n-nodes-mcp e conectar com mcp-server da API.
- [ ] **T051** C11. Documentar processo de export/backup dos JSONs de workflows (Cron export diário p/ repo).
- [ ] **T052** C12. Testar N8N Runners external broker (cartorio_n8n-runner:5680) p/ escalabilidade.
- [ ] **T053** C13. Limpar workflows inativos (5) movendo para pasta `archive/n8n/` p/ despoluir a UI.
- [ ] **T054** C14. Revisar integração N8N -> Redis: usar keyspace events ao invés de polling onde possível.
- [ ] **T055** C15. WF11 (Monitor Cartório): Validar tempo limite (Stale Threshold) p/ alerts de atendimento parado.
- [ ] **T056** C16. WF12 (Chatbot LLM e2e): Refinar prompts system injetados dinamicamente p/ o LiteLLM/OpenClaw.
- [ ] **T057** C17. Adicionar tags de classificação a todos os WFs no painel do N8N (core, util, lgpd).
- [ ] **T058** C18. Otimizar chamadas ao Evolution-API via N8N p/ enviar textos divididos e typing indicators.
- [ ] **T059** C19. Implementar cacheamento N8N via subworkflow Redis p/ reduzir idas redundantes ao DB.
- [ ] **T060** C20. Criar suite de testes simulados de webhook in para os Workflows primários (via curl scripts).

## SQUAD D - OPENCLAW AGENT E EVOLUTION API (cartorio-llm)

- [ ] **T061** D1. Refinar System Prompt Cartório Bot (OpenClaw): torná-lo mais curtos, diretos e sem emojis.
- [ ] **T062** D2. Validar integração do model `deepseek-v4-flash` recém-configurado via endpoints testes.
- [ ] **T063** D3. Revisar fallbacks de providers (LiteLLM / OpenClaw) p/ evitar retry tempest quando internet falha.
- [ ] **T064** D4. Testar a flag `thinking: {enabled: true}` e mapear output do deepseek (chain of thought logger).
- [ ] **T065** D5. Validar OpenClaw Channels configurados (Telegram `HOLD_TOKEN` e WhatsApp `HOLD_QR`).
- [ ] **T066** D6. Evolution-API: Refinar a doc `docs/platforms/evolution-api.md` sobre tratamento de mídia/audios.
- [ ] **T067** D7. Evolution-API: Adicionar webhook signature validation (HMAC) no node de entrada do webhook (N8N ou API).
- [ ] **T068** D8. Evolution-API: Configurar Typebot ou RabbitMQ se houver sobrecarga de webhooks incoming.
- [ ] **T069** D9. Testar limite de context window (1M) enviando histórico denso p/ agent e checando tempo de resposta/token usage.
- [ ] **T070** D10. Integrar `cartorio_mcp_api` profundamente no agent para cálculo dinâmico de emolumentos via MCP Tool call.
- [ ] **T071** D11. Tratar timeouts do modelo de LLM c/ respostas gracefully fallbacks (ex: 'Sistema indisponível').
- [ ] **T072** D12. Configurar Redis Memory curta vs Long-term DB memory para session continuity no OpenClaw.
- [ ] **T073** D13. Atualizar/Verificar os 4 Hooks WebSocket do OpenClaw (`pii_scrub`, `lgpd_consent`, `handoff_decision`, `dead_mans_switch`).
- [ ] **T074** D14. Ajustar temperatura de 0.2 para 0.1 se respostas jurídicas precisarem de mais precisão determinística.
- [ ] **T075** D15. Otimizar `canned_response_matcher`: mapear faq estático antes da chamada LLM (economia token).
- [ ] **T076** D16. Evolution-API: Atualizar configs de presença (enviar typing indicator dinâmico baseado em tamanho resposta LLM).
- [ ] **T077** D17. Monitorar `codex-bar.app` para validar queda drástica de consumo via compactação JSON.
- [ ] **T078** D18. Documentar logs do Gateway OpenClaw p/ facilitar troubleshoot.
- [ ] **T079** D19. Habilitar auto-restart e watchdog via EasyPanel docker metrics no Gateway.
- [ ] **T080** D20. Configurar e testar integração de imagem (vision) caso usuário mande foto de CNH/RG.

## SQUAD E - CHATWOOT, REDIS E FRONTEND ADMIN (cartorio-ux)

- [ ] **T081** E1. Testar webhook de Chatwoot -> N8N validando payload JSON (evitar quebra em conversas multi-agentes).
- [ ] **T082** E2. Configurar Redis Session Keyspace: definir TTL absoluto máximo e documentar no `docs/platforms/redis.md`.
- [ ] **T083** E3. Ajustar `dashboard_runtime.js` de admin dashboards p/ outline keyboard acessibilidade (focus-visible + brand ring).
- [ ] **T084** E4. Chatwoot: Revisar Macros (Canned Responses) criadas no CRM p/ facilitar escreventes.
- [ ] **T085** E5. Redis: Substituir `KEYS *` por `SCAN` em todas as rotinas administrativas python para segurança/performance.
- [ ] **T086** E6. Redis: Configurar persistence RDB + AOF para recuperação de falha da memória de curto prazo.
- [ ] **T087** E7. Chatwoot: Testar handover API `POST /api/v1/integrations/chatwoot/handoff` assegurando pausa do OpenClaw.
- [ ] **T088** E8. Playwright script para validar visualmente interface do Painel Administrativo gerado.
- [ ] **T089** E9. Documentar Sidekiq (Worker Queue do Chatwoot) no `docs/platforms/chatwoot.md`.
- [ ] **T090** E10. Verificar logs Nginx/Traefik do proxy do Chatwoot (WSS/ActionCable).
- [ ] **T091** E11. Mapear metadados do user no Chatwoot via Custom Attributes baseados no DB Supabase.
- [ ] **T092** E12. Otimizar script local `dashboard.py` p/ carregar dados reais mocados vs banco real dev.
- [ ] **T093** E13. Revisar script de geração HTML frontend: não comitar o output `.html` local no repositório final.
- [ ] **T094** E14. Chatwoot: Documentar integração com OpenClaw via LobeChat ou UI agent interface.
- [ ] **T095** E15. Redis: Monitorar hits/misses de rate-limit via Prometheus metrics export.
- [ ] **T096** E16. Validar layout responsivo do Admin Painel (Mobile UX para escreventes via celular).
- [ ] **T097** E17. Criar automação para export do histórico de chat do Chatwoot -> Supabase Long Storage.
- [ ] **T098** E18. Documentar lifecycle de uma conversa no CRM: Novo -> Bot (OpenClaw) -> Bot Paused (Hitl) -> Resolvido.
- [ ] **T099** E19. Configurar alertas no Redis caso memória passe de 80% do teto.
- [ ] **T100** E20. Revisar todo log do Frontend para remover informações sensíveis PII no console.log.
