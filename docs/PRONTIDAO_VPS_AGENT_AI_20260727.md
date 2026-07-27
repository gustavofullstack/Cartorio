# Prontidão da VPS — Agent AI Cartório

**Data da evidência:** 27/07/2026. Este documento separa processo saudável,
integração autenticada e aceitação real por canal. Nenhuma credencial, dado de
cliente ou conteúdo de conversa foi usado ou registrado nesta auditoria.

## Veredito

`BASE_OPERACIONAL_PARCIAL — NÃO PRONTO PARA DECLARAR 100% FUNCIONAL`.

A base de serviços está disponível, mas há bloqueios de recuperação, canais e
agente. Um HTTP 200, container 1/1 ou webhook configurado não equivale a uma
conversa atendida de ponta a ponta.

## Evidências confirmadas

| Área | Estado | Evidência segura |
| --- | --- | --- |
| Infraestrutura | verde | API, Supabase/Postgres, Redis, n8n, Evolution, Chatwoot e OpenClaw em execução; sem container unhealthy/restarting observado. |
| Capacidade | verde | VPS com aproximadamente 11 GiB livres de memória e 165 GiB livres em disco no momento da coleta. |
| API/radar | verde | `/api/v1/health/radar` e `/api/v1/health/integracoes` retornaram verde; os conectores declarados estavam online. |
| MCP | integrado | rejeita acesso sem chave; `initialize` e `tools/list` autenticados retornaram HTTP 200 e 15 ferramentas. |
| Telegram | handshake confirmado | health do bot, webhook configurado e fila pendente igual a zero. Ainda sem conversa privada/grupo real. |
| n8n | parcialmente integrado | 32 workflows listados, 31 ativos. A chave de auditoria não tem permissão para consultar execuções, portanto não há evidência de sucesso recente dos fluxos. |
| WhatsApp/Evolution | indisponível para atendimento | API Evolution online, porém sessão `cartorio-2notas` fechada/desconectada. |
| Chatwoot | processo saudável, contrato não confirmado | interface e health disponíveis, mas a chave de API local consultada recebeu 401; hand-off e caixa humana não foram certificados. |
| Hermes/iMessage | não implantado | nenhum serviço Hermes ou segredo Hermes foi encontrado na VPS; não há round-trip iPhone. |
| Backup/recuperação | recuperado com pendências de observabilidade | backup físico novo (37 MB, gzip válido), backup lógico novo, catálogo válido e restore integral em Postgres temporário isolado; monitor local e `/health/backup` voltaram a sucesso. Ainda faltam mount para o endpoint v2 e exportação n8n. |
| Contrato Hermes | pronto para implantação | `docker stack config` renderizou o stack isolado com imagem fixada, rede interna, quatro Docker Secrets externos e allowlist Photon fail-closed. |

## Bloqueios P0 — resolver antes de produção autônoma

| Dono | Ação requerida | Critério de aceite |
| --- | --- | --- |
| Operação WhatsApp | Parear novamente a instância `cartorio-2notas` por QR com o telefone autorizado. | `session_connected=true` e mensagem real autorizada: cliente/telefone → Evolution → API/IA → resposta na mesma conversa. |
| Operação Hermes | Provisionar os quatro Docker Secrets apenas no gerenciador da VPS, aplicar o stack versionado e configurar provider aprovado/Photon allowlist. | `cartorio_hermes` 1/1, health interno autenticado, MCP `tools/list` e uma tool sem PII; nenhuma conexão direta a Postgres/Redis. |
| Operação iMessage | Configurar Photon com projeto/segredo e E.164 autorizados. | iPhone autorizado → Photon → Hermes → resposta no mesmo iPhone, com auditoria sanitizada. |
| Chatwoot/atendimento | Rotacionar ou reconciliar a credencial de API no secret manager e conferir o agente/caixa de escalonamento. | Consulta autenticada mínima e hand-off real para humano, sem PII em logs. |

## Pendências P1 — necessárias para governança e operação contínua

| Área | Ação | Critério de aceite |
| --- | --- | --- |
| Backup v2 | Adicionar o mount read-only de `/var/backups/cartorio` ao serviço API em uma janela de rollout controlada. | `/health/backup-v2` saudável, sem expor o conteúdo dos backups. |
| API | Fazer rollout controlado do backend com o novo health Hermes. A versão pública ainda retorna um falso `healthy` embora não exista serviço Hermes na VPS. | Sem `HERMES_API_URL`, `/agent-hermes/status` retorna `not_deployed`; com URL configurada, o endpoint prova `/health` antes de retornar `healthy`. |
| n8n | Rotacionar a chave em `/etc/cartorio-backup/n8n-api-key.env`, que hoje recebe 401, e conceder à credencial de observabilidade apenas leitura de workflows/execuções. | Exportação de workflows no backup e auditoria de execuções funcionam sem poder alterar/rodar workflow; amostra das rotas críticas recente e bem-sucedida. |
| Telegram | Executar os cenários de conversa privada e grupo descritos no guia E2E. | Webhook → modelo → resposta Telegram comprovado em cada cenário, incluindo erro controlado e HITL. |
| IA/provider | Testar inferência com mensagem sintética e sem PII após aprovação de custo. | Resposta do modelo, timeout/falha controlada, logs sanitizados e nenhuma decisão jurídica automática. |
| Segredos | Normalizar o arquivo local de referências para formato não executável e manter valores somente no gestor de segredos. | Validação de sintaxe, scanner de segredos verde e nenhuma chave em repositório/log. |
| Observabilidade | Criar alertas acionáveis para backup vencido, WhatsApp desconectado, webhook com falha e erro de workflow. | Alerta entregue a responsável e teste de disparo/recuperação registrado. |

## Aceite final obrigatório

Só mudar o estado para `REAL_E2E_PASS` quando todos os itens abaixo tiverem
registro de evidência, com dados sintéticos ou consentidos:

1. Backup restaurável e monitor verde.
2. Hermes e Photon implantados de forma isolada e fail-closed.
3. MCP autenticado, com ferramenta permitida executada sem PII.
4. Telegram privado e grupo: entrada, IA, resposta e fallback/HITL.
5. WhatsApp: pareamento e resposta na mesma conversa autorizada.
6. Chatwoot: hand-off humano real e retorno ao atendimento quando aplicável.
7. Logs/auditoria sem PII raw; protocolo continua `DRAFT` até validação humana.

## Sequência segura de execução

1. Recuperar backup e provar restauração antes de tocar nos canais.
2. Restabelecer WhatsApp e o acesso mínimo do Chatwoot.
3. Implantar Hermes como serviço novo pelos artefatos em `infra/hermes/`.
4. Executar E2E de cada canal em janela controlada, um por vez.
5. Registrar somente resultado, horário, versão e identificador sanitizado da evidência.

Não fazer deploy em massa, reinício de serviços existentes ou teste com dados
reais de clientes para resolver estas pendências.
