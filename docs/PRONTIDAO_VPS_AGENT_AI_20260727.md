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
| MCP | integrado | rejeita acesso sem chave; `initialize`, `tools/list` e chamada pública `cartorio_calcular_emolumento` autenticados retornaram HTTP 200, sem PII. |
| Telegram | handshake confirmado | health do bot, webhook configurado e fila pendente igual a zero. Ainda sem conversa privada/grupo real. |
| n8n | parcialmente integrado | 32 workflows listados, 31 ativos. A chave de auditoria não tem permissão para consultar execuções, portanto não há evidência de sucesso recente dos fluxos. |
| WhatsApp/Evolution | indisponível para atendimento | API Evolution online, porém sessão `cartorio-2notas` fechada/desconectada. |
| Chatwoot | processo saudável, contrato não confirmado | interface e health disponíveis, mas a chave de API local consultada recebeu 401; hand-off e caixa humana não foram certificados. |
| Hermes/iMessage | não implantado na VPS; interação externa observada | preflight de 27/07 bloqueado: rede/Swarm válidos, mas os quatro Docker Secrets Hermes estão ausentes. Capturas de iMessage recebidas em 27/07 mostram respostas cartoriais em outro ambiente e, depois, respostas repetidas de rate limit do provider; não há prova de serviço na VPS nem round-trip Hermes/Photon nela. |
| Backup/recuperação | recuperado com pendências de observabilidade | backup físico novo (37 MB, gzip válido), backup lógico novo, catálogo válido e restore integral em Postgres temporário isolado; monitor local e `/health/backup` voltaram a sucesso. Ainda faltam mount para o endpoint v2 e exportação n8n. |
| Contrato Hermes | pronto para implantação | `docker stack config` renderizou o stack isolado com imagem fixada, rede interna, quatro Docker Secrets externos e allowlist Photon fail-closed. |

## Inventário Cartório-only da VPS

| Componente | Estado atual | Próxima evidência necessária |
| --- | --- | --- |
| FastAPI / MCP | API e radar verdes; MCP autenticado e `tools/list` validado | Rollout controlado do health Hermes corrigido. |
| Redis 8 | online pelo radar e serviço Swarm 1/1 | Validar DLQ/outbox com evento sintético autorizado. |
| Postgres / Supabase | serviço `cartorio_supabase` 1/1; backup físico/lógico e restore isolado válidos | Mount read-only para o health de backup v2. |
| Chatwoot CRM | UI e serviços Chatwoot/Sidekiq 1/1; a própria credencial configurada no `cartorio_api` retorna 401 | Gerar credencial válida no Chatwoot, atualizar o secret manager e provar hand-off humano. O health corrigido no código reportará `degraded` para UI 200 + API 401 após rollout. |
| Telegram | bot/webhook configurados, fila pendente zero | Conversa privada e grupo com resposta e HITL reais. |
| Evolution API / WhatsApp | Evolution online; sessão `cartorio-2notas` fechada | Parear QR e comprovar resposta na mesma conversa. |
| Evo-Hub / WA-CLI | não implantados na VPS do Cartório | Decidir se são necessários; não instalar componentes paralelos sem arquitetura aprovada. |
| Hermes / Photon iMessage | não implantados; nenhum secret Hermes existe. Há evidência visual de resposta em ambiente externo, interrompida por rate limit do provider. | Criar secrets nativos, implantar stack, configurar provider com quota observável e executar round-trip iPhone. |
| n8n | 32 workflows, 31 ativos; snapshot de workflows entra no backup via fallback interno validado | Credencial dedicada de observabilidade com leitura de execuções; a chave exclusiva de backup antiga retorna 401. |
| OpenClaw / chat agêntico | gateway 1/1; `/v1/models` lista 3 modelos com credencial compatível do gateway, mas `OPENCLAW_API_KEY` da API retorna 401 | Alinhar no secret manager a credencial bearer da API com o gateway e fazer rollout controlado; depois executar inferência sintética, fallback e hand-off por canal. |
| Export CNJ | rotas e proteções de exportação no código | Teste autorizado com papel DPO, dataset sintético e auditoria. |
| Tailscale / SSH | Tailscale `Running`; VPS responde por SSH bounded | Revisão periódica de ACLs/chaves sem expor material de acesso. |
| MiniMax Coding Plan | não testado nesta auditoria | Configurar somente no secret manager e executar inferência sintética após autorização de custo. |

## Contratos de código validados nesta rodada

