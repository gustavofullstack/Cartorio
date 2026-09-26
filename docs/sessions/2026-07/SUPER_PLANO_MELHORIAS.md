# Plano de Melhorias (100 Tasks)

## Fase 1: Fundação e Supabase Central (Tasks 1-20)
1. **Ativar Supabase Auth:** Substituir a autenticação JWT manual nos endpoints D26-D32 pelo Supabase Auth nativo para maior segurança e compliance LGPD.
2. **Implementar Supabase RLS (Row Level Security):** Reforçar políticas de segurança no banco de dados para garantir isolamento de dados por cliente/operador.
3. **Migrar Cron Jobs:** Transferir o script de retenção LGPD (`lgpd_memory_retention.py`) do Python local para o Supabase Cron.
4. **Configurar Database Webhooks:** Criar webhooks no Supabase para notificar a API FastAPI automaticamente em mudanças críticas nas tabelas `protocolo` e `conversa`.
5. **Integração com Supabase Vault:** Migrar credenciais de integrações externas para o Vault do Supabase para gestão segura sem vazamentos.
6. **Supabase Edge Functions:** Avaliar e migrar endpoints de processamento leve para Edge Functions para reduzir carga da API principal.
7. **Integração Supabase Storage:** Otimizar o armazenamento e recuperação de documentos gerados pelo OCR diretamente no Supabase Storage.
8. **Configurar Supabase Queues:** Implementar sistema de filas nativas no Supabase para substituir a lógica manual de DLQ em Python para mensagens com falha.
9. **Ativar Realtime Subscriptions:** Utilizar o Supabase Realtime para notificar o frontend em tempo real sobre atualizações de status de protocolo.
10. **Explorar Supabase GraphQL:** Habilitar suporte GraphQL para permitir consultas de dados flexíveis do frontend dashboard de analytics.
11. **Refatorar Modelos SQLAlchemy:** Ajustar os modelos do FastAPI para alinhamento perfeito com as tabelas otimizadas e views criadas diretamente no Supabase.
12. **Sincronização de Cache Redis/Supabase:** Configurar gatilhos para invalidar o cache Redis (`redis://localhost:6379/0`) quando os webhooks do Supabase dispararem atualizações de dados.
13. **Dashboard de Saúde do Supabase:** Integrar métricas de saúde e uso do banco de dados ao dashboard interno utilizando a API administrativa do Supabase.
14. **Rotinas de Backup Integradas:** Consolidar os scripts de backup customizados usando a funcionalidade de Pular no tempo (Point in Time Recovery) do Supabase.
15. **Otimização de Consultas de Auditoria:** Melhorar a indexação das tabelas de auditoria para acelerar as verificações de `audit_integrity`.
16. **Padronização de Retorno (RFC 7807):** Assegurar que todas as interações com o Supabase retornem detalhes do problema em conformidade com o padrão em caso de erro.
17. **Refatorar `mcp_server.py`:** Adicionar ferramentas (tools) nativas do Supabase ao MCP Server para orquestração de infraestrutura gerenciada pelo modelo de linguagem.
18. **Ativar Supabase Vector:** Instalar a extensão `pgvector` e criar tabelas para suportar a busca semântica em FAQs institucionais (Conhecimento Institucional).
19. **Testes E2E Supabase Auth:** Desenvolver testes automatizados garantindo o login correto e emissão de tokens utilizando a infraestrutura baseada no Supabase.
20. **Revisar Políticas LGPD (RLS):** Garantir através de testes no banco de dados que as políticas RLS atendem aos direitos do titular (Art. 18).

