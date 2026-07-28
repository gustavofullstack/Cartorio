## 2024-05-24 - Fix Timing Attack in API Key Validation
**Vulnerability:** String comparison operator `!=` used to validate API keys
**Learning:** Simple string comparison operations fail fast, allowing attackers to incrementally guess valid secrets based on response times
**Prevention:** Use constant-time compare methods like `hmac.compare_digest()` to defend against timing attacks
