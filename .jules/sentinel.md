## 2026-06-30 - Remove Hardcoded Telegram Bot Token
**Vulnerability:** A hardcoded Telegram bot token was found in `backend/app/api/v1/telegram.py`.
**Learning:** Hardcoded credentials represent a critical vulnerability as they can be easily extracted from source control. The code specifically commented that the token should not be rotated, but it was stored in plaintext in the codebase.
**Prevention:** Always use environment variables or configuration files for secrets. In this codebase, the Pydantic Settings class `Settings` should be updated or utilized to securely load tokens like `telegram_bot_token`.
