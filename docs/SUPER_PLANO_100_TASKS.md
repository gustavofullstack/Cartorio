# SUPER PLANO 100 TASKS - CARTÓRIO BOT

## N8N_ORCHESTRATION
_Otimização e testes dos workflows do N8N como hub central_

- [ ] **TSK-001**: Auditar e validar todos os workflows existentes no N8N para garantir fluxo bidirecional (Prioridade: HIGH)
  - Executar a tarefa descrita focada em melhoria do subsistema N8N_ORCHESTRATION para elevar confiabilidade, estabilidade ou performance.
- [ ] **TSK-002**: Implementar tratamento de erros (Error Trigger) global nos workflows do N8N (Prioridade: HIGH)
  - Executar a tarefa descrita focada em melhoria do subsistema N8N_ORCHESTRATION para elevar confiabilidade, estabilidade ou performance.
- [ ] **TSK-003**: Migrar credenciais em texto plano nos nós N8N para uso centralizado via N8N Credentials (Prioridade: HIGH)
  - Executar a tarefa descrita focada em melhoria do subsistema N8N_ORCHESTRATION para elevar confiabilidade, estabilidade ou performance.
- [ ] **TSK-004**: Implementar nó N8N para gerenciar timeout entre respostas lentas da API ou Supabase (Prioridade: MEDIUM)
  - Executar a tarefa descrita focada em melhoria do subsistema N8N_ORCHESTRATION para elevar confiabilidade, estabilidade ou performance.
- [ ] **TSK-005**: Configurar cache no nó HTTP Request do N8N para reduzir acessos redundantes à API (Prioridade: MEDIUM)
  - Executar a tarefa descrita focada em melhoria do subsistema N8N_ORCHESTRATION para elevar confiabilidade, estabilidade ou performance.
- [ ] **TSK-006**: Testar resiliência com N8N Queue Mode (Workers) configurado em alta disponibilidade (Prioridade: MEDIUM)
  - Executar a tarefa descrita focada em melhoria do subsistema N8N_ORCHESTRATION para elevar confiabilidade, estabilidade ou performance.
- [ ] **TSK-007**: Padronizar o JSON de saída de todos os sub-workflows para manter o contrato da API (Prioridade: MEDIUM)
  - Executar a tarefa descrita focada em melhoria do subsistema N8N_ORCHESTRATION para elevar confiabilidade, estabilidade ou performance.
- [ ] **TSK-008**: Otimizar logs e execução de histórico no N8N para economizar banco de dados (Prioridade: MEDIUM)
  - Executar a tarefa descrita focada em melhoria do subsistema N8N_ORCHESTRATION para elevar confiabilidade, estabilidade ou performance.
- [ ] **TSK-009**: Criar workflow N8N de monitoramento (ping diário) nos Endpoints de saúde da infraestrutura (Prioridade: MEDIUM)
  - Executar a tarefa descrita focada em melhoria do subsistema N8N_ORCHESTRATION para elevar confiabilidade, estabilidade ou performance.
- [ ] **TSK-010**: Remodelar sub-workflows complexos com Merge nodes para otimizar processamento paralelo (Prioridade: HIGH)
  - Executar a tarefa descrita focada em melhoria do subsistema N8N_ORCHESTRATION para elevar confiabilidade, estabilidade ou performance.

## API_ENHANCEMENTS
_Melhorias na API para integração completa e resiliência_

- [ ] **TSK-011**: Criar endpoints dedicados na API para Health Check aprimorado e Métricas Prometheus (Prioridade: HIGH)
  - Executar a tarefa descrita focada em melhoria do subsistema API_ENHANCEMENTS para elevar confiabilidade, estabilidade ou performance.
- [ ] **TSK-012**: Implementar rate limiting via Redis para todos os endpoints da API pública (Prioridade: HIGH)
  - Executar a tarefa descrita focada em melhoria do subsistema API_ENHANCEMENTS para elevar confiabilidade, estabilidade ou performance.
