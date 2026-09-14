## 2025-03-26 - Missing Auth in Bot Admin Endpoints
**Vulnerability:** Admin endpoints for processing hard deletes (e.g., `get_revogacoes` and `post_marcar_deletado`) were exposed without authentication.
**Learning:** Even internal-facing routers (like bot handling) can contain admin-level functions that require explicit service-to-service auth, as a missing gate can expose sensitive operations.
**Prevention:** Ensure every endpoint logically classified as `[Admin]` explicitly uses `Depends(require_cartorio_api_key)` or `require_dpo_role`, regardless of the router prefix.
