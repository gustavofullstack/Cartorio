# SUPER PLANO DE MELHORIAS - 100 TASKS (Iteração Contínua)
**Data**: $(date +%Y-%m-%d)
**Objetivo**: Analisar, Testar, Corrigir, Melhorar, Otimizar, Organizar e Documentar a Infraestrutura e Aplicação do Cartório (API, N8N, Chatwoot, Evolution-API, OpenClaw, Redis, Supabase, Telegram Bot). Foco total em iterar sobre o que existe, garantindo 100% de estabilidade, integração completa, observabilidade total e adoção integral de boas práticas de LLMs e Infra.

---

## 🟢 SQUAD 1 - S1: API FastAPI Core (Estabilização e Otimização)
- [ ] **T1**: Otimizar rotas de Emolumentos (`/api/v1/emolumento/calcular`) implementando Redis Cache direto e validando dependência de banco de dados (`func.count()`).
- [ ] **T2**: Revisar logs de erro e warnings (Ruff/Mypy/Sentry) e garantir supressão elegante sem ofuscar falhas reais.
- [ ] **T3**: Expandir Testes Unitários de API para endpoints negligenciados. Rodar de forma cirúrgica (por arquivo/diretório).
- [ ] **T4**: Auditar Middleware de Audit Chain e LGPD, garantindo PII Scrubber ativo em todas as rotas e payloads recebidos.
- [ ] **T5**: Consolidar e otimizar Rate Limiting usando a estrutura Redis existente, bloqueando brute-forces na camada FastAPI (fail-open resiliente).
- [ ] **T6**: Refatorar lógicas de Handoff na API para que respondam mais rápido ao Chatwoot/N8N via BackgroundTasks.
- [ ] **T7**: Adicionar testes E2E específicos para o webhook da Evolution-API na API.
- [ ] **T8**: Refinar as validações Pydantic V2 para que os erros retornem mensagens user-friendly (PT-BR) e não vazem detalhes de esquema.
- [ ] **T9**: Configurar Prometheus custom metrics na API (tempo de PII scrub, taxa de acerto do cache, tempos de resposta LLM no gateway).
- [ ] **T10**: Revisar o arquivo `.env.example` e secret rotation guides (mesmo sem rotacionar chaves, a doc deve estar coerente).

## 🟢 SQUAD 2 - S2: N8N (Workflows, Integrações e Resiliência)
- [ ] **T11**: Auditar e organizar todos os workflows do N8N (1 a 11), categorizando-os e comentando cada step complexo.
- [ ] **T12**: Configurar Dead Letter Queue (DLQ) global e rotinas de Retry no N8N (Exp Backoff já previsto, testar funcionalidade).
- [ ] **T13**: Validar integração N8N ↔ Supabase (CRUD via Node Oficial).
- [ ] **T14**: Refinar integração N8N ↔ Redis para controle de state das conversas e idempotência de Webhooks.
- [ ] **T15**: Analisar os workflows atuais e identificar onde as requisições estão falhando ou lentas. Otimizar chamadas HTTP.
- [ ] **T16**: Implementar verificação de HMAC/Assinatura em todos os webhooks N8N para máxima segurança.
- [ ] **T17**: Revisar o nó "Monitor Cartório" para garantir que ele rode sem gerar gargalo ou timeout no runner externo.
- [ ] **T18**: Atualizar dependências e plugins comunitários no ambiente N8N (Evolution-API, Chatwoot) - validando as integrações com os endpoints locais.
- [ ] **T19**: Adicionar anotações "LGPD" dentro dos Workflows N8N indicando onde o dado mascarado transita e onde é persistido.
- [ ] **T20**: Testar E2E do Handoff (Evolution -> N8N -> Chatwoot -> API -> N8N) e logar os gargalos de performance.

