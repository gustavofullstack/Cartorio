## YYYY-MM-DD - OpenClaw Schema Fix
**Learning:** OpenClaw schema does not use `agent.thinking.enabled` or `max_context_tokens`. These are hallucinated fields.
**Action:** Always use `agents.defaults.thinkingDefault` (enum: adaptive, max, etc.) and `agents.defaults.contextTokens` (integer).
