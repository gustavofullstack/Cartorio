## 2024-09-08 - Fix SSL verification bypass in health radar
**Vulnerability:** HTTPX client initialized with verify=False bypassing SSL certificate checks.
**Learning:** Hardcoding verify=False in monitoring endpoints (like health radar) can expose the system to MITM attacks, even for internal or trusted domains.
**Prevention:** Always enforce SSL validation by removing verify=False or passing a custom SSL context if specific internal CAs are needed.
