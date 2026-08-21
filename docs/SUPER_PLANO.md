# SUPER PLANO DE MELHORIAS (100 TASKS)

Este documento contém 100 tarefas focadas em testar, corrigir, otimizar, organizar, documentar e melhorar o ecossistema completo do projeto (API, N8N, Chatwoot, Evolution-API, Redis, Supabase, Agent AI e OpenClaw Gateway).

## Task 1: Implement rate limiting per IP
- **Componente:** API
- **Categoria:** Security
- **Descrição:** Add IP-based rate limiting to all public API endpoints using Redis to prevent DDoS and abuse.

## Task 2: Audit trailing slashes in endpoints
- **Componente:** API
- **Categoria:** Security
- **Descrição:** Ensure strict enforcement of trailing slash policies across API routes to avoid duplicate content and routing errors.

## Task 3: Implement Row Level Security (RLS) for public tables
- **Componente:** Supabase
- **Categoria:** Database
- **Descrição:** Review and enforce Supabase RLS policies on all user-facing tables to prevent unauthorized data access.

## Task 4: Configure Webhooks to N8N
- **Componente:** Chatwoot
- **Categoria:** Integration
- **Descrição:** Set up and secure Chatwoot webhooks pointing to N8N for automated ticket categorization.

## Task 5: Optimize WhatsApp message routing
- **Componente:** N8N
- **Categoria:** Workflow
- **Descrição:** Refactor N8N workflow to route incoming WhatsApp messages faster by reducing redundant conditional nodes.

## Task 6: Enable caching for static media
- **Componente:** Evolution-API
- **Categoria:** Performance
- **Descrição:** Configure Evolution-API and Traefik to aggressively cache frequently sent media like PDF forms and images.

## Task 7: Set up memory usage alerts
- **Componente:** Redis
- **Categoria:** Monitoring
- **Descrição:** Configure Prometheus and Grafana alerts for Redis memory usage exceeding 80% to prevent eviction issues.

## Task 8: Add E2E tests for tool execution
- **Componente:** Agent AI
- **Categoria:** Testing
- **Descrição:** Create automated tests in pytest to verify the OpenClaw agent correctly calls the emolumento API tool with mock data.

## Task 9: Sanitize user inputs before LLM
- **Componente:** Agent AI
- **Categoria:** Security
- **Descrição:** Implement a preprocessing step to strip executable code or injection attempts before passing user text to DeepSeek-v4.

## Task 10: Document all MCP tool schemas
- **Componente:** API
- **Categoria:** Documentation
- **Descrição:** Update the OpenAPI spec to fully describe the schemas used by the Model Context Protocol tools exposed to the agent.

## Task 11: Setup Supabase Database Webhooks
- **Componente:** Supabase
- **Categoria:** Integration
- **Descrição:** Configure database triggers to notify N8N automatically when a new 'Protocolo' is created.

## Task 12: Add indexes for high-frequency queries
- **Componente:** Supabase
- **Categoria:** Performance
- **Descrição:** Analyze slow query logs and add composite indexes on created_at and status columns for the protocols table.

## Task 13: Customize Agent Handoff message
- **Componente:** Chatwoot
- **Categoria:** UX/UI
- **Descrição:** Create a clear, non-robotic standard greeting for when human agents take over a conversation from the Cartorio-Bot.

## Task 14: Implement workflow failure notifications
- **Componente:** N8N
- **Categoria:** Monitoring
- **Descrição:** Add a catch-all error trigger in N8N to send a Telegram alert to the dev team upon any workflow failure.

## Task 15: Test Telegram bot response latency
- **Componente:** Telegram Bot
- **Categoria:** Testing
- **Descrição:** Benchmark the end-to-end response time of the Telegram test bot and identify bottlenecks in the Redis cache layer.

## Task 16: Migrate tests to use parameterized inputs
- **Componente:** API
- **Categoria:** Testing
- **Descrição:** Refactor pytest suites for API endpoints to use pytest.mark.parametrize for broader edge-case coverage.

## Task 17: Separate Cache and Queue databases
- **Componente:** Redis
- **Categoria:** Architecture
- **Descrição:** Configure distinct Redis logical databases (e.g., DB 0 for cache, DB 1 for Sidekiq queues) to avoid key collisions.

## Task 18: Optimize system prompt context tokens
- **Componente:** Agent AI
- **Categoria:** Optimization
- **Descrição:** Condense the Cartorio-Bot system prompt to save tokens while retaining the strict serious tone and P0 rules.

## Task 19: Test instance recovery on reboot
- **Componente:** Evolution-API
- **Categoria:** Integration
- **Descrição:** Simulate a VPS restart and verify that Evolution-API automatically reconnects to WhatsApp without requiring manual QR scan.

