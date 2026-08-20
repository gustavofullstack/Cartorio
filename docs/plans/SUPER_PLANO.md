# SUPER PLANO - Otimização, Integração e Estabilização 100 Tasks

Este é o plano detalhado de 100 tarefas para melhorar, integrar, otimizar, testar e documentar todo o sistema do Cartório AI. O foco é a integração e configuração completa de: EVOLUTION-API -> API -> N8N -> CHATWOOT -> REDIS -> SUPABASE -> REDIS -> CHATWOOT -> N8N -> API -> EVOLUTION-API. NADA será refeito, apenas melhorado e otimizado. Chaves nunca serão rotacionadas.

## Fase 1: Supabase e Banco de Dados (Centralização) (Tasks 1-15)
1. Ativar e configurar extensões do Supabase (pg_stat_statements, pgcrypto).
2. Otimizar índices nas tabelas principais para ganho de performance (O(1)).
3. Criar webhooks de database do Supabase apontando para o N8N.
4. Mapear rotinas críticas para rodar via Supabase Cron.
5. Estruturar permissões RLS (Row Level Security) básicas e testar no backend.
6. Habilitar Supabase Vault para armazenar segredos não expostos em envs locais se necessário (não rotacionar, apenas organizar).
7. Criar GraphQL schema views para consultas otimizadas do N8N.
8. Configurar Queue no Supabase via pg_net para tarefas assíncronas do webhook.
9. Migrar cache estático (canned responses) para Redis sincronizado via Supabase trigger.
10. Revisar testes locais com DATABASE_URL de sqlite memory.
11. Auditar chamadas de API do Supabase (MCP/REST) evitando N+1 queries.
12. Criar painel básico no Supabase para acompanhamento do DPO.
13. Otimizar pool de conexão usando SQLAlchemy Async no backend.
14. Implementar healthcheck dedicado de Supabase na API.
15. Escrever/Documentar as estruturas do Banco de Dados no diretório de docs.

## Fase 2: Evolution-API (Tasks 16-25)
16. Revisar healthcheck do Evolution-API no backend (test_evolution_health.py).
17. Otimizar parser de eventos do Evolution API p/ reduzir alocação de string.
18. Integrar Evolution webhook diretamente na API/N8N usando HMCA verifier.
19. Testar envio em massa limitando RPS (rate limiting).
20. Mapear tipos de mensagens (audio, documento) para tratamento em LLM.
21. Garantir que LGPD mascaramento de PII ocorra antes de salvar histórico.
22. Evitar retentativas cíclicas no Evolution webhook (Dead-Letter-Queue).
23. Documentar fluxo Evolution API.
24. Adicionar monitoramento no Redis sobre taxa de falhas do Evolution.
25. Mapear testes mockados no pytest de Evolution HMAC.

## Fase 3: N8N (Tasks 26-40)
26. Auditar e testar fluxo do N8N webhook -> Chatwoot.
27. Criar/revisar workflow no N8N para automação de mensagens de cobrança.
28. Adicionar sub-workflow no N8N para LGPD DPO alert.
29. Revisar integração N8N -> Supabase (usando GraphQL).
30. Otimizar polling no N8N (usar webhooks push em vez de pull).
31. Tratar erros globais no N8N e jogar no Discord/Telegram Log.
32. Conectar N8N à API usando harness de contexto.
33. Simplificar branches do N8N para fluxos de handoff (Bot para Humano).
34. Adicionar retries e idempotency blocks nos workflows críticos.
35. Criar pipeline no N8N para sincronização de contatos.
36. Utilizar Redis node no N8N para gerenciar locks distribuídos de processos.
37. Testar workflows localmente e analisar consumo de token/CPU.
38. Criar documentação extensa no diretório `/docs/n8n/`.
39. Validar métricas de execução do N8N na API.
40. Refatorar nós duplicados para modularidade (Execute Workflow nodes).

## Fase 4: Chatwoot e CRM (Tasks 41-55)
41. Testar endpoint de handoff humano no Chatwoot (handoff_humano).
42. Criar macros úteis no Chatwoot para os atendentes (escreventes).
43. Sincronizar automações do N8N com tags no Chatwoot.
44. Criar rotinas de pre-computation para respostas enlatadas (CANNED_RESPONSES) no Chatwoot.
45. Validar que o Bot pausa a atuação quando a conversa recebe 'hitl_router' no Chatwoot.
46. Integrar webhook do Chatwoot no Redis para pub/sub veloz (Event Bus).
47. Assegurar mascaramento PII nas interfaces visíveis, exceto para escopos autorizados.
48. Testar integração Chatwoot-Sidekiq (Background jobs).
49. Melhorar logs do webhook do Chatwoot no backend (test_webhook_chatwoot_api.py).
50. Gerar documentação profunda da arquitetura do Chatwoot + API.
51. Limitar histórico exposto do Chatwoot no payload para o N8N (corte para tokens curtos).
52. Refinar pipeline de sincronização do DPO (Right to Erasure) dentro do Chatwoot.
53. Fazer testes de concorrência massiva de webhooks de entrada.
54. Monitorar filas do Sidekiq via métricas no Prometheus (se ativados).
55. Confirmar sync dos contatos Evolution -> Chatwoot.

