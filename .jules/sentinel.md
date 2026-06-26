## 2026-06-26 - Timing Attack Vulnerability in API Key Verification
**Vulnerability:** Timing attack vulnerability due to direct string comparison (`!=`) of `X-API-Key` headers in FastAPI endpoints.
**Learning:** Developers sometimes manually compare `api_key != settings.cartorio_api_key` without using the built-in, secure `_verify_api_key(api_key)` or `hmac.compare_digest` method. This allows for an enumeration attack to slowly deduce the key.
**Prevention:** Always use `hmac.compare_digest(provided, expected)` for sensitive string comparisons like API keys, passwords, or tokens to ensure constant-time comparison, or reuse the centralized `_verify_api_key` helper function.
