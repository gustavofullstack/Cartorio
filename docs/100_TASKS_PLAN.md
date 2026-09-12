# SUPER PLANO DE MELHORIAS - 100 TASKS (PROJETO CARTÓRIO)

## VISÃO GERAL
Este plano visa analisar, testar, corrigir, melhorar, otimizar e documentar todas as partes vitais do sistema: API (FastAPI), n8n (workflows), Chatwoot (CRM), Evolution API (WhatsApp), OpenClaw Gateway (LLMs), Redis (cache/memória) e Supabase (PostgreSQL + Auth + Storage).
A estratégia será executar de 1 ou 2 agentes no máximo de cada vez, evitando alto consumo de tokens e limites de rate.

## PILARES DE MELHORIA
1. **API (FastAPI)** - Correções de tipagem (mypy), testes rigorosos, rate limiting aprimorado e logs refinados.
2. **n8n (Workflows)** - Automação de idempotência, auditoria profunda nos 34 workflows atuais, fix de tratamento de erros.
3. **Chatwoot & Evolution API** - Garantir sync bidirecional entre chatwoot e Evolution (Webhook via Redis), estabilidade da sessão e fallbacks para human handoff (HITL).
4. **Supabase (PostgreSQL & Features)** - Configurar Database Webhooks para o n8n, garantir RLS em todas as tabelas e ativar CRON jobs internos para expurgo de PII (LGPD).
5. **OpenClaw & LLMs** - Ajuste fino nas prompts do Agente do Cartório, revisão do thinking adaptativo, verificação do limite de contexto (1M).
6. **Integração Telegram Bot** - Melhoria no debounce de mensagens, mock LGPD para estabilizar testes de CI e testes E2E com envio simulado.
7. **Documentação e Observabilidade** - Atualizar READMEs, registrar logs de acesso (Grafana/Sentry/Prometheus) sem vazar PII, gerar mapeamentos.

---

## 100 TAREFAS DE EXECUÇÃO

*(Ver o JSON correspondente `docs/100_TASKS_PLAN_COMPACT.json` para leitura e tracking otimizado por LLMs)*

### SQUAD API CORE
1. Implement mypy strict typing and solve 0 errors in all new endpoints.
2. Add Redis Rate Limiting to avoid spam over `/agendar` endpoint.
3. Fix LGPD Mocks in tests to avoid connection timeouts during test suite execution.
4. Optimize dict indexing for `CANNED_RESPONSES` to replace O(N) lookups.
5. Enhance error handling for FastAPI validation errors.
6. Ensure all admin endpoints enforce `require_cartorio_api_key` explicitly.
7. Review HTTP clients and ensure no `verify=False` is used to prevent MitM attacks.
8. Implement telemetry using OpenTelemetry for core execution flows.
9. Audit all environment variables loaded by pydantic `BaseSettings`.
10. Create Health check endpoints that verify specific DB and Redis connection states.
11. Refactor common utility functions into a dedicated shared module.
12. Ensure all endpoints return strict JSON responses even on 500 errors.
13. Audit logging levels to ensure Production is not too noisy.

### SQUAD N8N OPS
14. Audit all 34 workflows to use environment variables `{{ $env.CARTORIO_API_KEY }}` instead of hardcoded API keys.
15. Create a new fallback workflow for Chatwoot handoff failures.
16. Setup n8n workflow for automated daily metrics reporting to Telegram group.
17. Audit workflows for potential infinite loops.
18. Refactor error handling workflow (`00-error-handler`).
19. Create test data scenarios for each n8n trigger.
20. Standardize logging formats across all JS code nodes.
21. Create a deployment workflow for n8n to sync dev and prod.
22. Implement robust retry nodes for unstable external endpoints.

### SQUAD EVOLUTION API
23. Implement a webhook reconnect mechanism when device is unlinked.
24. Ensure session persistence mapping correctly into Chatwoot inboxes.
25. Clear zombie sessions from Redis to prevent 401 unlinked errors.
26. Create auto-reply rules for off-hours directly in API layer.
27. Implement message sanitization before sending to WhatsApp.
28. Monitor connection state over Redis keys.
29. Set up alerts for specific Evolution webhook failures.
30. Handle media messages gracefully if they exceed processing limits.
31. Ensure read receipts are processed without logging PII.

