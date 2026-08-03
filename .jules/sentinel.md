## 2026-07-28 - Hardcoded secrets in config
**Vulnerability:** Hardcoded Telegram token in agent config.
**Learning:** Even when the user insists on providing secrets and skipping rotation, secrets must never be hardcoded in version-controlled config files.
**Prevention:** Always use environment variable references (e.g., `${TELEGRAM_TOKEN}`) in JSON or YAML configuration files to prevent secrets from being tracked by git.