- [ ] **TSK-013**: Refatorar estrutura de dependências (deps) em Pydantic PII serializers (Prioridade: HIGH)
  - Executar a tarefa descrita focada em melhoria do subsistema API_ENHANCEMENTS para elevar confiabilidade, estabilidade ou performance.
- [ ] **TSK-014**: Assegurar que todas as rotas validam Authorization tokens de maneira constant-time (Prioridade: MEDIUM)
  - Executar a tarefa descrita focada em melhoria do subsistema API_ENHANCEMENTS para elevar confiabilidade, estabilidade ou performance.
- [ ] **TSK-015**: Revisar manipulação de exceptions globais FastAPI, retornando respostas consistentes Pydantic (Prioridade: MEDIUM)
  - Executar a tarefa descrita focada em melhoria do subsistema API_ENHANCEMENTS para elevar confiabilidade, estabilidade ou performance.
- [ ] **TSK-016**: Otimizar o FastAPI Gunicorn workers e concorrência para reduzir picos de latência (Prioridade: MEDIUM)
  - Executar a tarefa descrita focada em melhoria do subsistema API_ENHANCEMENTS para elevar confiabilidade, estabilidade ou performance.
- [ ] **TSK-017**: Adicionar auditoria de requests sensíveis nos Controllers da API (gravar em DB) (Prioridade: MEDIUM)
  - Executar a tarefa descrita focada em melhoria do subsistema API_ENHANCEMENTS para elevar confiabilidade, estabilidade ou performance.
- [ ] **TSK-018**: Isolar lógica de Chatwoot Webhooks em Router próprio na API, fora das rotas Genéricas (Prioridade: MEDIUM)
  - Executar a tarefa descrita focada em melhoria do subsistema API_ENHANCEMENTS para elevar confiabilidade, estabilidade ou performance.
- [ ] **TSK-019**: Implementar teste de contrato (Contract Testing) na rota de cálculo de Emolumentos (Prioridade: MEDIUM)
  - Executar a tarefa descrita focada em melhoria do subsistema API_ENHANCEMENTS para elevar confiabilidade, estabilidade ou performance.
- [ ] **TSK-020**: Melhorar a serialização de Timestamp/Timezones nas respostas JSON da API (Prioridade: HIGH)
  - Executar a tarefa descrita focada em melhoria do subsistema API_ENHANCEMENTS para elevar confiabilidade, estabilidade ou performance.

## SUPABASE_FULL_USAGE
_Utilização profunda do Supabase (Cron, Webhooks, Vault, GraphQL, Queues)_

- [ ] **TSK-021**: Configurar Database Webhooks no Supabase para sincronização em tempo real de protocolos (Prioridade: HIGH)
  - Executar a tarefa descrita focada em melhoria do subsistema SUPABASE_FULL_USAGE para elevar confiabilidade, estabilidade ou performance.
- [ ] **TSK-022**: Migrar armazenamento de chaves sensíveis obsoletas para o Supabase Vault (Prioridade: HIGH)
  - Executar a tarefa descrita focada em melhoria do subsistema SUPABASE_FULL_USAGE para elevar confiabilidade, estabilidade ou performance.
- [ ] **TSK-023**: Criar rotinas no Supabase Cron (pg_cron) para limpeza de logs antigos > 30 dias (Prioridade: HIGH)
  - Executar a tarefa descrita focada em melhoria do subsistema SUPABASE_FULL_USAGE para elevar confiabilidade, estabilidade ou performance.
- [ ] **TSK-024**: Implementar Supabase Queues com pgmq para fila de mensagens assíncronas (Prioridade: MEDIUM)
  - Executar a tarefa descrita focada em melhoria do subsistema SUPABASE_FULL_USAGE para elevar confiabilidade, estabilidade ou performance.
