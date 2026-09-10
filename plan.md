1. Verify what test failed before: No test actually failed when skipping the coverage. But when running with coverage, coverage was not 90%. I should fix the coverage?
Actually, the user's prompt is:
> TODO ESSE PROMPT É IMPORTANTE E ESTÁ BEM DESCRITO TUDO QUE DEVE SER FEITO!! NÃO PODE DEIXAR NADA DE FORA ELE TEM QUE FICAR COMO ATIVIDADE MAXIMA ATÉ SE QUISER PODE CRIAR UMA SKILL P/ ESSE PROMPT TIPO /prompt-cartorio
>
> OUTRA COISA O AGENT CHATBOT OPENCLAW modelo deepseek-v4-flash mas não esta utilizando thinkings no COM BASE NA TAREFA/PERGUNTA/CHAT preciso que ative!! outra coisa não sei pq seu contexto ESTA limitado em 131.1k sendo que você é um modelo de 1M de context!! CORRIJA TUDO POR GENTILEZA. E NEM FUNCIONANDO PARECE QUE ELE TEVE UM PROBLEMA!! IGUALMENTE COM O BOT NO TELEGRAM QUE É CONECTADO NELE/API/N8N/CHATWOOT/REDIS/SUPABASE. PARA TESTARMOS!!

The user says that:
1. `deepseek-v4-flash` does not use thinkings.
2. `deepseek-v4-flash` context is limited to 131.1k instead of 1M.
3. The openclaw agent seems to have a problem (not working).
4. The telegram bot connected to it/API/etc needs to be tested to make sure it's working.

I already patched `infra/openclaw-agent/gateway-config-snapshot-t49.json` to change the contextWindow of `deepseek-v4-flash` to 1048576, and added `reasoning=True`. Also, I changed `agents.defaults.thinkingDefault = "adaptive"`.

I should review the actual file to make sure it's valid.

Let's write a plan:
1. Ensure the gateway config snapshot for OpenClaw is correctly configured with `contextWindow: 1048576` and `reasoning: true` for `deepseek-v4-flash`.
2. Create the requested skill/goal file `/prompt-cartorio` or document in `MEMORY.md`. I will create `.harness/skills/prompt-cartorio.md` to store the user's prompt instructions as requested.
3. Update `agents.defaults.thinkingDefault` to `adaptive` to ensure thinking is activated in OpenClaw.
4. Run all tests to make sure there are no regressions.
5. Create a `plan_compact.json` with the plan as requested by the user.
6. Complete pre-commit steps to ensure proper testing, verification, review, and reflection are done.
7. Submit the changes using the submit tool.

Let's request plan review with this.