## Task 20: Configure Sidekiq concurrency
- **Componente:** Chatwoot
- **Categoria:** Architecture
- **Descrição:** Tune Chatwoot's Sidekiq worker concurrency settings in EasyPanel based on available VPS CPU cores.

## Task 21: Store third-party keys in Vault
- **Componente:** Supabase
- **Categoria:** Security
- **Descrição:** Migrate raw API keys in Supabase edge functions/cron jobs to use Supabase Vault for secure secrets management.

## Task 22: Document N8N environment variables
- **Componente:** N8N
- **Categoria:** Documentation
- **Descrição:** Create a comprehensive markdown file explaining all N8N custom environment variables used in the cartorio project.

## Task 23: Implement pagination for large lists
- **Componente:** API
- **Categoria:** Performance
- **Descrição:** Ensure all GET endpoints returning lists (e.g., /protocolos) enforce pagination to prevent memory exhaustion.

## Task 24: Standardize 'emolumento' formatting
- **Componente:** Agent AI
- **Categoria:** UX/UI
- **Descrição:** Ensure the agent always returns monetary values in Brazilian Reais (R$) format (e.g., R$ 1.234,56).

## Task 25: Verify fallback provider failover
- **Componente:** Agent AI
- **Categoria:** Integration
- **Descrição:** Test if OpenClaw correctly routes to fallback models when the primary deepseek-v4-flash API is simulated to be down.

## Task 26: Automate database backups
- **Componente:** Supabase
- **Categoria:** Database
- **Descrição:** Configure pg_dump cron jobs or Supabase Point-in-Time Recovery to ensure daily backups are shipped to external storage.

## Task 27: Enable Redis TLS/SSL
- **Componente:** Redis
- **Categoria:** Security
- **Descrição:** Secure Redis connections using TLS to encrypt data in transit between API/N8N and the Redis instance.

## Task 28: Add health check endpoint to monitoring
- **Componente:** Evolution-API
- **Categoria:** Monitoring
- **Descrição:** Integrate Evolution-API's /health endpoint into Prometheus and setup Uptime Kuma alerts.

## Task 29: Create SLA response time report specs
- **Componente:** Chatwoot
- **Categoria:** Documentation
- **Descrição:** Draft SQL queries to extract first-response and resolution SLA metrics from Chatwoot's Postgres database.

## Task 30: Add E2E tests for database connection pooling
- **Componente:** API
- **Categoria:** Testing
- **Descrição:** Create a load test using Locust to verify SQLAlchemy connection pool limits and timeouts under heavy concurrent load.

## Task 31: Prune N8N execution logs
- **Componente:** N8N
- **Categoria:** Performance
- **Descrição:** Configure EXECUTIONS_DATA_PRUNE in N8N to automatically delete old workflow execution logs and save disk space.

## Task 32: Implement GraphQL introspection limits
- **Componente:** Supabase
- **Categoria:** Architecture
- **Descrição:** Disable GraphQL introspection in Supabase production to prevent unauthorized schema discovery.

## Task 33: Add inline keyboard buttons
- **Componente:** Telegram Bot
- **Categoria:** UX/UI
- **Descrição:** Improve the Telegram bot test interface by adding inline buttons for common actions like 'Consultar Protocolo'.

## Task 34: Harden PII Scrubber skill
- **Componente:** Agent AI
- **Categoria:** Security
- **Descrição:** Update the pii_scrubber regex to aggressively mask CPF/RG and credit card numbers before logging prompts.

## Task 35: Rotate JWT signing keys
- **Componente:** API
- **Categoria:** Security
- **Descrição:** Implement a secure procedure (without actually rotating now) for how JWT secrets will be managed and rotated annually.

## Task 36: Test bulk message sending rate limits
- **Componente:** Evolution-API
- **Categoria:** Testing
- **Descrição:** Verify Evolution-API handles rate limits gracefully when N8N attempts to send 100+ notifications simultaneously.

## Task 37: Sync Chatwoot contacts with Supabase
- **Componente:** Chatwoot
- **Categoria:** Integration
- **Descrição:** Create an N8N workflow to upsert Chatwoot contact details into Supabase whenever a new user starts a chat.

## Task 38: Tune Redis persistence settings
- **Componente:** Redis
- **Categoria:** Performance
- **Descrição:** Adjust Redis AOF (Append Only File) settings to balance between data durability and write performance.

## Task 39: Implement context window pruning
- **Componente:** Agent AI
- **Categoria:** Architecture
- **Descrição:** Ensure OpenClaw dynamically summarizes older conversation history when nearing the 1M context token limit.