- [ ] **TSK-025**: Estabelecer políticas RLS (Row Level Security) sólidas em todas as tabelas expostas (Prioridade: MEDIUM)
  - Executar a tarefa descrita focada em melhoria do subsistema SUPABASE_FULL_USAGE para elevar confiabilidade, estabilidade ou performance.
- [ ] **TSK-026**: Otimizar índices B-Tree no PostgreSQL para queries do dashboard em `protocolos` (Prioridade: MEDIUM)
  - Executar a tarefa descrita focada em melhoria do subsistema SUPABASE_FULL_USAGE para elevar confiabilidade, estabilidade ou performance.
- [ ] **TSK-027**: Configurar replicação read-only no Supabase para aliviar a carga das queries analíticas (Prioridade: MEDIUM)
  - Executar a tarefa descrita focada em melhoria do subsistema SUPABASE_FULL_USAGE para elevar confiabilidade, estabilidade ou performance.
- [ ] **TSK-028**: Testar e ativar PostgREST limit configurations e max_rows nas respostas nativas (Prioridade: MEDIUM)
  - Executar a tarefa descrita focada em melhoria do subsistema SUPABASE_FULL_USAGE para elevar confiabilidade, estabilidade ou performance.
- [ ] **TSK-029**: Implementar migrations controladas no ambiente Dev e Prod (Prioridade: MEDIUM)
  - Executar a tarefa descrita focada em melhoria do subsistema SUPABASE_FULL_USAGE para elevar confiabilidade, estabilidade ou performance.
- [ ] **TSK-030**: Ativar Supabase Storage para lidar com uploads/anexos temporários recebidos pelo WhatsApp (Prioridade: HIGH)
  - Executar a tarefa descrita focada em melhoria do subsistema SUPABASE_FULL_USAGE para elevar confiabilidade, estabilidade ou performance.

## CHATWOOT_CRM
_Melhorias no Chatwoot para HITL, CRM e automação de atendimento_

- [ ] **TSK-031**: Configurar Chatwoot Sidekiq para alta disponibilidade de jobs e Background Workers (Prioridade: HIGH)
  - Executar a tarefa descrita focada em melhoria do subsistema CHATWOOT_CRM para elevar confiabilidade, estabilidade ou performance.
- [ ] **TSK-032**: Implementar automação de Hand-off (HITL) no Chatwoot via regra de roteamento (Prioridade: HIGH)
  - Executar a tarefa descrita focada em melhoria do subsistema CHATWOOT_CRM para elevar confiabilidade, estabilidade ou performance.
- [ ] **TSK-033**: Adicionar Tags automáticas baseadas em Intent do bot via OpenClaw/Chatwoot API (Prioridade: HIGH)
  - Executar a tarefa descrita focada em melhoria do subsistema CHATWOOT_CRM para elevar confiabilidade, estabilidade ou performance.
- [ ] **TSK-034**: Sincronizar a inatividade de agente humano do Chatwoot para retornar controle ao Bot (Prioridade: MEDIUM)
  - Executar a tarefa descrita focada em melhoria do subsistema CHATWOOT_CRM para elevar confiabilidade, estabilidade ou performance.
- [ ] **TSK-035**: Revisar webhooks Chatwoot (Inbound e Outbound) para tratar conversas como JSON robusto (Prioridade: MEDIUM)
  - Executar a tarefa descrita focada em melhoria do subsistema CHATWOOT_CRM para elevar confiabilidade, estabilidade ou performance.
- [ ] **TSK-036**: Otimizar performance de carregamento no Painel Chatwoot rodando na VPS (Prioridade: MEDIUM)
  - Executar a tarefa descrita focada em melhoria do subsistema CHATWOOT_CRM para elevar confiabilidade, estabilidade ou performance.
- [ ] **TSK-037**: Testar fallback visual e avisos sonoros de Notification Server do Chatwoot (Prioridade: MEDIUM)
  - Executar a tarefa descrita focada em melhoria do subsistema CHATWOOT_CRM para elevar confiabilidade, estabilidade ou performance.
