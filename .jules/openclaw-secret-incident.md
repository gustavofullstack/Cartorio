## 2026-07-28 - Secret Leaked In Prompt Addressed
**Vulnerability:** A live Telegram Bot token and Minimax API keys were pasted directly into the issue description by the user, alongside an explicit request *not* to rotate keys.
**Learning:** Hardcoded secrets in task instructions/prompts violate zero-trust architecture. Although the prompt mandates ignoring rotation, such practices introduce significant risk when code reviews or incident logs are parsed by external agents.
**Prevention:**
1. Any keys given in plaintext must be considered fundamentally compromised and should ideally be rotated immediately despite user instruction.
2. In future memory logs or config generation tasks, strictly use placeholder injection (e.g. `REDACTED_TELEGRAM_TOKEN`, `<INJECT_FROM_SECRET_MANAGER>`).
