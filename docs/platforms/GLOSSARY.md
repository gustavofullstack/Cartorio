# Cartório 2notas — Glossário de Termos Cartoriais + Técnicos

**Versão**: 1.0.0 (2026-06-26)
**Squad C** — Glossário para Agentes, Devs, Atendentes e DPO

---

## 1. Termos Cartoriais (Domínio de Negócio)

| Termo | Definição |
|-------|-----------|
| **Cartório** | Estabelecimento público onde se registram atos jurídicos (notas, protestos, registros). |
| **Tabelião / Tabeliã** | Dirige o cartório de notas. No Brasil, é concursado (cargo público). |
| **Notas (Cartório de)** | Tipo de cartório que lavra escrituras públicas, procurações, etc. |
| **Reconhecimento de Firma** | Ato pelo tabelião que verifica autenticidade de assinatura em documento. |
| **Procuração** | Documento pelo qual uma pessoa autoriza outra a agir em seu nome. |
| **Escritura Pública** | Documento lavrado por tabelião em livro de notas, com fé pública. |
| **Testamento** | Ato pelo qual pessoa dispõe de seus bens para depois de sua morte. |
| **Certidão** | Cópia autêntica de documento ou ato lavrado em cartório. |
| **Certidão de Casamento** | Cópia do registro de casamento (serve para diversos fins). |
| **Certidão de Nascimento** | Cópia do registro de nascimento. |
| **Certidão de Óbito** | Cópia do registro de óbito. |
| **Averbação** | Anotação à margem de um registro para modificar ou atualizar informações. |
| **Registro de Imóveis** | Tipo de cartório que registra propriedades (não é este cartório de notas). |
| **RTD / RCPJ** | Registro de Títulos e Documentos / Registro Civil de Pessoas Jurídicas. |
| **Protesto** | Ato formal de registrar a não-pagamento de um título (letra de câmbio, cheque). |
| **Selo / Selo Digital** | Forma de autenticação de atos cartoriais (comprovante de pagamento de emolumento). |
| **Selo Eletrônico** | Versão digital do selo, com assinatura digital ICP-Brasil. |
| **Emolumento** | Taxa/valor pago pelo serviço cartorial (regulamentado por lei estadual). |
| **Custas** | Despesas processuais adicionais (publicações, certidões, etc.). |
| **ISS** | Imposto Sobre Serviços (incide sobre emolumentos). |
| **FAARPEN** | Fundo Especial do Poder Judiciário (parte dos emolumentos vai para lá). |
| **MG (Estado)** | Minas Gerais (UF do Cartório 2º Notas de Uberlândia). |
| **Selo Fiscal Eletrônico** | Sistema MG de emissão de selos digitais. |

---

## 2. Termos Técnicos — API

| Termo | Definição |
|-------|-----------|
| **API (FastAPI)** | Application Programming Interface (Python 3.11+ com FastAPI v0.6.0). |
| **REST** | Representational State Transfer (estilo arquitetural para APIs web). |
| **Endpoint** | URL específica de uma API que aceita requisições (ex: `/api/v1/protocolos`). |
| **HTTP Methods** | GET (ler), POST (criar), PUT (atualizar), DELETE (remover), PATCH (atualizar parcial). |
| **Status Code** | Código de resposta (200 OK, 404 Not Found, 500 Internal Server Error, 401 Unauthorized). |
| **JSON** | JavaScript Object Notation (formato de troca de dados). |
| **Schema (Pydantic)** | Definição da estrutura de dados (validação automática). |
| **Pydantic V2** | Biblioteca Python para validação de dados (usar `model_config = ConfigDict(...)`). |
| **Path Parameter** | Parte variável da URL (ex: `/api/v1/cliente/{cliente_id}`). |
| **Query Parameter** | Parâmetros após `?` na URL (ex: `?limit=10&offset=0`). |
| **Request Body** | Dados enviados no body (JSON) da requisição. |
| **Response Body** | Dados retornados no body (JSON) da resposta. |
| **X-API-Key** | Header de autenticação usado para identificar o cliente da API. |
| **Bearer Token** | Tipo de token de autenticação (enviado no header `Authorization: Bearer <token>`). |
| **CORS** | Cross-Origin Resource Sharing (define quais origens podem acessar a API). |
| **Health Check** | Endpoint que retorna status do serviço (`/health` retorna 200 OK). |

---

