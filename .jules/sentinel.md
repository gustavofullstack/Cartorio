## 2026-08-28 - Removed disabled SSL verification in health radar
**Vulnerability:** Disabled SSL validation (`verify=False`) in `httpx.AsyncClient` in `health_radar_expanded.py`.
**Learning:** Hardcoding `verify=False` leaves the service vulnerable to man-in-the-middle attacks when health-checking Traefik router domains.
**Prevention:** Avoid disabling SSL verification in production code; use properly configured certificates and trust stores.