- [ ] **TSK-038**: Implementar Macros do Chatwoot para encerramento padrão e pesquisa de satisfação CSAT (Prioridade: MEDIUM)
  - Executar a tarefa descrita focada em melhoria do subsistema CHATWOOT_CRM para elevar confiabilidade, estabilidade ou performance.
- [ ] **TSK-039**: Personalizar as Inbox e Widgets do Chatwoot para identificar Evolution-API claramente (Prioridade: MEDIUM)
  - Executar a tarefa descrita focada em melhoria do subsistema CHATWOOT_CRM para elevar confiabilidade, estabilidade ou performance.
- [ ] **TSK-040**: Adicionar scripts para limpeza agendada de anexos pesados de conversas expiradas (Prioridade: HIGH)
  - Executar a tarefa descrita focada em melhoria do subsistema CHATWOOT_CRM para elevar confiabilidade, estabilidade ou performance.

## EVOLUTION_API
_Aperfeiçoamento da integração WhatsApp via Evolution-API_

- [ ] **TSK-041**: Configurar Webhooks do Evolution-API para recebimento de mensagens na API central (Prioridade: HIGH)
  - Executar a tarefa descrita focada em melhoria do subsistema EVOLUTION_API para elevar confiabilidade, estabilidade ou performance.
- [ ] **TSK-042**: Tratar status de entrega de mensagem do Evolution (Read Receipts, Delivered) (Prioridade: HIGH)
  - Executar a tarefa descrita focada em melhoria do subsistema EVOLUTION_API para elevar confiabilidade, estabilidade ou performance.
- [ ] **TSK-043**: Otimizar tratativa de medias Inbound (imagens/áudios) convertendo-os no N8N/API (Prioridade: HIGH)
  - Executar a tarefa descrita focada em melhoria do subsistema EVOLUTION_API para elevar confiabilidade, estabilidade ou performance.
- [ ] **TSK-044**: Criar rotina de Heartbeat pro Evolution API e auto-reconnect do Socket do WhatsApp (Prioridade: MEDIUM)
  - Executar a tarefa descrita focada em melhoria do subsistema EVOLUTION_API para elevar confiabilidade, estabilidade ou performance.
- [ ] **TSK-045**: Implementar Rate Limiter no disparo em lote no Evolution-API para evitar banimentos de conta (Prioridade: MEDIUM)
  - Executar a tarefa descrita focada em melhoria do subsistema EVOLUTION_API para elevar confiabilidade, estabilidade ou performance.
- [ ] **TSK-046**: Validar o fluxo Inbound/Outbound do Chatwoot + Evolution-API Inbox Channel (Prioridade: MEDIUM)
  - Executar a tarefa descrita focada em melhoria do subsistema EVOLUTION_API para elevar confiabilidade, estabilidade ou performance.
- [ ] **TSK-047**: Revisar persistência do Session ID e tokenização no Redis (Prioridade: MEDIUM)
  - Executar a tarefa descrita focada em melhoria do subsistema EVOLUTION_API para elevar confiabilidade, estabilidade ou performance.
- [ ] **TSK-048**: Configurar auto-limpeza de cache de mídias baixadas temporariamente no Evolution-API (Prioridade: MEDIUM)
  - Executar a tarefa descrita focada em melhoria do subsistema EVOLUTION_API para elevar confiabilidade, estabilidade ou performance.
- [ ] **TSK-049**: Fazer deploy e testes rigorosos da fila RabbitMQ/Redis integrada no Evolution-API (Prioridade: MEDIUM)
  - Executar a tarefa descrita focada em melhoria do subsistema EVOLUTION_API para elevar confiabilidade, estabilidade ou performance.
- [ ] **TSK-050**: Testar envio dinâmico de botões interativos e Message Templates pelo WhatsApp (Prioridade: HIGH)
  - Executar a tarefa descrita focada em melhoria do subsistema EVOLUTION_API para elevar confiabilidade, estabilidade ou performance.

