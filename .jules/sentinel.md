## 2024-07-25 - Timing attack vulnerability on X-API-Key Validation
**Vulnerability:** The `X-API-Key` was being validated using insecure `==` and `!=` operators in `backend/app/api/v1/router.py` and `backend/app/api/v1/lgpd_direitos.py`.
**Learning:** Using standard string equality operators for secrets allows for timing attacks, where an attacker can guess a secret byte by byte based on the response time.
**Prevention:** Always use constant-time comparison methods, such as `hmac.compare_digest`, when verifying secrets like API keys.
