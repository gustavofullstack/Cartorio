# SUPER_PLANO - 100 Granular Improvement Tasks

## S1: S1: API Central & Performance

- **T1**: Implement targeted `uv run pytest` for specific API endpoints
  - *Description*: To avoid timeouts, configure automated tests to target individual endpoints instead of the whole suite.
- **T2**: Optimize Supabase count queries in API
  - *Description*: Replace `.scalars().all()` with `func.count()` to prevent O(N) memory overhead for counting records.
- **T3**: Validate HMAC keys in API webhooks securely
  - *Description*: Always use `hmac.compare_digest` when verifying Evolution-API webhooks to prevent timing attacks.
- **T4**: Enable strict Pydantic model validation on API schemas
  - *Description*: Audit and enforce strictly typed requests to prevent unexpected inputs in API.
- **T5**: Setup automatic local `uv venv` activation for API testing
  - *Description*: Create an automated script that creates a venv and installs dev dependencies before running tests locally.
- **T6**: Add custom exception handlers in FastAPI
  - *Description*: Refine global exception handling to avoid exposing sensitive internal state in errors while still logging it properly.
- **T7**: Review API rate limiting configurations
  - *Description*: Test and document the effectiveness of rate limiting on the `/api/v1/integrations/` endpoints.
- **T8**: Implement Healthcheck and DB Probe in API
  - *Description*: Ensure there's an internal endpoint explicitly for checking Supabase and Redis connection health.
- **T9**: Enhance API response speed via connection pooling
  - *Description*: Check SQLAlchemy configurations for optimal connection pooling with Supabase PostgreSQL.
- **T10**: Review dependencies for security updates
  - *Description*: Analyze `pyproject.toml` and update any outdated/vulnerable dependencies safely.

## S2: S2: N8N Workflows & Automation

- **T11**: Centralize Chatwoot webhook integration in N8N
  - *Description*: Move dispersed logic into a single cohesive workflow that directs events to Chatwoot appropriately.
- **T12**: Configure N8N workflow error handling nodes
  - *Description*: Ensure all API calls from N8N have proper fallback paths to avoid silent workflow failures.
- **T13**: Optimize N8N payload processing
  - *Description*: Ensure only required fields are transformed in N8N to reduce CPU utilization.
- **T14**: Create standard workflow documentation templates
  - *Description*: Document each N8N workflow's inputs and outputs in the repository for consistency.
- **T15**: Implement retry logic for Evolution-API nodes
  - *Description*: Configure N8N workflows interacting with Evolution-API to retry up to 3 times on network failure.
- **T16**: Secure N8N webhook endpoints
  - *Description*: Verify that N8N webhook entry points validate request signatures sent from the API.
- **T17**: Refine N8N logging mechanism
  - *Description*: Instead of keeping huge logs, configure workflows to write summarized logs to Supabase via API.
- **T18**: Develop a test suite for N8N workflows
  - *Description*: Create synthetic events via curl scripts to trigger and assert correct N8N workflow executions.
- **T19**: Standardize N8N variable naming conventions
  - *Description*: Review existing workflows and normalize variable names to camelCase for uniformity.
- **T20**: Implement workflow monitoring alerts
  - *Description*: Configure N8N to send a Telegram alert to Gustavo/Pietra on workflow critical failures.

## S3: S3: Supabase Integration & Database

- **T21**: Setup Supabase Database Webhooks for realtime events
  - *Description*: Configure triggers to notify the API or N8N when crucial tables are updated.
- **T22**: Implement proper timestamps for CNJ reports
  - *Description*: Ensure all test records explicitly set `created_at` fields to support reliable date-filtered reporting.
- **T23**: Configure Supabase CRON jobs for cleanup tasks
  - *Description*: Automate the deletion of old ephemeral session data directly in the database.
- **T24**: Integrate Supabase Vault for secret management
  - *Description*: Evaluate if N8N/API keys should be migrated to Supabase Vault for enhanced security.