## REDIS_STATE_MEMORY
_Gestão de estado, cache rápido e sessões via Redis_

- [ ] **TSK-051**: Mapear a hierarquia de chaves (Key Space) no Redis para Sessões do WhatsApp e Bot (Prioridade: HIGH)
  - Executar a tarefa descrita focada em melhoria do subsistema REDIS_STATE_MEMORY para elevar confiabilidade, estabilidade ou performance.
- [ ] **TSK-052**: Definir políticas de TTL automáticas (Eviction) para não esgotar a RAM da VPS (Prioridade: HIGH)
  - Executar a tarefa descrita focada em melhoria do subsistema REDIS_STATE_MEMORY para elevar confiabilidade, estabilidade ou performance.
- [ ] **TSK-053**: Implementar Redis Lock (Redlock) para evitar concorrência em scripts de geração de protocolo (Prioridade: HIGH)
  - Executar a tarefa descrita focada em melhoria do subsistema REDIS_STATE_MEMORY para elevar confiabilidade, estabilidade ou performance.
- [ ] **TSK-054**: Mover histórico recente de conversas para lista Redis antes da inserção em batch no DB (Prioridade: MEDIUM)
  - Executar a tarefa descrita focada em melhoria do subsistema REDIS_STATE_MEMORY para elevar confiabilidade, estabilidade ou performance.
- [ ] **TSK-055**: Otimizar o Redis Persistence (AOF / RDB) para segurança sem matar performance de IO (Prioridade: MEDIUM)
  - Executar a tarefa descrita focada em melhoria do subsistema REDIS_STATE_MEMORY para elevar confiabilidade, estabilidade ou performance.
- [ ] **TSK-056**: Usar Hashes do Redis em vez de Strings serializadas JSON para sessão de usuários (Prioridade: MEDIUM)
  - Executar a tarefa descrita focada em melhoria do subsistema REDIS_STATE_MEMORY para elevar confiabilidade, estabilidade ou performance.
- [ ] **TSK-057**: Implementar alertas de alto consumo de Memória no Redis (Prioridade: MEDIUM)
  - Executar a tarefa descrita focada em melhoria do subsistema REDIS_STATE_MEMORY para elevar confiabilidade, estabilidade ou performance.
- [ ] **TSK-058**: Estruturar cache de Respostas Comuns e FAQs estáticas sem acessar DB principal (Prioridade: MEDIUM)
  - Executar a tarefa descrita focada em melhoria do subsistema REDIS_STATE_MEMORY para elevar confiabilidade, estabilidade ou performance.
- [ ] **TSK-059**: Separar namespaces para ambientes diferentes ou multi-inbox no Chatwoot (Prioridade: MEDIUM)
  - Executar a tarefa descrita focada em melhoria do subsistema REDIS_STATE_MEMORY para elevar confiabilidade, estabilidade ou performance.
- [ ] **TSK-060**: Otimizar Redis Pub/Sub usado entre FastMCP, Gateway e OpenClaw (Prioridade: HIGH)
  - Executar a tarefa descrita focada em melhoria do subsistema REDIS_STATE_MEMORY para elevar confiabilidade, estabilidade ou performance.

## OPENCLAW_AGENT
_Tuning fino do Agent AI Cartório, prompts, tools, hooks_

- [ ] **TSK-061**: Testar a skill 'pii_scrubber' do OpenClaw com payloads reais do WhatsApp (CPF/RG) (Prioridade: HIGH)
  - Executar a tarefa descrita focada em melhoria do subsistema OPENCLAW_AGENT para elevar confiabilidade, estabilidade ou performance.
- [ ] **TSK-062**: Validar limits do context_window e o uso de thinking via deepseek-v4-flash (Prioridade: HIGH)
  - Executar a tarefa descrita focada em melhoria do subsistema OPENCLAW_AGENT para elevar confiabilidade, estabilidade ou performance.
