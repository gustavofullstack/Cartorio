# Plano Mestre de Integração e Otimização do Cartório 2º Notas (100 Tasks)

**Objetivo:** Centralizar, integrar, estabilizar e documentar o ecossistema completo do Cartório AI (API, N8N, Chatwoot, Evolution-API, Supabase, Redis e OpenClaw). Executar em pequenos lotes (1 a 2 agentes por vez) para economizar tokens, focando na melhoria contínua sem refazer o que já funciona e priorizando a integração das frentes.

## Estratégia de Execução
O plano consiste em 100 tarefas (TASKS) divididas em 5 frentes principais, onde cada etapa deve incluir verificação explícita com ferramentas (testes, ruff, mypy) antes do commit.

### Fase 1: Fundação do Supabase (O Banco de Dados Central)
*Status atual (Memória)*: Supabase tem 0 tabelas ativas em uso pela aplicação e carece de configuração profunda.

1. *Inicializar migrations do Supabase*
2. *Configurar webhooks do banco de dados (Supabase → N8N)*
3. *Implementar Jobs pg_cron no Supabase*
4. *Configurar Vault para secrets no Supabase*
5. *Ativar canais Realtime do Supabase*
6. *Storage: Criar buckets seguros para documentos*
7. *RLS (Row Level Security)*: Habilitar políticas rigorosas.
8. *GraphQL Endpoint*: Configurar PostgREST.
9. *Integração API ↔ Supabase Postgres*
10. *Auditoria pgaudit ativa*
11. *Supabase MCP Server local config*
12. *Supabase Queue para processamento assíncrono*
13. *Migrar histórico do SQLite em memória para Supabase DEV*
14. *Validação HMAC no PG*
15. *Documentar Supabase no README e DB.md*
16. *Backup Automatizado (S3)*
17. *Testes de Conexão com Supabase no GitHub Actions*
18. *Rate Limit de Queries (Postgres)*
19. *Views Materializadas para Analytics*
20. *Índices para Busca Full-Text*

### Fase 2: Robustez da API FastAPI e Redis
21. *Implementar Cache Centralizado com Redis*
22. *Refinar a validação de Idempotência no Telegram/Evolution*
23. *Ativar Dead Letter Queue (DLQ)*
24. *Validar Schema OpenAPI do FastAPI no CI*
25. *Criar Documentação Completa da API (API.md)*
26. *Implementar Redlock distribuído para concorrência*
27. *Aprimorar Healthcheck Radar com métricas de Redis*
28. *Adicionar Soft Delete global em SQLAlchemy*
29. *Criar Views de Rate Limiting*
30. *Adicionar Prometheus exporter no FastAPI*
31. *Rotas v2 (Sunset v1 planning)*
32. *Integração com Sentry para erros 500*
33. *Padronizar Erros RFC 7807 problem+json*
34. *Teste E2E Completo na API*
35. *Otimizar queries N+1 (SQLAlchemy selectinload)*
36. *Documentar todos os Middlewares no Wiki*
37. *Health Check de Integrações*
38. *Endpoint Admin de Retenção*
39. *Revisão de PII Scrubbing nos Logs*
40. *Garantir cobertura >90% nos Routers*

### Fase 3: N8N como Workflow Engine Central
41. *Documentar 28+ workflows no README do N8N*
42. *Implementar Error Handler Global no N8N*
43. *Adicionar política de Retry em nós HTTP (N8N)*
44. *Backup Diário de Workflows (N8N) no Supabase*
45. *Testar Workflow de Respostas Rápidas*
46. *Configurar Logs JSON no N8N com Correlation_id*
47. *Métricas N8N no Prometheus*
48. *Alerta Telegram para falhas P0 do N8N*
49. *Playwright E2E runner para 28 Workflows*
50. *Workaround de Variáveis Globais via Env*
51. *Limpar execuções mortas (Prune Cron)*
52. *Deduplicação de mensagens (N8N ↔ Redis)*
53. *Assinatura HMAC nos Webhooks do N8N*
54. *Workflow: Direito ao Esquecimento (LGPD)*
55. *Workflow: Sincronização Analítica*
56. *Workflow: Backup Diário DB*
57. *Aprimorar UI dos Webhooks no N8N*
58. *Padronizar nomes de nós N8N (KISS)*
59. *Configurar Tailscale SSH para o contêiner N8N*
60. *Testar escalabilidade do N8N Runner*

### Fase 4: Chatwoot e Evolution-API (CRM e Mensageria)
61. *Integrar Evolution-API ao Chatwoot Inbox*
62. *Implementar Handoff Humano Bidirecional (API ↔ Chatwoot)*
63. *Popular Canned Responses no Chatwoot (50 templates)*
64. *Habilitar Webhook Signature Validation*
65. *Configurar DNS e Proxy para Chatwoot.2notasudi*
66. *Conectar WhatsApp Meta API Oficial (Fallback)*
67. *Atributos Customizados (CPF/CNPJ Hash) no Chatwoot*
68. *Macros de Handoff (10 macros)*
69. *Relatórios Semanais via Chatwoot APIs*
70. *Automações Internas (Labels)*
71. *Bot Handoff 1-Click na UI*
72. *Deduplicação UUID no Webhook Evolution*
73. *Mapear Status de Entrega (Read/Delivered)*
74. *Desabilitar Inscrições Públicas (Signup Disable) Chatwoot*
75. *Webhook Evolution Retries*
76. *Tratar Media e Documentos via Evolution*
77. *Adicionar Enquetes Interativas (LGPD Polls) no WhatsApp*
78. *Rate Limit por JID no Webhook*
79. *Download Completo da Doc. Chatwoot (.md local)*
80. *Download Completo da Doc. Evolution (.md local)*

### Fase 5: OpenClaw Agent AI (O Assistente Cartório)
81. *Validar e Garantir ContextTokens=1048576 (1M)*
82. *Ajustar Persona do Agent ("Direto, curto, sério, sem emojis")*
83. *Conectar OpenClaw com N8N via MCP Tools*
84. *Teste E2E do Telegram Bot integrado (Ponta a Ponta)*
85. *Ativar Thinking Mode="adaptive" no Gateway*
86. *Resolver Problema do Contexto Limitado (131k vs 1M)*
87. *Registrar as 7 Cartorio Skills explicitamente no config*
88. *Configurar Fallback Providers (OpenCode Go → Claude)*
89. *Monitorar Consumo de Tokens via Codex-Bar CLI*
90. *Adicionar Caching de Prompt no OpenClaw*
91. *Isolar Agent Runtime do Gateway*
92. *Reduzir Latência do Proxy LLM*
93. *Documentar Arquitetura do OpenClaw*
94. *Testes de Concorrencia (5x paralelo) no OpenClaw*
95. *Garantir PII Scrubbing Antes e Depois do LLM*
96. *Dashboard Local de Uso do OpenClaw*
97. *Bloquear Respostas Inseguras (Jailbreak Guardrails)*
98. *Gerar `.harness/memory/openclaw-lessons.md`*
99. *Conectar o Browser Agent UI ao OpenClaw para Testes Visuais*
100. *Orquestrar Teste de Integração Geral: Evolution → API → N8N → Chatwoot → Redis → Supabase → OpenClaw*