## 🟢 SQUAD 3 - S3: OpenClaw Agent (Inteligência Artificial, Modelos e Contexto)
- [ ] **T21**: Validar o carregamento do `cartorio-bot.openclaw.json` com `deepseek-v4-flash`, 1M context e Thinking Mode ativados.
- [ ] **T22**: Integrar o OpenClaw Agent com o MCP da API, validando todas as Tools via chamadas simuladas.
- [ ] **T23**: Auditar o system_prompt do OpenClaw para ser direto, sério, sem emojis e com rigor máximo em LGPD e Emolumentos.
- [ ] **T24**: Testar as Fallback Chains do OpenClaw (MiniMax, mimo, etc.) e garantir que o transition time é < 2s.
- [ ] **T25**: Monitorar token consumption (Codex-Bar) da engine `deepseek-v4-flash` via logs do gateway.
- [ ] **T26**: Revisar hooks on_message_in e on_response_out (PII Scrub e Audit) do gateway OpenClaw.
- [ ] **T27**: Otimizar a persistência de sessão e janela deslizante no OpenClaw (evitar estouro dos 1M de token com sumarização).
- [ ] **T28**: Revisar integração do OpenClaw com Chatwoot (pausar bot quando escrevente assume o controle).
- [ ] **T29**: Adicionar logs detalhados de RAG/Thinking Process do deepseek no OpenClaw (para depuração via API).
- [ ] **T30**: Documentar as skills do OpenClaw atualizadas dentro da `infra/openclaw-agent/skills/`.

## 🟢 SQUAD 4 - S4: Supabase Core & Banco de Dados
- [ ] **T31**: Configurar backups automáticos, cron e pg_dump no Supabase.
- [ ] **T32**: Implementar e testar Supabase Database Webhooks para tabelas sensíveis (notificar API de alterações críticas).
- [ ] **T33**: Utilizar Supabase Edge Functions / Cron para rotinas de manutenção e limpeza (ex: excluir chats velhos base na política LGPD).
- [ ] **T34**: Habilitar e configurar o Supabase Vault para dados sensíveis em repouso.
- [ ] **T35**: Otimizar RLS (Row Level Security) nas 134 tabelas e garantir acessos apenas por Auth validado ou Service Role.
- [ ] **T36**: Habilitar Supabase Queues (pgmq) e transferir tarefas pesadas da API para filas (geração de PDF, cálculos massivos).
- [ ] **T37**: Implementar introspecção Supabase GraphQL para dashboards internos seguros.
- [ ] **T38**: Monitorar performance (pg_stat_statements) do Supabase via queries lentas e criar índices necessários.
- [ ] **T39**: Auditar uso de conexões (Connection Pooling / Supavisor) para garantir estabilidade em picos.
- [ ] **T40**: Atualizar diagramas ER da documentação Supabase e relacionamentos críticos de Audit/Emolumentos.

## 🟢 SQUAD 5 - S5: Telegram Bot e Testes Multi-Canal
- [ ] **T41**: Garantir funcionamento 100% do Telegram Bot (`@TestCartorioBot`) com o webhook configurado e seguro (`8859206262:AAHNZ1a5L9O0U_4sXXTWQAVtEI4BnQjPH_Q`).
- [ ] **T42**: Criar fluxos de testes de integração via script Python para mandar/receber via Telegram, validando a via expressa da IA.
- [ ] **T43**: Tratar Edge-cases do Telegram (mídia pesada, áudio, contatos) via N8N ou OpenClaw.
- [ ] **T44**: Garantir que as restrições LGPD se apliquem ao Telegram de forma isolada do WhatsApp (termo de aceite próprio).
- [ ] **T45**: Auditar latência ponta a ponta (Bot -> API -> OpenClaw -> Supabase -> API -> Bot) e fixar metas < 2.5s.
- [ ] **T46**: Atualizar a documentação do Telegram Guide, removendo configs de desenvolvimento obsoletas.
- [ ] **T47**: Configurar botão "Falar com Humano" nativo no Telegram e garantir Handoff para o Chatwoot.
- [ ] **T48**: Assegurar idempotência total no recebimento das mensagens do Telegram Webhook via Redis.
- [ ] **T49**: Validar o comando /start para resetar sessões sem quebrar o log de auditoria.
- [ ] **T50**: Adicionar suporte básico de Web Apps no Telegram (se necessário para envio seguro de docs).

