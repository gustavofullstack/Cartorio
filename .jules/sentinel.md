## 2026-06-29 - Fixed Timing Attack in API Key Validation
**Vulnerability:** Standard equality operators (`!=`, `==`) were used to compare API keys in some router endpoints, exposing them to timing attacks.
**Learning:** Python's `hmac.compare_digest` must be used for all constant-time string comparisons involving secrets (like API keys or tokens) to mitigate timing side-channel attacks.
**Prevention:** Ensure new route endpoints correctly utilize `hmac.compare_digest` or rely on centralized dependency injection (e.g., `Depends(require_cartorio_api_key)`) that implements it.
