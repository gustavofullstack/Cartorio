# Hermes Lark com MiniMax

Este runbook descreve o contrato de produção do Hermes/Pietra no Lark. Ele não
contém credenciais nem identificadores de usuários.

## Roteamento aprovado

- Provider Hermes: `minimax`
- Modelo primário: `MiniMax-M3`
- Endpoint: `https://api.minimax.io/anthropic`
- Contingência: `MiniMax-M2.7-highspeed`, no mesmo provider
- Credencial: Docker Secret `hermes_minimax_api_key`
- Lark: OAuth nativo do `hermes gateway setup`, persistido com modo `0600` no
  volume `hermes_cartorio_data`
- Persona: Docker Config `hermes_cartorio_soul_v1`, originado de
  `infra/openclaw-agent/workspace/SOUL.md`

`provider: openai` não é válido no Hermes Agent 0.19.0. Para um endpoint
OpenAI-compatible genérico, use um provider customizado. Para a API MiniMax,
use sempre o provider nativo `minimax`.

## Validação por camadas

1. `docker service ls` deve mostrar `cartorio_hermes 1/1`.
2. Os logs devem registrar uma única conexão WebSocket do Lark e nenhum
   `Another gateway instance`.
3. `hermes auth status minimax` deve reconhecer o provider. A chave é injetada
   apenas no processo do gateway; nunca imprima o valor.
4. Execute um prompt sintético sem dados pessoais nos modelos M3 e
   M2.7-highspeed.
5. Envie uma mensagem real no Lark e confirme:
   `Lark → Hermes → MiniMax → Hermes → mesmo chat Lark`.
6. Para perguntas sobre capacidades, confirme que a resposta cita somente
   serviços notariais e não lista ferramentas, programação ou automações.

HTTP 200 isolado, serviço `1/1` ou WebSocket conectado são evidências parciais;
somente o passo 5 autoriza declarar o canal operacional.

## Falhas conhecidas

- `Unknown provider 'openai'`: configuração usou um slug inexistente.
- `429 rate_limit_error`: a credencial existe, mas a conta está limitada.
- Duas telas “Hermes Gateway Starting”: o profile persistido iniciou uma
  instância S6 e o Swarm iniciou outra. O entrypoint deve executar
  `hermes gateway stop` antes do processo foreground.
- Eventos auxiliares `message_read` sem processor podem aparecer nos logs;
  diferencie-os de falhas no evento de mensagem e na inferência.
- Alterar `SOUL.md` não muda uma sessão já aberta. Faça backup e renove somente
  a sessão do canal afetado para que o novo system prompt seja carregado.

## Rollback

Antes de alterações, salve o `docker service inspect` em
`/var/backups/cartorio/hermes-lark/` e copie `config.yaml` para
`/opt/data/backups/`. Em falha de rollout, use a revisão anterior do serviço e
restaure a cópia de configuração; nunca copie credenciais para o repositório.