## 3. Termos Técnicos — Banco de Dados (Supabase)

| Termo | Definição |
|-------|-----------|
| **Supabase** | Plataforma BaaS (Backend as a Service) baseada em PostgreSQL. |
| **PostgreSQL** | Sistema de gerenciamento de banco de dados relacional (open source). |
| **DB Schema** | Estrutura das tabelas, colunas, tipos e relações (`public` schema neste caso). |
| **Tabela** | Estrutura bidimensional (linhas e colunas) que armazena dados. |
| **Coluna** | Campo de uma tabela (com tipo definido: text, integer, boolean, jsonb, etc.). |
| **Primary Key (PK)** | Coluna que identifica unicamente cada linha (geralmente `id` UUID ou BIGSERIAL). |
| **Foreign Key (FK)** | Coluna que referencia PK de outra tabela (relacionamento). |
| **Index** | Estrutura de dados que acelera buscas (B-tree, Hash, GIN, etc.). |
| **RLS (Row Level Security)** | Segurança por linha (filtra dados baseado em usuário/papel). |
| **JWT (JSON Web Token)** | Token assinado usado para autenticação stateless. |
| **PostgREST** | API REST automática gerada direto do schema Postgres. |
| **GraphQL (pg_graphql)** | API GraphQL nativa do Postgres (extensão). |
| **pgmq** | Filas (queues) nativas do Postgres (processamento assíncrono). |
| **Realtime** | WebSocket que envia mudanças no DB em tempo real. |
| **pg_notify / LISTEN** | Mecanismo de notificação assíncrona entre processos do Postgres. |
| **Alembic** | Ferramenta de migrations para SQLAlchemy. |
| **Outbox Pattern** | Padrão para garantir consistência eventual (events em outbox table). |
| **Vault** | Armazenamento seguro de credenciais (Supabase Vault). |
| **Storage** | Armazenamento de arquivos (S3-compatible) no Supabase. |
| **Edge Functions** | Funções serverless (Deno) executadas no edge. |
| **pgvector** | Extensão para busca de similaridade em vetores (embeddings). |
| **pgaudit (ou custom)** | Trigger que registra todas as mudanças em audit_log. |

---

## 4. Termos Técnicos — N8N

| Termo | Definição |
|-------|-----------|
| **N8N** | Plataforma de automação de workflows (low-code, open source). |
| **Workflow** | Fluxo de tarefas automatizadas (representado como nodes conectados). |
| **Node** | Bloco de funcionalidade (ex: HTTP Request, Set, IF, etc.). |
| **Trigger** | Node que inicia o workflow (ex: Webhook, Schedule, Manual). |
| **Webhook** | Endpoint HTTP que recebe dados externos e dispara workflow. |
| **Credentials** | Credenciais salvas para uso em nodes (ex: API Key, OAuth Token). |
| **Expression (N8N)** | Sintaxe `{{ $json.field }}` para acessar dados de nodes anteriores. |
| **Sticky Note** | Nota visual no canvas do N8N (documentação inline). |
| **HTTP Request** | Node que faz chamadas HTTP (GET, POST, PUT, DELETE). |
| **Wait** | Node que pausa o workflow por um tempo determinado. |
| **IF** | Node que condiciona o fluxo baseado em uma expressão. |
| **Loop / SplitInBatches** | Node que itera sobre uma lista de itens. |
| **Error Trigger** | Node que captura erros e redireciona o fluxo. |
| **Sub-workflow** | Workflow que é chamado por outro workflow (reutilização). |
| **Execute Command** | Node que executa comandos no shell. |
| **Code (Function)** | Node que executa JavaScript customizado. |
| **Cron** | Expressão de agendamento (ex: `0 3 * * *` = todo dia às 3h). |
| **n8n-runner** | Processo separado que executa workflows (scaling horizontal). |
| **X-Correlation-ID** | Header que rastreia uma requisição através de múltiplos sistemas. |
| **MCP (Model Context Protocol)** | Protocolo para fornecer tools a LLMs. |

---

## 5. Termos Técnicos — LGPD