- **T25**: Enhance RLS (Row Level Security) policies
  - *Description*: Audit and refine RLS policies to ensure user data isolation is strictly enforced at the database level.
- **T26**: Implement robust pagination in Supabase queries
  - *Description*: Standardize pagination across API endpoints to avoid querying massive datasets at once.
- **T27**: Optimize Database Indexing
  - *Description*: Review slow queries and create missing indices on frequently filtered columns in Supabase.
- **T28**: Configure Supabase Queues for background tasks
  - *Description*: Offload non-critical asynchronous tasks (like email sending) to Supabase Queues.
- **T29**: Integrate Supabase GraphQL for specific read-heavy endpoints
  - *Description*: Evaluate GraphQL for dashboards where flexible data retrieval reduces multiple API calls.
- **T30**: Document the Supabase schema properly
  - *Description*: Ensure all tables and their relationships are accurately reflected in `docs/platforms/SUPABASE.md`.

## S4: S4: Redis Caching & Memory

- **T31**: Optimize Redis TTL strategies
  - *Description*: Ensure all cached items have explicit and optimal Time To Live (TTL) settings to prevent memory exhaustion.
- **T32**: Standardize Redis key formats
  - *Description*: Use a strict namespace pattern (e.g., `cartorio:session:<id>`) for all Redis keys.
- **T33**: Implement Redis connection resilience in API
  - *Description*: Ensure the API gracefully falls back to direct DB queries if Redis is temporarily unavailable.
- **T34**: Optimize Sidekiq queue handling via Redis
  - *Description*: Analyze Chatwoot's Sidekiq queue performance in Redis and adjust concurrency settings.
- **T35**: Centralize conversation context storage
  - *Description*: Ensure the N8N -> Redis and OpenClaw -> Redis context synchronization is flawless.
- **T36**: Setup Redis memory monitoring alerts
  - *Description*: Implement a script to alert when Redis memory usage exceeds 80%.
- **T37**: Review Redis security configurations
  - *Description*: Verify that Redis requires authentication and is not exposed to the public internet.
- **T38**: Implement efficient Redis batch operations
  - *Description*: Refactor API logic to use pipelines for multiple Redis sets/gets instead of sequential calls.
- **T39**: Document Redis session lifecycle
  - *Description*: Create a flow diagram of how session data enters and leaves Redis.
- **T40**: Implement graceful Redis degradation
  - *Description*: Test and document system behavior when Redis is forcefully restarted.

## S5: S5: Chatwoot CRM & Customer Success

- **T41**: Optimize Chatwoot API integration
  - *Description*: Review how N8N updates Chatwoot conversations to reduce API payload sizes.
- **T42**: Configure HITL (Human in the Loop) handoff logic
  - *Description*: Ensure OpenClaw's handoff endpoint cleanly transfers control to human agents in Chatwoot without race conditions.
- **T43**: Customize Chatwoot conversation tags
  - *Description*: Automate tag assignment based on the user's intent classified by OpenClaw.
- **T44**: Implement Chatwoot custom attributes mapping
  - *Description*: Ensure user data collected by OpenClaw is correctly saved as custom attributes in Chatwoot contacts.
- **T45**: Refine Chatwoot automation rules
  - *Description*: Audit built-in Chatwoot automation rules to ensure they don't conflict with N8N workflows.
- **T46**: Optimize Chatwoot webhook delivery
  - *Description*: Configure Chatwoot to only dispatch webhooks for relevant events (e.g., message created) to reduce N8N load.
- **T47**: Enhance Chatwoot agent response speed
  - *Description*: Test and configure Chatwoot caching to improve the dashboard loading time for human agents.
- **T48**: Implement automated summary notes in Chatwoot
  - *Description*: When a handoff occurs, the OpenClaw agent should post an internal note summarizing the conversation context.
- **T49**: Configure Chatwoot Out-of-Office auto-replies
  - *Description*: Ensure auto-replies correctly pause OpenClaw processing to prevent double-replying.
