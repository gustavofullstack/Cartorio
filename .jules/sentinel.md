## 2026-07-16 - Timing Attack Vulnerability in HMAC Comparison
**Vulnerability:** Comparing HMAC signatures using standard string equality (`==`) rather than constant-time comparison methods.
**Learning:** Standard string equality (`==`) returns `False` as soon as a mismatch is found, allowing attackers to infer the correct signature character by character based on response times (timing attack).
**Prevention:** Always use `hmac.compare_digest()` for cryptographic comparisons to ensure the comparison time is constant regardless of where the mismatch occurs. Ensure to check for `None` before passing values to `hmac.compare_digest()`.
