## 2026-07-07 - Hardcoded API Key in Fallback Agent
**Vulnerability:** A hardcoded API key (`e39dss0k1baohuqkprjv`) was found in `LITELLM_KEY` within `cartorio_agent.py` as a default parameter for `os.environ.get`.
**Learning:** Fallback mechanisms and proxy connectors (like LiteLLM proxy) sometimes introduce hardcoded dummy or testing keys in source code. This bypasses the central `Pydantic Settings` configuration, making it a critical security leak and configuration mismanagement.
**Prevention:** Never use hardcoded strings as defaults for `os.environ.get` for any secrets. Always route secrets through `app.config.Settings` and inject them dynamically. Validate if the key exists during execution, and fail securely or use an established fallback chain if absent.