- Chatwoot health: UI acessível e token rejeitado resultam em `degraded`, não
  em falso `online` (`tests/test_chatwoot_endpoints_v6.py`).
- WhatsApp: sessão `close`, resposta sem campo de sessão ou Evolution fora do
  ar nunca são promovidos a estado utilizável
  (`tests/test_whatsapp_session_health_e2.py`).
- Telegram: assinatura, idempotência, scrubbing de PII, debounce, timeout e
  fallback do webhook são cobertos (`tests/test_telegram_webhook_e2e.py`).
- Webhook Chatwoot: HMAC obrigatório coberto
  (`tests/test_webhook_chatwoot_api.py`).
- Provider LLM: se todos os providers responderem HTTP 429, o agente devolve
  mensagem cartorial em PT-BR, oferece `/humano` e registra a métrica
  `provider_rate_limited`; o texto técnico do provider não é encaminhado ao
  cliente (`tests/test_cartorio_agent_g9.py`).

Esses testes certificam contratos de código. Eles não substituem os E2Es com
telefone, usuário autorizado, CRM e provider reais listados neste documento.

## Bloqueios P0 — resolver antes de produção autônoma

| Dono | Ação requerida | Critério de aceite |
| --- | --- | --- |
| Operação WhatsApp | Parear novamente a instância `cartorio-2notas` por QR com o telefone autorizado. | `session_connected=true` e mensagem real autorizada: cliente/telefone → Evolution → API/IA → resposta na mesma conversa. |
| Operação Hermes | Provisionar os quatro Docker Secrets apenas no gerenciador da VPS, aplicar o stack versionado e configurar provider aprovado/Photon allowlist. | `cartorio_hermes` 1/1, health interno autenticado, MCP `tools/list` e uma tool sem PII; nenhuma conexão direta a Postgres/Redis. |
| Operação iMessage | Configurar Photon com projeto/segredo e E.164 autorizados. | iPhone autorizado → Photon → Hermes → resposta no mesmo iPhone, com auditoria sanitizada. |
| Operação de provider | Definir limite, observabilidade e fallback aprovado para o provider do Hermes antes de expor o canal. | Mensagem sintética autorizada responde sem rate limit; quando houver esgotamento, a resposta é uma mensagem cartorial em PT-BR, sem repetição em loop, e há alerta operacional. |
| Chatwoot/atendimento | Rotacionar ou reconciliar a credencial de API no secret manager e conferir o agente/caixa de escalonamento. | Consulta autenticada mínima e hand-off real para humano, sem PII em logs. |

## Pendências P1 — necessárias para governança e operação contínua

| Área | Ação | Critério de aceite |
| --- | --- | --- |
| Backup v2 | Adicionar o mount read-only de `/var/backups/cartorio` ao serviço API em uma janela de rollout controlada. | `/health/backup-v2` saudável, sem expor o conteúdo dos backups. |
| Continuidade | Configurar cópia offsite criptografada dos backups para bucket aprovado. A VPS não possui CLI, arquivo de credencial nem configuração de bucket para essa rotina. | Upload de backup novo, checksum remoto, restore drill a partir da cópia offsite e retenção documentada. |
| API | Fazer rollout controlado do backend com o novo health Hermes. A versão pública ainda retorna um falso `healthy` embora não exista serviço Hermes na VPS. | Sem `HERMES_API_URL`, `/agent-hermes/status` retorna `not_deployed`; com URL configurada, o endpoint prova `/health` antes de retornar `healthy`. |
| n8n | Criar credencial dedicada de observabilidade, com leitura de workflows/execuções, e aposentar a chave exclusiva de backup que retorna 401. | Exportação de workflows no backup e auditoria de execuções funcionam sem poder alterar/rodar workflow; amostra das rotas críticas recente e bem-sucedida. |
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

O script versionado `infra/backup/cartorio-offsite-sync.sh` está pronto para
esse gate e falha fechado até receber `AWS_S3_BUCKET`, `AWS_REGION` e
credenciais exclusivamente pelo ambiente seguro da VPS.

Para reexecutar o diagnóstico somente leitura na VPS, use
`infra/scripts/cartorio-vps-readiness.sh`. Ele não imprime segredos e retorna
`CARTORIO_VPS_READINESS=PASS` somente quando todos os contratos verificados
estiverem íntegros, incluindo serviços, backup, Chatwoot, n8n, WhatsApp,
OpenClaw e os secrets Hermes.

Não fazer deploy em massa, reinício de serviços existentes ou teste com dados
reais de clientes para resolver estas pendências.
