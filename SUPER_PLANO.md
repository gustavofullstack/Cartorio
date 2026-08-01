# SUPER PLANO DE MELHORIAS (100 TASKS)

## S1: Supabase Configuration & Integration
**Description**: Centralize DB usage by enabling Vault, Webhooks, Queues, Cron, and GraphQL.

- [ ] T1: Configure Supabase Vault for secure credential storage.
- [ ] T2: Enable Supabase Database Webhooks for realtime event triggers.
- [ ] T3: Implement Supabase Queues for asynchronous background jobs.
- [ ] T4: Set up Supabase Cron for scheduled tasks (e.g., daily reports).
- [ ] T5: Enable and test Supabase GraphQL for advanced analytical queries.
- [ ] T6: Migrate hardcoded database credentials to Supabase Vault.
- [ ] T7: Create integration tests for Supabase API interactions.
- [ ] T8: Refactor user authentication flows to fully leverage Supabase Auth.
- [ ] T9: Audit and optimize Row Level Security (RLS) policies.
- [ ] T10: Document Supabase integration patterns and architecture.

## S2: N8N Workflows Optimization & Testing
**Description**: Improve N8N as a central hub, fixing workflows, testing, and centralizing logic.

- [ ] T1: Audit existing N8N workflows for failed executions and bottlenecks.
- [ ] T2: Standardize error handling and retry logic across all workflows.
- [ ] T3: Integrate N8N closely with API via unified webhook endpoints.
- [ ] T4: Implement testing harness for automated workflow validation.
- [ ] T5: Optimize N8N API rate limits and throttling controls.
- [ ] T6: Update N8N nodes to their latest API schemas.
- [ ] T7: Centralize workflow variables and credentials using external Vault.
- [ ] T8: Implement telemetry and logging for every critical workflow step.
- [ ] T9: Create mock-based tests for third-party integrations in N8N.
- [ ] T10: Document all active N8N workflows and their dependencies.

## S3: Evolution-API & Chatwoot Integration Reliability
**Description**: Ensure stable WhatsApp connection, CRM routing, and HITL flow.

- [ ] T1: Audit Evolution-API webhook delivery reliability to API/N8N.
- [ ] T2: Optimize Chatwoot inbox assignment logic for HITL handoffs.
- [ ] T3: Implement automatic retry mechanisms for Evolution-API message failures.
- [ ] T4: Configure Chatwoot Sidekiq workers for high concurrency.
- [ ] T5: Enhance Evolution-API instance health checks and auto-restarts.
- [ ] T6: Map all Chatwoot custom attributes to Supabase user profiles.
- [ ] T7: Create a monitoring dashboard for WhatsApp message latency.
- [ ] T8: Streamline the Chatwoot <-> OpenClaw Agent pause/resume flow.
- [ ] T9: Conduct load testing on Chatwoot webhook endpoints.
- [ ] T10: Document Evolution-API and Chatwoot integration architecture.

## S4: Redis Advanced Caching & Real-time Pipeline
**Description**: Improve Redis usage for caching, session memory, and quick retrieval.

- [ ] T1: Implement Redis Stream consumers for high-throughput event logging.
- [ ] T2: Configure Redis Sentinel for high availability and failover.
- [ ] T3: Optimize Redis TTLs for short-lived session contexts.
- [ ] T4: Replace expensive database aggregate queries with Redis cached counters.
- [ ] T5: Implement Redis Pub/Sub for real-time dashboard updates.
- [ ] T6: Audit Redis memory usage and configure eviction policies.
- [ ] T7: Create integration tests for Redis cache invalidation logic.
- [ ] T8: Secure Redis instances with strong authentication and TLS.
- [ ] T9: Implement Redis-based rate limiting for public API endpoints.
- [ ] T10: Document Redis schema, keyspaces, and data structures.

## S5: OpenClaw Agent Tuning & Hooks Optimization
**Description**: Refine Agent AI Cartorio behavior, skills, and tools execution.

- [ ] T1: Validate deepseek-v4-flash thinking capability across all tool calls.
- [ ] T2: Test OpenClaw agent 1M context window limits with large conversation histories.
- [ ] T3: Optimize OpenClaw system prompt for maximum adherence to no-emoji policy.
- [ ] T4: Audit and improve OpenClaw MCP tools parameter schemas.
- [ ] T5: Implement stricter PII scrubbing hooks before tool execution.
- [ ] T6: Enhance agent fallback mechanisms when primary LLM fails.
- [ ] T7: Develop automated prompt evaluations for legal accuracy.
- [ ] T8: Integrate OpenClaw directly with Supabase Vault for credential retrieval.
- [ ] T9: Test agent integration end-to-end via Telegram Bot.
- [ ] T10: Update OpenClaw skills documentation and JSON schemas.

