## 2025-01-20 - Prevent Timing Attacks on API Key Validation
**Vulnerability:** Standard string comparison (`==` or `!=`) was used for validating `X-API-Key` headers (`settings.cartorio_api_key`) in `router.py` and `lgpd_direitos.py`.
**Learning:** Using standard string comparison operators (`!=` or `==`) for sensitive secrets, like API keys, makes the application susceptible to timing attacks, as they return early on the first mismatched character.
**Prevention:** Always use constant-time comparison methods, such as `hmac.compare_digest()`, when validating API keys, tokens, or passwords to prevent information leakage through timing side-channels.
