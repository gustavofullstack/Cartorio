# Estado Runtime — 2026-07-19

> **Snapshot canônico de runtime em 2026-07-19.** Este documento substitui, para
> decisão operacional corrente, as afirmações de disponibilidade em
> `CANAL_HEALTH_MATRIX.md` (16/07) e `INTEGRATION_MATRIX_G7.md` (17/07). Os dois
> permanecem como registros históricos de suas respectivas sondagens.
>
> Não contém segredos, tokens, cabeçalhos de autenticação, dados de atendimento ou
> identificadores de pessoas. “Confirmado” significa somente que a rota indicada
> respondeu na sondagem desta data; não é uma aprovação de go-live nem prova de
> fluxo de negócio ponta a ponta.

## Fonte e limites da evidência

Sondagem HTTP/DNS/TLS externa realizada em 2026-07-19, complementada por testes
locais de contrato. Rotas autenticadas foram avaliadas apenas quanto à barreira de
acesso, sem registrar ou utilizar credenciais. A versão exposta pela API pública
permanece `0.5.4`; por isso, funcionalidades entregues localmente após essa imagem
não são consideradas publicadas em produção.

| Legenda | Critério |
|---|---|
| **Confirmado** | Resposta observada nesta data, no endpoint público indicado. |
| **Parcial** | A camada respondeu, mas falta uma condição para uso integrado. |
| **Não verificado** | Não houve evidência de execução ponta a ponta nesta sondagem. |
| **Bloqueado** | Há falha concreta ou alteração externa necessária. |

## Matriz de estado atual

| Domínio | Estado | Evidência de 19/07 | Limite / próximo validador |
|---|---|---|---|
| FastAPI público | **Confirmado** | `/health`, `/ready` e `/api/v1/health/radar` responderam `200`. | API pública ainda expõe `0.5.4`; realizar deploy aprovado e repetir smoke antes de atribuir rotas novas à produção. |
| Postgres/Supabase e Redis | **Confirmado via radar** | Radar público reportou ambos online. | Não substitui migration online nem teste de restauração. |
| N8N | **Confirmado** | `/healthz` respondeu `200`. | Executar workflow de teste autenticado e auditar execução; health não prova integração. |
| Evolution API | **Confirmado** | Endpoint raiz respondeu `200`. | Validar instância, webhook assinado e fluxo WhatsApp com caso controlado. |
| Chatwoot | **Confirmado** | Endpoint raiz respondeu `200`. | Validar handoff autenticado e correlação com Atendimento sem PII. |
| OpenClaw | **Parcial** | `/health` respondeu `200`; `/v1/models` recusou sem token (`401`), como esperado. | Criar token de operador com escopo mínimo e validar fluxo autenticado. |
| OpenClaw CORS | **Bloqueado** | `OPTIONS` para endpoints da API retornou `405` sem cabeçalhos CORS. | Ajustar CORS no serviço/proxy sob mudança aprovada e repetir preflight. |
| LobeChat serviço interno | **Parcial** | Endpoint EasyPanel `/chat` respondeu `200`. | Não prova o hostname público nem a integração com OpenClaw. |
| LobeChat público | **Bloqueado** | `lobe.2notasudi.com.br` retornou `NXDOMAIN`; SNI forçado apresentou certificado autoassinado. | Criar DNS/rota Traefik e certificado válido; revalidar DNS + TLS + UI. |
| DNS/TLS dos domínios principais | **Confirmado, exceto LobeChat** | Domínios principais resolveram para o endereço de produção e apresentaram TLS válido na sondagem. | Manter monitor de expiração; LobeChat continua exceção explícita. |
| Telegram | **Não verificado** | Sem prova de `getWebhookInfo` ou entrega ponta a ponta nesta data. | Registrar webhook por canal seguro e executar cenário de teste sem dados reais. |
| Webhooks (Telegram/Evolution/Chatwoot) | **Não verificado** | Há testes locais e contratos; não houve entrega externa E2E nesta sondagem. | Validar assinatura, idempotência e handoff em ambiente controlado. |
| WebSocket de atendimentos | **Não verificado** | Cobertura local existe; não houve handshake WSS público registrado. | Executar smoke autenticado via proxy e validar fechamento/erros. |
| MCP montado na API | **Não verificado** | Servidor e testes locais existem; o mount público não foi comprovado. | Rodar cliente MCP autenticado após deploy da imagem atual. |
| Swagger/OpenAPI e Postman | **Confirmado localmente** | Gate semântico OpenAPI, referências e coleção Postman passaram no repositório. | A especificação publicada depende do deploy da API atual. |
| Exportação CNJ | **Confirmado localmente** | Testes de autorização e aprovação independente passaram. | A imagem pública `0.5.4` não prova que as rotas CNJ estejam implantadas. |
| OpenCode Zen / fallback | **Não verificado em runtime** | Configuração e testes locais existem; nenhuma conta foi exercitada nesta sondagem. | Injetar credenciais exclusivamente pelo gerenciador de segredos e testar sem PII, após aprovação operacional. |
| Tailscale/SSH | **Não verificado** | Não houve nova sondagem nesta data. | Executar checagem de ACL/conectividade a partir de operador autorizado. |

## Resultado de prontidão

O núcleo de infraestrutura observado está acessível, mas **não há evidência para
declarar o sistema 100% integrado ou pronto para go-live**. Os bloqueios objetivos
são DNS/TLS do LobeChat e CORS do OpenClaw. Além deles, Telegram, webhooks,
WebSocket, MCP, Tailscale, fluxos autenticados e a publicação da imagem atual
precisam de validação E2E.

## Sequência curta de revalidação

1. Corrigir DNS, Traefik/TLS do LobeChat e CORS do OpenClaw por mudança revisada.
2. Publicar a imagem de API aprovada e confirmar versão/rotas com smoke externo.
3. Executar E2E controlado: Telegram, Evolution, Chatwoot handoff, WebSocket e MCP.
4. Executar migration online e exportação CNJ em ambiente autorizado, com aprovação
   independente e logs sem PII.
5. Atualizar **este** snapshot com data, comando e resultado; não editar snapshots
   históricos para simular uma nova sondagem.

**Atualizado por equipe de integração — 2026-07-19**
