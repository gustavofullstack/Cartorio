## 2026-06-27 - Hardcoded Telegram Bot Token
**Vulnerability:** A Telegram bot token was hardcoded in `backend/app/api/v1/telegram.py` and some test/script files.
**Learning:** Hardcoding secrets exposes them in version control and creates a risk if the source code is compromised.
**Prevention:** Load sensitive secrets through environment variables or configuration files that are not tracked in version control, and keep fallback mechanisms secure.