## Fase 5: API Interna e Otimização Backend (Tasks 56-75)
56. Testar todos os endpoints de `/api/v1/agendamento`.
57. Testar todos os endpoints de `/api/v1/protocolo`.
58. Testar endpoints de emolumento real e aplicar cache O(1).
59. Atualizar dependências críticas se necessário (sem quebrar NADA).
60. Executar `uv run ruff format .` em todos os diretórios backend.
61. Aplicar `# noqa: F401, F841` para silenciar temporariamente falsos positivos se isolado.
62. Configurar Redis com prefixos por ambiente (`dev:`, `prod:`).
63. Integrar MCP API ao OpenClaw com descrições rígidas (harness).
64. Validar schemas OpenAPI, preenchendo strings dummy (64 chars) nos envs.
65. Prevenir N+1 queries na leitura do histórico de atendimento.
66. Testar idempotência nas rotas mutáveis (POST, PUT).
67. Corrigir falhas pendentes de testes locais (skip nos do Playwright filesystem `test_chromium_browser_cache_via_filesystem`).
68. Rodar testes de integração E2E com `pytest -m "not playwright"`.
69. Criar documentação estruturada `/docs/api/`.
70. Otimizar serialização Pydantic em retornos longos.
71. Analisar logs de gargalos nas chamadas LLM e adicionar traces.
72. Implementar caching de JWT public keys O(1) na inicialização.
73. Validar métricas de SLO.
74. Aplicar circuit breaker nas integrações externas (N8N).
75. Revisar e documentar uso dos MCP servers (Model Context Protocol).

## Fase 6: OpenClaw e Agente Cartório (Tasks 76-90)
76. Garantir configuração cartorio-bot.openclaw.json com `deepseek-v4-flash`, context 1M, thinking enabled (Feito em parte!).
77. Restringir system prompt para não usar emojis, ser sério, não decidir isenções e usar API. (Feito em parte!)
78. Validar pipeline: Recebimento Evento -> Trigger Agent -> Run Skills.
79. Testar as Skills: `pii_scrubber`, `lgpd_consent_checker`, `audit_logger`.
80. Revisar fluxo do Telegram Bot integrado ao OpenClaw para testes diretos (Não mexer no token, é intocável).
81. Corrigir possíveis falhas de conexão WebSocket do OpenClaw.
82. Criar scripts de simulação (mock chat) pro OpenClaw agent local.
83. Conectar ferramentas MCP diretamente ao context do Agente, forçando-o a usá-las (Harnessing forte).
84. Auditar respostas geradas garantindo zero alucinação no valor do emolumento.
85. Testar Dead Man's Switch (On Error) do OpenClaw acionando o Telegram do grupo da Pietra.
86. Monitorar e logar o uso de tokens por conversa do OpenClaw.
87. Testar comportamento do agente via API com falhas injetadas nos endpoints MCP.
88. Melhorar a documentação do agente.
89. Realizar teste de carga no OpenClaw local/vps se disponível.
90. Assegurar que o agente responda com protocolo DRAFT quando solicitado criação.

## Fase 7: DevOps, CI/CD e Métricas Gerais (Tasks 91-100)
91. Validar todos os fluxos do Easypanel para deploy (arquivos YAML/JSON).
92. Revisar uso de variáveis obrigatórias de CI (AUDIT_HMAC_KEY, etc).
93. Automatizar scripts de checagem do openapi snapshot para não falharem.
94. Analisar e testar integração de metrics Prometheus com API e Redis.
95. Conferir configs do ambiente production vs dev para evitar vazamentos de memória.
96. Configurar testes para rodar arquivos separadamente (não todos de uma vez p/ evitar timeouts no pytest).
97. Integrar memory logging (`.jules/bolt.md`, `.jules/sentinel.md`) para anotações críticas.
98. Escrever documentação final de arquitetura de alta disponibilidade (HA).
99. Validar funcionamento e acessos da API via SSH e EasyPanel (nenhum erro pendente).
100. Relatório de Fechamento de Ciclo (todas 100 tasks checadas) apontando otimizações consolidadas.
