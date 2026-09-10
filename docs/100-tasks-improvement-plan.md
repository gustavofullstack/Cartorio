# 100-Task Improvement Plan for Cartório Agent AI Ecosystem

**Goal:** Analyze, test, fix, improve, optimize, organize, document, and comment across all 14 pillars of the platform, orchestrating safely using only 1 or 2 subagents concurrently.

## Phase 1: Diagnostics and Baseline Stabilization (Tasks 1-20)
1. Full diagnostic of `cartorio-backend` health on Hostinger.
2. Verify Redis operational queues (`bot_mute`, `rate_limit`, `sessions`).
3. Audit Supabase Realtime and Auth setup.
4. Test current N8N workflows (1 to 38) against the mocked LLM fallback.
5. Re-run complete local `make qa` and address any skipped/pending flaky tests.
6. Check Traefik routers configuration in EasyPanel.
7. Validate Telegram `@TestCartorioBot` connectivity (webhook idempotency).
8. Inspect WhatsApp (Evolution API) connection stability and session health.
9. Verify OpenClaw Gateway proxy logs and timeout settings.
10. Ensure Chatwoot connection hooks are fully operational.
11. Add deep observability (OpenTelemetry) traces to `test_telegram_e2e_5x.py`.
12. Review `health_radar_expanded.py` for correct fail-open behavior.
13. Centralize all `.env.example` keys to match current live required configs.
14. Optimize Dockerfile layers for the FastAPI backend.
15. Remove or archive dead code blocks and obsolete scripts in `scripts/`.
16. Ensure `pre-commit` hooks cover all formatting rules strictly.
17. Review `N8N_DASHBOARD_2026-06-30.md` against live N8N state.
18. Validate the `redis_queues` category in the Health Radar.
19. Re-run `test_vps_readiness_audit.py` with full strict coverage.
20. Document initial baseline findings in `STATUS.md`.

## Phase 2: Supabase Integration & Centralization (Tasks 21-40)
21. Fully implement Supabase Vault for secret management.
22. Configure Supabase Cron jobs for stale cache cleanup.
23. Setup Supabase Database Webhooks for real-time `outbox_messages` push to N8N.
24. Migrate remaining local SQLite test fixtures to mock Supabase PostgREST.
25. Implement Supabase GraphQL endpoints for frontend dash queries.
26. Set up strict RLS (Row Level Security) policies for the `clientes` table.
27. Setup RLS for the `emolumentos` table.
28. Set up RLS for the `protocolos` table.
29. Review and optimize PostgreSQL indices for `updated_at` triggers.
30. Centralize all user identity tracking into Supabase Auth.
31. Improve error handling for Supabase 401 Unauthorized responses.
32. Document Supabase architecture in `docs/SUPABASE_ARCHITECTURE.md`.
33. Create unit tests for Supabase Auth JWT validation middleware.
34. Implement Supabase Queues for background task processing (replacing local tasks).
35. Verify connection pooling (PgBouncer) settings for Supabase.
36. Add Supabase Realtime subscriptions to the N8N listener workflow.
37. Optimize database migrations (`alembic`) for zero-downtime deployment.
38. Create a disaster recovery test script for Supabase backups.
39. Write documentation for the Supabase Vault integration.
40. Complete an end-to-end test of the Supabase data pipeline.

