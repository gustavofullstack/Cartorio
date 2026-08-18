# SUPER PLANO DE MELHORIAS CARTÓRIO (100 TASKS)

## Fase 1: Arquitetura Core e Integração (API & N8N)
1.  **API: Revisão Geral de Endpoints:** Auditar e documentar todos os endpoints RESTful da API central.
2.  **API: Implementar Rate Limiting:** Adicionar controle de requisições na API para proteção contra abusos.
3.  **API: Logging Centralizado:** Integrar sistema de logging detalhado com suporte a trace IDs.
4.  **API: Validação de Inputs Avançada:** Refinar Pydantic models para garantir sanitização máxima dos dados.
5.  **API: Health Checks:** Expandir endpoints de health checks para incluir conectividade com Redis, Supabase, Chatwoot e N8N.
6.  **API: Tratamento de Erros:** Padronizar respostas de erro (RFC 7807 Problem Details).
7.  **N8N: Revisão de Workflows Existentes:** Analisar e otimizar cada workflow ativo para garantir consistência.
8.  **N8N: Padronização de Nomenclatura:** Renomear workflows, nodes e tags seguindo um padrão rigoroso.
9.  **N8N: Gestão de Erros nos Workflows:** Adicionar Error Trigger workflows para captura e notificação de falhas no N8N.
10. **N8N: Versionamento de Workflows:** Configurar exportação automatizada dos workflows do N8N para o repositório git.
11. **Integração API <-> N8N:** Implementar autenticação via API Key/HMAC nas chamadas do N8N para a API.
12. **Integração API <-> N8N:** Otimizar tempo de resposta das chamadas da API acionadas via Webhook do N8N.
13. **Segurança:** Implementar headers de segurança em todas as requisições API (CORS, CSP, HSTS).

## Fase 2: Banco de Dados Central (Supabase)
14. **Supabase: Modelagem Inicial:** Revisar e documentar a estrutura atual do banco de dados relacional.
15. **Supabase RLS (Row Level Security):** Configurar políticas RLS rigorosas para todas as tabelas sensíveis.
16. **Supabase Database Webhooks:** Criar webhooks no Supabase para notificar a API sobre mudanças cruciais (ex: novo usuário).
17. **Supabase Cron Jobs:** Configurar rotinas via pg_cron para limpeza de dados temporários e métricas.
18. **Supabase Vault:** Migrar chaves e segredos utilizados em functions para o Supabase Vault.
19. **Supabase GraphQL:** Habilitar e testar acessos via API GraphQL nativa do Supabase para relatórios específicos.
20. **Supabase Storage:** Configurar buckets privados e públicos com políticas rigorosas para armazenamento de documentos.
21. **Supabase Auth:** Configurar e testar integrações de autenticação, unificando usuários do sistema.
22. **Supabase Queues/Edge Functions:** Analisar e implementar filas para processamento assíncrono de tarefas pesadas.
23. **Backup e Restore:** Validar políticas automáticas de backup do Supabase e criar scripts de restore para DR (Disaster Recovery).
24. **Otimização de Índices:** Analisar queries lentas e criar índices necessários para as tabelas principais.

## Fase 3: Comunicação e Filas (Redis & Telegram)
25. **Redis: Revisão da Estrutura de Cache:** Padronizar as chaves (keys) no Redis (ex: `cartorio:cache:user:{id}`).
26. **Redis: TTL Inteligente:** Implementar expiração adequada para todos os tipos de cache para evitar memory leaks.
27. **Redis: Pub/Sub:** Implementar comunicação via Pub/Sub para eventos em tempo real entre API e Chatwoot.
28. **Redis: Monitoramento:** Configurar dashboard para visualização de uso de memória e hit rate do Redis.
29. **Telegram Bot: Configuração Inicial:** Validar o token e conexão do bot de testes no ambiente local.
30. **Telegram Bot: Comandos Administrativos:** Implementar comandos como `/health`, `/stats` para monitoramento via admin.
31. **Telegram Bot: Alertas de Sistema:** Configurar bot para enviar alertas críticos (ex: API offline, erro no Supabase).
32. **Telegram Bot: Testes E2E:** Criar fluxo de testes end-to-end simulando cliente no bot do Telegram.