## Task 40: Add Datadog/NewRelic APM tracing
- **Componente:** API
- **Categoria:** Monitoring
- **Descrição:** Integrate OpenTelemetry into the FastAPI backend to trace request latency across the microservices.

## Task 41: Document ER diagram
- **Componente:** Supabase
- **Categoria:** Documentation
- **Descrição:** Generate and store an Entity-Relationship diagram mapping out the core tables: users, protocols, messages, logs.

## Task 42: Restrict N8N webhook IP access
- **Componente:** N8N
- **Categoria:** Security
- **Descrição:** Configure N8N to only accept incoming webhook requests from the internal API and Chatwoot IPs.

## Task 43: Customize WhatsApp presence
- **Componente:** Evolution-API
- **Categoria:** UX/UI
- **Descrição:** Ensure Evolution-API sets the 'typing...' presence state while the Agent AI is processing a response.

## Task 44: Link Telegram IDs to Supabase users
- **Componente:** Telegram Bot
- **Categoria:** Integration
- **Descrição:** Update the API to map a user's Telegram chat ID to their master account profile in the database.

## Task 45: Simulate LGPD opt-out request
- **Componente:** Agent AI
- **Categoria:** Testing
- **Descrição:** Write a test case validating that if a user says 'apague meus dados', the agent correctly triggers the LGPD workflow.

## Task 46: Document Redis key namespaces
- **Componente:** Redis
- **Categoria:** Documentation
- **Descrição:** Create a dictionary defining the structure and TTL for all Redis keys (e.g., 'session:{id}', 'ratelimit:{ip}').

## Task 47: Containerize API with minimal base image
- **Componente:** API
- **Categoria:** Architecture
- **Descrição:** Optimize the API Dockerfile to use python:3.11-alpine or slim to reduce image size and attack surface.

## Task 48: Monitor Sidekiq queue depth
- **Componente:** Chatwoot
- **Categoria:** Monitoring
- **Descrição:** Add a Grafana dashboard panel specifically tracking the depth of Chatwoot's 'default' and 'mailers' queues.

## Task 49: Test RLS policies with anonymous role
- **Componente:** Supabase
- **Categoria:** Testing
- **Descrição:** Write API tests using an unauthenticated Supabase client to prove that sensitive data cannot be read.

## Task 50: Connect N8N to Redis for deduplication
- **Componente:** N8N
- **Categoria:** Integration
- **Descrição:** Use N8N Redis node to store processed message IDs and prevent processing duplicate webhooks from Evolution-API.

## Task 51: Optimize Webhook delivery timeout
- **Componente:** Evolution-API
- **Categoria:** Performance
- **Descrição:** Adjust Evolution-API webhook timeout settings to fail fast and retry gracefully if the API is momentarily down.

## Task 52: Implement structured output for tools
- **Componente:** Agent AI
- **Categoria:** UX/UI
- **Descrição:** Ensure all tools called by the agent return data in strict JSON schema to prevent parsing errors.

## Task 53: Migrate to Webhooks instead of Polling
- **Componente:** Telegram Bot
- **Categoria:** Architecture
- **Descrição:** Change the Telegram bot integration from long-polling to webhooks to reduce CPU usage and improve response time.

## Task 54: Enable Gzip/Brotli compression
- **Componente:** API
- **Categoria:** Performance
- **Descrição:** Add compression middleware to FastAPI to reduce the payload size of large JSON responses.

## Task 55: Simulate Redis failure
- **Componente:** Redis
- **Categoria:** Testing
- **Descrição:** Write an E2E test verifying that the API gracefully degrades (e.g., skips caching) if the Redis instance crashes.

## Task 56: Enforce 2FA for agents
- **Componente:** Chatwoot
- **Categoria:** Security
- **Descrição:** Configure Chatwoot instance settings to mandate Two-Factor Authentication for all human operators and admins.

## Task 57: Clean up unused storage buckets
- **Componente:** Supabase
- **Categoria:** Optimization
- **Descrição:** Audit Supabase Storage and remove any test buckets or orphaned files to optimize costs.

## Task 58: Standardize workflow naming convention
- **Componente:** N8N
- **Categoria:** UX/UI
- **Descrição:** Rename all N8N workflows using a prefix system (e.g., 'CRON - Cleanup', 'WH - WhatsApp Inbound').

## Task 59: Document WebSocket event payload
- **Componente:** Evolution-API
- **Categoria:** Documentation
- **Descrição:** Record the exact JSON structure of Evolution-API's message.upsert WebSocket events for developer reference.

