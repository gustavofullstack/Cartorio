## 2024-05-24 - [Remove Hardcoded LiteLLM API Key]
**Vulnerability:** A hardcoded API key (`e39dss0k1baohuqkprjv`) was present as a fallback for the `LITELLM_API_KEY` environment variable in `backend/app/services/cartorio_agent.py`.
**Learning:** Hardcoded API keys pose a critical security risk. Fallbacks should route through the application configuration settings, avoiding dummy/testing keys that can leak into the source code.
**Prevention:** Always use `app.config.Settings` or environment variables exclusively for secrets. Ensure testing keys are not embedded in the source code as string defaults.
