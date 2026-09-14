# SUPER PLANO DE MELHORIAS — 100 TASKS
**Foco:** Otimizar e integrar: Evolution-API -> API -> N8N -> Chatwoot -> Redis -> Supabase -> Redis -> Chatwoot -> N8N -> API -> Evolution-API

## 1. Supabase Centralization (10 Tasks)
- [ ] T01. Configurar Supabase Cron para limpeza de sessões antigas (Redis fallback).
- [ ] T02. Configurar Supabase Webhooks para notificar N8N em updates na tabela `clientes`.
- [ ] T03. Configurar Supabase Webhooks para notificar N8N em updates na tabela `agendamentos`.
- [ ] T04. Centralizar logs de auditoria via Supabase GraphQL.
- [ ] T05. Implementar fila (Queues) no Supabase para jobs de longo processamento.
- [ ] T06. Ativar Supabase Vault para gerenciar chaves de terceiros com segurança.
- [ ] T07. Validar políticas RLS para garantir isolamento multi-tenant seguro.
- [ ] T08. Otimizar `pool_size` e `max_connections` (Tuning A15).
- [ ] T09. Criar painel de health check nativo do Supabase via API.
- [ ] T10. Integrar logs do Supabase com o Loki/Grafana.

## 2. N8N & Automações (20 Tasks)
- [ ] T11. Testar e validar Workflow de entrada `evo-in`.
- [ ] T12. Auditar Workflow #23 (Stale detector) para garantia de disparo cron 5min.
- [ ] T13. Refatorar autenticação via N8N_MCP_JWT para MCP clients.
- [ ] T14. Testar Workflow de handoff Chatwoot.
- [ ] T15. Atualizar integração n8n-nodes-evolution-api (Community).
- [ ] T16. Atualizar n8n-nodes-chatwoot (Community).
- [ ] T17. Atualizar n8n-nodes-mcp.
- [ ] T18. Configurar retentativas automáticas em workflows críticos (DLQ).
- [ ] T19. Integrar n8n Webhook Secret validation na API do Cartório (Header `X-N8N-API-KEY`).
- [ ] T20. Criar workflow de backup automático do Supabase e enviar p/ S3.
- [ ] T21-T30. [Reservadas p/ testes de workflows individuais].

## 3. OpenClaw Agent AI (20 Tasks)
- [ ] T31. Garantir que a janela de contexto está 1M no `cartorio-bot.openclaw.json`.
- [ ] T32. Validar que `thinking` está `true` no modelo `deepseek-v4-flash`.
- [ ] T33. Validar personalidade "direto, curto, sério, sem emojis" na System Prompt.
- [ ] T34. Integrar ferramenta: N8N (via MCP `cartorio_mcp_api`).
- [ ] T35. Integrar ferramenta: Chatwoot (via MCP `cartorio_mcp_chatwoot`).
- [ ] T36. Integrar ferramenta: Supabase (via MCP `cartorio_mcp_supabase`).
- [ ] T37. Integrar Redis cache nas respostas do OpenClaw.
- [ ] T38. Validar hitl_router (Handoff humano p/ Chatwoot).
- [ ] T39. Mapeamento de intenções PII_scrubber nativo em todas as I/O.
- [ ] T40. Auditar latência e tokens via Supabase.
- [ ] T41-T50. [Testes de stress nos modelos opencode_go de fallback].

## 4. Chatwoot CRM (15 Tasks)
- [ ] T51. Configurar Chatwoot Webhooks recebendo Evolution.
- [ ] T52. Configurar Chatwoot Outbound API chamando N8N.
- [ ] T53. Adicionar tags automáticas baseadas em intenção detectada pelo OpenClaw.
- [ ] T54. Auditar sync de banco de dados entre Chatwoot (Supabase).
- [ ] T55. Testar failover caso Chatwoot-sidekiq falhe.
- [ ] T56. Conectar Canned Responses (mensagens rápidas) na UI com Redis.
- [ ] T57-T65. [Métricas e Painéis].

## 5. API Backend (15 Tasks)
- [ ] T66. Validar Pydantic models em todos os payloads.
- [ ] T67. Melhorar O(N) dict lookups para constantes O(1).
- [ ] T68. Documentar rotas via OpenAPI (`scripts/openapi_snapshot.py`).
- [ ] T69. Executar `uv run ruff format` em todo backend atômico.
- [ ] T70. Remover `# noqa` obsoletos.
- [ ] T71. Fechar vulnerabilidades de secrets expostos.
- [ ] T72. Adicionar testes 100% de coverage na classe SupabaseRESTClient.
- [ ] T73. Atualizar dependências HTTPX e Redis.
- [ ] T74. Isolar chamadas de terceiros (Mock/VCR nos testes).
- [ ] T75-T80. [Circuit breakers e logs].

## 6. Infra & Segurança (20 Tasks)
- [ ] T81. Validar e consertar A records no Cloudflare (n8n, supabase, chatwoot).
- [ ] T82. Traefik rules: assegurar TLS strict.
- [ ] T83. Redis: garantir persistência RDB habilitada.
- [ ] T84. Evolution API: gerenciar cache de QRs expirados.
- [ ] T85. Limpeza de logs rotativos do Loki.
- [ ] T86. Documentar SSH Tailscale ports.
- [ ] T87. Revisar alertas Prometheus.
- [ ] T88. Garantir 0 Rotação de chaves.
- [ ] T89. Finalizar memória de aprendizado.
- [ ] T90-T100. [Ajustes Finos e Otimizações Finais].
