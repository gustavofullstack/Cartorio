## 2026-08-02 - Timing Attack Vulnerability in Token and Key Routers
**Vulnerability:** Found standard string equality (`==`) being used to compare sensitive tokens and secrets in `backend/app/services/n8n_token_router.py` and `backend/app/services/audit_keys.py`. This makes the application susceptible to timing attacks, allowing an attacker to guess secrets character by character.
**Learning:** Python's standard equality operator short-circuits on the first mismatched character. When comparing secrets, this reveals information about the secret's structure based on response time.
**Prevention:** Always use `hmac.compare_digest()` from the built-in `hmac` library to perform constant-time comparisons when validating API keys, tokens, or cryptographic secrets.
