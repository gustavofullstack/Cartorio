## 2025-02-14 - HTTP Client Verification Override
**Vulnerability:** Found `verify=False` in `httpx.AsyncClient` inside `backend/app/api/v1/health_radar_expanded.py`, disabling SSL/TLS certificate validation.
**Learning:** This could expose the application to man-in-the-middle (MITM) attacks when the health radar checks the internal Traefik routers.
**Prevention:** Always enforce strict SSL/TLS validation when making HTTP requests, even in health checks for internal infrastructure, by omitting `verify=False`.