## Fase 2: Evolution API e N8N Workflows (Tasks 21-40)
21. **Unificar Webhooks Evolution API:** Centralizar o processamento de todos os webhooks da Evolution API em um único router de entrada com roteamento inteligente.
22. **Retry Mechanism Evolution:** Melhorar a resiliência no envio de mensagens com políticas avançadas de *exponential backoff* via Celery ou N8N Queue.
23. **Gerenciamento de Instâncias Evolution API:** Criar endpoints administrativos para criar, deletar e reiniciar instâncias da Evolution API diretamente pelo Dashboard.
24. **Monitoramento de Queda de QR Code:** Implementar um alerta via N8N/Telegram quando o status da conexão da Evolution API mudar para desconectado (QR code exigido).
25. **Sincronização Bidirecional Evolution <-> N8N:** Otimizar o workflow para que as atualizações de presença/digitação (typing indicators) sejam passadas suavemente entre Evolution API e N8N.
26. **Documentar Fluxos Ativos no N8N:** Atualizar a documentação detalhada sobre os 34 workflows ativos.
27. **Backup Automático N8N Workflows:** Agendar um workflow N8N para fazer backup diário de todos os workflows para um repositório seguro ou Supabase Storage.
28. **Teste E2E de Workflows N8N:** Criar scripts em Python para invocar os webhooks do N8N e validar as saídas de forma automatizada no pipeline CI/CD.
29. **Revisar Limites de Execução (Rate Limit) N8N:** Ajustar configurações de *rate limit* nos *trigger nodes* do N8N para prevenir sobrecargas caso a Evolution API mande uma rajada de mensagens (DDoS de mensagens).
30. **Padronização de Nomenclatura no N8N:** Renomear *nodes* nos workflows do N8N de acordo com o padrão do time *cartorio-n8n* para maior clareza.
31. **Otimização de Contexto no N8N:** Filtrar o payload JSON repassado pelo N8N ao OpenClaw Gateway para economizar tokens, removendo campos meta desnecessários da Evolution API.
32. **Redução de Latência N8N:** Analisar e otimizar *nodes* de função JavaScript lentos.
33. **Tratamento Global de Erros (Error Trigger N8N):** Implementar um workflow mestre no N8N para capturar falhas em outros fluxos e disparar notificações para o canal SRE.
34. **Auditoria de Ações no N8N:** Inserir chamadas HTTP nos workflows para o endpoint `/api/v1/audit/create` visando rastrear modificações de estado originadas no N8N.
35. **Integração N8N com Telegram Bot:** Finalizar o webhook e integração do bot @TestCartorioBot para suportar fluxos complexos de atendimento de fallback no N8N.
36. **Suporte a Mídias Ricas na Evolution API:** Adicionar suporte em workflows N8N para processar vídeos e áudios com transcrição via API externa (OpenAI Whisper).
37. **Limpeza de Arquivos Temporários:** Workflow N8N para purgar imagens temporárias recebidas da Evolution API após o processamento via OCR (LGPD).
38. **Criação de Templates de WhatsApp (Evolution):** Gerenciar e pré-aprovar templates de mensagem ativa.
39. **Atualizar Agentes Múltiplos:** Testar o envio de contexto em paralelo para N8N simulando alto tráfego com o script SQUAD E.
40. **Revisar *Dead Letter Queue* N8N:** Otimizar as filas de refugo para fluxos que falham persistentemente em chamadas a APIs externas.

## Fase 3: Integração Chatwoot e CRM (Tasks 41-60)
41. **Pausar IA via Chatwoot (Handoff):** Ajustar o endpoint de *handoff* e *webhooks* do Chatwoot para pausar perfeitamente as interações da IA assim que o operador (HITL) assume a conversa.
42. **Status Typings do Chatwoot para Evolution API:** Repassar status de "digitando..." do atendente no Chatwoot para a interface do WhatsApp.
43. **Integração do Histórico do Chatwoot no Supabase:** Armazenar os logs de encerramento de ticket do Chatwoot permanentemente no Supabase para cumprir políticas de retenção de 2 anos.
44. **Macros de Resposta Rápida (Canned Responses):** Expandir as macros de resposta rápida integrando chamadas via API ao backend de consulta de Emolumentos.
45. **Autenticação Unificada Chatwoot:** Integrar autenticação do Chatwoot com os perfis de atendentes gerenciados na API FastAPI.
46. **Notificações Push do Chatwoot:** Configurar alertas de alta prioridade (ex: solicitação de urgência) do Chatwoot diretamente para o Telegram pessoal do escrevente líder.
47. **Rotulagem Automática LGPD:** Adicionar labels automáticas (ex: "Solicitação_Esquecimento") nas conversas do Chatwoot com base na identificação da IA.
48. **Reconhecimento de Intent (Chatwoot Webhook):** Processar mensagens iniciais via IA e atribuir automaticamente a caixa de entrada (inbox) correta no Chatwoot (ex: Protesto, Notas, Financeiro).
49. **Dashboard Customizado no Chatwoot:** Integrar um iframe ao Chatwoot que exibe o painel construído no *Agent AI Data Panel* (`dashboard.html`).
50. **Anonimização no Chatwoot (LGPD):** Sincronizar as exclusões do Supabase com o Chatwoot: ao deletar cliente no BD central, anonimizar dados no Chatwoot CRM usando a API.
51. **Limitar Contexto de Operador:** Configurar permissões avançadas no Chatwoot para que operadores terceiros só vejam conversas que não contenham PII sensível sem mascaramento.
52. **Integração de Agendamentos (Chatwoot):** Exibir os agendamentos pendentes do cliente consultado no painel lateral do Chatwoot usando uma integração customizada HTTP.
53. **Atualização da Extensão `pgvector` no Chatwoot:** Verificar se a extensão necessária para a funcionalidade de "Agent SDK" no banco Postgres do Chatwoot está performando corretamente (fixar crashloops antigos).
54. **Atalhos (Shortcuts) Integrados:** Adicionar comandos de barra (ex: `/protocolo 12345`) no chat interno do Chatwoot que disparam chamadas silenciosas para a API backend e retornam dados contextuais.
55. **Recuperação de Conversas Órfãs:** Implementar script que audita e reconecta sessões de Chatwoot onde o fluxo do Evolution API foi interrompido indevidamente.
56. **Métricas de Tempo de Resposta (SLA):** Extrair dados do Chatwoot, enviar para o banco central e exportar para o Prometheus para alertas de violação de SLA (> 10min).
57. **Gestão do Sidekiq Chatwoot:** Monitorar filas do Sidekiq do Chatwoot usando Prometheus export e alertas.
58. **Desabilitar CSAT Padrão:** Configurar Chatwoot para não enviar pesquisa de satisfação caso a conversa tenha sido atendida 100% pela IA.
59. **Botões Interativos no Chatwoot:** Habilitar suporte ao envio de opções estruturadas do WhatsApp (botões/listas) através do agente OpenClaw acoplado.
60. **Teste de Carga do Webhook Chatwoot:** Realizar testes de *flood* para garantir que o webhook aguente rajadas de encerramentos automáticos.

