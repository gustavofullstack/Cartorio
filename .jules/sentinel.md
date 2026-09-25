## 2024-05-20 - Ensure standard SSL Validation
**Vulnerability:** Found `verify=False` in `backend/app/api/v1/health_radar_expanded.py` when verifying Traefik domains.
**Learning:** Bypassing SSL validation opens MITM (Man In The Middle) attacks. Traefik endpoints are public domains and must use standard SSL validation.
**Prevention:** Always rely on standard certificate chains rather than disabling verification outright.
