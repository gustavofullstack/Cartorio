# Glossário Cartório — Termos Técnicos e Jurídicos

> Glossário completo de termos usados no projeto (técnicos + cartoriais + jurídicos).
> Última atualização: 2026-06-26.

## Índice

1. [Termos Cartoriais](#1-termos-cartoriais)
2. [Termos Jurídicos](#2-termos-jurídicos)
3. [Termos Técnicos - Infraestrutura](#3-termos-técnicos---infraestrutura)
4. [Termos Técnicos - Backend](#4-termos-técnicos---backend)
5. [Termos Técnicos - Banco de Dados](#5-termos-técnicos---banco-de-dados)
6. [Termos LGPD / Compliance](#6-termos-lgpd--compliance)
7. [Termos de Atendimento](#7-termos-de-atendimento)
8. [Siglas e Acrônimos](#8-siglas-e-acrônimos)
9. [Nomes Próprios do Sistema](#9-nomes-próprios-do-sistema)
10. [Termos em Inglês (Gírias Tech)](#10-termos-em-inglês-gírias-tech)

---

## 1. Termos Cartoriais

| Termo | Definição |
|-------|-----------|
| **Tabelião / Tabeliã** | Notário que dirige o cartório e tem fé pública |
| **Tabelionato de Notas** | Cartório onde se lavram instrumentos públicos (escrituras, procurações, atas, etc) |
| **Fé Pública** | Atribuição do Estado dada ao tabelião para autenticar atos |
| **Escritura Pública** | Instrumento público lavrado pelo tabelião em livro próprio |
| **Procuração** | Instrumento pelo qual uma pessoa outorga poderes a outra para agir em seu nome |
| **Reconhecimento de Firma** | Ato pelo tabelião atesta que a assinatura é autêntica |
| **Autenticação** | Cópia fiel de documento conferida com o original |
| **Ata Notarial** | Documento que registra fato ou situação presenciada pelo tabelião |
| **Testamento** | Ato personalíssimo pelo qual alguém dispõe sobre seus bens para depois da morte |
| **Selo / Selo Digital** | Elemento de segurança (físico ou eletrônico) que garante autenticidade |
| **Emolumento** | Valor cobrado por serviço notarial (tabela oficial do Estado) |
| **Notificação** | Ato pelo qual se dá ciência de algo a alguém |
| **Registro Civil** | Registro de nascimentos, casamentos, óbitos (não é Notas) |
| **Registro de Imóveis** | Registro de propriedades (não é Notas) |
| **RTD / RTDPJ** | Registro de Títulos e Documentos / Pessoas Jurídicas |
| **CNS** | Código Nacional de Selos (identifica cada selo digital) |
| **Código de Segurança** | Hash alfanumérico do selo digital |

---

## 2. Termos Jurídicos

| Termo | Definição |
|-------|-----------|
| **CPF** | Cadastro de Pessoas Físicas (Receita Federal) |
| **CNPJ** | Cadastro Nacional da Pessoa Jurídica |
| **RG** | Registro Geral (documento de identidade) |
| **CNH** | Carteira Nacional de Habilitação |
| **CTPS** | Carteira de Trabalho e Previdência Social |
| **PIS/PASEP** | Programa de Integração Social |
| **Título de Eleitor** | Documento que permite voto |
| **CRC** | Conselho Regional de Contabilidade |
| **OAB** | Ordem dos Advogados do Brasil |
| **CREA** | Conselho Regional de Engenharia e Agronomia |
| **ANPD** | Autoridade Nacional de Proteção de Dados |
| **ANOREG/BR** | Associação dos Notários e Registradores do Brasil |
| **CNJ** | Conselho Nacional de Justiça |
| **Provimento** | Ato administrativo do CNJ que regulamenta serviços notariais |
| **Código Civil** | Lei 10.406/2002 |
| **Código de Processo Civil** | Lei 13.105/2015 |
| **LGPD** | Lei Geral de Proteção de Dados (Lei 13.709/2018) |
| **RIPD** | Relatório de Impacto à Proteção de Dados |
| **Titular** | Pessoa natural a quem os dados pessoais se referem |
| **Controlador** | Quem toma decisões sobre o tratamento de dados |
| **Operador** | Quem realiza o tratamento em nome do controlador |
| **Encarregado/DPO** | Pessoa indicada para ser o canal de comunicação entre controlador, titulares e ANPD |

---

## 3. Termos Técnicos - Infraestrutura

| Termo | Definição |
|-------|-----------|
| **VPS** | Virtual Private Server (servidor virtual privado) |
| **Hostinger** | Empresa de hosting (onde fica nossa VPS) |
| **Easypanel** | UI/gerenciador para Docker Swarm |
| **Docker Swarm** | Orquestrador de containers (modo nativo do Docker) |
| **Container** | Unidade de execução isolada de uma aplicação |
| **Service (Swarm)** | Definição declarativa de como rodar um container (replicas, network, etc) |
| **Stack (Swarm)** | Conjunto de services relacionados |
| **Volume (Docker)** | Armazenamento persistente para containers |
| **Network (Docker)** | Rede virtual isolada entre containers |
| **Traefik** | Reverse proxy moderno com SSL automático |
| **Let's Encrypt** | Autoridade certificadora que emite SSL grátis |
| **Tailscale** | VPN WireGuard zero-config |
| **Cloudflare** | CDN + DNS + WAF + DDoS protection |
| **DNS A Record** | Mapeamento domínio → IP |
| **SSL/TLS** | Protocolo de criptografia HTTPS |
| **Port (Porta)** | Número lógico que identifica um serviço (80, 443, 5678, etc) |
| **Bind Mount** | Mapeamento diretório host ↔ container |
| **Healthcheck** | Endpoint que reporta saúde de um serviço |
| **Restart Policy** | Política de reinício (always, on-failure, etc) |
| **Rolling Update** | Atualização sem downtime (substitui containers gradualmente) |

---

## 4. Termos Técnicos - Backend

| Termo | Definição |
|-------|-----------|
| **API** | Application Programming Interface (interface de programação) |
| **REST** | Representational State Transfer (estilo arquitetural) |
| **FastAPI** | Framework web Python assíncrono de alta performance |
| **Endpoint** | URL de uma API (ex: `/api/v1/clientes`) |
| **Pydantic** | Biblioteca de validação de dados (V2 com ConfigDict) |
| **SQLAlchemy** | ORM Python para SQL |
| **Alembic** | Ferramenta de migrations para SQLAlchemy |
| **ORM** | Object-Relational Mapping (mapeamento objeto↔tabela) |
| **Async / Await** | Programação assíncrona (corrotinas) |
| **Corrotina** | Função que pode ser pausada e resumida |
| **Middleware** | Código que intercepta requisições antes do endpoint |
| **Dependency Injection** | Padrão onde dependências são injetadas (FastAPI Depends) |
| **Pydantic Schema** | Modelo de validação de entrada/saída |
| **DTO** | Data Transfer Object (objeto de transferência de dados) |
| **Webhook** | Callback HTTP acionado por evento externo |
| **MCP** | Model Context Protocol (protocolo de tools para LLMs) |
| **FastMCP** | Implementação Python do MCP |
| **WebSocket** | Protocolo de comunicação full-duplex sobre TCP |
| **JWT** | JSON Web Token (token de autenticação) |
| **OAuth2** | Protocolo de autorização |
| **HMAC** | Hash-based Message Authentication Code |
| **PII** | Personally Identifiable Information (dados pessoais) |
| **PII Scrub** | Remoção de PII antes de logar/processar |
| **Problem Details (RFC 7807 / 9457)** | Formato padrão de resposta de erro HTTP |
| **OpenAPI** | Especificação de API (ex-Swagger) |
| **CORS** | Cross-Origin Resource Sharing |
| **Rate Limiting** | Limitação de requisições por cliente |
| **Idempotência** | Garantia que múltiplas execuções produzem mesmo resultado |
| **Retry Policy** | Política de retentativas em caso de falha |
| **Exponential Backoff** | Retry com espera crescente (1s, 2s, 4s, 8s, ...) |
| **Circuit Breaker** | Padrão que para de chamar serviço com falhas |
| **Dead Man's Switch** | Alerta quando algo esperado NÃO acontece (ex: audit log parou) |
| **Slow Query** | Query SQL com latência acima do threshold |
| **Pool de Conexões** | Cache de conexões DB reutilizáveis |
| **Connection Pool** | Idem (em inglês) |
| **Health Check / Health Radar** | Endpoint que verifica saúde de múltiplos serviços |
| **Correlation ID** | ID único que rastreia uma requisição através de múltiplos serviços |
| **Audit Log** | Log de auditoria (todas as ações do sistema) |
| **Audit Trail** | Trilha de auditoria (histórico completo) |
| **Versionamento /api/v1, /api/v2** | Versionamento de API por URL |
| **Soft Delete** | Exclusão lógica (campo deleted_at) vs hard delete |
| **Materialized View** | View SQL materializada fisicamente para performance |
| **Cache Hit / Cache Miss** | Se query encontrou no cache ou precisou ir ao DB |
| **TTL** | Time To Live (tempo de vida do cache) |
| **Pub/Sub** | Publish/Subscribe (mensageria assíncrona) |
| **Redlock** | Algoritmo de lock distribuído com Redis |

---

## 5. Termos Técnicos - Banco de Dados

| Termo | Definição |
|-------|-----------|
| **PostgreSQL** | Banco de dados relacional open source (usamos 15+) |
| **Supabase** | Plataforma de BaaS (Backend as a Service) com Postgres |
| **Tabela** | Estrutura de dados relacional (linhas × colunas) |
| **Schema** | Namespace dentro do banco (public, auth, storage, etc) |
| **RLS** | Row Level Security (segurança por linha) |
| **Policy** | Regma de RLS (USING, WITH CHECK) |
| **PostgREST** | API REST automática em cima do Postgres |
| **pg_graphql** | Extensão para GraphQL nativo do Postgres |
| **pgmq** | Postgres Message Queue (filas) |
| **pg_cron** | Cron jobs nativos do Postgres |
| **pg_net** | Cliente HTTP nativo do Postgres |
| **pg_audit** | Auditoria nativa do Postgres |
| **pg_vector** | Extensão para embeddings/busca semântica |
| **pg_notify** | Mecanismo de notificação assíncrona |
| **Trigger** | Função executada automaticamente em INSERT/UPDATE/DELETE |
| **Função (SQL)** | Procedure armazenada no DB |
| **RPC** | Remote Procedure Call (chamada de função remota) |
| **Outbox Pattern** | Padrão de mensageria confiável com tabela outbox |
| **Migration** | Script de evolução do schema (criado por Alembic) |
| **Alembic Head** | Última versão do schema |
| **Drift (Alembic)** | Divergência entre schema real e versionado |
| **Alembic Stamp** | Marcar manualmente uma versão sem rodar migration |
| **WAL** | Write-Ahead Log (log de transações Postgres) |
| **pg_basebackup** | Backup físico do cluster Postgres |
| **Backup Logical** | Backup via pg_dump (SQL) |
| **Backup Physical** | Backup via pg_basebackup (binário) |
| **Foreign Key** | Restrição de integridade referencial |
| **Índice** | Estrutura para acelerar queries |
| **View** | Query SQL nomeada e reusável |
| **Materialized View** | View com resultado armazenado fisicamente |
| **JSON / JSONB** | Tipo de dado para JSON (JSONB indexável) |
| **UUID** | Identificador único universal |
| **Timestamptz** | Timestamp com timezone (recomendado) |
| **INET** | Tipo nativo para IPs |
| **CITEXT** | Tipo case-insensitive text |

---

## 6. Termos LGPD / Compliance

| Termo | Definição |
|-------|-----------|
| **LGPD** | Lei Geral de Proteção de Dados (Lei 13.709/2018) |
| **ANPD** | Autoridade Nacional de Proteção de Dados (órgão regulador) |
| **Titular** | Pessoa natural a quem os dados se referem |
| **Controlador** | Quem decide o tratamento de dados (Cartório 2º Notas) |
| **Operador** | Quem trata dados em nome do controlador (Pietra, etc) |
| **Encarregado / DPO** | Data Protection Officer - canal entre titular, controlador e ANPD |
| **RIPD** | Relatório de Impacto à Proteção de Dados |
| **Consentimento** | Manifestação livre, informada e inequívoca do titular |
| **Base Legal** | Fundamentação para tratar dados (consentimento, contrato, legítimo interesse, etc) |
| **Finalidade** | Propósito do tratamento |
| **Necessidade** | Princípio de tratar só o mínimo necessário |
| **Adequação** | Princípio de adequar tratamento à finalidade |
| **Livre Acesso** | Direito do titular de acessar seus dados (D06) |
| **Portabilidade** | Direito de receber dados em formato estruturado (D08) |
| **Exclusão** | Direito de apagar dados desnecessários (D09) |
| **Correção** | Direito de corrigir dados incompletos ou incorretos (D07) |
| **Revogação** | Direito de revogar consentimento a qualquer momento |
| **Oposição** | Direito de se opor a tratamento |
| **Anonimização** | Técnica que torna dado não identificável (irreversível) |
| **Pseudonimização** | Técnica que substitui identificador direto por indireto (reversível com chave) |
| **Hash Reversível** | Hash que pode ser revertido com chave (usar com cuidado) |
| **PII** | Personally Identifiable Information |
| **Dado Pessoal** | Qualquer informação que identifique pessoa natural |
| **Dado Sensível** | Origem racial, convicção religiosa, opinião política, dado genético, biométrico, saúde, vida sexual |
| **Dado Anonimizado** | Dado que não pode mais ser associado ao titular |
| **Tratamento** | Toda operação com dados pessoais (coleta, armazenamento, uso, etc) |
| **Transferência Internacional** | Envio de dados para outro país |
| **Incidente de Segurança** | Evento que compromete confidencialidade, integridade ou disponibilidade |
| **Data Breach** | Vazamento de dados |
| **Notificação de Breach** | Comunicação obrigatória à ANPD em 72h (P0) |
| **Política de Privacidade** | Documento público que explica como dados são tratados |
| **Termo de Consentimento** | Documento de aceite explícito |
| **Política de Cookies** | Como cookies são usados |
| **Encarregado Designado** | DPO oficialmente designado |
| **Princípio da Finalidade** | Usar dados só para o fim declarado |
| **Princípio da Necessidade** | Coletar o mínimo necessário |
| **Privacy by Design** | Privacidade desde o design do sistema |
| **Privacy by Default** | Privacidade por padrão (configurações mais restritivas) |

---

## 7. Termos de Atendimento

| Termo | Definição |
|-------|-----------|
| **Cliente Novo** | Primeira interação com o cartório |
| **Cliente Recorrente** | Já tem cadastro/protocolo |
| **Atendimento** | Interação de serviço (WhatsApp, presencial, etc) |
| **Protocolo** | Identificador único de uma solicitação (LGPD) |
| **Status do Protocolo** | Aberto, Em Andamento, Concluído, Cancelado |
| **Agendamento** | Reserva de horário para atendimento presencial |
| **Slot** | Horário disponível na agenda |
| **Segunda Via** | Cópia adicional de documento |
| **Emolumento** | Valor tabelado do serviço |
| **HITL** | Human In The Loop (atendente intervém no bot) |
| **Bot Pausado** | Estado onde Pietra não responde (humano assumiu) |
| **Bot Retomado** | Estado onde Pietra volta a responder |
| **Macro** | Ação predefinida no Chatwoot (1-click) |
| **Canned Response** | Resposta pronta no Chatwoot |
| **Label / Tag** | Etiqueta de categorização |
| **Inbox** | Canal de atendimento (WhatsApp, Email, etc) |
| **Conversa** | Thread de mensagens com um cliente |
| **SLA** | Service Level Agreement (tempo máximo de resposta) |
| **SLO** | Service Level Objective (meta de qualidade) |
| **SLI** | Service Level Indicator (métrica de qualidade) |
| **CSAT** | Customer Satisfaction (pesquisa de satisfação) |
| **NPS** | Net Promoter Score (recomendação) |
| **FCR** | First Contact Resolution (resolvido no 1º contato) |
| **TMA** | Tempo Médio de Atendimento |
| **TME** | Tempo Médio de Espera |
| **Parecer** | Documento técnico/jurídico sobre um caso |

---

## 8. Siglas e Acrônimos

| Sigla | Significado |
|-------|-------------|
| **API** | Application Programming Interface |
| **REST** | Representational State Transfer |
| **HTTP/HTTPS** | HyperText Transfer Protocol / Secure |
| **TCP** | Transmission Control Protocol |
| **UDP** | User Datagram Protocol |
| **DNS** | Domain Name System |
| **CDN** | Content Delivery Network |
| **WAF** | Web Application Firewall |
| **DDoS** | Distributed Denial of Service |
| **CI/CD** | Continuous Integration / Continuous Deployment |
| **SDK** | Software Development Kit |
| **UI** | User Interface |
| **UX** | User Experience |
| **QA** | Quality Assurance |
| **SRE** | Site Reliability Engineering |
| **KPI** | Key Performance Indicator |
| **OKR** | Objectives and Key Results |
| **MVP** | Minimum Viable Product |
| **POC** | Proof of Concept |
| **ADR** | Architecture Decision Record |
| **RFC** | Request for Comments (especificação técnica) |
| **URL** | Uniform Resource Locator |
| **URI** | Uniform Resource Identifier |
| **UUID** | Universally Unique Identifier |
| **JWT** | JSON Web Token |
| **CORS** | Cross-Origin Resource Sharing |
| **CSRF** | Cross-Site Request Forgery |
| **XSS** | Cross-Site Scripting |
| **SQLi** | SQL Injection |
| **ORM** | Object-Relational Mapping |
| **CRUD** | Create, Read, Update, Delete |
| **ACL** | Access Control List |
| **RBAC** | Role-Based Access Control |
| **ABAC** | Attribute-Based Access Control |
| **SSO** | Single Sign-On |
| **MFA** | Multi-Factor Authentication |
| **TOTP** | Time-based One-Time Password |
| **HMAC** | Hash-based Message Authentication Code |
| **PII** | Personally Identifiable Information |
| **LGPD** | Lei Geral de Proteção de Dados |
| **DPO** | Data Protection Officer |
| **ANPD** | Autoridade Nacional de Proteção de Dados |
| **RIPD** | Relatório de Impacto à Proteção de Dados |
| **CPF** | Cadastro de Pessoas Físicas |
| **CNPJ** | Cadastro Nacional da Pessoa Jurídica |
| **RG** | Registro Geral |
| **CNH** | Carteira Nacional de Habilitação |
| **CNS** | Código Nacional de Selos |
| **ADR** | Acordo de Defesa (militar) - também Architecture Decision Record |
| **ANOREG** | Associação dos Notários e Registradores |
| **CNJ** | Conselho Nacional de Justiça |
| **MCP** | Model Context Protocol |
| **LLM** | Large Language Model |
| **AGI** | Artificial General Intelligence |
| **AI** | Artificial Intelligence |
| **ML** | Machine Learning |
| **NLP** | Natural Language Processing |
| **HITL** | Human In The Loop |
| **SLA** | Service Level Agreement |
| **SLO** | Service Level Objective |
| **SLI** | Service Level Indicator |
| **CSAT** | Customer Satisfaction Score |
| **NPS** | Net Promoter Score |
| **TMA** | Tempo Médio de Atendimento |
| **TME** | Tempo Médio de Espera |
| **FCR** | First Contact Resolution |
| **VPS** | Virtual Private Server |
| **OS** | Operating System |
| **HW** | Hardware |
| **SW** | Software |
| **DB** | Database |
| **WF** | Workflow (N8N) |
| **RT** | Real-Time |
| **E2E** | End-to-End |
| **TDD** | Test-Driven Development |
| **BDD** | Behavior-Driven Development |
| **DDD** | Domain-Driven Design |
| **SOLID** | Single responsibility, Open-closed, Liskov, Interface segregation, Dependency Inversion |
| **DRY** | Don't Repeat Yourself |
| **KISS** | Keep It Simple, Stupid |
| **YAGNI** | You Aren't Gonna Need It |
| **12-Factor** | Metodologia de apps cloud-native |

---

## 9. Nomes Próprios do Sistema

| Nome | Significado |
|------|-------------|
| **Pietra** | Agent AI (OpenClaw) que atende clientes |
| **Cartório Chatbot** | Nome informal do sistema |
| **Cartório 2º Notas** | Nome formal (2º Cartório de Notas de Uberlândia) |
| **2notasudi** | Abreviação para o domínio (Udi = Uberlândia) |
| **api / flow / whatsapp / chat / supbase / agent / easypanel** | Subdomínios do 2notasudi.com.br |
| **TriQ Hub** | Sister project (servidor Linux para testes WhatsApp) |
| **MacBook Pro Gus** | Máquina de dev (Gustavo) |
| **Tabela MG 2026** | Tabela oficial de emolumentos de Minas Gerais para 2026 |
| **Super Prompt v4.0.0** | Documento mestre de 2000+ linhas (este contexto) |
| **Brain / Cérebro** | Sistema de memória do agent (BRAIN squad) |
| **Squad** | Grupo de agents/tarefas (S0, A, B, C, D, E, H, J, BRAIN, DOCS) |
| **Loop Engineer** | Modo de operação contínua até completion |
| **Super Cérebro** | CEO + CTO + Orquestrador + Tech Lead + Senior + FullStack |

---

## 10. Termos em Inglês (Gírias Tech)

| Termo | Significado |
|-------|-------------|
| **Bug** | Erro no código |
| **Feature** | Funcionalidade |
| **Refactor** | Reorganizar código sem mudar comportamento |
| **Tech Debt** | Débito técnico (código subótimo que precisa melhorar) |
| **Hotfix** | Correção urgente em produção |
| **Patch** | Conjunto de mudanças pequenas |
| **Release** | Versão lançada |
| **Rollback** | Voltar para versão anterior |
| **Rollout** | Implantar gradualmente |
| **Deploy** | Implantar em produção |
| **Build** | Compilar/construir |
| **Test** | Teste |
| **Staging** | Ambiente de pré-produção |
| **Production / Prod** | Produção |
| **Sandbox** | Ambiente isolado para testes |
| **Mock** | Objeto/serviço simulado para testes |
| **Stub** | Implementação parcial para testes |
| **Fixture** | Dados de teste pré-definidos |
| **Coverage** | Cobertura de testes |
| **Lint / Linting** | Análise estática de código |
| **Type Check** | Verificação de tipos |
| **Hot Path** | Caminho crítico de performance |
| **Cold Path** | Caminho raramente executado |
| **Bottleneck** | Gargalo de performance |
| **Throughput** | Vazão (req/s) |
| **Latency** | Latência (ms) |
| **Jitter** | Variação de latência |
| **Backpressure** | Pressão de volta (quando consumidor é mais lento) |
| **Idempotent** | Operação que pode ser repetida sem efeito colateral |
| **Stateless** | Sem estado (cada request é independente) |
| **Stateful** | Com estado (memória entre requests) |
| **Long Polling** | Polling longo (cliente espera resposta) |
| **Server-Sent Events (SSE)** | Eventos do servidor para cliente |
| **WebSocket** | Conexão full-duplex |
| **gRPC** | RPC de alta performance (HTTP/2) |
| **GraphQL** | Query language para APIs |
| **Webhook** | Callback HTTP |
| **Polling** | Verificar periodicamente |
| **Cron** | Agendador de tarefas |
| **Worker** | Processo que executa tarefas em background |
| **Queue** | Fila de tarefas |
| **Topic** | Tópico (pub/sub) |
| **Fan-out** | Distribuir para múltiplos consumers |
| **Fan-in** | Agregar de múltiplos producers |
| **Race Condition** | Condição de corrida (2+ threads competem) |
| **Deadlock** | Impasse (2+ processos esperando um ao outro) |
| **Starvation** | Inanição (processo nunca consegue recurso) |
| **Thread-safe** | Seguro para uso com múltiplas threads |
| **Async** | Assíncrono |
| **Sync** | Síncrono |
| **Promise / Future** | Valor que será resolvido no futuro |
| **Callback** | Função chamada quando algo acontece |
| **Event-driven** | Orientado a eventos |
| **Stream** | Fluxo contínuo de dados |
| **Batch** | Lote |
| **Pipeline** | Sequência de transformações |
| **Side Effect** | Efeito colateral (mudança de estado) |
| **Pure Function** | Função pura (sem side effects) |
| **Immutability** | Imutabilidade |
| **Memoization** | Cache de resultados de funções |
| **Lazy Evaluation** | Avaliação tardia |
| **Eager Loading** | Carregamento antecipado |
| **N+1 Problem** | Problema clássico de ORM (1 query + N para cada item) |
| **Connection Pool** | Pool de conexões |
| **Memory Leak** | Vazamento de memória |
| **Garbage Collection** | Coleta de lixo |
| **Heap** | Área de memória dinâmica |
| **Stack** | Pilha de execução |
| **Segfault** | Segmentation Fault (acesso inválido de memória) |
| **OOM** | Out Of Memory |
| **DoS** | Denial of Service |
| **DDoS** | Distributed Denial of Service |
| **XSS** | Cross-Site Scripting |
| **CSRF** | Cross-Site Request Forgery |
| **SSRF** | Server-Side Request Forgery |
| **RCE** | Remote Code Execution |
| **LFI/RFI** | Local/Remote File Inclusion |
| **SQLi** | SQL Injection |
| **XXE** | XML External Entity |
| **0-day** | Vulnerabilidade desconhecida |
| **CVE** | Common Vulnerabilities and Exposures |
| **CVSS** | Common Vulnerability Scoring System |
| **Pentest** | Penetration Test |
| **Red Team** | Equipe ofensiva (testes) |
| **Blue Team** | Equipe defensiva (SOC) |
| **Purple Team** | Red + Blue juntos |
| **SOC** | Security Operations Center |
| **SIEM** | Security Information and Event Management |
| **IDS/IPS** | Intrusion Detection/Prevention System |
| **VPN** | Virtual Private Network |
| **TLS** | Transport Layer Security |
| **mTLS** | Mutual TLS |
| **PKI** | Public Key Infrastructure |
| **CA** | Certificate Authority |
| **CSR** | Certificate Signing Request |
| **OCSP** | Online Certificate Status Protocol |
| **CRL** | Certificate Revocation List |

---

## Recursos Adicionais

- **Glossário técnico-jurídico**: `/docs/platforms/GLOSSARY.md` (versão expandida 200+ termos)
- **Architecture Diagram**: `/docs/platforms/ARCHITECTURE_DIAGRAM.md` (9 diagramas Mermaid)
- **API Reference**: `/docs/API_QUICK_REFERENCE.md`
- **Troubleshooting**: `/docs/TROUBLESHOOTING.md`

---

**Mantido por**: Pietra (orquestrador)
**Próxima revisão**: 2026-07-02
**Versão**: 1.0.0