## Fase 4: CRM e Atendimento (Chatwoot)
33. **Chatwoot: Configuração de Caixas de Entrada:** Organizar inboxes por canal (WhatsApp, Telegram, Web).
34. **Chatwoot: Labels e Macros:** Criar sistema de categorização e atalhos para os atendentes (HITL).
35. **Chatwoot: Automação de SLA:** Configurar regras de automação baseadas em tempo de resposta.
36. **Chatwoot: Webhooks para API/N8N:** Garantir que eventos do Chatwoot disparem fluxos corretos.
37. **Chatwoot Sidekiq:** Monitorar e otimizar o processamento de filas do Sidekiq do Chatwoot.
38. **Chatwoot: API Customizada:** Documentar integração customizada que a API central faz com a API do Chatwoot.
39. **Chatwoot: Integração de Contatos:** Sincronizar contatos do Supabase com a base do Chatwoot via API.
40. **Chatwoot: Customização Visual:** Ajustar a interface (se necessário e possível via UI/variáveis) para padrão visual da marca.

## Fase 5: Agente IA - OpenClaw e Evolution API
41. **Evolution API: Instância WhatsApp:** Verificar estabilidade da conexão principal e documentar processo de relink (QR Code).
42. **Evolution API: Webhooks:** Configurar webhooks para entrega, leitura e recebimento de mensagens no N8N.
43. **Evolution API: Tratamento de Tipos de Mídia:** Garantir suporte para áudio, imagem e documentos no fluxo de recebimento.
44. **OpenClaw: Configuração do DeepSeek:** Validar o provider `deepseek-v4-flash` com `thinking: enabled` no `cartorio-bot.openclaw.json`.
45. **OpenClaw: Revisão do System Prompt:** Refinar regras de HITL, LGPD e tom de voz no prompt.
46. **OpenClaw: Context Window:** Certificar uso correto da janela de 1M no JSON.
47. **OpenClaw: Tools de Consulta:** Testar a tool `consultar_emolumento` garantindo resposta sem inventar dados.
48. **OpenClaw: Tools de Protocolo:** Testar fluxo de `criar_protocolo` com direcionamento correto para HITL.
49. **OpenClaw: Handoff:** Otimizar e testar a tool `handoff_humano` direcionando perfeitamente para o Chatwoot.
50. **OpenClaw MCP: Integração:** Testar `cartorio_mcp_api`, `cartorio_mcp_supabase` e `cartorio_mcp_chatwoot`.
51. **OpenClaw Hooks:** Validar `pii_scrub` (LGPD) antes de salvar logs.
52. **Integração Evolution -> OpenClaw:** Preparar o canal final de comunicação (apenas após 100% de testes).

## Fase 6: Deploy, Infraestrutura (EasyPanel) e CI/CD
53. **EasyPanel: Revisão de Containers:** Auditar limites de CPU e Memória para os serviços principais na VPS.
54. **EasyPanel: Redes Internas:** Validar comunicação restrita entre containers (evitar expor portas desnecessariamente).
55. **EasyPanel: Certificados SSL:** Garantir renovação automática para todos os subdomínios (Traefik).
56. **EasyPanel: Volumes Permanentes:** Documentar mapeamento de volumes para o Supabase, Redis e Evolution API.
57. **CI/CD: GitHub Actions - Linter:** Garantir pipeline de Ruff/Prettier/ESLint bloqueando commits com erros.
58. **CI/CD: GitHub Actions - Testes:** Criar jobs separados para testes unitários, de integração e e2e (Playwright).
59. **CI/CD: GitHub Actions - OpenAPI:** Automatizar verificação de quebras de contrato (Snapshot Check).
60. **CI/CD: GitHub Actions - Deploy Automatizado:** Configurar CD via webhooks do EasyPanel ou SSH.
61. **Docker: Otimização de Imagens:** Analisar os Dockerfiles para reduzir tamanho e melhorar cache de build.

## Fase 7: Segurança, LGPD e Logs
62. **Auditoria de Secrets:** Varredura em busca de hardcoded secrets (tokens, chaves) em arquivos versionados.
63. **Gestão do .env:** Padronizar `.env.example` sem valores reais e gerenciar secrets via Vault/Infra.
64. **Mascara de Dados (PII):** Garantir que a API mascare CPF/RG nos retornos não autorizados.
65. **LGPD Consentimento:** Integrar fluxo de opt-in/opt-out em todos os pontos de contato do cliente.
66. **Logs Centralizados:** Agregar logs do backend, N8N e Chatwoot em um dashboard (ex: Grafana/Loki, se viável, ou painel próprio).
67. **Alertas de Segurança:** Configurar notificações caso ocorram muitas tentativas falhas de login na API.

