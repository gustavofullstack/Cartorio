# cartorio-ai · BOOTSTRAP

Onboarding de um agente novo no projeto Cartório em **<10 minutos**. Ordem de leitura obrigatória:

## 1. Contexto (3 min)
1. `../AGENTS.md` — stack, comandos `make`, regras P0, gotchas de integração.
2. `README.md` (deste pacote) — o que é o cartorio-ai e o estado do projeto.
3. `identity/SOUL.md` — por que existimos e o que nunca fazemos.

## 2. Estado atual (3 min)
4. `planning/TASKS.md` → abre `../SUPER_PLANO_G9_100_TASKS.md` (plano ativo, 14/100 em 2026-07-20).
5. `memory/MEMORY.md` — fatos de hoje: webhook re-sincronizado, fallback zen, CNJ export.
6. `../STATUS.md` — snapshot operacional mais recente.

## 3. Limites (2 min)
7. `security/SECURITY.md` — segredos, PII 3-camadas, audit chain, proibição de rotação.
8. `compliance/CNJ.md` — fluxo CNJ/DPO se a tarefa tocar exportação ou relatório de proteção.

## 4. Execução (2 min)
9. Escopo de arquivos da sua missão — nunca edite fora dele (agents rodam em paralelo).
10. Comandos: `cd backend && uv run pytest <alvo> -q` (nunca a suíte inteira com coverage);
    `make qa` só quando o orquestrador pedir gate completo.

## Regras duras de boot
- Não commite nem faça push — o orquestrador commita (mensagem termina com `Modified by Gustavo Almeida`).
- Não imprima valores de secrets/tokens — mascare sempre.
- Não rotacione nenhuma chave — proibido pelo dono.
- Responda em português.
