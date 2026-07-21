## 2025-02-28 - Insecure API Key Comparisons
**Vulnerability:** API key verification was performed using direct string comparison (`api_key != settings.cartorio_api_key`), which is vulnerable to timing attacks. This could allow an attacker to guess the API key character by character by measuring the response time.
**Learning:** Some endpoints in the codebase were manually comparing the API key instead of using the central dependency `require_cartorio_api_key`, and these manual checks bypassed the constant-time comparison protections.
**Prevention:** Always use `hmac.compare_digest` for cryptographic secrets or string equality checks related to authentication to prevent timing attacks. Prefer reusing centralized authentication dependencies.
