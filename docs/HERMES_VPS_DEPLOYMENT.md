# Hermes Cartorio na VPS — contrato de implantação

**Estado verificado em 2026-07-28:**
`LARK_TRANSPORT_E2E_PASS / LGPD_RELOAD_PENDING`.
`cartorio_hermes` está `1/1`, o WebSocket Lark está conectado, MiniMax-M3 e
MiniMax-M2.7-highspeed responderam a inferências reais, o MCP autenticado está
habilitado com uma única ferramenta selecionada e Felipe completou um
round-trip real sem interromper a sessão de Gustavo.

O alvo é um único serviço `cartorio_hermes` no Docker Swarm, na rede
`easypanel-cartorio`, com estado persistente em volume próprio. Na VPS ele
atende somente Lark/Feishu e integra-se ao FastAPI pela API/MCP. Photon/iMessage
continua no Mac, onde existe a dependência nativa do Messages.app.

## Artefatos versionados

- `infra/hermes/docker-stack.yml` — serviço isolado, uma réplica, limites de
  recurso, rollback e Docker Secrets. Na
  primeira inicialização ele copia a configuração versionada para o volume;
  atualizações de perfil exigem migração revisada, não sobrescrita silenciosa.
- `infra/hermes/config.cartorio.yaml` — perfil Hermes sem credenciais literais.
- `infra/hermes/.env.example` — nomes das variáveis não secretas e dos segredos
  exigidos.
- `infra/hermes/preflight-vps.sh` — gate somente leitura de Swarm, rede e nomes
  dos secrets; não lê nem imprime conteúdo de credenciais.

O serviço usa uma imagem imutável do Hermes Agent publicada no registry do
Easypanel e fixada por digest no manifesto. O diretório persistente é
`/opt/data`; credenciais Lark criadas pelo onboarding nativo ficam nesse volume
com modo `0600`.

## Segredos e limites atuais

Os dois segredos abaixo devem existir **diretamente no gerenciador de
segredos da VPS**; é proibido copiá-los de um Mac, `.env`, log ou repositório:

| Segredo | Finalidade |
| --- | --- |
| `hermes_minimax_api_key` | autentica MiniMax-M3 e o fallback M2.7-highspeed |
| `hermes_mcp_cartorio_api_key` | contém o valor do segredo de produção `MCP_API_KEY` e autentica MCP contra a API do Cartório |

`FEISHU_ALLOW_ALL_USERS=false`, `FEISHU_GROUP_POLICY=allowlist` e
`FEISHU_REQUIRE_MENTION=true` são invariantes. A disponibilidade do app no Lark
é a fronteira organizacional upstream; o pairing do Hermes é uma segunda
barreira fail-closed. `CARTORIO_API_KEY` não substitui `MCP_API_KEY`.

## Sequência obrigatória de implantação

1. Confirmar os dois Docker Secrets no ambiente de produção, sem imprimi-los.
2. Carregar a configuração não secreta exclusivamente no Easypanel/Swarm.
3. Executar `bash infra/hermes/preflight-vps.sh` na VPS e exigir
   `HERMES_PREFLIGHT=PASS`.
4. Validar o manifesto sem implantar: `docker stack config -c infra/hermes/docker-stack.yml`.
5. Implantar como serviço novo: `docker stack deploy -c infra/hermes/docker-stack.yml cartorio`.
6. Conferir `docker service ps cartorio_hermes` e logs sanitizados; não faça
   replacement durante atendimento ativo.
7. Executar `hermes mcp test cartorio` no contexto do processo que recebeu os
   secrets e confirmar `1 selected`.
8. Validar uma chamada MCP sem PII e confirmar que a resposta contém apenas
   dados permitidos.
9. Provar o round-trip Lark com cada novo usuário autorizado sem revogar grants
   anteriores.
10. Validar separadamente WhatsApp, Telegram e iMessage; disponibilidade de
    container não certifica nenhum canal.

## Critérios de aceite

| Camada | Evidência mínima |
| --- | --- |
| Serviço | `cartorio_hermes` 1/1 e sem crashloop |
| MCP | handshake + `tools/list` + uma tool permitida, sem PII em log |
| Dados | acesso somente pela API/MCP, RLS preservada; Hermes não recebe acesso direto ao Postgres/Redis |
| Lark | usuário no escopo do app + pairing → MiniMax → resposta no mesmo chat |
| Outros canais | aceites independentes; não herdam o estado operacional do Lark |
| LGPD/HITL | scrub antes de LLM, nenhuma decisão jurídica automática, auditoria registrada |

O transporte Lark passou para Gustavo e Felipe. O aceite LGPD completo depende
de ativar o filtro de logs no próximo replacement controlado. Isso não promove
WhatsApp ou iMessage a operacionais.

## Rollback

Use o histórico do Swarm; não remova serviço ou volume durante um incidente:

```bash
docker service rollback cartorio_hermes
```

Preserve o volume `hermes_cartorio_data`. Excluir volume, pairing, sessão ou
logs exige autorização explícita e análise de retenção/LGPD.
