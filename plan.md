# 100 Tasks Improvement Plan - Cartório Agent AI

## API / Core Backend (Tasks 1-20)
1. Optimize rate limit checks using Redis pipelining.
2. Refactor `cartorio_agent.py` to decouple LLM calls from tool execution.
3. Enhance FastMCP implementation with stricter Pydantic validation.
4. Implement proactive PII redaction caching for repetitive queries.
5. Standardize error responses to RFC 7807 for all v1 endpoints.
6. Reduce database pool timeout edge cases using exponential backoff.
7. Migrate legacy synchronous DB queries to pure `asyncpg` where applicable.
8. Add comprehensive Prometheus metrics for API latency percentiles.
9. Refine Audit chain logs to include tracing headers.
10. Implement zero-downtime schema migrations validation checks.
11. Add a dead-letter queue (DLQ) retry mechanism for failed webhooks.
12. Optimize `emolumento_real_djalma.py` static dictionary lookups to O(1).
13. Enhance `ai_data_extractor.py` handling of fuzzy PII matches.
14. Secure endpoint headers using strict CSP policies.
15. Add E2E tests for the LGPD Art. 18 workflows.
16. Implement dynamic Redis TTL for session state caching.
17. Introduce graceful degradation when third-party APIs fail.
18. Validate N8N integration health continuously.
19. Refactor `app/services/lgpd/` into a modular package.
20. Create synthetic E2E tests for database connection recycling.

## Supabase / Database (Tasks 21-40)
21. Setup Supabase Vault to securely manage environment keys.
22. Configure Supabase Realtime for WebSocket chat updates.
23. Optimize `audit_log` indexing for high read concurrency.
24. Establish Database Webhooks for realtime N8N syncing.
25. Migrate scheduled Python crons to Supabase pg_cron.
26. Optimize pgBouncer pool sizes based on real usage metrics.
27. Utilize Supabase GraphQL for internal dashboard stats.
28. Secure `anon` and `service_role` keys through RLS policies.
29. Create automated database backup validation scripts.
30. Index heavily searched `cliente` fields (e.g., telefone).
31. Establish row-level security for `emolumento` modifications.
32. Setup Supabase Queues for background AI extraction jobs.
33. Tune PostgREST configurations for faster REST throughput.
34. Analyze query plans for the `atendimento` endpoints.
35. Create database schema validation on CI.
36. Review and prune stale `webhook_event` logs daily.
37. Implement database-level data masking for PII fields.
38. Add failover checks for Supabase read replicas.
39. Document Supabase Vault configurations for new devs.
40. Monitor Supabase CPU/Memory utilization via Prometheus.

## OpenClaw / Agent AI / Security (Tasks 41-60)
41. Set OpenClaw context to 1M tokens (Fix 131.1k bug).
42. Enable adaptive thinkings for complex task reasoning.
43. Refine Pietra Persona prompt: no emojis, direct, short, serious.
44. Ensure PII is scrubbed before reaching OpenClaw API.
45. Standardize OpenClaw fallback chains to prevent timeouts.
46. Create E2E test for OpenClaw gateway connection.
47. Implement rate limiting on OpenClaw model endpoints.
48. Audit OpenClaw API keys against leakage.
49. Review `agent.json` settings for strict adherence to persona.
50. Add logging wrapper for OpenClaw tool usage.
51. Restrict internal tool usage only to verified channels.
52. Conduct automated penetration testing on the MCP interface.
53. Create a unified system prompt generator script.
54. Monitor token consumption per session using local db.
55. Enforce strict type checking on MCP tool inputs.
56. Create synthetic tests for handling OpenClaw 429s.
57. Refine fallback latency timeout settings.
58. Audit all E.164 phone number masking algorithms.
59. Review human-in-the-loop (HITL) triggering conditions.
60. Create standard response templates for LGPD inquiries.

## Evolution API / WhatsApp / Chatwoot (Tasks 61-80)
61. Validate Evolution API WhatsApp E2E connectivity.
62. Stabilize QR code pairing lifecycle using exponential reconnect.
63. Integrate Evolution API webhooks directly to N8N.
64. Implement robust retry mechanisms for Evolution message sending.
65. Audit Evolution API token rotation strategy (do not rotate).
66. Optimize Chatwoot CRM database queries.
67. Ensure Chatwoot sidekiq workers have adequate Redis memory.
68. Implement Chatwoot API rate limiting.
69. Connect Chatwoot inboxes directly to Supabase logs.
70. E2E test the pause/resume bot flow via Chatwoot.
71. Verify Chatwoot API keys securely using HMAC.
72. Implement automated CRM tagging based on user intent.
73. Secure internal Chatwoot APIs via Tailscale.
74. Improve Chatwoot dashboard latency.
75. Add webhooks for Chatwoot conversation assignment.
76. Optimize WhatsApp media attachment handling.
77. Verify Evolution API instance status automatically.
78. Clear stale Chatwoot sessions weekly.
79. Integrate Chatwoot events to the internal audit log.
80. Document Evolution API deployment topology.

## N8N / Workflows / Redis (Tasks 81-100)
81. Standardize N8N authentication using environment variables.
82. Export and version all N8N workflows locally.
83. E2E test N8N workflows against mock API responses.
84. Secure N8N runner instances via internal network constraints.
85. Integrate N8N seamlessly with Supabase Database Webhooks.
86. Monitor N8N runner CPU/Memory usage.
87. Create an N8N node for calculating Emolumentos.
88. Optimize Redis caching for N8N workflow states.
89. Use Redis Redlock for preventing concurrent N8N job execution.
90. Optimize Redis memory usage with strict TTL policies.
91. Add Redis slow log monitoring to the dashboard.
92. Secure Redis connections using TLS.
93. E2E test Redis failover resilience.
94. Analyze Redis cache hit/miss ratio for API endpoints.
95. Consolidate N8N webhook endpoints.
96. Document N8N workflow error handling strategies.
97. Audit Redis keys for compliance with LGPD (PII removal).
98. Automate N8N deployment sync with git repository.
99. Setup Slack/Discord alerts for N8N workflow failures.
100. Conduct final overarching smoke test for the entire pipeline.