| Termo | Definição |
|-------|-----------|
| **LGPD** | Lei Geral de Proteção de Dados (Lei nº 13.709/2018, Brasil). |
| **DPO (Data Protection Officer)** | Encarregado de Proteção de Dados (responsável pelo LGPD na empresa). |
| **PII (Personally Identifiable Information)** | Dado pessoal que identifica uma pessoa (CPF, RG, email, telefone). |
| **PHI (Personal Health Information)** | Dado de saúde (protegido por LGPD Art. 11). |
| **Base Legal** | Justificativa legal para tratamento de dados (consentimento, contrato, legítimo interesse). |
| **Consentimento** | Autorização livre, informada e inequívoca do titular para tratamento de dados. |
| **Titular** | Pessoa natural a quem se referem os dados pessoais. |
| **Controlador** | Pessoa natural ou jurídica que decide sobre o tratamento de dados. |
| **Operador** | Pessoa natural ou jurídica que realiza o tratamento em nome do controlador. |
| **Encarregado (DPO)** | Pessoa indicada pelo controlador para aceitar reclamações e comunicações. |
| **ANPD** | Autoridade Nacional de Proteção de Dados (órgão fiscalizador). |
| **RIPD (Relatório de Impacto)** | Documento que descreve riscos de tratamento de dados (obrigatório para casos sensíveis). |
| **Anonimização** | Processo de remover identificadores pessoais (irreversível). |
| **Pseudonimização** | Processo de substituir dados por identificadores artificiais (reversível com chave). |
| **Portabilidade** | Direito do titular de receber seus dados em formato estruturado. |
| **Direito de Acesso** | Direito do titular de saber quais dados são tratados. |
| **Direito de Exclusão** | Direito do titular de solicitar eliminação dos dados. |
| **Retenção** | Prazo que os dados são mantidos (ex: 365 dias conversas, 5 anos audit). |
| **Criptografia** | Técnica de proteger dados em repouso (at rest) ou em trânsito (in transit). |
| **Hash** | Função unidirecional que transforma dados (ex: SHA-256). |
| **Trilha de Auditoria (Audit Trail)** | Registro de todas as ações que afetam dados (quem, quando, o quê). |
| **Vazamento (Data Breach)** | Incidente de segurança que resulta em perda/comprometimento de dados. |
| **Notificação ANPD** | Comunicação obrigatória à ANPD em caso de vazamento (Art. 48 LGPD). |

---

## 6. Termos Técnicos — OpenClaw / Agent AI

| Termo | Definição |
|-------|-----------|
| **OpenClaw** | Plataforma de Agent AI (gateway local com storage SQLite). |
| **Agent** | Programa que age autonomamente (percebe, decide, age). |
| **Pietra** | Nome do nosso Agent AI Cartório (personalidade: direto, sério, sem emojis). |
| **LLM (Large Language Model)** | Modelo de linguagem de grande porte (minimax-m3, deepseek-v4-flash, etc.). |
| **minimax-m3** | Modelo principal do Pietra (1M context, thinking adaptive, $0 cost). |
| **deepseek-v4-flash** | Modelo secundário (compat OpenAI, OpenCode-Go provider). |
| **MCP (Model Context Protocol)** | Protocolo para fornecer tools a LLMs (padronizado pela Anthropic). |
| **Tool (Function Calling)** | Função que o LLM pode invocar (ex: `consultar_protocolo`, `calcular_emolumento`). |
| **Prompt** | Texto enviado ao LLM (system + user messages). |
| **System Prompt** | Instruções fixas que definem o comportamento do agent. |
| **User Prompt** | Mensagem do usuário (cliente). |
| **Assistant Response** | Resposta gerada pelo LLM. |
| **Context Window** | Quantidade máxima de tokens que o LLM pode processar (1M para minimax-m3). |
| **Tokens** | Unidades de texto processadas pelo LLM (~0.75 palavras por token em inglês). |
| **Thinking** | Raciocínio interno do LLM antes de gerar resposta (adaptive mode). |
| **Temperature** | Parâmetro que controla a criatividade (0 = determinístico, 1 = criativo). |
| **Max Tokens** | Número máximo de tokens na resposta. |
| **Stream** | Resposta enviada incrementalmente (token por token). |
| **Top P** | Parâmetro de nucleus sampling (considera apenas os tokens com probabilidade acumulada ≥ P). |
| **Function Calling** | Capacidade do LLM de invocar funções externas. |
| **Prompt Injection** | Ataque onde usuário injeta instruções maliciosas no prompt. |
| **HITL (Human In The Loop)** | Padrão onde humano intervém em decisões críticas. |
| **RAG (Retrieval Augmented Generation)** | Técnica de fornecer contexto relevante ao LLM antes de gerar resposta. |
| **Skills** | Conjunto predefinido de tools + prompts para uma tarefa específica. |

