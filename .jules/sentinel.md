## 2026-07-15 - [Remove hardcoded API Key from OpenClaw integration]
**Vulnerability:** A fallback API key/password (`@Techno832466`) was hardcoded directly in `backend/app/integrations/openclaw.py`.
**Learning:** Hardcoding fallback credentials creates a critical risk if this source code is ever leaked. Downstream logic must be adapted to handle missing secrets securely by raising structural errors rather than defaulting to static placeholders.
**Prevention:** Always rely on secure environment configurations or fallback to empty strings combined with robust downstream error handling for secrets.
