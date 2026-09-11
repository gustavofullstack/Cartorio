# SUPER PLANO DE MELHORIAS (100 TASKS) - CARTÓRIO AI

## Squad A: Infraestrutura e Deploy (Tasks 1-10)
1. Atualizar e rotacionar as chaves (simuladas, não reais) se necessário na infra local para segurança.
2. Monitorar o health-check de todos os serviços (EasyPanel, n8n, api, etc) via cron job.
3. Criar scripts de backup do banco de dados PostgreSQL automaticamente para S3.
4. Otimizar as configurações do Traefik para roteamento e cache reverso.
5. Criar pipeline de deploy staging para produção no GitHub Actions (ou Gitlab).
6. Realizar auditoria dos contêineres e imagens Docker buscando CVES usando o trivy.
7. Atualizar as dependências Python (`uv.lock`) para resolver vulnerabilidades de dependabot.
8. Configurar alertas no Prometheus e Grafana para latência na API > 1s.
9. Isolar tráfego da Redis apenas para redes privadas do Tailscale/Swarm.
10. Otimizar as configurações do servidor N8N reduzindo memória e worker pools no EasyPanel.

## Squad B: Banco de Dados e Supabase (Tasks 11-20)
11. Implementar `Row Level Security` em tabelas críticas do Supabase para todos perfis.
12. Criar Supabase Database Webhooks integrando ações no DB diretamente com a API FastAPI.
13. Configurar cron jobs no Supabase pra arquivamento de logs acima de 365 dias (LGPD).
14. Usar Supabase GraphQL API para consultas complexas e unificadas pelo N8N.
15. Integrar filas (`Queues`) via pgmq para tarefas de processamento longo na base de dados.
16. Implementar Supabase Vault pra tokens encriptados no nível de colunas e dados criptografados sensíveis de PIIS.
17. Fazer queries de re-indexação na PostgreSQL periodicamente pra performance e query tunning.
18. Limpar e otimizar conexões (Pooler PgBouncer) do DB para o Backend.
19. Replicar DB pra read-replicas de alta disponibilidade.
20. Mapear schema para views e functions PostgreSQL.

## Squad C: API Backend (Tasks 21-30)
21. Escrever e documentar as roles/scopes no Fastapi pra cada token HMAC ou API Key.
22. Testar e otimizar endpoints MCP, refazendo benchmarks de latência (< 500ms).
23. Atualizar Swagger Docs e gerar nova documentação OpenApi.
24. Adicionar endpoints para relatórios estatísticos (quantos emolumentos calculados).
25. Mover lógica linear pesada (loops O(N)) para lookups O(1) com dicionários pra cache in-memory.
26. Auditar as camadas de `_get_lgpd_consent` para 100% cobrir as tools MCP.
27. Reduzir as dependências inutilizadas em `pyproject.toml`.
28. Adicionar Rate Limits globais com Redis pra IP + user-agent além da sessão normal.
29. Aprimorar formatação global do código via `ruff format` em pre-commits.
30. Escrever mais testes unitários na API cobrindo mocks de PII Scrubbing.

## Squad D: Integração N8N (Tasks 31-40)
31. Auditar `infra/n8n-workflows` substituindo tokens por `$env.CARTORIO_API_KEY`.
32. Testar todos os 34 workflows N8N ativos um por um com payloads mockados.
33. Configurar error nodes e dead-letter queues no N8N pra falhas silenciosas.
34. Atualizar N8N workflows com documentação descritiva (`README` em markdown no workflow).
35. Ajustar e afinar timeouts pra webhook response e evitar "timeout apos 30s" atoa.
36. Criar scripts de import/export automatizado do N8N na VPS local.
37. Reduzir nodes excessivos no N8N em favor de processamento direto no MCP server (backend).
38. Melhorar regex de filtros do N8N antes do envio da mensagem pra API/LLM.
39. Validar fallback dos LLM models via N8N caso a primária caia.
40. Refinar o roteamento de prioridade "HITL" no N8N pra Chatwoot.

## Squad E: OpenClaw e Modelos AI (Tasks 41-50)
41. Testar o envio de "thinkings" do Openclaw com perguntas complexas via prompt no log.
42. Refinar persona no `SOUL.md` sem emojis, mais séria, direta e resolutiva.
43. Remover limitação hardcoded do context pra todos outros LLM (Sonnet, GPT) pra 1M e superior.
44. Auditar logs para uso do `deepseek-v4-flash` pra conferir latência.
45. Limpar `AGENTS.md` tirando exemplos antigos de context windows obsoletos.
46. Testar Handoff no OpenClaw via commands (`/humano`).
47. Testar limites do `prompt caching` no Minimax e deepseek.
48. Analisar output JSON do OpenClaw format adherence (schema validators pydantic em cima).
49. Testar limite de sessão e heartbeats long-running session recov com OpenClaw.
50. Testar hooks `pre-response` e `post-response` no agent.

