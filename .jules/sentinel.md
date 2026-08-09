## 2024-08-09 - [Timing attack vulnerability on API Key Validation]
**Vulnerability:** Found insecure API key comparisons using `==` or `!=` directly against `settings.cartorio_api_key`. This exposes the API to timing attacks.
**Learning:** Some endpoints in `backend/app/api/v1/router.py` and `backend/app/api/v1/lgpd_direitos.py` bypassed the secure dependency `require_cartorio_api_key` or `hmac.compare_digest` in favor of a direct string comparison `api_key != settings.cartorio_api_key`.
**Prevention:** Always use `hmac.compare_digest` when comparing API keys or secret tokens. In FastAPI, try to enforce `require_cartorio_api_key` dependency universally where possible.
