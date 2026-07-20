# cartorio-ai · brain/BRAIN.md

Como o agente do Cartório **pensa e decide**. Deriva de `../../.harness/AGENTS.md` e das lessons
do ciclo G6–G9.

## Workflow obrigatório (ciclo de mudança)

`analisar → testar → corrigir → melhorar → otimizar → documentar → comentar → salvar na memória`

- Pular etapa = bug. Em `audit*` ou `pii*`, pular etapa = incidente.
- Toda mudança termina com evidência: teste que falha se regredir + entrada de memória.

## Honesty gate

1. `[x]` em plano SÓ com evidência de 1 linha (arquivo, commit, saída de teste, probe).
2. Nunca reportar "feito" sem artefato verificável; reportar o que NÃO foi feito e por quê.
3. Precedente: plano G8 foi reescrito com tick fraudulento 100/100 → reset para 5/100 evidenced.
   A regra existe porque já foi violada.

## Diagnóstico antes de correção

- Sessão 2026-07-20 validou o método: 4 diagnósticos read-only (E1 telegram, E2 LLM, E3 infra,
  E4 testes) precederam qualquer patch — resultado: causa-raiz (webhook sem `secret_token`)
  corrigida com re-sync, não com tentativa-e-erro em prod.
- Probes funcionais são evidência mínima de canal: `response_sent=true` (síncrono) e
  `scheduled=true` (debounce async) — mas `scheduled` ≠ entregue; confirmar a entrega async
  é task aberta (G9.03.T4).

## Gestão de contexto e escopo

- Agents rodam em paralelo com escopo de arquivos exclusivo — nunca editar fora dele.
- Não re-verificar fatos já validados na sessão (custa tempo e introduz ruído); usar o contexto.
- Mycorrhiza de memória: projeto → `../../.harness/memory/MEMORY.md`; sessão →
  `../../.brain/memory/YYYY-MM-DD.md`; este pacote → `../memory/MEMORY.md`.

## Falha silenciosa é o inimigo

- Telegram: regra sempre-200 exceto 401 de secret (A3); debounce com feedback garantido (A6).
- LLM: silêncio de 15-20min (timeout único × 6 tentativas) é tratado como bug P1 (E2).
- Toda exceção vira exceção tipada (`app.core.exceptions`) — nunca `raise Exception`.
