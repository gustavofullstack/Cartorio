## 2024-05-18 - Prevent Timing Attacks in API Key Validation
**Vulnerability:** Used standard string equality operator `!=` to validate `settings.cartorio_api_key`.
**Learning:** Standard string comparisons fail early, allowing attackers to guess keys byte-by-byte via timing side-channels.
**Prevention:** Always use `hmac.compare_digest()` for comparing secrets, tokens, and API keys.