- [ ] **TSK-063**: Enriquecer o System Prompt com regras e exemplos few-shot de respostas de cálculo de Emolumentos (Prioridade: HIGH)
  - Executar a tarefa descrita focada em melhoria do subsistema OPENCLAW_AGENT para elevar confiabilidade, estabilidade ou performance.
- [ ] **TSK-064**: Refinar as Tools do OpenClaw (consultar_emolumento) adicionando schemas JSON robustos (Prioridade: MEDIUM)
  - Executar a tarefa descrita focada em melhoria do subsistema OPENCLAW_AGENT para elevar confiabilidade, estabilidade ou performance.
- [ ] **TSK-065**: Otimizar os hooks de on_message_in e on_response_out para auditar Logs sem delay excessivo (Prioridade: MEDIUM)
  - Executar a tarefa descrita focada em melhoria do subsistema OPENCLAW_AGENT para elevar confiabilidade, estabilidade ou performance.
- [ ] **TSK-066**: Adicionar Tool específica para handoff explícito de atendente humano ao OpenClaw (Prioridade: MEDIUM)
  - Executar a tarefa descrita focada em melhoria do subsistema OPENCLAW_AGENT para elevar confiabilidade, estabilidade ou performance.
- [ ] **TSK-067**: Validar e simular comportamento de erro via hook on_error (Dead Man Switch) (Prioridade: MEDIUM)
  - Executar a tarefa descrita focada em melhoria do subsistema OPENCLAW_AGENT para elevar confiabilidade, estabilidade ou performance.
- [ ] **TSK-068**: Melhorar a conexão Websocket do endpoint do Agente e testes de auto-recover (Prioridade: MEDIUM)
  - Executar a tarefa descrita focada em melhoria do subsistema OPENCLAW_AGENT para elevar confiabilidade, estabilidade ou performance.
- [ ] **TSK-069**: Limitar temperatura e token outputs baseados na task usando LLM Router Config (Prioridade: MEDIUM)
  - Executar a tarefa descrita focada em melhoria do subsistema OPENCLAW_AGENT para elevar confiabilidade, estabilidade ou performance.
- [ ] **TSK-070**: Verificar fluxo de consentimento LGPD antes da extração de dados PII pelo Agente (Prioridade: HIGH)
  - Executar a tarefa descrita focada em melhoria do subsistema OPENCLAW_AGENT para elevar confiabilidade, estabilidade ou performance.

## TESTING_QA
_Testes end-to-end, testes unitários, testes de integração, cobertura_

- [ ] **TSK-071**: Expandir testes E2E do fluxo Inbound Início: WhatsApp -> OpenClaw -> Supabase (Prioridade: HIGH)
  - Executar a tarefa descrita focada em melhoria do subsistema TESTING_QA para elevar confiabilidade, estabilidade ou performance.
- [ ] **TSK-072**: Criar testes unitários para o N8N Workflow Executor (mocks de chamadas HTTP) (Prioridade: HIGH)
  - Executar a tarefa descrita focada em melhoria do subsistema TESTING_QA para elevar confiabilidade, estabilidade ou performance.
- [ ] **TSK-073**: Adicionar testes unitários rigorosos na camada de Sanitização de PII (CPF/RG/Tel) (Prioridade: HIGH)
  - Executar a tarefa descrita focada em melhoria do subsistema TESTING_QA para elevar confiabilidade, estabilidade ou performance.
- [ ] **TSK-074**: Validar cálculo de Emolumentos comparando as faixas com Tabela Oficial via Pytest (Prioridade: MEDIUM)
  - Executar a tarefa descrita focada em melhoria do subsistema TESTING_QA para elevar confiabilidade, estabilidade ou performance.
- [ ] **TSK-075**: Implementar testes de carga (Load Testing) simples na API e N8N com Locust (Prioridade: MEDIUM)
  - Executar a tarefa descrita focada em melhoria do subsistema TESTING_QA para elevar confiabilidade, estabilidade ou performance.
