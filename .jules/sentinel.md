## 2026-07-18 - Missing SSL Verification in Internal Traefik Checks
**Vulnerability:** The internal Traefik health check used `httpx.AsyncClient` with `verify=False` against public domain hostnames (e.g., api.2notasudi.com.br).
**Learning:** Disabling verification likely existed to avoid issues with local/self-signed certs during dev, but since these checks hit public internet domains, it exposes the radar monitoring to MITM attacks.
**Prevention:** Never use `verify=False` for endpoints with public internet domains, even in internal monitoring scripts. Use proper CA trust chains or local host files if routing internally.
