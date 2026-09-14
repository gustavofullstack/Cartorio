1. **Update `infra/openclaw/cartorio-bot.openclaw.json`:**
   - I have already updated `infra/openclaw/cartorio-bot.openclaw.json` to configure the OpenClaw AI agent to use `deepseek-v4-flash`, enable thinking (`"thinking": {"enabled": true}`), set the `context_window` to `1048576`, and update the `system_prompt` to be direct, short, serious, devoid of emojis, and to consistently leverage APIs/MCPs/Tools. This addresses the user request for agent personality and config.

2. **Run tests to verify changes:**
   - Use `run_in_bash_session` to run Pytest for the integration tests to make sure there are no breakages caused by this config update. Since `infra/openclaw/cartorio-bot.openclaw.json` is mainly JSON metadata used by scripts and deployments, this checks our setup.

3. **Complete pre-commit steps to ensure proper testing, verification, review, and reflection are done.**
   - Run the pre commit tool to get instructions on checks before submit.

4. **Submit changes:**
   - Once pre-commit passes, run the `submit` tool to wrap up this isolated OpenClaw AI agent config change.
