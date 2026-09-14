## 2026-07-28 - [Hardcoded X-API-Key]
**Vulnerability:** A hardcoded shared secret `cartorio-api-shared-secret-v1` was used as the `X-API-Key` header value in `infra/n8n-workflows/07-pesquisa-satisfacao.json`.
**Learning:** Workflows sometimes fallback to hardcoded keys instead of environment variables, leading to potential credential leaks and brittle auth that breaks when keys are rotated.
**Prevention:** Always enforce the use of `={{ $env.CARTORIO_API_KEY }}` via automated scanning or workflow linters to ensure dynamic, environment-based credential injection.
