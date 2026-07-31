# Lark/Hermes recovery — 2026-07-31

Correlation: `corr-lark-hermes-20260731`

## Estado

- `cartorio_hermes`: `1/1`, uma task ativa, sem segunda instância observada.
- Transporte visual no mesmo chat: texto e imagem receberam resposta.
- MCP Cartório: conexão autenticada passou somente dentro do contexto do Docker Secret; nenhum valor de segredo foi registrado.
- Eventos Lark observados: legado P1 (`message`/`message_read`); inbound P2 não foi comprovado.
- `processor not found` permanece bloqueador do aceite operacional completo.

## Correção Git publicada

Commit `7f9255f` remove a tentativa insegura de ingestão ZIP do bot Flask legado,
que não é o consumidor Hermes canônico. O caminho público permanece sem bypass do
pipeline privado BRAIN/HITL, sem caminho absoluto local e sem eco de exceção.

Validação local: `18 passed` em `tests/test_lark_legacy_security.py`, compilação
Python e `git diff --check` aprovados.

## Bloqueadores para T5

1. Alterar no tenant Lark a assinatura para `im.message.receive_v1` e remover o
   evento legado `message`; retirar `message_read` legado ou usar a variante P2.
2. Observar somente eventos P2 após a alteração.
3. Executar DM sintética autorizada: Lark → Hermes → MiniMax → mesmo chat.
4. Confirmar cálculo oficial via MCP, ausência de erros `processor not found` e
   ausência de reasoning/progresso público.

Nenhum serviço Hermes foi reiniciado ou alterado durante esta etapa. O deploy do
Hermes fica bloqueado até a ação administrativa no tenant e revisão do artefato
canônico de produção.