- **T50**: Document Chatwoot operator guidelines
  - *Description*: Create a standard operating procedure document for human agents using Chatwoot.

## S6: S6: Evolution API & WhatsApp Integrations

- **T51**: Ensure robust Evolution API webhook handling
  - *Description*: Refactor API webhook receivers to immediately return 200 OK and process the payload asynchronously.
- **T52**: Implement secure webhook signature validation
  - *Description*: Enforce strict validation of Evolution API signatures using constant-time comparison in the API.
- **T53**: Configure Evolution API connection auto-reconnect
  - *Description*: Ensure instances reliably reconnect on network failures and alert if manual intervention (QR scan) is needed.
- **T54**: Optimize WhatsApp media handling
  - *Description*: Ensure media files received via Evolution API are properly processed, scanned, and stored in Supabase Storage.
- **T55**: Implement robust message deduplication
  - *Description*: Use Redis to detect and discard duplicate webhook events from Evolution API.
- **T56**: Configure WhatsApp consent management logic
  - *Description*: Ensure users can opt-out and their preferences are respected before sending any outbound messages.
- **T57**: Enhance message formatting capabilities
  - *Description*: Standardize the formatting (bolding, lists) of AI-generated responses before sending to Evolution API.
- **T58**: Implement interactive message support
  - *Description*: Test and integrate WhatsApp buttons and lists via Evolution API to improve user experience.
- **T59**: Monitor Evolution API instance health
  - *Description*: Create a CRON job to periodically check the status of all Evolution API instances.
- **T60**: Document Evolution API quirks and limitations
  - *Description*: Record specific behaviors (like rate limits or payload structures) in `EVOLUTION-API.md`.

## S7: S7: Openclaw Agent AI & NLP Capabilities

- **T61**: Activate DeepSeek-v4-flash thinking capabilities
  - *Description*: Verify the `thinking` enabled flag correctly activates the extended reasoning context window for the bot.
- **T62**: Refine OpenClaw system prompts
  - *Description*: Continuously test and adjust prompts to guarantee direct, serious, and emoji-free responses.
- **T63**: Implement robust PII scrubbing before NLP
  - *Description*: Ensure CPF, RG, and raw protocol numbers are strictly masked before sending to the LLM.
- **T64**: Enhance OpenClaw Tool call reliability
  - *Description*: Add fallback strategies for when the `consultar_emolumento` API endpoint is slow or unresponsive.
- **T65**: Test OpenClaw context window utilization
  - *Description*: Simulate long conversations to ensure the 1M context window is handled efficiently without causing excessive token costs.
- **T66**: Implement strict formatting rules for OpenClaw outputs
  - *Description*: Configure the agent to strictly follow standard legal vocabulary as required by the cartorio context.
- **T67**: Optimize OpenClaw MCP integrations
  - *Description*: Test the API, Supabase, and Chatwoot MCPs to ensure the agent correctly uses external tools.
- **T68**: Implement automated intent classification testing
  - *Description*: Create a test suite to ensure the agent accurately identifies user intent across 50 common phrases.
- **T69**: Configure fallback LLM providers
  - *Description*: Ensure OpenClaw gracefully degrading to fallback providers if DeepSeek experiences an outage.
- **T70**: Monitor OpenClaw token consumption
  - *Description*: Integrate tracking using Codex-Bar to ensure token usage per conversation remains within acceptable limits.

## S8: S8: Security, Auditing & LGPD

- **T71**: Enforce strict LGPD consent checks
  - *Description*: Ensure all workflows and tools respect the `lgpd_scope` before processing user data.
- **T72**: Implement automated PII deletion via Supabase CRON
  - *Description*: Ensure data older than the retention policy is securely and automatically wiped.
- **T73**: Audit and restrict system API Keys
  - *Description*: Verify that all integrations use least-privilege tokens and that secrets are never hardcoded in files.