## Fase 8: Testes Abrangentes (Backend & E2E)
68. **Testes Unitários: Serviços e Regras de Negócio:** Cobertura > 80% nos pacotes `services/` do backend.
69. **Testes Unitários: Utils e Helpers:** Garantir robustez em funções de formatação e cálculo.
70. **Testes de Integração: API e Banco de Dados:** Validar chamadas com banco em memória (SQLite/Mock) para CRUDs.
71. **Testes de Integração: Redis:** Simular leitura/escrita e expiração nos testes.
72. **Testes de Contrato (OpenAPI):** Refinar scripts que garantem compatibilidade do Swagger com a implementação.
73. **Testes E2E: Saúde da Infra (Playwright):** Garantir que o script `test_e2e_health.py` valide a comunicação completa.
74. **Testes de Carga (Opcional/Básico):** Criar script (K6 ou Locust) para estressar endpoints cruciais.
75. **Mock de Ambiente:** Criar fixtures padrão (usuário de teste, protocolo fictício) para testes consistentes.

## Fase 9: UX/UI (Painéis, Ferramentas Internas e Agent Browser)
76. **UX: Dashboard de Revisão de Usuários:** Melhorar acessibilidade (A11y, focus, contraste) do `user-review-dashboard`.
77. **UX: Dashboard de Operações:** Otimizar visualização de tabelas e carregamento de dados no `operations-dashboard`.
78. **UI/UX Python Scripts:** Garantir que o JS gerado por `dashboard.py` seja otimizado e modular.
79. **Frontend Linter:** Garantir padrões com pnpm, lint e format (sem npm/yarn).
80. **Agent Browser na VPS:** Testar usabilidade do browser nativo via GUI local caso necessário.
81. **Acessibilidade: Focus Rings:** Adicionar `outline: 2px solid var(--brand);` focado para navegação por teclado.

## Fase 10: Otimização de Performance e Refatoração
82. **SQLAlchemy: Otimização de Queries:** Substituir `len(all())` por `func.count()` em todo o código backend.
83. **API: Otimização de Resposta (Gzip/Brotli):** Habilitar compressão para respostas de API de grande tamanho.
84. **Refatoração: DRY (Don't Repeat Yourself):** Isolar lógica duplicada nos roteadores do FastAPI.
85. **Refatoração: Injeção de Dependências:** Melhorar o uso de `Depends` no FastAPI para conexões de banco e autenticação.
86. **Cache de Requisições:** Armazenar respostas constantes da API em cache no backend para evitar processamento.

## Fase 11: Documentação, Memória e Organização
87. **Documentação Geral (README.md):** Atualizar diagrama de arquitetura do sistema no README.
88. **Documentação de API (Swagger/Redoc):** Melhorar as descrições dos endpoints e Schemas (Models) do Pydantic.
89. **Documentação de Ambiente (AGENTS.md):** Atualizar regras e orientações para agentes autônomos.
90. **Diário de Bordo (Journals):** Criar/Atualizar `.jules/bolt.md` e `.jules/palette.md` com aprendizados técnicos e de UX.
91. **Documentação N8N:** Criar README detalhando as integrações e fluxos de cada webhook ativo.
92. **Documentação Supabase:** Listar tabelas, políticas de segurança e webhooks ativos no repositório.
93. **Documentação Evolution API:** Criar guia rápido de reset de instância/QR code.
94. **Limpeza de Repositório:** Remover arquivos temporários (`txt`, `.db` locais), scripts obsoletos.
95. **Code Comments:** Adicionar docstrings detalhadas em todas as funções públicas críticas.

## Fase 12: Ajustes Finais e Orquestração
96. **Monitoramento de Custos/Tokens (Codex-Bar):** Analisar log de tokens da IA durante execução, otimizar chamadas.
97. **Revisão de Erros de Lint (Ruff/MyPy):** Resolver Warnings residuais, mantendo tipagem estrita (MyPy).
98. **Simulação Completa do Fluxo (Dry-Run):** Executar Evolution -> API -> N8N -> Supabase -> Chatwoot -> Telegram sem envio real.
99. **Orquestração: Configuração do Plug-and-Play:** Deixar Agent OpenClaw engatilhado, apenas aguardando flag de ativação.
100. **Entrega e Review do Status:** Atualizar STATUS.md validando que todos os serviços estão em sincronia.
