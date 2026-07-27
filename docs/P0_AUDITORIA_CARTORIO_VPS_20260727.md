# P0 — Auditoria Cartorio AI 100% VPS

Data: 27/07/2026
Escopo: somente o projeto Cartorio AI / 2º Servico Notarial de Uberlandia.

## Regra de topologia

- O VAIO / Agent OS nao pertence ao projeto Cartorio.
- Nenhum runtime, deploy, banco, cache, gateway, agente ou dependencia operacional do Cartorio deve depender do VAIO.
- A VPS Hostinger do Cartorio e a autoridade de runtime de producao.
- Clientes locais podem ser usados apenas como interface administrativa quando tecnicamente inevitavel; isso nunca deve ser confundido com backend de producao.

## Veredito atual

`NO_GO_FOR_100_PERCENT`.

A infraestrutura base esta de pe, mas os canais e o agente ainda nao possuem evidencia suficiente para declarar producao autonoma E2E.

## Incidente P0 observado — iMessage

Screenshots de 27/07/2026 mostram o Cartorio Bot respondendo repetidamente ao cliente com a mensagem interna do provider:

`The model provider is rate-limiting requests. Please wait a moment and try again.`

Isso prova tres falhas simultaneas:

1. erro interno de provider esta vazando para UX do cliente;
2. nao ha circuit-breaker/backoff/fallback efetivo no caminho observado;
3. o caminho iMessage atual nao esta certificado como Photon -> Hermes VPS -> provider aprovado -> MCP -> resposta.

Aceite para fechamento:

- nenhuma mensagem bruta de provider chega ao cliente;
- 429/timeout/5xx viram resposta curta e neutra ou handoff, com retry limitado e jitter;
- circuit breaker impede tempestade de retries;
- fallback somente para provider/modelo explicitamente aprovado;
- logs guardam codigo/classe do erro, nunca segredo ou payload com PII;
- round-trip real no iPhone autorizado fica registrado com timestamp, build/commit e correlation id sanitizado.

## Estado por componente

### Hermes

Artefatos de deploy existem em `infra/hermes/`, incluindo imagem fixada por digest, quatro Docker Secrets externos, rede `easypanel-cartorio`, allowlist Photon fail-closed, MCP interno e rollout com rollback. Isso e contrato pronto, nao prova de runtime.

Falta:

- criar `hermes_api_server_key`;
- criar `hermes_llm_api_key`;
- criar `hermes_mcp_cartorio_api_key`;
- criar `hermes_photon_project_secret`;
- definir `HERMES_LLM_BASE_URL`, `HERMES_LLM_MODEL`, `PHOTON_PROJECT_ID`, `PHOTON_ALLOWED_USERS`;
- `docker stack deploy` controlado;
- provar `cartorio_hermes` 1/1;
- provar health interno autenticado;
- provar `tools/list` e uma tool sem PII;
- provar falha controlada do provider.

### API / FastAPI / MCP

Confirmado: API e radar responderam, MCP exige autenticacao e foram observadas 15 tools.

Falta:

- rollout da versao que nao retorna falso `healthy` para Hermes ausente;
- mount read-only de backup para `/health/backup-v2`;
- E2E de tool call vindo de canal real;
- smoke completo apos rollout.

### Redis

Base operacional. Antes do GO final, provar em runtime:

- idempotencia de webhook;
- sliding-window/rate tier;
- circuit breaker do LLM;
- DLQ/backoff;
- comportamento fail-open apenas onde projetado, sem transformar falha de dependencia em resposta enganosa ao cliente.

### Postgres / Supabase

Base e restore isolado foram validados.

Falta:

- sign-off/migration LGPD 0028;
- verificacao da cadeia de auditoria apos migration;
- teste de restore + `audit/verify` no estado final;
- confirmar RLS/Auth/Storage nos fluxos realmente usados pelos canais.

### Chatwoot

Processo/UI saudavel, contrato de API nao certificado por 401 na credencial auditada.

Falta:

- reconciliar credencial no secret manager;
- validar inbox/agente/automacoes;
- Telegram, WhatsApp, iMessage e chat agentico convergirem no CRM conforme arquitetura;
- handoff IA -> humano real;
- retorno humano -> automacao quando permitido;
- garantir que decisao juridica/documental nunca seja auto-aprovada.