---

## 7. Termos Técnicos — Infraestrutura

| Termo | Definição |
|-------|-----------|
| **VPS (Virtual Private Server)** | Servidor virtual privado (Hostinger neste caso). |
| **Docker** | Plataforma de containers (empacota app + dependências). |
| **Docker Swarm** | Orquestrador de containers (modo nativo do Docker). |
| **Easypanel** | Interface web para gerenciar Docker Swarm (alternativa self-hosted). |
| **Traefik** | Reverse proxy + load balancer + SSL termination. |
| **Let’s Encrypt** | Autoridade certificadora gratuita (certificados SSL auto-renovados). |
| **Cloudflare** | CDN + DNS + DDoS protection + WAF. |
| **Tailscale** | VPN mesh baseado em WireGuard (conexão segura Mac↔VPS). |
| **SSH (Secure Shell)** | Protocolo de acesso remoto criptografado. |
| **chmod 600** | Permissão de arquivo: leitura/escrita só pelo dono. |
| **Backup incremental** | Backup que copia apenas arquivos modificados desde o último backup. |
| **Volume Docker** | Diretório persistente gerenciado pelo Docker. |
| **Bind Mount** | Diretório do host montado dentro de um container. |
| **MCP Server** | Servidor que implementa Model Context Protocol. |
| **FastMCP 3.x** | Framework Python para criar MCP servers rapidamente. |
| **Rota (Traefik)** | Configuração de roteamento de URL para serviço backend. |
| **Router (FastAPI)** | Componente que agrupa endpoints relacionados. |
| **Endpoint Health** | `/health` retorna 200 OK se tudo está UP. |
| **Health Radar** | `/api/v1/health/radar` retorna status de TODOS os serviços. |

---

## 8. Termos Técnicos — DevOps / CI-CD

| Termo | Definição |
|-------|-----------|
| **CI/CD** | Continuous Integration / Continuous Deployment. |
| **GitHub Actions** | Plataforma de CI/CD integrada ao GitHub. |
| **Render** | Plataforma de deploy com preview deployments. |
| **Deploy** | Processo de colocar código em produção. |
| **Rollback** | Reverter para versão anterior em caso de problemas. |
| **Docker Service** | Unit de deploy no Docker Swarm. |
| **docker service update** | Comando que atualiza um service no Swarm. |
| **Pre-commit hook** | Script executado antes de cada commit (validação automática). |
| **mypy** | Type checker estático para Python. |
| **ruff** | Linter e formatter Python rápido (substituto do flake8/black/isort). |
| **pytest** | Framework de testes para Python. |
| **Coverage** | Percentual de código coberto por testes. |
| **Conventional Commits** | Padrão de mensagem de commit (`feat:`, `fix:`, `docs:`, `test:`, etc.). |
| **Semver** | Versionamento semântico (MAJOR.MINOR.PATCH). |
| **Changelog** | Registro de mudanças por versão. |
| **Tag (Git)** | Marcador de versão (ex: `v0.6.0`). |
| **Branch (Git)** | Linha de desenvolvimento (ex: `master`). |
| **Pull Request (PR)** | Proposta de merge de código. |
| **Merge (Git)** | Incorporação de código de uma branch em outra. |
| **Conflict (Git)** | Conflito entre versões do mesmo arquivo. |
| **Rebase (Git)** | Reaplicação de commits sobre outra base. |
| **Cherry-pick (Git)** | Seleção de um commit específico de outra branch. |
| **Stash (Git)** | Guarda temporária de mudanças não commitadas. |
| **Pipeline (CI/CD)** | Sequência de etapas automatizadas (lint → test → build → deploy). |

---

## 9. Termos Multi-Provider LLM

| Termo | Definição |
|-------|-----------|
| **Provider** | Serviço de LLM (OpenAI, Anthropic, Google, etc.). |
| **Multi-Provider** | Capacidade de usar múltiplos providers de LLM. |
| **Base URL** | Endpoint do provider (ex: `https://opencode.ai/zen/go/v1`). |
| **Compat OpenAI** | Padrão de API compatível com OpenAI (compat com deepseek-v4-flash). |
| **API Key** | Chave secreta para autenticação no provider. |
| **Model** | Versão específica do LLM (ex: `minimax-m3`, `deepseek-v4-flash`). |
| **Token** | Unidade de cobrança (input + output). |
| **Rate Limit** | Limite de requisições por minuto/dia. |
| **Custo (cost)** | Preço por 1K tokens (input/output diferenciados). |
| **Provider opencode_go** | Provider low-cost (compat OpenAI) usado para Pietra. |
| **Provider openclaw** | Provider local (fallback) usado em cenários offline. |
| **Provider codestral** | Provider Mistral (alternativa europeia). |