- **T74**: Implement constant-time comparison for secrets
  - *Description*: Audit the entire codebase to ensure `hmac.compare_digest` is used for all token validations.
- **T75**: Enhance audit logging granularity
  - *Description*: Ensure the `audit_logger` skill in OpenClaw accurately records HITL decisions and data access events.
- **T76**: Conduct a mock security incident response drill
  - *Description*: Document the steps taken to handle a hypothetical data leak or unauthorized access attempt.
- **T77**: Review EasyPanel firewall configurations
  - *Description*: Ensure only necessary ports are open and that databases/Redis are strictly internal.
- **T78**: Implement secure headers in the API
  - *Description*: Add Helmet-like protections (CORS, CSP, HSTS) to the FastAPI application.
- **T79**: Automate dependency vulnerability scanning
  - *Description*: Integrate a tool in the CI pipeline to flag known vulnerabilities in `pyproject.toml`.
- **T80**: Document LGPD compliance procedures
  - *Description*: Maintain a clear, up-to-date document detailing how the system adheres to LGPD requirements.

## S9: S9: Frontend Dashboards & UX/UI

- **T81**: Migrate inline styles to CSS variables
  - *Description*: Ensure both `user-review-dashboard` and `operations-dashboard` utilize CSS variables for consistent theming.
- **T82**: Fix `:focus-visible` accessibility issues
  - *Description*: Implement explicit focus outlines for interactive elements, ensuring `outline: none;` is isolated from `:focus-visible`.
- **T83**: Optimize dashboard data generation scripts
  - *Description*: Ensure `python dashboard.py` runs efficiently and handles missing data gracefully.
- **T84**: Implement Playwright verification scripts
  - *Description*: Create reproducible frontend tests to verify UI changes automatically.
- **T85**: Enhance dashboard responsiveness
  - *Description*: Ensure dashboards are fully usable on mobile devices, adjusting grid layouts accordingly.
- **T86**: Implement skeleton loaders in UI
  - *Description*: Add loading states to the dashboard to improve perceived performance during data fetching.
- **T87**: Standardize error state UI
  - *Description*: Create a consistent visual pattern for displaying data loading errors in the dashboards.
- **T88**: Implement robust form validation in UI
  - *Description*: Add client-side validation to all dashboard forms to prevent invalid data submission.
- **T89**: Optimize dashboard assets for performance
  - *Description*: Minify generated CSS/JS and compress any images used in the dashboards.
- **T90**: Document dashboard architecture
  - *Description*: Create a guide on how the Python script dynamically generates the HTML and injects data.

## S10: S10: DevOps, CI/CD & Monitoring

- **T91**: Automate API testing in CI
  - *Description*: Configure the CI pipeline to run `uv run pytest --no-cov` on all pull requests.
- **T92**: Enforce strict linting in CI
  - *Description*: Configure the CI pipeline to fail if `uv run ruff check .` finds any errors or formatting issues.
- **T93**: Implement automated token usage tracking
  - *Description*: Create a script to periodically query token consumption and report it to a monitoring dashboard.
- **T94**: Configure Prometheus metrics collection
  - *Description*: Ensure the API exposes relevant metrics for monitoring system health and performance.
- **T95**: Implement centralized logging
  - *Description*: Configure all services (API, N8N, Chatwoot) to send logs to a central aggregation service.
- **T96**: Automate deployment rollbacks
  - *Description*: Configure EasyPanel to support quick rollbacks in case a new deployment introduces critical bugs.
- **T97**: Implement infrastructure as code auditing
  - *Description*: Review EasyPanel configuration files to ensure consistency across environments.
- **T98**: Create comprehensive disaster recovery plan
  - *Description*: Document the steps required to restore the entire system from backups.
- **T99**: Optimize Docker image builds
  - *Description*: Refine Dockerfiles to use multi-stage builds and reduce the final image size.
- **T100**: Setup automated dependency updates
  - *Description*: Implement a tool (like Dependabot/Renovate) to create PRs for outdated dependencies automatically.