### Telegram

Handshake/webhook/fila foram confirmados. Falta E2E humano:

- DM;
- grupo;
- texto;
- erro controlado;
- handoff;
- tool MCP;
- dedupe/replay;
- mensagem longa e concorrencia.

### WhatsApp — Evolution API / Evo-Hub / WA-CLI

Evolution esta online, mas `cartorio-2notas` esta desconectada.

Falta:

- QR pelo telefone oficial;
- `session_connected=true`;
- inbound real -> API/Hermes -> resposta na mesma conversa;
- dedupe de webhook;
- reconnect;
- teste de midia/documento permitido;
- handoff Chatwoot;
- WA-CLI usado apenas como ferramenta de operacao/teste, nao como fonte de verdade paralela.

### Photon / iMessage

Estado atual: nao certificado e com incidente de UX/provider.

Falta:

- projeto/segredo;
- allowlist E.164;
- fail-closed;
- remover qualquer dependencia legada que bypassa Hermes VPS;
- provar transport real sem leak de controle interno;
- provar tool MCP a partir do iMessage;
- provar erro de provider mascarado + retry/backoff/circuit-breaker.

### n8n

Workflows existem e a maioria esta ativa, mas a credencial de observabilidade nao prova execucoes.

Falta:

- credencial read-only;
- export automatico versionado;
- amostra recente de execucoes criticas;
- alerta de workflow falhando;
- evitar que n8n vire segundo orquestrador concorrente do Hermes sem ownership explicito.

### Export CNJ / LGPD

Implementacao nao equivale a homologacao operacional.

Falta:

- migration/sign-off 0028;
- dual control onde aplicavel;
- artefato imutavel;
- teste de export sem PII raw indevida;
- trilha de auditoria e restauracao verificadas no build final.

### Tailscale / SSH

Acesso administrativo esta disponivel.

Gate final:

- bancos/caches nao expostos publicamente;
- SSH por chave;
- acesso limitado;
- scripts bounded/timeout;
- nenhum segredo em shell history/log;
- inventario de portas e ACLs validado.

### MiniMax Coding Plan

A chave de producao nao deve ser escrita em Git, docs, logs, screenshots de diagnostico ou mensagens do bot. Esta auditoria nao replica o valor literal e nao executa rotacao.

Falta provar pelo caminho final:

- endpoint/base URL configurado no secret/runtime;
- modelo aprovado realmente usado;
- uma inferencia sintetica sem PII;
- timeout;
- 429;
- 5xx;
- retry limitado com exponential backoff + jitter;
- circuit breaker;
- resposta neutra/handoff quando indisponivel;
- metrica de latencia/sucesso/erro/circuit-open.

## Ordem de execucao P0

1. Corrigir o caminho iMessage para impedir leak de erro interno imediatamente.
2. Implantar Hermes na VPS com os quatro secrets e provider aprovado.
3. Provar Hermes -> MCP sem PII.
4. Conectar Photon ao Hermes final e repetir E2E iMessage.
5. Parear WhatsApp e provar Evolution E2E.
6. Reconciliar Chatwoot e provar handoff real.
7. Executar Telegram DM/grupo E2E.
8. Fazer rollout do health Hermes correto e backup-v2.
9. Concluir LGPD 0028 + audit verify + restore final.
10. Rodar suite QA completa e smoke remoto.
11. Registrar evidence ledger por canal.
12. Somente entao declarar `REAL_E2E_PASS`.

## Definition of Done

O Cartorio AI so esta 100% quando:

- VPS e a autoridade de runtime;
- Hermes esta 1/1 e autenticado;
- provider aprovado responde e falha de forma controlada;
- MCP tool real funciona por Telegram, WhatsApp e iMessage;
- Chatwoot recebe/escalona os canais;
- WhatsApp esta pareado;
- Telegram DM+grupo passou;
- iMessage nao vaza erro interno;
- backup restaura;
- audit chain valida;
- LGPD/HITL permanecem fail-closed;
- observabilidade detecta desconexao, 429, webhook, workflow e backup vencido;
- nenhuma credencial existe em Git ou logs;
- nenhuma dependencia VAIO/Agent OS existe no projeto.
