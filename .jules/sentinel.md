## 2024-05-24 - [Fix timing attack vulnerability in API key verification]
**Vulnerability:** API key verification used `!=` standard string equality instead of a constant-time comparison, making it susceptible to timing attacks.
**Learning:** Hardcoded comparisons or standard `==` / `!=` operators check strings character by character and return immediately upon finding a mismatch. This allows attackers to deduce secrets by measuring response times.
**Prevention:** Always use `hmac.compare_digest` for cryptographic checks to ensure constant-time string comparisons.
