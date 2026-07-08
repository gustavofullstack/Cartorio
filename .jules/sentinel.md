## 2024-07-08 - Remove Hardcoded Telegram Bot Token
**Vulnerability:** A hardcoded Telegram Bot API token was found in `backend/app/api/v1/telegram.py`.
**Learning:** Storing secrets directly in source code allows unauthorized access if the repository is compromised. Secrets must always be loaded via environment variables or configuration managers.
**Prevention:** Ensure all sensitive configurations (API keys, tokens, passwords) are defined in `app.config.Settings` and fetched at runtime. Check for hardcoded strings during code review.
