## 2026-07-04 - [Remove Hardcoded Secret in OpenClaw Integration]
**Vulnerability:** A hardcoded API key (`@Techno832466`) was used as a fallback for the `openclaw` LLM integration.
**Learning:** Hardcoded credentials bypass secure configuration practices and pose a critical security risk if the source code is exposed.
**Prevention:** Always require API keys and secrets to be provided via environment variables or secure configuration mechanisms. Raise explicit configuration errors (e.g., `ChatError` with `ChatErrorKind.CONFIG`) when credentials are missing instead of falling back to insecure defaults.
