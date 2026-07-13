# 100 Tasks Improvement Plan - Cartório 2notas Chatbot

> **Objective:** Continuous improvement across the entire Cartório 2notas system as per the CEO's directive. "100 Tasks for today" distributed among squad agents (1 or 2 concurrently at most) to optimize token cost, maximize delivery quality, and avoid bugs.

## SQUAD A (cartorio-dev) - Backend, LGPD, Audit
1. Refactor backend tests to mock all external HTTP calls avoiding external dependency failures.
2. Complete integration tests for `test_api.py`.
3. Add rate limiting metrics dashboard using Prometheus.
4. Refactor /protocolos cache invalidation logic.
5. Add unit tests for PII scrubbing output layer.
6. Verify caching mechanism for /protocolos endpoint.
7. Implement sliding window rate limit for login attempts.
8. Add tests for DLQ processing queue.
9. Refactor Sentry integration to support dynamic environment tagging.
10. Ensure zero Ruff warnings remain across the entire backend app folder.

## SQUAD B (cartorio-n8n) - N8N, Evolution, Chatwoot
11. Audit N8N Workflows and document dead branches.
12. Verify Chatwoot Inbox integration for Telegram.
13. Implement automated backup for N8N workflows.
14. Optimize Chatwoot canned responses synchronization.
15. Verify N8N webhook idempotent responses.
16. Implement error handling loop in N8N workflow 01.
17. Verify webhook payload processing from Evolution API.
18. Validate N8N database connection pool size.
19. Refactor N8N API Keys variable injection in workflows.
20. Check Evolution API health checks stability.

## SQUAD C (cartorio-zcode) - Integration, Docs, OpenClaw
21. Verify OpenClaw adaptive thinking configuration across all deployments.
22. Enhance `docs/ARCHITECTURE.md` with new deployment state.
23. Create user guide for the automated testing tools.
24. Document the `tasks_squads_plan.md` framework and orchestration process.
25. Validate 1M context windows limits metrics on OpenClaw.
26. Optimize `.harness/memory` index logic.
27. Update `docs/API.md` with latest endpoints.
28. Document Redis configuration setup process.
29. Review cross-agent knowledge passing mechanism.
30. Audit agent token consumption reporting tools.


## SQUAD D (cartorio-lgpd) - Compliance, DPA, Audit ANPD
31. Verify data retention policies for audit logs (1825 days).
32. Test /lgpd/direito-esquecimento endpoint idempotency.
33. Review DPO email notification templates.
34. Audit anonymization routines for /clientes.
35. Validate consent tracking in N8N workflows.
36. Review PII regex patterns (add passport validation).
37. Test soft delete functionality across all models.
38. Verify pseudonymization in metrics endpoints.
39. Document procedure for handling ANPD data breach notifications.
40. Audit role-based access control (RBAC) in API.

## SQUAD E (cartorio-frontend) - UI/UX
41. Review Chatwoot custom attributes mapping.
42. Update Pietra Agent custom avatar in Chatwoot.
43. Add skip-links to custom Swagger UI.
44. Ensure high contrast mode in custom Swagger UI.
45. Implement custom OpenAPI styling for the documentation portal.
46. Test UI accessibility with screen readers.
47. Optimize CSS bundle sizes.
48. Verify responsive layout for mobile admin views.
49. Review error message copy for user friendliness.
50. Implement visual progress indicators for long-running workflows.

## SQUAD F (cartorio-qa) - Testing
51. Expand E2E Playwright test suite for Chatwoot handoff.
52. Add property-based testing for CPF validation logic.
53. Introduce mutation testing for PII scrubber.
54. Create load tests for /chat endpoint using Locust.
55. Set up chaos engineering experiments (Redis failure simulation).
56. Review code coverage reports to identify missing edge cases.
57. Test fallback mechanism with simulated 503 errors.
58. Audit third-party library vulnerabilities (Snyk/Dependabot).
59. Write test cases for idempotency key collisions.
60. Create parameterized tests for emolumento calculations.

## SQUAD G (cartorio-infra) - DevOps, DB
61. Validate automated database backup restore procedures.
62. Optimize PostgreSQL connection pool settings.
63. Implement query logging for slow queries (>100ms).
64. Review Docker Swarm deployment configurations.
65. Configure log rotation for application logs.
66. Set up automated SSL certificate renewal checks.
67. Add resource limits (CPU/Memory) to docker services.
68. Implement zero-downtime deployment pipeline.
69. Audit database indexes for missing coverage.
70. Set up network policies in docker swarm.

## SQUAD H (cartorio-metrics) - Observability
71. Build custom Grafana dashboard for API metrics.
72. Implement custom Prometheus exporter for N8N queue length.
73. Set up alerting for high error rates (>1%).
74. Trace OpenClaw API calls using OpenTelemetry.
75. Review Sentry grouping rules for better error triaging.
76. Create SLI/SLO dashboards for core services.
77. Monitor Redis cache hit/miss ratio.
78. Set up automated reports for API usage.
79. Audit application logs for sensitive information leaks.
80. Integrate metrics with Telegram bot for weekly summaries.

## SQUAD I (cartorio-security) - SecOps
81. Run SAST analysis on the codebase (Bandit).
82. Review dependency tree for outdated packages.
83. Validate rate-limiting configurations against DDoS vectors.
84. Implement security headers (CSP, HSTS) in the API.
85. Audit webhook signature verification logic.
86. Set up automated dependency updates (Renovate).
87. Review TLS configurations for obsolete ciphers.
88. Create incident response runbook for security breaches.
89. Perform threat modeling for the OpenClaw integration.
90. Test API endpoints for IDOR vulnerabilities.

## SQUAD J (cartorio-agent) - AI Optimization
91. Fine-tune OpenClaw system prompts for better accuracy.
92. Evaluate newer LLM models for potential integration.
93. Optimize RAG implementation (if applicable).
94. Implement semantic caching for frequent queries.
95. Analyze LLM cost metrics and optimize token usage.
96. Test agent resilience against prompt injection.
97. Expand agent skill set with document OCR capabilities.
98. Review agent fallback logic for high latency scenarios.
99. Implement human-in-the-loop (HITL) quality checks for agent outputs.
100. Create a comprehensive training dataset from resolved conversations.