- [ ] **TSK-076**: Integrar verificação estática rigorosa no pre-commit para Pydantic 2.x incompatibilities (Prioridade: MEDIUM)
  - Executar a tarefa descrita focada em melhoria do subsistema TESTING_QA para elevar confiabilidade, estabilidade ou performance.
- [ ] **TSK-077**: Garantir 100% test coverage na camada de Criptografia HMAC e Validações Seguras (Prioridade: MEDIUM)
  - Executar a tarefa descrita focada em melhoria do subsistema TESTING_QA para elevar confiabilidade, estabilidade ou performance.
- [ ] **TSK-078**: Adicionar testes visuais do fluxo Dashboard Operations na rotina Playwright (Prioridade: MEDIUM)
  - Executar a tarefa descrita focada em melhoria do subsistema TESTING_QA para elevar confiabilidade, estabilidade ou performance.
- [ ] **TSK-079**: Criar suíte de teste de resiliência e failover redis (Prioridade: MEDIUM)
  - Executar a tarefa descrita focada em melhoria do subsistema TESTING_QA para elevar confiabilidade, estabilidade ou performance.
- [ ] **TSK-080**: Desenvolver testes contratuais via Schemathesis nas rotas expostas no OpenAPI JSON (Prioridade: HIGH)
  - Executar a tarefa descrita focada em melhoria do subsistema TESTING_QA para elevar confiabilidade, estabilidade ou performance.

## OPS_CI_CD_EASYPANEL
_Deployments, CI/CD, monitoramento e EasyPanel_

- [ ] **TSK-081**: Configurar e automatizar backup agendado do Supabase no painel Hostinger/EasyPanel (Prioridade: HIGH)
  - Executar a tarefa descrita focada em melhoria do subsistema OPS_CI_CD_EASYPANEL para elevar confiabilidade, estabilidade ou performance.
- [ ] **TSK-082**: Migrar segredos em Actions ou Webhooks local para injeção via EasyPanel Secrets (Prioridade: HIGH)
  - Executar a tarefa descrita focada em melhoria do subsistema OPS_CI_CD_EASYPANEL para elevar confiabilidade, estabilidade ou performance.
- [ ] **TSK-083**: Implementar notificação Telegram de sucesso/falha do CI/CD de produção (Prioridade: HIGH)
  - Executar a tarefa descrita focada em melhoria do subsistema OPS_CI_CD_EASYPANEL para elevar confiabilidade, estabilidade ou performance.
- [ ] **TSK-084**: Estruturar Build Cache de imagens Docker para reduzir o tempo de deploy no EasyPanel (Prioridade: MEDIUM)
  - Executar a tarefa descrita focada em melhoria do subsistema OPS_CI_CD_EASYPANEL para elevar confiabilidade, estabilidade ou performance.
- [ ] **TSK-085**: Adicionar regras de Healthcheck DockerCompose nas dependências (Redis, API, DB) (Prioridade: MEDIUM)
  - Executar a tarefa descrita focada em melhoria do subsistema OPS_CI_CD_EASYPANEL para elevar confiabilidade, estabilidade ou performance.
- [ ] **TSK-086**: Reduzir logs espúrios (DEBUG) dos containers rodando em Produção (Prioridade: MEDIUM)
  - Executar a tarefa descrita focada em melhoria do subsistema OPS_CI_CD_EASYPANEL para elevar confiabilidade, estabilidade ou performance.
- [ ] **TSK-087**: Adicionar proteção rate_limit no nível do ingress Traefik dentro do EasyPanel (Prioridade: MEDIUM)
  - Executar a tarefa descrita focada em melhoria do subsistema OPS_CI_CD_EASYPANEL para elevar confiabilidade, estabilidade ou performance.
- [ ] **TSK-088**: Rotacionar chaves de dev obsoletas ou separar estritamente variáveis de dev/prod (Prioridade: MEDIUM)
  - Executar a tarefa descrita focada em melhoria do subsistema OPS_CI_CD_EASYPANEL para elevar confiabilidade, estabilidade ou performance.
