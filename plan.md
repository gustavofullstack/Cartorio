# Cartorio Task Plan

## 1. [cartorio-dev] Verify OpenClaw Configuration
- Ensure cartorio-bot uses deepseek-v4-flash, thinking: true, 1M context window, and strict serious tone without emojis.

## 2. [cartorio-docs] Generate comprehensive docs
- Create detailed documentation for Evolution API, N8N, Chatwoot, Supabase, and Redis integrations.

## 3. [cartorio-data] Supabase Deep Integration
- Configure Supabase Webhooks, Cron, Vault, and fully utilize its MCP for centralized DB operations.

## 4. [cartorio-n8n] N8N Workflow Audit
- Test and fix the 34 N8N workflows ensuring they properly integrate with API, Chatwoot, and Evolution API.

## 5. [cartorio-dev] API & Redis Caching Optimization
- Optimize Redis caching for API lists and N8N workflow states to reduce latency and Supabase load.

## 6. [cartorio-bot] Telegram Bot Testing
- Test the Telegram Bot flow using the test token, ensuring LGPD compliance mocking works.

## 7. [cartorio-docs] Memory updates
- Update local memory, loop memory, and session tracking to optimize token usage.

## 8. [cartorio-n8n] Chatwoot CRM Integrations
- Ensure Chatwoot handles human handoffs and pauses OpenClaw agent correctly.

## 9. [cartorio-dev] Test Suite Adjustments
- Fix broken tests, ignore Playwright cache tests if needed, mock Telegram early exits.

## 10. [cartorio-orchestration] Setup Subagent Tasks
- Prepare the next batch of 10 tasks for the subagents.
