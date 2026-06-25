# Onboarding Time — Cartório Chatbot

> Guia de onboarding para novos membros do time (devs, ops, suporte).
> Última atualização: 2026-06-26.

## TL;DR

**Tempo para produtividade**: 3-5 dias (devs) | 1-2 dias (ops) | 0.5 dia (suporte).
**Pré-requisito**: Conhecimento básico de Docker, Python, Postgres e LGPD.

**Regra de ouro**: SEMPRE ler `/docs/VERSIONAMENTO_PROJETO.md` PRIMEIRO.

---

## Índice

1. [Dia 0: Antes de Começar](#1-dia-0-antes-de-começar)
2. [Dia 1: Setup e Conhecer o Sistema](#2-dia-1-setup-e-conhecer-o-sistema)
3. [Dia 2: Mergulhar no Backend](#3-dia-2-mergulhar-no-backend)
4. [Dia 3: Workflows e Agent](#4-dia-3-workflows-e-agent)
5. [Dia 4: LGPD e Compliance](#5-dia-4-lgpd-e-compliance)
6. [Dia 5+: Contribuir e Operar](#6-dia-5-contribuir-e-operar)
7. [Onboarding por Papel](#7-onboarding-por-papel)
8. [Comandos Essenciais](#8-comandos-essenciais)
9. [Recursos e Contatos](#9-recursos-e-contatos)

---

## 1. Dia 0: Antes de Começar

### 1.1 Ler (obrigatório, 2h)

```
✅ docs/VERSIONAMENTO_PROJETO.md (5min - leia PRIMEIRO)
✅ PROMPT.MD (Super Prompt v4.0.0 - 30min - visão completa)
✅ SESSION_SUMMARY mais recente (10min - estado atual)
✅ docs/CHANGELOG.md (15min - histórico)
✅ docs/ARCHITECTURE.md (10min - arquitetura macro)
✅ docs/platforms/ARCHITECTURE_DIAGRAM.md (10min - diagramas)
✅ docs/GLOSSARIO_CARTORIO.md (20min - termos)
```

### 1.2 Instalar (30min)

```bash
# 1. Tailscale (VPN)
# Mac: https://tailscale.com/download/mac
# Linux: curl -fsSL https://tailscale.com/install.sh | sh

# 2. Docker Desktop (Mac)
# https://www.docker.com/products/docker-desktop/

# 3. Python 3.11+
brew install python@3.11

# 4. IDE (VSCode recomendado)
brew install --cask visual-studio-code
# Extensions: Python, Docker, Mermaid, Markdown, GitLens

# 5. Git
brew install git
git config --global user.name "Seu Nome"
git config --global user.email "seu@email.com"

# 6. SSH Key (para VPS)
ssh-keygen -t ed25519 -C "cartorio-$(whoami)" -f ~/.ssh/id_ed25519_cartorio
# Adicionar pub key no servidor (pedir para Gustavo)
```

### 1.3 Clonar Repositório (5min)

```bash
git clone https://github.com/gustavofullstack/Cartorio.git
cd Cartorio

# Adicionar SSH config
cat >> ~/.ssh/config << 'EOF'
Host vps-cartorio
    HostName 100.99.172.84
    User root
    IdentityFile ~/.ssh/id_ed25519_cartorio
    StrictHostKeyChecking no
EOF

# Testar conexão
ssh vps-cartorio "docker ps | head -3"
```

---

## 2. Dia 1: Setup e Conhecer o Sistema

### 2.1 Manhã: Setup Local (2h)

```bash
# 1. Backend local
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
pip install -r requirements-dev.txt

# 2. Variáveis de ambiente
cp .env.example .env
# Editar .env com credenciais (pedir para Gustavo)

# 3. Rodar local
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# 4. Verificar
curl http://localhost:8000/health
# Esperado: {"status":"ok"}
```

### 2.2 Tarde: Conhecer os Serviços (4h)

**Roteiro de exploração** (1h cada):

#### 2.2.1 API FastAPI (1h)

```bash
# 1. Swagger UI
open https://api.2notasudi.com.br/docs

# 2. Health radar
curl https://api.2notasudi.com.br/api/v1/health/radar | jq

# 3. Listar endpoints
curl https://api.2notasudi.com.br/openapi.json | jq '.paths | keys'

# 4. Testar endpoint simples
curl https://api.2notasudi.com.br/api/v1/emolumentos?tipo=reconhecimento_firma

# 5. Ver código
code backend/app/main.py
code backend/app/api/v1/router.py
code backend/app/services/
```

**Entender**:
- Estrutura de pastas
- Middleware chain (PII Scrub, SlowLog, Problem Details)
- Schemas Pydantic V2 (ConfigDict)
- Endpoints versionados (`/api/v1/`, `/api/v2/`)

#### 2.2.2 N8N Workflows (1h)

```bash
# 1. UI
open https://flow.2notasudi.com.br

# 2. Listar workflows
curl -fsS "https://flow.2notasudi.com.br/api/v1/workflows" \
  -H "X-N8N-API-KEY: $N8N_KEY" | jq '.data[] | {id, name, active}'

# 3. Workflow principal (consulta emolumento)
# UI: Workflows → "01 - Consulta Emolumento WhatsApp v3"
# Entender: trigger, error handler, retry policy, X-Correlation-ID

# 4. Ver execuções recentes
# UI: Executions → filtrar por status=error
```

**Entender**:
- Padrão B07 (retry 3x exp backoff em 63/63 HTTP nodes)
- Padrão B08 (timeout 5s/10s em 130/130 HTTP nodes)
- Error handler global (WF #00)
- Sticky notes com contexto

#### 2.2.3 Supabase (1h)

```bash
# 1. Studio
open https://supbase.2notasudi.com.br:3000

# 2. Listar tabelas via PostgREST
curl "https://supbase.2notasudi.com.br/rest/v1/clientes?select=count" \
  -H "apikey: $SUPABASE_ANON_KEY" -H "Authorization: Bearer $JWT"

# 3. RLS ativo
ssh vps-cartorio "docker exec \$(docker ps -qf 'name=cartorio_supabase-db') psql -U postgres -c \"SELECT tablename, rowsecurity FROM pg_tables WHERE schemaname='public' AND rowsecurity=true;\""

# 4. Alembic
ssh vps-cartorio "docker exec \$(docker ps -qf 'name=cartorio_api') alembic current"
```

**Entender**:
- 13 tabelas core (clientes, protocolos, atendimentos, etc)
- RLS policies
- Triggers (audit_log, updated_at, outbox)
- Alembic head 2026_06_25_0014

#### 2.2.4 OpenClaw (Agent AI) (1h)

```bash
# 1. Health
curl https://agent.2notasudi.com.br/health

# 2. Configuração (no VPS)
ssh vps-cartorio
cat /var/lib/docker/volumes/cartorio_openclaw-gateway_config/_data/agents/main/agent/agent.json | jq
cat /var/lib/docker/volumes/cartorio_openclaw-gateway_config/_data/agents/main/agent/models.json | jq

# 3. Skills
cat /var/lib/docker/volumes/cartorio_openclaw-gateway_config/_data/agents/main/agent/agent.json | jq '.skills'

# 4. Testar via WebSocket
python scripts/test_openclaw_ws.py
```

**Entender**:
- Contexto 1M tokens (corrigido)
- Thinking adaptive ON
- 7 skills ativas
- WebSocket `/v1/chat` (HTTP /v1/chat retorna 404 - usar WS)

---

## 3. Dia 2: Mergulhar no Backend

### 3.1 Estrutura do Código (1h)

```bash
backend/
├── app/
│   ├── main.py              # FastAPI app + middleware
│   ├── config.py            # Settings (pydantic-settings)
│   ├── api/
│   │   ├── v1/router.py     # 58 endpoints v1
│   │   └── v2/router.py     # endpoints v2 (alpha)
│   ├── models/              # SQLAlchemy
│   ├── schemas/             # Pydantic V2 (ConfigDict)
│   ├── services/            # Lógica de negócio
│   │   ├── audit.py
│   │   ├── emolumento.py
│   │   ├── lgpd.py
│   │   ├── openclaw_client.py
│   │   ├── chatwoot.py
│   │   ├── evolution.py
│   │   ├── redis_cache.py
│   │   └── ...
│   ├── middleware/
│   │   ├── pii_scrub.py
│   │   ├── slow_log.py
│   │   ├── problem_details.py
│   │   └── ...
│   └── dependencies/
├── tests/                   # 1245+ testes
├── alembic/                 # Migrations
└── mcp_server.py            # FastMCP 3.x (164 tools)
```

### 3.2 Adicionar Endpoint (exercício prático, 2h)

```python
# 1. Schema: backend/app/schemas/cliente.py
from pydantic import BaseModel, ConfigDict

class ClienteCreate(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    nome: str
    cpf: str  # PII - será scrubbed em logs
    telefone: str

# 2. Service: backend/app/services/cliente_service.py
async def criar_cliente(payload: ClienteCreate) -> Cliente:
    # Validar CPF (LGPD)
    # Checar duplicado
    # Persistir
    # Audit log
    return cliente

# 3. Endpoint: backend/app/api/v1/router.py
@router.post("/clientes", response_model=ClienteResponse)
async def criar(
    payload: ClienteCreate,
    service: ClienteService = Depends(get_cliente_service),
):
    return await service.criar(payload)

# 4. Test: backend/tests/test_cliente_create.py
async def test_criar_cliente_sucesso():
    # ARRANGE
    payload = {"nome": "João", "cpf": "12345678900", "telefone": "34999999999"}
    
    # ACT
    response = client.post("/api/v1/clientes", json=payload)
    
    # ASSERT
    assert response.status_code == 201
    assert response.json()["nome"] == "João"

# 5. Rodar
pytest backend/tests/test_cliente_create.py -v
mypy backend/app/services/cliente_service.py
ruff check backend/app/services/cliente_service.py
```

### 3.3 Padrões Obrigatórios (1h)

```python
# Pydantic V2 SEMPRE com ConfigDict
class MySchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    ...

# Async/await em I/O
async def fetch_data():
    async with httpx.AsyncClient() as client:
        return await client.get(...)

# Type hints SEMPRE
def process(payload: ClienteCreate) -> ClienteResponse: ...

# Logging estruturado
logger.info(
    "cliente.criado",
    extra={"correlation_id": cid, "cliente_id": cid_val}
)

# PII Scrub antes de logar
logger.info(scrub_pii(f"Cliente {cliente.nome} CPF {cliente.cpf}"))

# Audit log em ações sensíveis
audit.log(action="CREATE", entity="cliente", entity_id=cid)
```

### 3.4 Gates de Qualidade (30min)

```bash
# SEMPRE rodar antes de commit
mypy backend/ --ignore-missing-imports
ruff check backend/ --fix
pytest backend/tests/ -v --tb=short

# Meta: 0 errors, 0 warnings, 100% pass
```

---

## 4. Dia 3: Workflows e Agent

### 4.1 N8N Workflow (2h)

**Criar WF simples** (cálculo de emolumento isolado):

```
1. Webhook trigger
2. Set node (extrair parâmetros)
3. HTTP Request → /api/v1/emolumentos (com X-Correlation-ID, retry, timeout)
4. If (status 200) → Respond
5. If (status != 200) → Error handler global (WF #00)
6. Salvar JSON da chamada
```

**Padrões**:
- Sticky note inicial com contexto
- Error handler conectado
- HTTP node com timeout 5s + retry 3x
- Header X-Correlation-ID em todos HTTP
- Logging estruturado

### 4.2 Agent Skill (2h)

**Adicionar skill "consulta-cep"** (exemplo):

```bash
# 1. SSH VPS
ssh vps-cartorio

# 2. Backup
cp /var/lib/docker/volumes/cartorio_openclaw-gateway_config/_data/agents/main/agent/agent.json \
   /var/lib/docker/volumes/cartorio_openclaw-gateway_config/_data/agents/main/agent/agent.json.bak

# 3. Editar
nano /var/lib/docker/volumes/cartorio_openclaw-gateway_config/_data/agents/main/agent/agent.json
```

```json
{
  "skills": [
    ...,
    {
      "name": "consulta-cep",
      "description": "Busca endereço por CEP via ViaCEP",
      "triggers": ["cep", "endereço", "endereco"],
      "handler": "consulta_cep_handler",
      "tool": "GET https://viacep.com.br/ws/{cep}/json/"
    }
  ]
}
```

```bash
# 4. Restart
docker service update --force cartorio_openclaw-gateway

# 5. Testar
curl -X POST "https://api.2notasudi.com.br/api/v1/test/openclaw" \
  -H "X-API-Key: $API_KEY" \
  -d '{"message": "Qual o CEP 38400-100?"}'
```

---

## 5. Dia 4: LGPD e Compliance

### 5.1 Conceitos (2h)

Ler:
- `/docs/ripd.md` (Relatório de Impacto)
- `/docs/consent.md` (Termo de Consentimento)
- `/docs/privacy-policy.md` (Política de Privacidade)
- `/docs/LGPD.md`

Entender:
- 10 bases legais (Art. 7º e 11º)
- Direitos do titular (Art. 18) - D06 a D25
- RIPD obrigatório
- Notificação ANPD em 72h (data breach)

### 5.2 Implementação (2h)

```python
# Endpoint D09 - Exclusão
@router.delete("/lgpd/meus-dados/{cpf}")
async def excluir_dados(cpf: str, service: LgpdService = Depends()):
    # 1. Validar identidade (autenticação forte)
    # 2. Registrar solicitação (data_subject_requests)
    # 3. Agendar anonimização (30 dias)
    # 4. Audit log
    # 5. Notificar DPO
    return {"status": "scheduled", "data": "2026-07-26"}

# Endpoint D08 - Portabilidade
@router.get("/lgpd/portabilidade/{cpf}")
async def exportar_dados(cpf: str, service: LgpdService = Depends()):
    # 1. Coletar dados de todas as tabelas
    # 2. Gerar JSON
    # 3. Compactar em ZIP
    # 4. Upload para S3 com link assinado (7d)
    # 5. Mandar email
    return {"url": "https://s3...", "expires_at": "..."}
```

### 5.3 Auditoria (1h)

```sql
-- Ver últimos audit logs
SELECT * FROM audit_log ORDER BY created_at DESC LIMIT 20;

-- Ver ações de um usuário
SELECT * FROM audit_log WHERE user_id = $1 ORDER BY created_at DESC;

-- Verificar integridade (hash chain)
SELECT * FROM audit_log WHERE chain_valid = false;
```

---

## 6. Dia 5+: Contribuir e Operar

### 6.1 Fluxo de Trabalho (TDD)

```
1. Criar branch (não! master only - ver .harness/STANDARDS.md)
2. RED: Escrever teste que falha
3. GREEN: Implementar código mínimo
4. REFACTOR: Melhorar
5. mypy + ruff + pytest
6. Commit (mensagem canônica)
7. Push
8. CI roda (GitHub Actions)
9. Deploy automático (Easypanel)
10. Atualizar SESSION_SUMMARY
```

### 6.2 Convenção de Commits

```bash
# Formato: type(scope): description

feat(api): add LGPD data export endpoint
fix(openclaw): correct context size to 1M
docs(platforms): add ARCHITECTURE_DIAGRAM.md
chore(deps): update fastapi to 0.115
test(lgpd): add rights request test cases
refactor(services): simplify cliente service
perf(api): add Redis cache to emolumento lookup
style(backend): apply ruff formatting
ci(github): add mypy to CI pipeline
build(docker): optimize image size
ops(monitoring): add Grafana dashboard
```

### 6.3 Participar da Operação

**Rotação semanal** (responsabilidade compartilhada):
- **Seg-Sex 09:00**: Daily health check (15min)
- **Seg-Sex 17:00**: Resumir incidentes do dia (15min)
- **Sábado**: Backup review + reports mensais

**On-call** (1 semana por vez):
- Recebe alertas Telegram P0/P1
- Resolve ou escala
- Postmortem em caso de incidente

---

## 7. Onboarding por Papel

### 7.1 Dev Backend

```
Dia 1: Setup + conhecer API
Dia 2: Estrutura código + padrões
Dia 3: Criar endpoint (exercício)
Dia 4: LGPD + audit
Dia 5+: Features reais
```

**Tarefas iniciais sugeridas**:
- Corrigir 1 issue marcada `good first issue`
- Adicionar 1 teste faltando
- Melhorar documentação de 1 endpoint

### 7.2 DevOps / SRE

```
Dia 1: Setup + conhecer VPS + serviços
Dia 2: Deploy + CI/CD
Dia 3: Monitoramento + alertas
Dia 4: Backup + recovery
Dia 5+: Hardening
```

**Tarefas iniciais sugeridas**:
- Configurar 1 alerta Prometheus novo
- Adicionar 1 dashboard Grafana
- Documentar 1 runbook

### 7.3 Dev N8N

```
Dia 1: Setup + conhecer N8N
Dia 2: Padrões (B07, B08, B09, B10)
Dia 3: Criar WF simples
Dia 4: Integrar com Chatwoot
Dia 5+: Workflows complexos
```

**Tarefas iniciais sugeridas**:
- Aplicar B09 (logs JSON) em 1 WF
- Adicionar 1 métrica Prometheus em 1 WF
- Criar 1 WF de teste

### 7.4 Suporte / Atendimento

```
Meio dia: Conhecer Chatwoot
Meio dia: Conhecer fluxos de atendimento
Dia 2: HITL + bot pausa
Dia 3: Macros + canned responses
```

**Tarefas iniciais sugeridas**:
- Responder 10 tickets reais
- Criar 3 canned responses novas
- Documentar 1 FAQ

### 7.5 QA

```
Dia 1: Setup + conhecer Swagger
Dia 2: Rodar suite completa (1245+ testes)
Dia 3: Criar 10 testes
Dia 4: Cobertura
Dia 5+: Testes E2E
```

---

## 8. Comandos Essenciais

### 8.1 Git

```bash
# Estado
git status -sb
git log --oneline -10
git fetch origin

# Commit (canônico)
git add -A
git commit -m "feat(scope): description"
git push origin master

# Sync (se cartorio-dev commitou)
git fetch && git rebase origin/master  # se conflito
```

### 8.2 Docker

```bash
# SSH VPS
ssh vps-cartorio

# Ver serviços
docker service ls

# Logs
docker service logs cartorio_api --tail 100 -f

# Restart
docker service update --force cartorio_api

# Inspecionar
docker inspect <container> --format '{{json .State.Health}}' | jq
```

### 8.3 Backend

```bash
# Local
cd backend && source venv/bin/activate

# Servidor
uvicorn app.main:app --reload

# Gates
mypy backend/ --ignore-missing-imports
ruff check backend/ --fix
pytest backend/tests/ -v

# Migration
alembic revision --autogenerate -m "add xxx"
alembic upgrade head
alembic downgrade -1
```

### 8.4 Health Checks

```bash
# Radar (8 serviços)
curl https://api.2notasudi.com.br/api/v1/health/radar | jq

# Individual
for svc in api n8n evolution chatwoot supbase agent easypanel; do
  echo -n "$svc: "
  curl -fsS -o /dev/null -w "%{http_code}\n" "https://$svc.2notasudi.com.br/health" 2>/dev/null || echo "DOWN"
done

# Redis
ssh vps-cartorio "redis-cli -h localhost -p 6379 -a \$REDIS_AUTH PING"
```

### 8.5 Backup

```bash
# Forçar backup
ssh vps-cartorio "/usr/local/bin/cartorio-backup.sh"

# Verificar
ssh vps-cartorio "ls -lah /var/backups/cartorio/ | tail -5"
curl -fsS https://api.2notasudi.com.br/api/v1/health/backup -H "X-API-Key: $API_KEY"
```

### 8.6 Logs

```bash
# API
ssh vps-cartorio "docker service logs cartorio_api --tail 100 -f"

# N8N
ssh vps-cartorio "docker service logs cartorio_n8n --tail 100 -f"

# OpenClaw
ssh vps-cartorio "docker service logs cartorio_openclaw-gateway --tail 100 -f"

# Audit
psql $SUPABASE_URL -c "SELECT * FROM audit_log ORDER BY created_at DESC LIMIT 20"
```

---

## 9. Recursos e Contatos

### 9.1 Documentação Interna

| Doc | Path |
|-----|------|
| Super Prompt | `/PROMPT.MD` |
| Versionamento | `/docs/VERSIONAMENTO_PROJETO.md` |
| Changelog | `/docs/CHANGELOG.md` |
| Architecture | `/docs/ARCHITECTURE.md` |
| Diagramas | `/docs/platforms/ARCHITECTURE_DIAGRAM.md` |
| Glossário | `/docs/platforms/GLOSSARY.md` |
| Glossário Cartório | `/docs/GLOSSARIO_CARTORIO.md` |
| FAQ Operacional | `/docs/FAQ_OPERACIONAL.md` |
| Monitoring | `/docs/MONITORING_GUIDE.md` |
| Troubleshooting | `/docs/TROUBLESHOOTING.md` |
| Deploy | `/docs/DEPLOYMENT.md` |
| LGPD | `/docs/LGPD.md` |
| API Quick Ref | `/docs/API_QUICK_REFERENCE.md` |
| Task Bank | `/.harness/task-bank-100-melhorias.json` |
| Standards | `/.harness/STANDARDS.md` |
| Agents | `/.harness/AGENTS.md` |

### 9.2 Documentação Externa (já baixada)

| Plataforma | Doc |
|------------|-----|
| Evolution API | `/docs/platforms/EVOLUTION.md` + `EVOLUTION_API_v2.3.7_OFFICIAL.md` |
| N8N | `/docs/platforms/N8N.md` + `N8N_v1.94_OFFICIAL.md` (7856 linhas) |
| Chatwoot | `/docs/platforms/CHATWOOT.md` |
| Supabase | `/docs/platforms/SUPABASE.md` |
| Redis | `/docs/platforms/REDIS.md` |
| OpenClaw | `/docs/platforms/OPENCLAW.md` |
| Jules | `/docs/platforms/JULES.md` |

### 9.3 Contatos

| Quem | Como |
|------|------|
| **Gustavo Almeida (CEO)** | Telegram DM 6682284055 |
| **Squad Pietra** | Telegram grupo -5006771024 |
| **DPO** | dpo@2notasudi.com.br |
| **VPS SSH** | ssh vps-cartorio (Tailscale) |
| **Easypanel** | https://easypanel.2notasudi.com.br |

---

## 10. Checklist Final

Antes de considerar onboarding completo:

- [ ] Leu Super Prompt v4.0.0
- [ ] Leu SESSION_SUMMARY mais recente
- [ ] Leu Versionamento, Changelog, Architecture
- [ ] Leu Diagramas e Glossário
- [ ] Leu LGPD, RIPD, Privacy Policy
- [ ] Leu FAQ Operacional e Troubleshooting
- [ ] Leu Monitoring Guide
- [ ] Leu ONBOARDING_TIME (este doc)
- [ ] Leu STANDARDS, AGENTS, PLAN_100_TASKS
- [ ] Configurou ambiente local (Python + Docker + Tailscale + SSH)
- [ ] Rodou `pytest backend/tests/ -v` (1245+ passed)
- [ ] Rodou `mypy backend/` (0 errors)
- [ ] Rodou `ruff check backend/` (0 errors)
- [ ] Acessou VPS via Tailscale
- [ ] Viu logs dos 8 serviços principais
- [ ] Criou 1 endpoint simples (exercício)
- [ ] Criou 1 WF simples (exercício)
- [ ] Adicionou 1 teste
- [ ] Respondeu 1 ticket de suporte
- [ ] Conheceu o time (Pietra squad)

**Se todos ✅**: Bem-vindo ao time! 🚀

---

**Mantido por**: Pietra (orquestrador)
**Próxima revisão**: 2026-07-02
**Versão**: 1.0.0
