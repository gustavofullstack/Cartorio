## 2026-06-29 - Missing Security Headers in FastAPI App
**Vulnerability:** The FastAPI application was missing essential HTTP security headers (HSTS, CSP, X-Frame-Options, X-Content-Type-Options, Referrer-Policy, X-XSS-Protection), leaving it vulnerable to various client-side attacks like clickjacking and XSS.
**Learning:** While the application had robust security in other areas (CORS, Idempotency, rate limiting, and auth), standard HTTP response headers were overlooked.
**Prevention:** Implemented `SecurityHeadersMiddleware` extending `BaseHTTPMiddleware` to inject these standard headers defensively on every request.