## Fase 4: Otimizações de IA e OpenClaw (Tasks 61-80)
61. **Model Switcher Adaptável:** Otimizar o roteador (router) OpenClaw para realizar *fallback* transparente de `deepseek-v4-flash` para `mimo` se o primeiro demorar mais de 3 segundos no *Time To First Token*.
62. **Context Window Profiler:** Monitorar e exibir nos logs o consumo real de tokens (max 1.048.576) do OpenClaw em conversas complexas.
63. **Refinamento do System Prompt (Zero-Shot):** Continuar refinando o prompt base do `cartorio-bot` removendo alucinações comuns baseadas em feedback do escrevente.
64. **Ajuste de Parâmetros Cognitivos (Thinkings):** Testar métricas comparativas com `thinkingDefault="adaptive"` e ajustar limiares se as respostas ficarem longas ou vagas.
65. **Otimização de Skills do OpenClaw:** Consolidar os 7 *skills* `.md` da pasta `infra/openclaw-agent/skills` em menos arquivos estruturados para economia de tokens de instrução.
66. **Suporte de Visão (OCR):** Adicionar chamadas API ao fluxo do bot para extração via Tesseract de imagens recebidas e processamento de PII *antes* de injetar no LLM.
67. **Otimização de Roteamento de Ferramentas (MCP):** Ajustar descrições e *schemas* das ferramentas exportadas em `mcp_server.py` para facilitar a decisão de uso do agente OpenClaw.
68. **Auditoria de Chamadas de Ferramentas:** Implementar *hook* `on_tool_call` para bloquear e registrar tentativas da IA de acessar endpoints protegidos que deveriam requerer intervenção humana prévia.
69. **Gerenciamento de Contexto Eficiente (Summarization):** Criar *job* que usa um LLM de baixo custo (ex: `mistral-free`) para sumarizar conversas do histórico antes de anexá-las no contexto longo do `deepseek-v4`.
70. **Bloqueio de Emojis em Saída:** Adicionar um filtro em Python que faz o *scrub* final nas respostas geradas removendo quaisquer emojis antes do envio.
71. **Monitoramento de Custos de API (Codex-bar CLI):** Integrar exportação de estatísticas de *tokens* em `api/v1/metrics` para o painel Grafana de Custos.
72. **Refinamento de Handoff IA:** Adicionar métricas sobre a *taxa de acurácia de handoff* (porcentagem de vezes que a IA pede ajuda quando a certeza cai).
73. **Agent Persona Consistency Test:** Criar rotina diária executando 5 casos de simulação pelo Telegram Bot para checar se a persona do bot foi alterada indevidamente.
74. **Atualização de Chaves API do OpenClaw:** Documentar e implementar mecanismo que impede a injeção falha ou vazamento de chaves `sk-cp-***`.
75. **Avaliação do OpenCode Zen/Qwen Coder:** Implementar benchmark executando cenários padrão com o Qwen Coder comparando custos com o Deepseek.
76. **Aprimoramento do PII Scrubber 3-Camadas:** Incluir verificação contra novos formatos vazados na internet para a Regex de proteção pré-LLM e pós-LLM.
77. **Suporte a Documentos Estruturados (PDF):** Enviar texto extraído de PDFs de procurações em chunks para extração de dados através do modelo IA.
78. **Gerenciamento Seguro do `agents.json`:** Certificar-se que alterações em parâmetros de LLM substituam configs obsoletas em memória (hot-reload sem perdas de websocket).
79. **Revisar Timeout do Provider (CORS/Preflight):** Monitorar logs e ajustar timeouts do OpenClaw Gateway para prevenir `408 Request Timeout` em interações complexas com N8N.
80. **Automação de Dicionário Jurídico:** Fornecer acesso contínuo a termos atualizados locais (TJMG) como RAG para as decisões de triagem do bot.