---

## 10. Siglas e Acrônimos

| Sigla | Significado |
|-------|-------------|
| **API** | Application Programming Interface |
| **REST** | Representational State Transfer |
| **HTTP** | Hypertext Transfer Protocol |
| **HTTPS** | HTTP Secure (com TLS/SSL) |
| **DNS** | Domain Name System |
| **SSL/TLS** | Secure Sockets Layer / Transport Layer Security |
| **VPS** | Virtual Private Server |
| **CDN** | Content Delivery Network |
| **JWT** | JSON Web Token |
| **RBAC** | Role-Based Access Control |
| **RLS** | Row-Level Security (Postgres) |
| **ORM** | Object-Relational Mapping |
| **MCP** | Model Context Protocol |
| **HITL** | Human In The Loop |
| **LGPD** | Lei Geral de Proteção de Dados |
| **DPO** | Data Protection Officer (Encarregado) |
| **ANPD** | Autoridade Nacional de Proteção de Dados |
| **PII** | Personally Identifiable Information |
| **RIPD** | Relatório de Impacto à Proteção de Dados |
| **MFA** | Multi-Factor Authentication |
| **SSO** | Single Sign-On |
| **CI/CD** | Continuous Integration / Continuous Deployment |
| **WAF** | Web Application Firewall |
| **CRUD** | Create, Read, Update, Delete |
| **DTO** | Data Transfer Object |
| **TDD** | Test-Driven Development |
| **BDD** | Behavior-Driven Development |
| **YAML** | YAML Ain't Markup Language |
| **JSON** | JavaScript Object Notation |
| **TOML** | Tom's Obvious, Minimal Language |
| **CLI** | Command Line Interface |
| **SDK** | Software Development Kit |
| **DB** | Database |
| **CRUD** | Create, Read, Update, Delete |
| **FK** | Foreign Key |
| **PK** | Primary Key |
| **DDL** | Data Definition Language (CREATE, ALTER, DROP) |
| **DML** | Data Manipulation Language (SELECT, INSERT, UPDATE, DELETE) |
| **DCL** | Data Control Language (GRANT, REVOKE) |
| **ACID** | Atomicity, Consistency, Isolation, Durability |
| **CAP** | Consistency, Availability, Partition tolerance |

---

## 11. Comandos Úteis (Cheat Sheet)

### SSH + Docker
```bash
# Conectar via Tailscale
ssh cartorio

# Ver todos os services
ssh cartorio "docker service ls"

# Logs de um service
ssh cartorio "docker service logs cartorio_api --tail 100"

# Restart de um service
ssh cartorio "docker service update --force cartorio_api"

# Inspecionar container
ssh cartorio "docker inspect cartorio_api.1.<id>"
```

### Git
```bash
# Update-index refresh (Lesson 181)
git update-index --refresh

# Status sem ruído
git status -sb

# Diff staged + unstaged
git diff --cached && git diff

# Stash + pop
git stash && git stash pop

# Cherry-pick de commit
git cherry-pick <hash>
```

### Backend (FastAPI)
```bash
# Rodar gates
cd backend && mypy app/ && ruff check app/ scripts/ && pytest tests/ -q

# Gates + coverage
pytest tests/ --cov=backend/app --cov-report=term-missing

# Migrations
alembic upgrade head
alembic revision --autogenerate -m "msg"
```

### OpenClaw / Modelos
```bash
# Validar context size
curl https://agent.2notasudi.com.br/health

# Testar conexão com opencode_go
curl -X POST https://opencode.ai/zen/go/v1/chat/completions \
  -H "Authorization: Bearer $OPENCODE_GO_API_KEY" \
  -d '{"model": "minimax-m3", "messages": [{"role": "user", "content": "test"}]}'
```

---

**Modified by Pietra/Mavis (c19 docs raiz) — 2026-06-26 18:30 BRT**
