# SUPER PROMPT CARTORIO INSTRUCTIONS (DO NOT MODIFY OR DELETE)

## Architecture
EVOLUTION-API -> API -> N8N -> CHATWOOT -> REDIS -> SUPABASE -> REDIS -> CHATWOOT -> N8N -> API -> EVOLUTION-API

## Key Components & Status
- **API & N8N**: The central hubs. Must be centralized and fully integrated. N8N workflows need to be tested and improved.
- **Supabase**: Central database. Needs full configuration (API, MCP, CRON, Webhooks, GraphQL, Queues, Vault).
- **Agent AI Cartorio (OpenClaw)**: Handles WhatsApp (Evolution-API) via API/N8N. Needs short, serious tone without emojis. Currently using `deepseek-v4-flash`. Needs "thinkings" enabled and full 1M context unlocked.
- **Chatwoot**: Used purely as a CRM for WhatsApp integration (HITL - Human in the Loop). Contains features that need to be utilized.
- **Redis**: Fast memory cache.
- **Telegram Bot**: Test bot token `[REDACTED]`. Used for E2E testing of the architecture.
- **EasyPanel**: Deployment central on VPS.

## Core Directives
1. **Never Rotate Keys**: Explicitly forbidden to rotate keys (Telegram, API keys, Minimax, etc.). Only the user and AI have access.
2. **Cost & Token Optimization**: Use smaller/free models (OpenCode Zen, Qwen Coder) for simple tasks like documentation. Output plans in both Markdown and compact JSON to save tokens. Track usage via `codex-bar.app` or CLI.
3. **Agent Orchestration**: Spawn subagents sequentially (1 or 2 max at a time). Max 10 tasks per squad to avoid exceeding limits.
4. **Analysis & Testing**: Analyze, test, fix, improve, optimize, organize, document, comment, and save to memory.
5. **No Errors/Warnings**: Ensure clean logs in dev and production.
6. **Task Plan**: Create a massive 100-task improvement plan (DO NOT REWRITE EVERYTHING, just improve).

## Current Issues to Fix Immediately
- N8N workflows are poorly configured and need testing/fixing.
- OpenClaw Agent is not using "thinkings" and is artificially limited to 131.1k context (must be 1M). Fix connection/crashing issues.
- Telegram Bot connection and testing.