## Fase 5: Memória, Cache e Documentação (Tasks 81-100)
81. **Expansão do Cache Redis:** Analisar top queries no Supabase via `pg_stat_statements` e aplicar cache do Redis em endpoints não dinâmicos.
82. **Política TTL Dinâmica:** Configurar chaves Redis (`redis_ttl_inventory.py`) para expirar no início do horário comercial do Cartório quando a base de dados sofrer bulk updates noturnos.
83. **Centralizar Endpoints Redis:** Modificar `mcp_server.py` para usar consistentemente a URL segura central.
84. **Documentação Interna do Orquestrador:** Descrever na API doc como agentes e subagentes trocam contexto e se coordenam de forma enxuta via JSON.
85. **Sincronização de Sessão (Browser Agent):** Configurar salvamento de histórico de intervenção do agente no painel EasyPanel para auditoria interna.
86. **Pre-cache de Agendamentos Frequentes:** Rotina que executa `warm_cache` em informações sensíveis mas previsíveis todo começo de semana.
87. **Padronização das Reuniões de Agent Team (Logs):** Formatar e arquivar outputs do orquestrador no diretório `.jules` garantindo conformidade de memory.
88. **Testes do Painel de Dados (Browser AI):** Automatizar testes via Playwright acessando `/dashboard` na VPS para validar visualmente.
89. **Criação Rápida de Atividades (SUI):** Implementar comando bash administrativo que injeta tarefas no `task-bank.json` com CLI interativa.
90. **Sincronizar Arquivos de Memória (`AGENTS.md`, `MEMORY.md`):** Consolidar as regras dispersas em repositórios antigos e transferir *learnings* relevantes para a pasta `.jules`.
91. **Reestruturar Arquitetura de Pastas de Docs:** Mover toda documentação técnica densa e PDFs desatualizados para repositório ou bucket AWS paralelo mantendo apenas os `.md` essenciais de plataforma.
92. **Revisão de Padrão JSON (Task Bank):** Adicionar esquema JSON strict (`$schema`) e rodar CI validando que nenhuma nova task do banco fure o formato *compacto*.
93. **Teste de Integração Contínua (Pre-commit):** Adicionar script `check_no_literal_keys.py` às verificações pré-commit para blindar vazamentos locais antes do envio a repositório.
94. **Health Check de Memória de Agentes:** Monitorar o peso em disco dos diretórios de cache do orquestrador e limpar aros > 7 dias não lidos.
95. **Otimização de Conexões de DB no FastAPI:** Habilitar e monitorar *connection pool* eficiente via SQLAlchemy/Supabase.
96. **Criação de Runbook Central do Pipeline AI:** Compilar 5 anos de problemas conhecidos de integração em um manual para diagnóstico do Evolution -> API -> N8N.
97. **Sintetizador Automático de Sessão:** Bot responsável por compilar resumos diários baseados na leitura das atualizações e envios na ferramenta Chatwoot e depositar no Telegram SRE.
98. **Simulação de Alta Disponibilidade:** Orquestrar cenário em staging simulando indisponibilidade de Redis usando mock (`idempotency_store_fake.py`) testando fail-open.
99. **Testes Unitários da API de Emolumentos:** Garantir >95% de cobertura testando valores limites do *TJMG 2026* e falhas no cálculo central.
100. **Validação Final da Topologia:** Realizar *review* cruzado das conexões de Tailscale, acessos do Gateway, certificados Traefik, e permissões do Vault garantindo 100% de estabilidade.