## 🟢 SQUAD 6 - S6: Chatwoot e CRM
- [ ] **T51**: Auditar caixas de entrada (Inboxes) do Chatwoot e garantir segmentação correta (WhatsApp vs Telegram vs Web).
- [ ] **T52**: Testar macros e "Canned Responses" no Chatwoot para os escreventes.
- [ ] **T53**: Verificar integração de Webhooks do Chatwoot para sinalizar fim de Handoff (Escrevente fechou o chat -> Bot reassume).
- [ ] **T54**: Configurar a UI do Chatwoot para exibição correta dos campos customizados (Protocolo, CPF Mascarado, Status Emolumento).
- [ ] **T55**: Analisar os Sidekiq workers do Chatwoot no docker swarm para garantir que não haja memory leaks / restart loops.
- [ ] **T56**: Criar Dashboard no Chatwoot (via scripts em app) para relatórios rápidos de atendimento e SLA de tempo de resposta.
- [ ] **T57**: Garantir que mensagens do Chatwoot sejam integradas ao Audit Chain e sincronizadas no Supabase de forma segura.
- [ ] **T58**: Melhorar a identificação de Leads Prospectados (S8 do ROADMAP) diretamente no Chatwoot CRM.
- [ ] **T59**: Realizar backup das configurações e contatos atuais do Chatwoot (via API e pg_dump).
- [ ] **T60**: Escrever "Runbook do Escrevente" atualizado para uso do CRM sem quebrar compliance LGPD.

## 🟢 SQUAD 7 - S7: Evolution-API e Gateway WhatsApp
- [ ] **T61**: Auditar estabilidade da Evolution-API v2.3.7 e checar conexões TypeBot / Webhook / RabbitMQ.
- [ ] **T62**: Otimizar payloads do Webhook da Evolution (enviar só o necessário para a API / N8N).
- [ ] **T63**: Implementar tratamento robusto para mensagens multimídia no WhatsApp (imagem para OCR de CNH/RG no futuro, hoje ignorar graciosamente).
- [ ] **T64**: Melhorar gestão de status (HOLD_QR, CONNECTED, DISCONNECTED) e disparar alertas via N8N caso a instância caia.
- [ ] **T65**: Documentar fluxo de rate limit no envio do Evolution-API para não tomar block do WhatsApp.
- [ ] **T66**: Testar envios massivos (Prospecção) controlados pela API (N8N) com atraso randômico (human-like delay).
- [ ] **T67**: Checar idempotência no recebimento das mensagens do WhatsApp, usando Redis e TTL 24h.
- [ ] **T68**: Configurar labels e tags da Evolution para refletir no Chatwoot / Supabase.
- [ ] **T69**: Testar formatações de markdown (negrito, itálico) recebidas do OpenClaw e enviadas via Evolution.
- [ ] **T70**: Implementar rotina "Dead Man's Switch" na Evolution-API (reiniciar docker container via Easypanel API se ping falhar seguidamente).

