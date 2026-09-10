## 2026-09-10 - Fix SSL certificate validation bypass
**Vulnerability:** SSL certificate checks were disabled (`verify=False`) in `httpx.AsyncClient` within `health_radar_expanded.py`.
**Learning:** This is likely an artifact from early local testing where valid certs weren't available. In production, this allows man-in-the-middle attacks.
**Prevention:** Never use `verify=False` in production code. Ensure testing environments use valid certificates or mock HTTP calls appropriately.