## Phase 3: N8N and Evolution API Orchestration (Tasks 41-60)
41. Audit N8N workflow `01-consulta-emolumento.json` for token efficiency.
42. Refactor N8N workflow `02-criar-protocolo.json` to use Supabase Webhooks.
43. Test and fix N8N workflow `12-chatbot-llm-end-to-end.json`.
44. Ensure N8N workflows use dynamic environment variables (`={{ $env.CARTORIO_API_KEY }}`).
45. Implement a robust retry policy in N8N for Evolution API timeouts.
46. Create a new N8N workflow for monitoring WhatsApp QR code expiration.
47. Centralize N8N error handling into a single reusable sub-workflow.
48. Test the integration between Evolution API and Chatwoot for human handoff.
49. Optimize Evolution API message ingestion throughput.
50. Add metrics collection for N8N workflow execution times.
51. Document all N8N workflows in a new `docs/N8N_WORKFLOWS.md` file.
52. Create a script to bulk-import N8N workflows into a clean environment.
53. Implement PII scrubbing within N8N before sending data to external APIs.
54. Test the Evolution API rate limit handling.
55. Set up alerts for Evolution API disconnect events.
56. Refactor the Chatwoot sidekiq integration for better background processing.
57. Verify Chatwoot macros for automated tagging and assignment.
58. Document the Chatwoot CRM configuration in `docs/CHATWOOT_CRM.md`.
59. Create an end-to-end test for the WhatsApp -> Evolution -> N8N -> Chatwoot flow.
60. Review and optimize the N8N runner resource limits (CPU/Memory).

## Phase 4: OpenClaw Agent AI and Model Optimization (Tasks 61-80)
61. Validate `deepseek-v4-flash` reasoning behavior with the new 1M context window.
62. Create a specific `system prompt` for OpenClaw that enforces a strict, serious tone without emojis.
63. Implement adaptive thinking triggers for complex legal queries.
64. Test the fallback mechanism to `anthropic-claude-sonnet-4.5` if `deepseek` times out.
65. Optimize the FastMCP tool definitions for token efficiency.
66. Add a new MCP tool for querying Supabase Realtime status.
67. Add a new MCP tool for retrieving Chatwoot agent availability.
68. Implement prompt caching for frequently asked questions (FAQs).
69. Create a dashboard to monitor LLM token consumption (input/output/reasoning).
70. Test the OpenClaw Gateway proxy for cross-origin resource sharing (CORS) issues.
71. Document the OpenClaw Gateway configuration in `docs/OPENCLAW_ARCHITECTURE.md`.
72. Implement rate limiting for the OpenClaw Gateway API.
73. Create a unit test for the OpenClaw Gateway timeout logic.
74. Optimize the payload size sent to the LLM (PII scrubbing + context reduction).
75. Review the `cartorio_api_emolumento_calcular` MCP tool for accuracy.
76. Review the `cartorio_api_protocolo_consultar` MCP tool for LGPD compliance.
77. Implement a "Dead Man's Switch" for the Agent AI to fail-safe to human routing.
78. Create an automated test for the Agent AI's response latency.
79. Document the prompt engineering guidelines in `docs/PROMPT_GUIDELINES.md`.
80. Conduct a full security audit of the Agent AI integration.

## Phase 5: Codebase Polish, Documentation, and Finalization (Tasks 81-100)
81. Run a comprehensive `ruff format` and `ruff check` across the entire codebase.
82. Ensure all Python files have descriptive docstrings (PEP 257).
83. Refactor any functions with a cyclomatic complexity > 10.
84. Update `README.md` with the latest system architecture diagram.
85. Create a `CONTRIBUTING.md` guide for future agents and developers.
86. Update `AGENTS.md` with the new OpenClaw configurations.
87. Document the local development setup process in `docs/LOCAL_DEV.md`.
88. Create a troubleshooting guide for common VPS deployment issues.
89. Implement a script to automatically rotate logs in the Hostinger VPS.
90. Verify the Tailscale SSH ACL configuration.
91. Add inline comments to complex regular expressions.
92. Optimize the `Dockerfile` for a smaller image size.
93. Create a `Makefile` target for running the 100-task orchestration.
94. Review all `TODO` and `FIXME` comments in the codebase.
95. Implement a continuous integration (CI) pipeline for the N8N workflows.
96. Create a dashboard in EasyPanel for monitoring system health.
97. Document the disaster recovery procedure in `docs/DISASTER_RECOVERY.md`.
98. Conduct a final end-to-end test of all integrated systems.
99. Record all learnings in `.jules/bolt.md`, `.jules/palette.md`, and `.jules/sentinel.md`.
100. Generate a final summary report of the 100-task improvement plan.
