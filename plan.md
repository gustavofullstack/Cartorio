# Roadmap de 100 Melhorias - Cartório AI (Agent Orchestrator)

## 1. Melhorias na API e Core (1-20)
1. Revisar PII scrubbing pre-LLM.
2. Adicionar coverage de testes para novos endpoints Telegram.
3. Melhorar rate limit no Traefik e Redis.
4. Otimizar chamadas ao Supabase (DB index).
5. Refatorar caching (Redis TTL adjustments).
6. Melhorar log masking (não vazar hashes sensíveis).
7. Verificar resiliência em falhas do Traefik.
8. Validar health probes via docker swarm.
9. Consolidar endpoints duplicados no Swagger.
10. Mover rotas deprecated (v2) para fallback.
11. Atualizar models.json para qwen e minimax.
12. Sincronizar MCP Tools com API inventory.
13. Reduzir latency p99 no E2E Chatwoot.
14. Auditar logs para leaks de LGPD.
15. Centralizar configurações do n8n API keys.
16. Adicionar schema validation rigoroso pydantic v2.
17. Atualizar dependências uv e pip.
18. Melhorar error handling em exceptions do FastAPI.
19. Configurar timeout global httpx AsyncClient.
20. Configurar Retry com backoff exp para Evolution API.

## 2. Integração N8N (21-40)
21. Mapear e otimizar Workflow #1.
22. Adicionar fallback cases n8n em timeout.
23. Documentar webhook payload schema n8n.
24. Configurar workflow isolation para Telegram.
25. Padronizar HTTP node auth (usar N8N credentials).
26. Validar Evolution API webhooks no n8n.
27. Integrar Supabase DB logic no n8n.
28. Revisar Redis polling em workflows cron.
29. Reduzir overhead em workflows de handoff.
30. Adicionar error handler global no n8n.
31. Otimizar Chatwoot triggers.
32. Atualizar N8N workflows para nova v1 API.
33. Revisar logs do n8n para PII leaks.
34. Criar monitoramento de Queue N8N.
35. Adicionar Slack/Telegram alert via n8n.
36. Limpar workflows antigos/desativados.
37. Testar cenários E2E (n8n -> FastAPI -> Supabase).
38. Garantir rate limit não impacta n8n HTTP requests.
39. Validar auth headers nos nodes HTTP.
40. Testar load no n8n_runner webhook.

## 3. Melhorias Supabase, DB e Redis (41-60)
41. Habilitar Supabase Vault para secrets.
42. Migrar cron local para Supabase Cron.
43. Mapear Database Webhooks para Notificações.
44. Otimizar Redis memory usage.
45. Configurar Redis persistence policy (RDB/AOF).
46. Configurar TLS em conexões do Postgres.
47. Implementar Realtime Supabase no Front/Dashboard.
48. Criar role-based RLS permissions rigorosas.
49. Limpar schemas antigos/migrations do Alembic.
50. Testar pgvector functions.
51. Otimizar deduplication do Redis (SETNX).
52. Implementar read-replica ou pool no PgBouncer.
53. Centralizar Supabase REST api para consultas externas.
54. Configurar Supabase GraphQL (opcional/review).
55. Verificar Redis sliding window cache performance.
56. Consolidar DLQ (Dead Letter Queue) no Supabase.
57. Documentar schema de tabelas no `docs/`.
58. Adicionar métricas ao Supabase Dashboard.
59. Refatorar auth proxy Supabase/Traefik.
60. Revisar indexes em chaves primárias/FK.

## 4. Evolução AI (OpenClaw, Agent, Prompting) (61-80)
61. Configurar contextTokens para 1048576 (1M) em todos config.
62. Configurar 'thinkings' adaptativo para modelos suportados.
63. Melhorar precisão do MCP (Model Context Protocol).
64. Otimizar system prompt Cartório (mais curto e direto).
65. Testar OpenCode-Zen fallback keys.
66. Configurar Qwen coder options.
67. Habilitar prompt caching (se suportado).
68. Remover emojis dos outputs AI system-wide.
69. Minimizar token usage (review JSON vs Markdown payloads).
70. Testar DeepSeek-v4-flash rate limit / cost.
71. Integrar ZCode/Zed para testes rápidos de agent.
72. Validar Chatwoot-sidekiq fallback handoff behavior.
73. Revisar skill registry no OpenClaw gateway.
74. Configurar max_tokens_per_response adequadamente.
75. Adicionar logs do Codex-bar para usage tracking.
76. Documentar Agent AI memory system e retentions.
77. Fazer stress test com contexto gigante.
78. Adicionar teste automatizado de context recall.
79. Mapear intent classifications de LLM.
80. Refinar UX nas respostas curtas WhatsApp.

## 5. Integração CRM (Chatwoot) e WhatsApp (Evolution) (81-100)
81. Validar webhook Chatwoot (Handoff humano).
82. Validar Chatwoot inbox rules (pausar bot).
83. Testar Evolution API instancing.
84. Configurar retry no envio Evolution.
85. Verificar idempotency em webhooks Evolution -> API.
86. Integrar status de message (read/delivered) via Evolution.
87. Testar envio de arquivos/media no WhatsApp.
88. Integrar contatos no Chatwoot (via Supabase).
89. Criar auto-assignment round-robin no Chatwoot.
90. Testar Evolution API gateway connection.
91. Documentar processo "só conectar o WhatsApp".
92. Revisar TLS do Chatwoot no Traefik.
93. Validar Telegram bot webhook (fallback/test).
94. Garantir que Telegram bot não cause conflito com N8N.
95. Limpar mensagens não resolvidas Chatwoot.
96. Integrar tag do Chatwoot (LGPD Request).
97. Configurar N8N para sync Chatwoot -> Supabase.
98. Adicionar quick replies no Evolution API messages.
99. Revisar dashboard frontend vanilla JS do Agent AI.
100. Auditar 100% integrações prontas para go-live.