### SQUAD CHATWOOT
32. Configure Canned Responses dynamically using existing API endpoints.
33. Enforce HITL queue for all protocol-related workflows automatically.
34. Audit agent permissions and ensure only admins can delete tickets.
35. Setup macros for quick response to common legal requests.
36. Implement Chatwoot custom attributes mapping for client CPF.
37. Audit agent inbox mapping.
38. Configure webhooks for ticket status changes.
39. Implement automatic ticket assignment based on payload metadata.
40. Ensure secure API access via `X-Access-Token` header constraints.

### SQUAD OPENCLAW
41. Verify 1M Context Window settings for `deepseek-v4-flash`.
42. Ensure adaptive thinking is set for the default agent models.
43. Integrate OpenClaw fallback providers explicitly into N8N LLM node.
44. Fine-tune system prompt to remove emojis and enforce serious tone.
45. Setup custom MCP hook for the OpenClaw agent execution.
46. Implement PII scrubbing explicitly as a pre-LLM pipeline.
47. Audit agent memory size constraints to fit context limits.
48. Test specific MCP calls using a local python script.
49. Review agent token consumption metrics after adaptive thinking update.

### SQUAD SUPABASE
50. Enable Database Webhooks pointing to n8n intake endpoints.
51. Configure pg_cron for automatic PII expurgo based on retention table.
52. Ensure RLS (Row Level Security) is fully configured for all 134 tables.
53. Utilize Supabase Vault for any custom sensitive tokens.
54. Configure GraphQL endpoints with proper auth limits.
55. Review index fragmentation on main transaction tables.
56. Ensure connection pooling is configured efficiently.
57. Audit database triggers for unexpected side-effects.
58. Ensure all table schemas have descriptive comments for LLM introspection.
59. Configure daily backup checks directly within Supabase Cron.

### SQUAD REDIS
60. Configure TTL checks for active chat sessions.
61. Set up a pub/sub queue for Chatwoot event webhooks.
62. Monitor Redis usage and memory thresholds using Python scripts.
63. Clear any stale Redlock entries automatically.
64. Implement sliding window rate limiting via Redis lua scripts.
65. Optimize cache eviction policies for non-critical data.
66. Implement specific prefixes for different cache domains (e.g., `tg:` vs `api:`).
67. Audit the size of keys to ensure no large blobs are degrading performance.
68. Create a script to gracefully wipe non-critical caches.

### SQUAD API TESTS
69. Increase test coverage for `_typing_loop` and `DEBOUNCE_WINDOW` mocks.
70. Add tests for webhook reconnect paths.
71. Audit and remove hardcoded keys from test files.
72. Mock Supabase calls in an entirely separated integration test suite.
73. Use dynamic future dates in tests to prevent expiration failures.
74. Test the entire data flow: EVOLUTION-API -> API -> N8N -> CHATWOOT.
75. Write security tests to check timing attack vulnerabilities in auth.
76. Ensure all mocked external dependencies have strict assertions.
77. Review the full test suite and categorize tests by execution speed.

### SQUAD OPS & INFRA
78. Setup EasyPanel alerting for high CPU usage.
79. Ensure Browser Agent is configured correctly on the VPS.
80. Create a unified system dashboard HTML for overall health.
81. Setup automatic database snapshotting via cron script.
82. Setup codex-bar token consumption tracking scripts.
83. Audit EasyPanel deploy scripts for idempotency.
84. Review memory notes and extract active incident response plans.
85. Ensure Tailscale ACLs are documented and verified.
86. Check SSH key access and ensure no keys are rotated unnecessarily.
87. Configure Traefik rate limits to prevent brute-force attacks.

### SQUAD DOCUMENTATION & OBSERVABILITY
88. Document all Evolution API endpoints in use.
89. Document Chatwoot Webhook configurations.
90. Create a diagram of N8N workflow interdependencies.
91. Generate Supabase Schema markdown documentation.
92. Document Redis Key usage patterns and TTLs.
93. Update AGENTS.md with new orchestration constraints.
94. Create runbooks for system restart and emergency shutdowns.
95. Consolidate all scattered STATUS.md files into a single reliable source.
96. Document the entire data pipeline and payload structures.

### SQUAD SYSTEM INTEGRATION (E2E)
97. Perform end-to-end latency checks across all services.
98. Verify LGPD compliance via data masking checks on final storage.
99. Verify Telegram Bot integration with specific testing endpoints.
100. Run full system benchmark using a load testing tool.
