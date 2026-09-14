# Cartório AI - Plano de Orquestração, Melhorias e Correções (Parte 1)

1. **Atualizar OpenClaw Agent Config (cartorio-bot) - Verificação**
   - Usar `read_file` em `infra/openclaw/cartorio-bot.openclaw.json` para verificar se as alterações do primary provider para `deepseek-v4-flash`, system_prompt e thinking foram corretamente aplicadas e mantiveram as propriedades obrigatórias.

2. **Planejamento de Tarefas (Spawn de Agentes)**
   - Utilizar a ferramenta de bash para criar um arquivo `plan_compact.json` e `plan_macro.md` especificando o seu conteúdo exato com o comando `cat << 'EOF' > plan_compact.json`. Eles conterão as macro tarefas do primeiro ciclo (focado em testes do Telegram, configuração e formatação).

3. **Integração e Validação do Telegram (Testes)**
   - Modificar `backend/tests/test_telegram_e2e.py` usando script python em `run_in_bash_session` ou string replacement para adicionar `patch('app.api.v1.telegram._get_lgpd_consent', new=AsyncMock(return_value=True))` nos testes que falham por causa de verificações (ou onde for necessário para testes passarem) - Ex: `test_e2e_start_command`.
   - Adicionar ou corrigir variáveis de ambiente mockadas no comando pytest (como `AUDIT_HMAC_KEY`, `CARTORIO_API_KEY`, etc).

4. **Qualidade de Código: Formatação e Linter**
   - Rodar `uv run ruff format backend/app/api/v1/telegram.py` via `run_in_bash_session`.
   - Rodar `uv run ruff check backend/app/api/v1/telegram.py` via `run_in_bash_session` para ver se existe algum warning remanescente e corrigi-lo.

5. **Testes do Backend**
   - Executar `uv run pytest backend/tests/test_telegram_e2e.py` com as variáveis de ambiente necessárias para atestar que os testes do Telegram funcionam.

6. **Pre Commit**
   - Complete pre-commit steps to ensure proper testing, verification, review, and reflection are done. (Usando `pre_commit_instructions`).

7. **Submissão**
   - Fazer submissão do trabalho final usando `submit`.
