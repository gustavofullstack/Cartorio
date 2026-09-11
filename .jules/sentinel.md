## 2026-07-28 - Fix API Key validation timing attacks
**Vulnerability:** Vulnerable API endpoints (admin_validate_n8n_wfs, admin_lgpd_relatorio_anual, get_protocolos_recentes_concluidos, lgpd_direitos_require_api_key) used standard string comparison operator (`!=`) against settings.cartorio_api_key, leading to potential timing attacks (CWE-208).
**Learning:** Security gates using simple operators (==/!=) leak execution time proportional to the number of matching prefix bytes.
**Prevention:** Always use constant-time comparison methods, such as `hmac.compare_digest`, when checking sensitive tokens/keys in Python, especially in FastAPI Dependency/Header handlers.
