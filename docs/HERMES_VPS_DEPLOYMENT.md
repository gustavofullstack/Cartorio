# Hermes Cartorio na VPS — contrato de implantação

**Estado atual em 2026-07-26:** `NOT_DEPLOYED`. A VPS executa OpenClaw, API,
Postgres/Supabase, Redis, n8n, Evolution e Chatwoot; não há serviço Hermes.

O alvo é um único serviço `cartorio_hermes` no Docker Swarm, na rede
`easypanel-cartorio`, com estado persistente em volume próprio. Ele não substitui
o FastAPI, OpenClaw, Evolution, Chatwoot ou n8n: integra-se a eles pela API e MCP.

## Artefatos versionados

- `infra/hermes/docker-stack.yml` — serviço isolado, uma réplica, health/API
  interna na porta 8642, limites de recurso, rollback e Docker Secrets. Na
  primeira inicialização ele copia a configuração versionada para o volume;
  atualizações de perfil exigem migração revisada, não sobrescrita silenciosa.
- `infra/hermes/config.cartorio.yaml` — perfil Hermes sem credenciais literais.
- `infra/hermes/.env.example` — nomes das variáveis não secretas e dos segredos
  exigidos.

O serviço usa a imagem oficial `nousresearch/hermes-agent` fixada no digest
AMD64 `sha256:6df245c22c49b5ad9f94dd9e3cf614263f4313f117d117a7d2abd4092fa804d2`,
resolvido em 2026-07-26. A documentação oficial informa que a API compatível e
health do gateway usam a porta 8642 e que o diretório persistente do container
é `/opt/data`.

## Pré-requisitos bloqueantes

Os quatro segredos abaixo devem ser criados **diretamente no gerenciador de
segredos da VPS**; é proibido copiá-los de um Mac, `.env`, log ou repositório:

| Segredo | Finalidade |
| --- | --- |
| `hermes_api_server_key` | autentica a API interna do Hermes |
| `hermes_llm_api_key` | autentica o provider LLM aprovado |
| `hermes_mcp_cartorio_api_key` | autentica MCP contra a API do Cartório |
| `hermes_photon_project_secret` | autentica o sidecar Photon/iMessage |

Também são necessários, como configuração não secreta: URL/modelo do provider
aprovado, `PHOTON_PROJECT_ID` e allowlist E.164. `PHOTON_ALLOW_ALL_USERS` fica
fixado em `false`.

## Sequência obrigatória de implantação

1. Criar os quatro Docker Secrets no ambiente de produção, sem imprimi-los.
2. Carregar a configuração não secreta exclusivamente no Easypanel/Swarm.
3. Validar o manifesto sem implantar: `docker stack config -c infra/hermes/docker-stack.yml`.
4. Implantar como serviço novo: `docker stack deploy -c infra/hermes/docker-stack.yml cartorio`.
5. Conferir `docker service ps cartorio_hermes` e logs sanitizados; nenhum serviço
   existente deve ser reiniciado.
6. Validar a API Hermes por dentro da rede com bearer token, depois `hermes mcp
   test cartorio` no container.
7. Validar uma chamada MCP sem PII e confirmar que a resposta contém apenas
   dados permitidos.
8. Iniciar o sidecar Photon e provar o round-trip real: iPhone autorizado →
   Photon → Hermes → MCP/API quando aplicável → resposta no mesmo iPhone.
9. Validar separadamente WhatsApp (Evolution), Chatwoot e Telegram/webhook;
   disponibilidade de container não certifica nenhum canal.

## Critérios de aceite

| Camada | Evidência mínima |
| --- | --- |
| Serviço | `cartorio_hermes` 1/1 e sem crashloop |
| API Hermes | health 200 interno e rejeição de chamada sem chave |
| MCP | handshake + `tools/list` + uma tool permitida, sem PII em log |
| Dados | acesso somente pela API/MCP, RLS preservada; Hermes não recebe acesso direto ao Postgres/Redis |
| Photon/iMessage | mensagem e resposta reais na mesma conversa autorizada |
| Evolution/Chatwoot | webhook → Hermes → resposta/hand-off por canal, cada um comprovado |
| LGPD/HITL | scrub antes de LLM, nenhuma decisão jurídica automática, auditoria registrada |

Enquanto qualquer linha acima não tiver evidência, o estado é
`REAL_TRANSPORT_NOT_CERTIFIED`, mesmo que o container esteja saudável.

## Rollback

Como Hermes é um serviço novo e isolado, o rollback não toca nos serviços atuais:

```bash
docker service rm cartorio_hermes
```

Preservar o volume `cartorio_hermes_cartorio_hermes_data` para investigação e
recuperação; só removê-lo mediante autorização explícita de retenção/LGPD.
