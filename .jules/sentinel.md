
## 2024-09-07 - Verify HTTPX Traefik Checks
**Vulnerability:** Found an issue where SSL certificates were not being validated during Traefik domain checks because `httpx.AsyncClient` used `verify=False`. This disabled the SSL/TLS verification allowing for a potential MITM attack (Man-in-the-Middle) even for health checks.
**Learning:** Even internal health checks on domains can be susceptible to interception. In an internal context, it's safer to properly provision and verify certificates (or configure internal CAs) rather than universally disabling verification `verify=False` which can mask larger configuration errors.
**Prevention:** Avoid passing `verify=False` to HTTP clients like `httpx` and `requests` unless in highly controlled and temporary testing environments. In production, ensure custom CAs or proper public certificates are used and verified correctly.
