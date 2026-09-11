1. **Configurar OpenClaw context limit para 1.000.000 tokens e OpenClaw Thinkings:**
   - O `contextWindow` estava configurado para 131k (herdado de antigamente). Foi ajustado em `infra/openclaw-agent/gateway-config-snapshot-t49.json` via comando `jq` para `1048576` no `deepseek-v4-flash`. Os testes já foram atualizados via sed local para bater o 1M com o snapshot configurado.
   - Usar `replace_with_git_merge_diff` para modificar `backend/app/integrations/fallback.py` alterando referências de `131K` a `1M` no arquivo e em `backend/app/config.py` se ainda tiver, como `131K ctx`.
   - O modo *thinkings* adaptativo já parece configurado em `gateway-config-snapshot-t49.json` e `backend/app/config.py`.

2. **Complete pre-commit steps to ensure proper testing, verification, review, and reflection are done.**
   - Chamarei a tool `pre_commit_instructions` e seguirei todas as instruções (formatação de código, lint, type checks).

3. **Submit as mudanças através da tool submit.**
   - Fazer commit das alterações de 1M no contexto do Agent AI Cartório.
