# Diagrama de Sistema — Cartório Chatbot

> Diagramas Mermaid de alta fidelidade mostrando todos os fluxos do sistema.
> Última atualização: 2026-06-26.

## Índice

1. [Visão Macro (C4 Level 1)](#1-visão-macro-c4-level-1)
2. [Container View (C4 Level 2)](#2-container-view-c4-level-2)
3. [Fluxo de Atendimento WhatsApp (E2E)](#3-fluxo-de-atendimento-whatsapp-e2e)
4. [Fluxo LGPD e Consentimento](#4-fluxo-lgpd-e-consentimento)
5. [Fluxo de Deploy](#5-fluxo-de-deploy)
6. [Fluxo de Backup e Recuperação](#6-fluxo-de-backup-e-recuperação)
7. [Fluxo HITL (Human In The Loop)](#7-fluxo-hitl-human-in-the-loop)
8. [Arquitetura de Rede](#8-arquitetura-de-rede)
9. [Topologia Docker Swarm](#9-topologia-docker-swarm)
10. [Fluxo de Dados por Camada](#10-fluxo-de-dados-por-camada)

---

## 1. Visão Macro (C4 Level 1)

```mermaid
graph TB
    Cliente[👤 Cliente<br/>WhatsApp]
    Gustavo[👤 Gustavo Almeida<br/>CEO + Admin]
    
    subgraph Sistema [🏛️ Cartório Chatbot - 2notasudi.com.br]
        direction TB
        API[🔧 API FastAPI<br/>api.2notasudi.com.br]
        Agent[🤖 Agent Pietra<br/>agent.2notasudi.com.br]
    end
    
    Telegram[📱 Telegram Bot<br/>@test_cartorio_bot]
    
    Cliente -->|WhatsApp| Sistema
    Gustavo -->|Admin/Deploy| Sistema
    Gustavo -->|Comandos| Telegram
    
    classDef external fill:#e1f5ff,stroke:#0277bd,stroke-width:2px
    classDef system fill:#c8e6c9,stroke:#2e7d32,stroke-width:3px
    classDef telegram fill:#fff3e0,stroke:#e65100,stroke-width:2px
    
    class Cliente,Gustavo external
    class API,Agent system
    class Telegram telegram
```

**Atores**:
- **Cliente**: Usuário final que manda mensagens WhatsApp
- **Gustavo**: CEO, admin do sistema, deploys, configs críticas
- **Telegram Bot**: Canal alternativo (pré-teste)

---

## 2. Container View (C4 Level 2)

```mermaid
graph LR
    subgraph Entrada [Entrada]
        WA[WhatsApp Business API]
        TG[Telegram]
    end
    
    subgraph Gateway [Gateway]
        EVO[Evolution API v2.3.7<br/>whatsapp.2notasudi.com.br]
    end
    
    subgraph Orquestracao [Orquestração]
        N8N[N8N Workflow Engine<br/>flow.2notasudi.com.br<br/>34 WFs]
    end
    
    subgraph Core [Core Services]
        API[FastAPI v0.6.0<br/>api.2notasudi.com.br<br/>58 endpoints]
        OCL[OpenClaw Gateway<br/>agent.2notasudi.com.br<br/>Agent Pietra]
    end
    
    subgraph Data [Dados]
        SUP[Supabase<br/>supbase.2notasudi.com.br<br/>134 tabelas]
        RED[Redis<br/>interno:6379<br/>cache+sessões]
    end
    
    subgraph CRM [CRM]
        CW[Chatwoot<br/>chat.2notasudi.com.br<br/>HITL]
    end
    
    subgraph Infra [Infraestrutura]
        EP[Easypanel<br/>easypanel.2notasudi.com.br]
        TR[Traefik<br/>SSL Proxy]
        TS[Tailscale<br/>VPN Privada]
    end
    
    WA -->|Webhook| EVO
    TG -->|Mensagem| N8N
    EVO -->|Webhook| N8N
    N8N -->|REST| API
    API -->|WebSocket| OCL
    API -->|SQL| SUP
    API -->|Cache| RED
    API -->|CRM| CW
    OCL -->|Tools| API
    N8N -->|MCP Tools| API
    
    classDef entry fill:#fff9c4,stroke:#f57f17
    classDef core fill:#c8e6c9,stroke:#1b5e20
    classDef data fill:#bbdefb,stroke:#0d47a1
    classDef infra fill:#f8bbd0,stroke:#880e4f
    
    class WA,TG entry
    class API,OCL core
    class SUP,RED,CW data
    class EP,TR,TS infra
```

---

## 3. Fluxo de Atendimento WhatsApp (E2E)

```mermaid
sequenceDiagram
    autonumber
    actor C as 👤 Cliente
    participant W as WhatsApp API
    participant E as Evolution API
    participant N as N8N (WF #01)
    participant A as FastAPI
    participant S as Supabase
    participant R as Redis
    participant O as OpenClaw (Pietra)
    participant T as Chatwoot
    
    C->>+W: "Olá, quero saber emolumento"
    W->>+E: Webhook MESSAGES_UPSERT
    E->>+N: POST /webhook/evo-in
    
    Note over N: WF #01 - Consulta Emolumento<br/>1. PII Scrub (CPF, telefone)<br/>2. X-Correlation-ID<br/>3. Retry 3x exp backoff
    
    N->>+A: POST /api/v1/atendimento/iniciar<br/>{phone, message, correlation_id}
    
    Note over A: Middleware chain:<br/>- PII Scrub<br/>- SlowLog (>500ms)<br/>- Problem Details (4xx/5xx)
    
    A->>S: SELECT cliente WHERE phone
    A->>R: GET session:{phone} (TTL 30min)
    A->>S: SELECT lgpd_consents WHERE cliente_id
    
    alt Cliente NOVO sem consent
        A-->>N: 200 OK {require_consent: true}
        N->>E: sendText "Bem-vindo! Precisamos do seu consentimento LGPD"
        E->>W: → Cliente
        C->>W: "ACEITO"
        W->>E: → Webhook
        E->>N: → WF #04 (Consentimento)
        N->>A: POST /api/v1/lgpd/consent
        A->>S: INSERT lgpd_consents
        A->>S: INSERT audit_log (LGPD art. 37)
    end
    
    A->>+O: WebSocket /v1/chat<br/>{message, session_id, cliente_id}
    
    Note over O: Thinking ON (adaptive)<br/>Skills: emolumento-calc<br/>Context: 1M tokens
    
    O->>A: MCP Tool: GET /api/v1/emolumentos?tipo=reconhecimento_firma
    A->>S: SELECT emolumentos WHERE tipo
    A-->>O: [{tipo, valor, prazo}]
    
    O->>A: MCP Tool: POST /api/v1/protocolo/criar
    A->>S: INSERT protocolos
    
    O-->>-A: {response: "Reconhecimento de firma: R$ 45,20. Prazo: 24h. Posso criar protocolo?"}
    
    A->>S: INSERT audit_log (atendimento, AI decision, tools called)
    A->>S: UPDATE conversas (mensagem AI)
    A->>T: POST /api/v1/conversations (CRM)
    
    A-->>-N: 200 OK {response}
    
    N->>E: POST /message/sendText {number, text}
    E->>W: → API
    W->>-C: "Reconhecimento de firma: R$ 45,20..."
    
    Note over C,T: HITL possível a qualquer momento:<br/>Gustavo/Atendente clica "Pausar Agent" no Chatwoot<br/>Agent pausado, contexto preservado
```

**Tempo esperado total**: 2-5 segundos (p95) entre mensagem do cliente e resposta.

---

## 4. Fluxo LGPD e Consentimento

```mermaid
flowchart TD
    Start([Cliente novo<br/>entra em contato]) --> Check{Session existe?}
    
    Check -->|Não| QueryConsent[GET /lgpd_consents<br/>WHERE phone]
    Check -->|Sim| LoadSession[Carregar sessão Redis]
    
    QueryConsent --> HasConsent{Tem consent?}
    
    HasConsent -->|Sim| LoadSession
    HasConsent -->|Não| SendConsent[Enviar termo LGPD<br/>via WhatsApp]
    
    SendConsent --> WaitReply{Aguarda resposta<br/>30min TTL}
    WaitReply -->|Timeout| Reject[Sair: "Consentimento<br/>necessário"]
    WaitReply -->|ACEITO/CONCORDO| RecordConsent[POST /lgpd/consent<br/>aceito_em: NOW]
    
    RecordConsent --> Audit1[INSERT audit_log<br/>LGPD art. 37]
    Audit1 --> NotifyDPO[notify_outbox_new<br/>→ N8N WF #04b]
    NotifyDPO --> LoadSession
    
    LoadSession --> ProcessMsg[Processar mensagem<br/>normalmente]
    ProcessMsg --> Audit2[INSERT audit_log<br/>toda ação]
    
    Audit2 --> RightCheck{Cliente exerceu<br/>direito LGPD?}
    RightCheck -->|Sim D09| ScheduleExclusion[POST /lgpd/data-subject-request<br/>type=EXCLUSION, prazo=30d]
    RightCheck -->|Sim D08| ExportData[GET /lgpd/portabilidade<br/>→ JSON+ZIP+S3 link 7d]
    RightCheck -->|Sim D07| UpdateData[PATCH /lgpd/meus-dados]
    RightCheck -->|Não| Continue[Continuar atendimento]
    
    ScheduleExclusion --> CronWait[Anonimização após 30d<br/>via N8N WF #24 cron diário]
    CronWait --> Anon[UPDATE clientes/protoccolos<br/>SET nome='ANON-{hash}', cpf=NULL]
    Anon --> AuditAnon[INSERT lgpd_audit_anpd<br/>type=ANONIMIZATION]
    AuditAnon --> Done([Fim])
    
    ExportData --> Done
    UpdateData --> Done
    Continue --> Done
    
    classDef lgpd fill:#ffebee,stroke:#c62828
    classDef consent fill:#e8f5e9,stroke:#2e7d32
    classDef neutral fill:#e3f2fd,stroke:#1565c0
    
    class SendConsent,RecordConsent,Audit1,Audit2,AuditAnon lgpd
    class HasConsent,RightCheck consent
    class Check,LoadSession,ProcessMsg neutral
```

**Retenção**:
- Conversas: 365 dias
- Audit log: 1825 dias (5 anos - LGPD art. 37)
- Consentimentos: permanente (até revogação)

---

## 5. Fluxo de Deploy

```mermaid
flowchart LR
    Dev([👨‍💻 Dev commita]) --> Push[git push origin master]
    Push --> GHA[GitHub Actions<br/>CI Pipeline]
    
    GHA --> Mypy{mypy 0?}
    GHA --> Ruff{ruff 0?}
    GHA --> Pytest{pytest 100%?}
    
    Mypy -->|Falha| Notify1[❌ Notificar dev<br/>bloqueia merge]
    Ruff -->|Falha| Notify1
    Pytest -->|Falha| Notify1
    
    Mypy -->|OK| Build[Build Docker image<br/>cartorio_api:vX.X.X]
    Ruff -->|OK| Build
    Pytest -->|OK| Build
    
    Build --> Tag[Tag image<br/>easypanel/cartorio/api:vX.X.X]
    Tag --> Deploy{Easypanel<br/>auto-deploy?}
    
    Deploy -->|Sim| Swarm[docker service update<br/>cartorio_api]
    Deploy -->|Não| Manual[Deploy manual<br/>via Easypanel UI]
    
    Swarm --> Health{Health check<br/>/health 200?}
    Manual --> Health
    
    Health -->|Falha| Rollback[Rollback automático<br/>imagem anterior]
    Health -->|OK| Smoke[Smoke test<br/>GET /api/v1/health/radar]
    
    Rollback --> Notify2[🚨 Alerta P0<br/>Telegram + Email]
    Smoke --> Update[Atualizar SESSION_SUMMARY<br/>+ CHANGELOG]
    
    Update --> Notify3[✅ Notificar Gustavo<br/>deploy concluído]
    Notify1 --> End([Fim])
    Notify2 --> End
    Notify3 --> End
    
    classDef ok fill:#c8e6c9,stroke:#1b5e20
    classDef fail fill:#ffcdd2,stroke:#b71c1c
    classDef process fill:#fff9c4,stroke:#f57f17
    
    class Build,Tag,Swarm,Manual,Smoke,Update,Notify3 ok
    class Notify1,Rollback,Notify2 fail
    class GHA,Mypy,Ruff,Pytest,Health,Deploy process
```

**Tempo total**: 3-7 minutos (mypy + ruff + pytest + build + deploy + smoke).

**Zero-downtime**: Swarm rolling update garante que sempre há N containers UP.

---

## 6. Fluxo de Backup e Recuperação

```mermaid
flowchart TD
    Cron1[Cron 03:00 BRT<br/>cartorio-backup.sh] --> DumpDB[pg_dump cartorio<br/>pg_dump n8n<br/>pg_dump chatwoot<br/>pg_dump evolution]
    Cron1 --> DumpWF[Backup N8N WFs<br/>via API]
    Cron1 --> DumpEnv[Backup .env files]
    
    DumpDB --> Compress[Compressão<br/>tar.gz]
    DumpWF --> Compress
    DumpEnv --> Compress
    
    Compress --> Storage[Salvar em<br/>/var/backups/cartorio/]
    Storage --> Rotate{>7 tarballs?}
    Rotate -->|Sim| DeleteOld[Apagar mais antigos]
    Rotate -->|Não| Validate
    DeleteOld --> Validate[Validar<br/>integridade]
    
    Validate --> HealthCheck[GET /api/v1/health/backup]
    HealthCheck --> Status{Status?}
    Status -->|OK| Log[Log sucesso]
    Status -->|FAIL| Alert[🚨 Alerta P0<br/>Telegram]
    
    Cron2[Cron 5min<br/>WF #21] --> HourlyCheck[Verificar última<br/>modificação]
    HourlyCheck --> Recent{< 24h?}
    Recent -->|Sim| Log
    Recent -->|Não| Alert
    
    Cron3[Cron 00/06/12/18 UTC<br/>pg_basebackup_4x.sh] --> BaseBackup[pg_basebackup<br/>+ WAL archiving]
    BaseBackup --> S3[Enviar para S3<br/>mensal]
    S3 --> LogS3[Log S3 upload]
    
    Log --> End1([Fim backup diário])
    LogS3 --> End1
    Alert --> End1
    
    style Cron1 fill:#c8e6c9
    style Cron2 fill:#c8e6c9
    style Cron3 fill:#c8e6c9
    style Alert fill:#ffcdd2,stroke:#b71c1c,stroke-width:3px
```

**Recuperação** (RTO < 1h, RPO < 24h):
1. SSH VPS
2. Localizar tarball mais recente
3. `tar -xzf backup-YYYY-MM-DD.tar.gz -C /restore/`
4. `psql -U postgres < restore/cartorio.sql`
5. Restart serviços
6. Validar com smoke test

---

## 7. Fluxo HITL (Human In The Loop)

```mermaid
sequenceDiagram
    autonumber
    actor C as 👤 Cliente
    participant A as FastAPI
    participant O as OpenClaw (Pietra)
    participant T as Chatwoot
    actor H as 👤 Atendente<br/>(Gustavo/Andre)
    
    C->>A: Mensagem
    A->>O: Processar
    O-->>A: Resposta
    A-->>C: Resposta
    
    Note over T,H: Atendente percebe que<br/>precisa assumir
    
    H->>T: Clica "Pausar Agent"<br/>na conversa X
    T->>A: Webhook conversation_updated<br/>{custom_attributes.bot_paused: true}
    A->>A: Marcar sessão Redis<br/>sess:{phone}.paused = true
    
    Note over A: Próxima mensagem do cliente:
    
    C->>A: Nova mensagem
    A->>A: Check sess.paused
    A-->>C: "Um atendente<br/>irá ajudá-lo"
    A->>T: Notificar atendente<br/>via Chatwoot notification
    T-->>H: "Cliente aguardando<br/>na conversa X"
    
    H->>T: Responde manualmente
    T->>C: Mensagem do atendente
    C->>T: Conversa continua<br/>com humano
    
    Note over H,T: Quando terminar:
    
    H->>T: Clica "Retomar Agent"
    T->>A: Webhook conversation_updated<br/>{custom_attributes.bot_paused: false}
    A->>A: Limpar sess.paused
    
    Note over A: Próxima mensagem do cliente:
    
    C->>A: Nova mensagem
    A->>O: Processar (contexto preservado)
    O-->>A: Resposta
    A-->>C: Resposta
```

**Benefícios**:
- Atendente pode intervir SEM perder contexto
- Cliente não percebe transição
- Bot pode ser retomado exatamente de onde parou

---

## 8. Arquitetura de Rede

```mermaid
graph TB
    Internet([🌐 Internet])
    
    subgraph CF [☁️ Cloudflare]
        DNS[DNS<br/>2notasudi.com.br]
        Proxy[Proxy + WAF + DDoS]
    end
    
    Internet --> CF
    CF -->|HTTPS<br/>Port 443| VPS
    
    subgraph VPS [🖥️ VPS Hostinger<br/>187.77.236.77 / 100.99.172.84]
        Traefik[Traefik<br/>Reverse Proxy<br/>SSL Termination]
        
        subgraph Swarm [Docker Swarm]
            API[cartorio_api:8000]
            N8N[cartorio_n8n:5678]
            EVO[cartorio_evolution-api:8080]
            CW[cartorio_chatwoot:3000]
            OCL[cartorio_openclaw:18789]
            SUP[cartorio_supabase:5432]
            RED[cartorio_redis:6379]
        end
        
        Traefik --> API
        Traefik --> N8N
        Traefik --> EVO
        Traefik --> CW
        Traefik --> OCL
        Traefik --> SUP
    end
    
    subgraph Tailscale [🔒 Tailscale VPN]
        Mac[💻 MacBook Pro<br/>100.83.180.16]
        iPhone1[📱 iPhone 17 Pro<br/>100.122.101.33]
        iPhone2[📱 iPhone Andre<br/>100.74.36.41]
        TriQ[🐧 TriQ Hub<br/>100.110.127.44]
    end
    
    Mac -.->|Tailscale SSH| VPS
    iPhone1 -.->|Tailscale| VPS
    iPhone2 -.->|Tailscale| VPS
    TriQ -.->|Tailscale| VPS
    
    classDef external fill:#e1f5ff,stroke:#0277bd
    classDef vps fill:#c8e6c9,stroke:#1b5e20
    classDef tailscale fill:#fff3e0,stroke:#e65100
    
    class Internet,CF external
    class VPS,Traefik,Swarm,API,N8N,EVO,CW,OCL,SUP,RED vps
    class Tailscale,Mac,iPhone1,iPhone2,TriQ tailscale
```

**Segurança**:
- Cloudflare: DDoS + WAF + bot management
- Tailscale: VPN WireGuard (criptografia ponta a ponta)
- Traefik: SSL Let's Encrypt (renovação auto)
- Docker Swarm: isolamento entre containers

---

## 9. Topologia Docker Swarm

```mermaid
graph TB
    subgraph SwarmManager [Swarm Manager]
        Manager[docker swarm manager<br/>187.77.236.77]
    end
    
    subgraph Services [12 Services]
        direction LR
        S1[cartorio_api<br/>:8000]
        S2[cartorio_n8n<br/>:5678]
        S3[cartorio_n8n-runner<br/>worker]
        S4[cartorio_evolution-api<br/>:8080]
        S5[cartorio_chatwoot<br/>:3000]
        S6[cartorio_chatwoot-sidekiq<br/>worker]
        S7[cartorio_openclaw-gateway<br/>:18789]
        S8[cartorio_redis<br/>:6379]
        S9[cartorio_redis_dbgate<br/>:3001]
        S10[cartorio_redis_rediscommander<br/>:8081]
        S11[easypanel<br/>:3000]
        S12[easypanel-traefik<br/>:80,:443]
    end
    
    subgraph Supabase [14 sub-containers]
        SB1[supabase-db]
        SB2[supabase-kong]
        SB3[supabase-postgrest]
        SB4[supabase-gotrue]
        SB5[supabase-storage]
        SB6[supabase-realtime]
        SB7[supabase-functions]
        SB8[supabase-studio]
        SB9[supabase-meta]
        SB10[supabase-edge-runtime]
        SB11[supabase-imgproxy]
        SB12[supabase-analytics]
        SB13[supabase-vector]
        SB14[supabase-logflare]
    end
    
    Manager --> S1
    Manager --> S2
    Manager --> S3
    Manager --> S4
    Manager --> S5
    Manager --> S6
    Manager --> S7
    Manager --> S8
    Manager --> S9
    Manager --> S10
    Manager --> S11
    Manager --> S12
    Manager --> SB1
    Manager --> SB2
    Manager --> SB3
    Manager --> SB4
    Manager --> SB5
    Manager --> SB6
    Manager --> SB7
    Manager --> SB8
    Manager --> SB9
    Manager --> SB10
    Manager --> SB11
    Manager --> SB12
    Manager --> SB13
    Manager --> SB14
    
    classDef manager fill:#c8e6c9,stroke:#1b5e20,stroke-width:3px
    classDef service fill:#bbdefb,stroke:#0d47a1
    classDef supabase fill:#fff9c4,stroke:#f57f17
    
    class Manager manager
    class S1,S2,S3,S4,S5,S6,S7,S8,S9,S10,S11,S12 service
    class SB1,SB2,SB3,SB4,SB5,SB6,SB7,SB8,SB9,SB10,SB11,SB12,SB13,SB14 supabase
```

**Total**: 12 services + 14 sub-containers = **26 containers** gerenciados.

---

## 10. Fluxo de Dados por Camada

```mermaid
graph TB
    subgraph Camada1 [Camada 1: Apresentação]
        UI1[Chatwoot UI<br/>chat.2notasudi.com.br]
        UI2[Easypanel UI<br/>easypanel.2notasudi.com.br]
        UI3[Telegram Bot<br/>@test_cartorio_bot]
    end
    
    subgraph Camada2 [Camada 2: Gateway]
        G1[Traefik<br/>SSL + Reverse Proxy]
        G2[Evolution API<br/>WhatsApp Gateway]
    end
    
    subgraph Camada3 [Camada 3: Orquestração]
        O1[N8N Workflows<br/>34 WFs ativos]
    end
    
    subgraph Camada4 [Camada 4: Aplicação]
        A1[FastAPI v0.6.0<br/>58 endpoints REST]
        A2[OpenClaw Gateway<br/>WebSocket]
    end
    
    subgraph Camada5 [Camada 5: Dados]
        D1[Supabase<br/>134 tabelas]
        D2[Redis<br/>Cache+Sessões]
    end
    
    UI1 -->|HTTPS| G1
    UI2 -->|HTTPS| G1
    UI3 -->|HTTPS| O1
    G1 --> O1
    G2 -->|Webhook| O1
    O1 -->|REST| A1
    A1 -->|WebSocket| A2
    A1 -->|SQL| D1
    A1 -->|Cache| D2
    A2 -->|Tools| A1
    
    classDef presentation fill:#fff3e0,stroke:#e65100
    classDef gateway fill:#f8bbd0,stroke:#880e4f
    classDef orchestration fill:#e1bee7,stroke:#4a148c
    classDef application fill:#c8e6c9,stroke:#1b5e20
    classDef data fill:#bbdefb,stroke:#0d47a1
    
    class UI1,UI2,UI3 presentation
    class G1,G2 gateway
    class O1 orchestration
    class A1,A2 application
    class D1,D2 data
```

**Princípios**:
- Cada camada é independente
- Falha em uma camada não derruba as outras
- Cada serviço tem health check próprio
- Auto-scaling horizontal (Swarm replicas)

---

## Como usar estes diagramas

1. **Visualização**: Mermaid renderiza nativamente em GitHub, GitLab, VS Code, Obsidian
2. **Edição**: Editar diretamente no Mermaid Live Editor (https://mermaid.live/)
3. **Export PNG/SVG**: Usar `mmdc` (Mermaid CLI) ou extensões Chrome
4. **Documentação**: Diagramas são referenciados em `/docs/ARCHITECTURE.md` e `/docs/platforms/ARCHITECTURE_DIAGRAM.md`

---

**Mantido por**: Pietra (orquestrador)
**Próxima revisão**: 2026-07-03
**Versão**: 1.0.0
