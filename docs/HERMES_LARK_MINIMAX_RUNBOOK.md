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
- Persona: Docker Config `hermes_cartorio_soul_v2`, originado de
  `infra/openclaw-agent/workspace/SOUL.md`
- Backend MCP: `http://cartorio_system-api:8000/mcp/`, autenticado pelo Docker
  Secret `hermes_mcp_cartorio_api_key`
- Ferramenta pública autorizada no Lark:
  `cartorio_calcular_emolumento`
- Guard de saída: plugin `pietra-public-output`, aplicado pelo hook oficial
  `transform_llm_output` somente ao canal Feishu/Lark

`provider: openai` não é válido no Hermes Agent 0.19.0. Para um endpoint
OpenAI-compatible genérico, use um provider customizado. Para a API MiniMax,
use sempre o provider nativo `minimax`.

## Perfil público final-only

O volume persiste `config.yaml` entre tasks. Por isso, apenas montar um novo
template não corrige flags antigas. O entrypoint executa
`reconcile_public_profile.py` em todo boot e impõe:

- `agent.max_turns: 8`;
- `tool_progress`, commentary, reasoning, streaming, mensagens intermediárias,
  avisos de tarefas longas e ACKs de busy desligados;
- `busy_input_mode: queue`, para uma segunda mensagem aguardar sem interromper
  nem publicar `Redirected current run (iteration N/M)`;
- somente o plugin `pietra-public-output`;
- todos os diretórios de skills instalados desabilitados no Feishu;
- somente o toolset `mcp-cartorio`, com allowlist de uma ferramenta;
- apenas Feishu no gateway da VPS. Photon/iMessage continua no sidecar do Mac.

O guard remove da cópia pública traces de reasoning/tool, mensagens de controle,
menus de capacidades genéricas e alegações jurídicas autônomas. Também mascara
PII e preserva a exigência de validação humana. Ele é uma última barreira; não
substitui o prompt da Pietra, o isolamento de toolsets ou o scrubber do backend.

Quando o chat é destinado a entregas do próprio agente, configure-o como home
channel uma única vez. Sem isso, uma sessão nova recebe o aviso operacional
`No home channel is set`, que não deve aparecer em atendimento público.

## Autorização de usuários Lark

O limite primário de disponibilidade é configurado no Lark Admin. O gateway
Hermes mantém uma segunda barreira independente:

- `FEISHU_ALLOW_ALL_USERS=false`;
- `FEISHU_GROUP_POLICY=allowlist`;
- `FEISHU_REQUIRE_MENTION=true`;
- usuários autorizados presentes nos stores global e do profile `default`.

Não use `allow_all_users=true` como substituto de escopo organizacional: essa
flag ignora o pairing no Hermes. Antes de liberar alguém, confirme pela API
oficial de visibilidade que a conta pertence ao escopo do app; depois aprove o
pairing sem revogar os grants existentes. Compare os dois stores e preserve
owner UID/GID `10000` e modo `0600`. Uma aprovação só está validada quando uma
mensagem real dessa pessoa percorre Lark → Hermes → provider → mesmo chat.

O endpoint de Contacts scope descreve o alcance de dados autorizado ao app,
mas não deve ser tratado como sincronizador automático do pairing. Se no futuro
houver automação, ela deve ser tenant-aware, aditiva e fail-closed: erro ou
escopo vazio nunca pode apagar grants existentes.

## Privacidade dos logs

O Hermes upstream registra previews de mensagens em três loggers internos.
Neste deployment, o plugin `pietra-public-output` instala um filtro nesses
loggers e substitui texto, nomes, IDs de usuário/chat/sessão e replies por
metadados não identificadores (tipo, provider, plataforma, contagens e
tamanhos). A proteção de secrets do upstream não substitui esse filtro de PII.

Depois de ativar uma versão que contenha o filtro, valide com conteúdo
sintético e faça a retenção/quarentena dos logs antigos conforme a política
LGPD. Não copie conteúdo de mensagens para tickets, commits ou diagnósticos.

## Validação por camadas

1. `docker service ls` deve mostrar `cartorio_hermes 1/1`.
2. Os logs devem registrar uma única conexão WebSocket do Lark e nenhum
   `Another gateway instance`.
3. `hermes auth status minimax` deve reconhecer o provider. A chave é injetada
   apenas no processo do gateway; nunca imprima o valor.
4. Execute um prompt sintético sem dados pessoais nos modelos M3 e
   M2.7-highspeed.
5. Rode `hermes mcp test cartorio` dentro do contexto que recebeu os Docker
   Secrets. O servidor pode anunciar várias tools, mas `hermes mcp list` deve
   mostrar apenas uma selecionada para este profile.
6. Execute um prompt sintético que obrigue
   `cartorio_calcular_emolumento` e confirme chamada de tool e resposta oficial.
7. Envie uma mensagem real no Lark e confirme:
   `Lark → Hermes → MiniMax → Hermes → mesmo chat Lark`.
8. Para perguntas sobre capacidades, confirme que a resposta cita somente
   serviços notariais e não lista ferramentas, programação ou automações.
9. Envie duas mensagens em sequência e confirme ausência de ACK de busy,
   `Redirected`, iteração, reasoning e progresso de ferramenta.

HTTP 200 isolado, serviço `1/1` ou WebSocket conectado são evidências parciais;
somente os passos 7–9 autorizam declarar o canal público operacional.

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
- `401 Unauthorized` em `hermes mcp test`: confirme que o processo de teste
  recebeu `MCP_CARTORIO_API_KEY`. Um `docker exec` novo não herda variáveis
  exportadas apenas pelo entrypoint do gateway.
- Config montado com owner root e modo `0440`: o processo Hermes (UID/GID
  `10000`) recebe `PermissionError`. Todos os Docker Configs usados pelo
  entrypoint devem declarar esse UID/GID.
- A resposta genérica com GitHub, pesquisa, mídia e automação foi causada por
  sessão congelada antes da persona e por skills/toolsets genéricos, não por
  falha de autenticação do MiniMax.
- `reqwest::Error(... IncompleteMessage)` com código `4028` pertence ao cliente
  que abriu a requisição, não ao gateway Python. Correlacione URL e timestamp:
  uma ocorrência em bridge antigo não prova falha do MiniMax da VPS.

## Atenção ao n8n

O volume do n8n contém uma chave de criptografia persistida. Antes de qualquer
redeploy, faça backup do volume e reconcilie `N8N_ENCRYPTION_KEY` com a chave já
existente. Nunca regenere a chave nem apague o arquivo de configuração: uma
divergência impede o n8n de descriptografar credenciais existentes.

## Rollback

Antes de alterações, salve o `docker service inspect` em
`/var/backups/cartorio/hermes-lark/` e copie `config.yaml` para
`/opt/data/backups/`. Em falha de rollout, use a revisão anterior do serviço e
restaure a cópia de configuração; nunca copie credenciais para o repositório.