## Task 60: Integrate OpenClaw with Supabase Vector
- **Componente:** Agent AI
- **Categoria:** Integration
- **Descrição:** Configure the agent to query a Supabase pgvector table for semantic search on Cartorio knowledge base articles.

## Task 61: Implement CQRS for Protocols
- **Componente:** API
- **Categoria:** Architecture
- **Descrição:** Separate the read models and write models for the Protocolos entity to improve query performance on the dashboard.

## Task 62: Switch to Redis Cluster
- **Componente:** Redis
- **Categoria:** Optimization
- **Descrição:** Evaluate and plan the migration from standalone Redis to Redis Cluster for high availability.

## Task 63: Optimize asset precompilation
- **Componente:** Chatwoot
- **Categoria:** Performance
- **Descrição:** Ensure Chatwoot Docker image precompiles Rails assets correctly so they are served instantly via NGINX.

## Task 64: Monitor Postgres connection count
- **Componente:** Supabase
- **Categoria:** Monitoring
- **Descrição:** Set up an alert if the Supabase Postgres instance exceeds 80% of its max_connections limit.

## Task 65: Create a dummy workflow for healthchecks
- **Componente:** N8N
- **Categoria:** Testing
- **Descrição:** Build a simple N8N workflow triggered by HTTP GET to verify that the N8N execution engine is alive.

## Task 66: Rotate Global API Key
- **Componente:** Evolution-API
- **Categoria:** Security
- **Descrição:** Verify the process for updating the Evolution-API global authentication key without downtime (do not rotate now).

## Task 67: Write guidelines for adding new tools
- **Componente:** Agent AI
- **Categoria:** Documentation
- **Descrição:** Create a tutorial in the docs explaining how developers can add new MCP tools to the Cartorio-Bot.

## Task 68: Track active user sessions
- **Componente:** Telegram Bot
- **Categoria:** Monitoring
- **Descrição:** Add metrics to count how many unique Telegram users interact with the test bot daily.

## Task 69: Remove unused dependencies
- **Componente:** API
- **Categoria:** Optimization
- **Descrição:** Audit requirements.txt/pyproject.toml and remove any Python packages that are no longer imported in the codebase.

## Task 70: Add prefix to all keys
- **Componente:** Redis
- **Categoria:** UX/UI
- **Descrição:** Ensure all Redis keys use a domain prefix (e.g., 'cartorio:dev:session') to allow multiple environments on one Redis.

## Task 71: Test Chatwoot API limits
- **Componente:** Chatwoot
- **Categoria:** Testing
- **Descrição:** Write a script to deliberately hit Chatwoot's rate limits and verify it returns a 429 Too Many Requests response.

## Task 72: Setup Supabase Cron for stale sessions
- **Componente:** Supabase
- **Categoria:** Integration
- **Descrição:** Use pg_cron in Supabase to automatically delete or archive conversation sessions older than 30 days.

## Task 73: Migrate from SQLite to Postgres for N8N
- **Componente:** N8N
- **Categoria:** Architecture
- **Descrição:** Ensure N8N is configured to use Supabase Postgres as its main database instead of the default SQLite.

## Task 74: Configure multi-device support
- **Componente:** Evolution-API
- **Categoria:** Architecture
- **Descrição:** Ensure Evolution-API instance is configured to handle WhatsApp multi-device sync seamlessly.

## Task 75: Cache frequent agent responses
- **Componente:** Agent AI
- **Categoria:** Performance
- **Descrição:** Implement a semantic cache layer (e.g., using Redis) so identical questions bypass the LLM entirely.

## Task 76: Restrict test bot to whitelisted IDs
- **Componente:** Telegram Bot
- **Categoria:** Security
- **Descrição:** Modify the Telegram bot logic to only respond to user IDs explicitly added to an allowlist in the database.

## Task 77: Audit CORS origins
- **Componente:** API
- **Categoria:** Security
- **Descrição:** Review FastAPI CORS middleware to ensure only the production frontend and EasyPanel domains are allowed.

## Task 78: Integrate Redis with FastAPI Cache
- **Componente:** Redis
- **Categoria:** Integration
- **Descrição:** Use fastapi-cache2 with the Redis backend to easily cache expensive endpoint responses via decorators.

## Task 79: Configure custom domain for Help Center
- **Componente:** Chatwoot
- **Categoria:** UX/UI
- **Descrição:** Setup DNS and SSL via Traefik to map Chatwoot's Help Center to 'ajuda.2notasudi.com.br'.

## Task 80: Optimize Realtime configuration
- **Componente:** Supabase
- **Categoria:** Performance
- **Descrição:** Restrict Supabase Realtime broadcasts to only the specific tables (e.g., 'messages') that the frontend needs.