## S6: API Core Enhancement & Standardization
**Description**: Centralize logic in the API and improve its endpoints.

- [ ] T1: Audit all API endpoints for consistent RESTful design patterns.
- [ ] T2: Standardize API error responses (RFC 7807 Problem Details).
- [ ] T3: Implement API pagination for all collection endpoints.
- [ ] T4: Optimize SQLAlchemy queries to eliminate N+1 fetching.
- [ ] T5: Replace in-memory list len() calls with optimized database count().
- [ ] T6: Add comprehensive input validation using Pydantic V2 features.
- [ ] T7: Implement API response caching via Redis middleware.
- [ ] T8: Setup continuous profiling for API memory and CPU bottlenecks.
- [ ] T9: Ensure 100% test coverage for critical business logic in API.
- [ ] T10: Generate complete OpenAPI (Swagger) documentation for all endpoints.

## S7: Security, Authentication & Audit Trails
**Description**: Enhance system-wide security, RBAC, and auditing.

- [ ] T1: Audit codebase for hardcoded secrets and move them to .env/Vault.
- [ ] T2: Implement constant-time comparison for all HMAC and token validations.
- [ ] T3: Enforce strict RBAC (Role-Based Access Control) on API endpoints.
- [ ] T4: Implement comprehensive audit logging for all database modifications.
- [ ] T5: Configure automated security scanning (SAST/DAST) in CI pipeline.
- [ ] T6: Secure all webhook endpoints with HMAC signature verification.
- [ ] T7: Review and tighten CORS and CSP headers on all exposed services.
- [ ] T8: Implement IP allowlisting for sensitive internal endpoints.
- [ ] T9: Conduct a simulated penetration test on the public-facing API.
- [ ] T10: Document security architecture and incident response plan.

## S8: Documentation & Knowledge Base Generation
**Description**: Download external docs and build internal system documentation.

- [ ] T1: Download and index complete Evolution-API documentation.
- [ ] T2: Download and index complete N8N documentation.
- [ ] T3: Download and index complete Chatwoot documentation.
- [ ] T4: Download and index complete Supabase documentation.
- [ ] T5: Download and index complete Redis documentation.
- [ ] T6: Generate detailed architectural diagrams of the system flow.
- [ ] T7: Write runbooks for common operational failures and alerts.
- [ ] T8: Document API integration points with internal service components.
- [ ] T9: Maintain PROGRESS.md with granular session tracking details.
- [ ] T10: Create a comprehensive onboarding guide for new developers.

## S9: Frontend & Dashboards Observability Improvements
**Description**: Improve internal dashboards for monitoring operations.

- [ ] T1: Audit User Review Dashboard for accessibility (:focus-visible) compliance.
- [ ] T2: Audit Operations Dashboard for accessibility compliance.
- [ ] T3: Optimize dashboard data generation scripts (dashboard.py) for speed.
- [ ] T4: Add real-time log streaming views to operations dashboard.
- [ ] T5: Ensure consistent UI components across all administrative interfaces.
- [ ] T6: Implement frontend error tracking and reporting boundaries.
- [ ] T7: Add token consumption and cost monitoring widgets to dashboards.
- [ ] T8: Optimize frontend asset loading using pnpm and modern bundlers.
- [ ] T9: Implement end-to-end UI verification tests using Playwright.
- [ ] T10: Document dashboard deployment and asset generation processes.

## S10: System Testing & CI/CD Pipeline Strengthening
**Description**: Ensure robustness via automated tests and continuous integration.

- [ ] T1: Configure parallel execution for pytest to reduce test suite duration.
- [ ] T2: Mock all external HTTP calls in backend tests using respx.
- [ ] T3: Enforce 100% strict formatting checks via ruff in CI.
- [ ] T4: Fix globally failing async test fixtures related to missing env vars.
- [ ] T5: Implement automated database migration testing (up/down).
- [ ] T6: Set up dependency vulnerability scanning (Dependabot/Renovate).
- [ ] T7: Implement automated load testing using locust or k6.
- [ ] T8: Ensure test environments correctly mock timezone-aware datetimes.
- [ ] T9: Consolidate deployment scripts for EasyPanel into a single pipeline.
- [ ] T10: Document CI/CD pipeline steps, environment variables, and secrets.
