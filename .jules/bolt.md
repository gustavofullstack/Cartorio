## 2026-07-28 - OpenClaw deepseek-v4-flash context configuration
**Learning:** The OpenClaw gateway configuration requires `reasoning: true` to enable thinking for deepseek models. The default configuration file was updated to use 1M context limit properly along with reasoning. Hardcoding tokens into bash scripts should be strictly avoided in favor of environment variables to maintain security protocols, even for testing scripts.
**Action:** Used `TELEGRAM_BOT_TOKEN` for the telegram setup script to prevent committing tokens to the repository.