- [ ] **TSK-089**: Configurar alerta Uptime Kuma na porta do OpenClaw WebSocket Gateway (Prioridade: MEDIUM)
  - Executar a tarefa descrita focada em melhoria do subsistema OPS_CI_CD_EASYPANEL para elevar confiabilidade, estabilidade ou performance.
- [ ] **TSK-090**: Validar volumes persistentes do N8N e Chatwoot para evitar perdas de storage (Prioridade: HIGH)
  - Executar a tarefa descrita focada em melhoria do subsistema OPS_CI_CD_EASYPANEL para elevar confiabilidade, estabilidade ou performance.

## DOCS_DX_OBSERVABILITY
_Documentação exaustiva, logs, métricas e DX_

- [ ] **TSK-091**: Documentar toda a topologia arquitetural atual em formato PlantUML (Prioridade: HIGH)
  - Executar a tarefa descrita focada em melhoria do subsistema DOCS_DX_OBSERVABILITY para elevar confiabilidade, estabilidade ou performance.
- [ ] **TSK-092**: Publicar documentação das rotas da API em Redoc / Swagger UI atualizados (Prioridade: HIGH)
  - Executar a tarefa descrita focada em melhoria do subsistema DOCS_DX_OBSERVABILITY para elevar confiabilidade, estabilidade ou performance.
- [ ] **TSK-093**: Criar Dashboard com Grafana exportando métricas do FastAPI, Redis e Supabase (Prioridade: HIGH)
  - Executar a tarefa descrita focada em melhoria do subsistema DOCS_DX_OBSERVABILITY para elevar confiabilidade, estabilidade ou performance.
- [ ] **TSK-094**: Estruturar logs estruturados em JSON no padrão ECS e configurar envio para Logstash ou similar (Prioridade: MEDIUM)
  - Executar a tarefa descrita focada em melhoria do subsistema DOCS_DX_OBSERVABILITY para elevar confiabilidade, estabilidade ou performance.
- [ ] **TSK-095**: Atualizar o guia de Quickstart para desenvolvedores, rodando a stack mínima local (Prioridade: MEDIUM)
  - Executar a tarefa descrita focada em melhoria do subsistema DOCS_DX_OBSERVABILITY para elevar confiabilidade, estabilidade ou performance.
- [ ] **TSK-096**: Documentar variáveis obrigatórias no `.env.example` sem expor secrets (Prioridade: MEDIUM)
  - Executar a tarefa descrita focada em melhoria do subsistema DOCS_DX_OBSERVABILITY para elevar confiabilidade, estabilidade ou performance.
- [ ] **TSK-097**: Registrar ADRs (Architecture Decision Records) sobre as configurações do OpenClaw (Prioridade: MEDIUM)
  - Executar a tarefa descrita focada em melhoria do subsistema DOCS_DX_OBSERVABILITY para elevar confiabilidade, estabilidade ou performance.
- [ ] **TSK-098**: Adicionar comentários nos trechos difíceis do cálculo de PII e Emolumentos na API (Prioridade: MEDIUM)
  - Executar a tarefa descrita focada em melhoria do subsistema DOCS_DX_OBSERVABILITY para elevar confiabilidade, estabilidade ou performance.
- [ ] **TSK-099**: Criar documento explicativo das permissões Role-based do Supabase (Prioridade: MEDIUM)
  - Executar a tarefa descrita focada em melhoria do subsistema DOCS_DX_OBSERVABILITY para elevar confiabilidade, estabilidade ou performance.
- [ ] **TSK-100**: Refatorar nomes de variáveis confusas no core para self-documenting code (Prioridade: HIGH)
  - Executar a tarefa descrita focada em melhoria do subsistema DOCS_DX_OBSERVABILITY para elevar confiabilidade, estabilidade ou performance.