## Squad F: Chatwoot e CRM (Tasks 51-60)
51. Configurar triggers automáticos no Chatwoot baseados na flag "urgente" no N8N.
52. Refinar bot/human handoff (pausar AI e transferir bot).
53. Fazer painel para visualização de filas no Chatwoot para gerentes.
54. Criar rotinas no Chatwoot API de arquivamento das conversas velhas.
55. Usar labels dinâmicos de atendimento (ex: `emolumento-ativo`).
56. Avaliar e aprimorar Chatwoot Inbox channels limit.
57. Integrar pesquisa NPS diretamente pelo Chatwoot no fim do ticket.
58. Otimizar Sidekiq performance pra evitar fila enchendo (Redis queue limits).
59. Analisar integrações nativas de webhooks e Chatwoot events API e otimizar re-try mechanisms.
60. Mapear o DRAFT protocol no chatwoot widget pros humanos.

## Squad G: Evolution API (Tasks 61-70)
61. Checar os webhooks da Evolution API, confirmando tempo de entrega de mensagens (SLA < 1s).
62. Configurar auto-read receipts dependendo da mensagem da Evolution.
63. Configurar re-envio em caso da network evolution cair (Failsafe Mechanism).
64. Analisar e ajustar envio de mídia, templates nativos via WABA.
65. Otimizar proxy traefik pra rate limits em endpoints da Evolution API.
66. Sincronizar cache de profiles do WhatsApp pra cache in-memory local.
67. Criar test-suite exclusivo pra Evolution-API no backend (`test_evolution_e2e.py`).
68. Mapear e corrigir status erráticos no callback.
69. Configurar timeout no evolution API de conexão de instancia.
70. Refinar LGPD e Evolution ingest pra ignorar mensagens deletadas pelo user.

## Squad H: LGPD, Segurança e Auditoria (Tasks 71-80)
71. Auditar PII Scrubber para regex de CPFs formatados incorretamente e vazados acidentalmente.
72. Auditar HMAC SHA-256 e constantes timing comparisons no hashing de keys de requests.
73. Checar retention policies de logs antigos se estão mesmo deletando > 1825 dias.
74. Adicionar sanitização de HTML/Markdown nos relatórios gerados do cartório.
75. Revisar todos endpoints e garantir que dependam de key/auth (onde aplicável, tirando public).
76. Refatorar JWT generation pra usar chaves mais fortes/ED25519 (se aplicável).
77. Automatizar scan de secrets nos commits (Gitleaks, pre-commits).
78. Rodar pentest básico no Traefik exposto.
79. Revisar "Consent gate" e verificar exceções que bypassam indevidamente.
80. Revisar Audit Service e adicionar IP ban local contra rate limits massivos.

## Squad I: Documentação e Conhecimento (Tasks 81-90)
81. Atualizar Documentação Completa N8N workflows.
82. Atualizar Documentação Completa Supabase config/RLS.
83. Atualizar Documentação Completa Chatwoot architecture.
84. Atualizar Documentação Completa Evolution API e proxies.
85. Documentação em Markdown sobre estrutura PII scrubber e LGPD logic pros devs.
86. Gerar diagramas UML da Arquitetura do EVOLUTION -> API -> N8N -> CHATWOOT.
87. Adicionar comentários explicativos robustos nas functions MCP do backend.
88. Registrar `AGENTS.md` e regras explícitas em todas as pastas raiz.
89. Organizar `.brain` em categorias pra agente consumir melhor de 1 em 1.
90. Criar documento do "Plano de Incidentes de Queda do Gateway/LLM".

## Squad J: Interface, Frontend e Playwright (Tasks 91-100)
91. Validar Playwright tests no Frontend local.
92. Avaliar foco na UI com double box-shadow nas interfaces do Supabase / Control UI (onde há acesso web local).
93. Utilizar ARIA attributes pra screen readers em outputs dinâmicos da interface web dashboard.
94. Otimizar as CSS classes do Dash/Chat evitando inline styles e preferindo variáveis CSS.
95. Verificar renderização dos PII placeholders na interface de auditoria interna.
96. Testar dashboard do controle de agente em mobile resoluções no playwright.
97. Otimizar imagens do site (WebP) na CDN.
98. Escrever documentação pro painel frontend interno de administração.
99. Adicionar feedback visual (`toast` polido) pra botões de Ação na Dashboard local.
100. Implementar modo dark global suportando system preferences de CSS `prefers-color-scheme`.
