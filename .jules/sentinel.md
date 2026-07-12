## 2025-02-14 - Remove hardcoded LITELLM_API_KEY
**Vulnerability:** A fallback API key `"e39dss0k1baohuqkprjv"` was hardcoded in `backend/app/services/cartorio_agent.py` as a fallback for the `LITELLM_API_KEY` environment variable.
**Learning:** Even fallback strings in `os.environ.get()` are a critical vulnerability as they embed secrets within version control, allowing unintended access if the environment configuration is missing.
**Prevention:** Never use hardcoded keys as defaults. Let missing keys fail explicitly, or rely on centralized, secure configuration mechanisms (e.g. `settings`).
