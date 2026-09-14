## 2024-05-24 - Timing Attack Vulnerability in API Key Validation
**Vulnerability:** API keys were being validated using simple string comparison (`!=`) instead of a constant-time comparison (`hmac.compare_digest`), making the endpoints vulnerable to timing attacks.
**Learning:** Found scattered instances of direct string comparisons in FastAPI route handlers that bypass the standard dependency logic (`require_cartorio_api_key`).
**Prevention:** Always use `hmac.compare_digest` for validating sensitive strings (like API keys, tokens) or use a centralized dependency function that implements it securely.