## 🟢 SQUAD 8 - S8: Infraestrutura Easypanel, Redis, Traefik & Networking
- [ ] **T71**: Auditar uso de memória no VPS master Hostinger (Easypanel metrics) e propor limites seguros (`--limit-memory`) nos containers.
- [ ] **T72**: Configurar persistência e políticas de AOF/RDB no Redis. Monitorar chaves não deletadas (memory leak de cache).
- [ ] **T73**: Auditar domínios, proxies e certificados Let's Encrypt no Traefik (Easypanel). Garantir renovação ok.
- [ ] **T74**: Otimizar rede Overlay do Swarm/Easypanel para menor latência na ponte Supabase -> API -> N8N.
- [ ] **T75**: Testar comunicação direta via IPs Docker vs DNS Swarm para isolar problemas de rede relatados no passado.
- [ ] **T76**: Avaliar segurança do acesso ao Easypanel Admin via Browser Agent AI e via Tailscale.
- [ ] **T77**: Implementar logs unificados (Grafana Loki ou semelhante via plugins locais) se aplicável, ou padronizar saídas stdout.
- [ ] **T78**: Configurar healthchecks no Docker Compose / Swarm para todos os serviços com restart policy robusta.
- [ ] **T79**: Atualizar configurações do Tailscale no servidor e garantir rotas MagicDNS corretas e persistentes.
- [ ] **T80**: Testar bloqueios de Firewall (Fail2Ban/Crowdsec) via Traefik labels limitando IPs abusivos (Rate Limiting dinâmico).

## 🟢 SQUAD 9 - S9: UX, Dashboards Internos & Frontend Tooling
- [ ] **T81**: Revisar e rodar o `dashboard.py` local no diretório `operations-dashboard` garantindo geração sem bugs visuais.
- [ ] **T82**: Corrigir bugs de acessibilidade CSS e foco (`:focus-visible` vs `:hover`) nas telas dinâmicas do front.
- [ ] **T83**: Padronizar as views para o Escrevente/CEO consumirem os logs PII free via interface (ao invés do Supabase cru).
- [ ] **T84**: Refinar Scripts Python para gerar painéis HTML estáticos do plano (como o `SUPER_STATUS.html`).
- [ ] **T85**: Implementar visualização do Flow "Evolution-API -> API -> N8N -> Chatwoot -> Redis -> Supabase" num mini dashboard de Health.
- [ ] **T86**: Garantir que as validações e testes Playwright cubram os componentes cruciais do Webchat / Dashboard.
- [ ] **T87**: Limpar dependências obsoletas de frontend/dashboard (ex: npm/pnpm files erráticos se houver).
- [ ] **T88**: Otimizar renderização do dashboard usando JS/CSS minificado quando gerado pelo Python (ex. Jinja templates).
- [ ] **T89**: Verificar renderização Mobile dos dashboards e UI gerada.
- [ ] **T90**: Garantir que nenhum artefato de build (`index.html` gerado dinâmico) faça diff monstruoso no git, usando gitignore apropriadamente.

## 🟢 SQUAD 10 - S10: Organização, Memória e Documentação (Agent Brain)
- [ ] **T91**: Compilar um arquivo `.jules/sentinel.md` atualizado com logs de segurança (sem detalhes sensíveis expostos, focando na prevenção).
- [ ] **T92**: Consolidar aprendizados de Frontend/UX no arquivo `.jules/palette.md` de acordo com a memória.
- [ ] **T93**: Atualizar PROGRESS.md e GOALS.md para refletir o status exato pós-correções, mantendo integridade histórica.
- [ ] **T94**: Criar arquivo `ROADMAP_JSON_COMPACT.json` espelhando este SUPER PLANO para uso otimizado de LLMs de contexto curto.
- [ ] **T95**: Remover arquivos de teste ou scripts temporários, limpando a workspace de patches soltos (`*.patch`, `*.orig`).
- [ ] **T96**: Testar e garantir aderência estrita de todas as novas rotas/modificações no arquivo `AGENTS.md` pertinente.
- [ ] **T97**: Padronizar Commit Messages em todo o processo para seguir as diretrizes.
- [ ] **T98**: Medir e salvar logs de consumo (Codex-Bar) das APIs da plataforma ao longo das sessões.
- [ ] **T99**: Gerar um relatório resumido de "Integrações 100% Funcionais" para aprovação do CEO.
- [ ] **T100**: Fazer pre-commit instructions e verificação final cruzada e declarar o MVP pronto para uso real (Produção Go-Live Final).
