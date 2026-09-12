## 2026-09-12 - Missing Authentication on Metrics Endpoints
**Vulnerability:** The N8N metrics endpoints `/api/v1/n8n/metrics/prometheus` and `/api/v1/n8n/metrics/summary` were exposed publicly without requiring the internal X-API-Key.
**Learning:** Endpoints meant for internal scrapers (like Prometheus) or dashboards need the same `Depends(require_cartorio_api_key)` protection as operational webhook endpoints to prevent data leakage or unauthenticated scraping of execution metrics.
**Prevention:** Always verify that every new router endpoint not explicitly meant for unauthenticated public use (like webhooks verified by other means, e.g., Telegram HMAC) includes the `_api_key: str = Depends(require_cartorio_api_key)` dependency in its signature.