## Task 81: Consolidate duplicate HTTP nodes
- **Componente:** N8N
- **Categoria:** Optimization
- **Descrição:** Refactor workflows to use a sub-workflow for standard API calls instead of repeating HTTP Request nodes.

## Task 82: Test media attachment handling
- **Componente:** Evolution-API
- **Categoria:** Testing
- **Descrição:** Write a test to ensure PDF attachments sent via WhatsApp are correctly parsed and saved to Supabase Storage.

## Task 83: Log LLM token usage
- **Componente:** Agent AI
- **Categoria:** Monitoring
- **Descrição:** Ensure every interaction logs the prompt/completion token count to Prometheus to monitor DeepSeek API costs.

## Task 84: Document Telegram command list
- **Componente:** Telegram Bot
- **Categoria:** Documentation
- **Descrição:** Create a help page detailing all available slash commands (e.g., /start, /status, /ajuda) for the bot.

## Task 85: Generate Pydantic model diagrams
- **Componente:** API
- **Categoria:** Documentation
- **Descrição:** Use erdantic to automatically generate UML diagrams of the Pydantic schemas used in the API.

## Task 86: Configure Redis Eviction Policy
- **Componente:** Redis
- **Categoria:** Architecture
- **Descrição:** Set maxmemory-policy to allkeys-lru to ensure the cache degrades gracefully when full.

## Task 87: Disable public signups
- **Componente:** Chatwoot
- **Categoria:** Security
- **Descrição:** Ensure ENABLE_ACCOUNT_SIGNUP is false in Chatwoot ENV to prevent unauthorized users from creating admin accounts.

## Task 88: Create Dashboard Views
- **Componente:** Supabase
- **Categoria:** UX/UI
- **Descrição:** Create Postgres SQL Views specifically tailored to provide aggregated stats for the admin operations dashboard.

## Task 89: Track N8N memory usage over time
- **Componente:** N8N
- **Categoria:** Monitoring
- **Descrição:** Monitor Node.js heap usage in N8N to detect memory leaks caused by large data processing in workflows.

## Task 90: Implement custom typing delays
- **Componente:** Evolution-API
- **Categoria:** UX/UI
- **Descrição:** Add artificial delays (e.g., 1-3 seconds) before sending Evolution-API messages to simulate human typing.

## Task 91: Stress test concurrent agent sessions
- **Componente:** Agent AI
- **Categoria:** Testing
- **Descrição:** Simulate 50 users talking to Cartorio-Bot simultaneously to verify the Gateway and LLM handle the concurrency.

## Task 92: Use async/await strictly
- **Componente:** Telegram Bot
- **Categoria:** Optimization
- **Descrição:** Review the Telegram bot code to ensure no blocking synchronous calls are made in the event loop.

## Task 93: Expose Prometheus metrics endpoint
- **Componente:** API
- **Categoria:** Integration
- **Descrição:** Add a /metrics endpoint to FastAPI using prometheus-client to expose request counts and latencies.

## Task 94: Monitor slowlog commands
- **Componente:** Redis
- **Categoria:** Monitoring
- **Descrição:** Periodically pull Redis SLOWLOG to identify if any API queries are taking longer than 10ms to execute.

## Task 95: Setup PostgreSQL read replica
- **Componente:** Chatwoot
- **Categoria:** Architecture
- **Descrição:** Configure Chatwoot to route heavy analytical dashboard queries to a Supabase read replica.

## Task 96: Review JWT expiration times
- **Componente:** Supabase
- **Categoria:** Security
- **Descrição:** Ensure Supabase auth tokens have short lifespans (e.g., 1 hour) and rely on secure refresh token rotation.

## Task 97: Document N8N backup strategy
- **Componente:** N8N
- **Categoria:** Documentation
- **Descrição:** Write a guide on how to export N8N workflows as JSON files and commit them to the git repository automatically.

## Task 98: Handle disconnected instance events
- **Componente:** Evolution-API
- **Categoria:** Integration
- **Descrição:** Ensure the system sends an urgent admin alert if Evolution-API emits a 'connection.update' event showing 'close'.

## Task 99: Audit OpenClaw configuration file
- **Componente:** Agent AI
- **Categoria:** Security
- **Descrição:** Review the openclaw.json file for any hardcoded keys, ensuring it strictly uses environment variable references.

## Task 100: Implement API versioning
- **Componente:** API
- **Categoria:** Architecture
- **Descrição:** Ensure all routes are properly versioned under /api/v1/ and plan the structure for future /api/v2/ breaking changes.
