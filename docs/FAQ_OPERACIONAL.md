# FAQ Operacional — Cartório Chatbot

> Perguntas frequentes operacionais para o time técnico.
> Última atualização: 2026-06-26.

## Índice

1. [Geral](#1-geral)
2. [Deploy e Atualizações](#2-deploy-e-atualizações)
3. [Bancos de Dados](#3-bancos-de-dados)
4. [Integrações](#4-integrações)
5. [Monitoramento e Logs](#5-monitoramento-e-logs)
6. [LGPD e Compliance](#6-lgpd-e-compliance)
7. [Agent AI (Pietra)](#7-agent-ai-pietra)
8. [N8N Workflows](#8-n8n-workflows)
9. [Segurança](#9-segurança)
10. [Performance](#10-performance)

---

## 1. Geral

### 1.1 O que é o Cartório Chatbot?

Sistema de **atendimento automatizado via WhatsApp** para o **2º Cartório de Notas de Uberlândia**, focado em:
- Consultar emolumentos (MG 2026)
- Criar protocolos de atendimento
- Agendar visitas presenciais
- Solicitar segunda via de documentos
- Colher consentimento LGPD

Tecnologia: FastAPI + N8N + Supabase + OpenClaw + Evolution API + Chatwoot + Redis.

### 1.2 Qual o status atual do sistema?

| Serviço | URL | Status |
|---------|-----|--------|
| API | api.2notasudi.com.br | ✅ UP |
| N8N | flow.2notasudi.com.br | ✅ UP |
| Supabase | supbase.2notasudi.com.br | ✅ UP |
| Evolution | whatsapp.2notasudi.com.br | ✅ UP |
| Chatwoot | chat.2notasudi.com.br | ✅ UP |
| OpenClaw | agent.2notasudi.com.br | ✅ UP |
| Redis | interno | ✅ UP |
| Easypanel | easypanel.2notasudi.com.br | ✅ UP |

Verificar em tempo real: `curl https://api.2notasudi.com.br/api/v1/health/radar`

### 1.3 Quem é Pietra?

**Pietra** é o **Agent AI** (OpenClaw Gateway) que atende clientes via WhatsApp. Personalidade:
- **Bem direto** — respostas curtas
- **Sério** — linguagem formal/profissional
- **Sem emojis** — contexto cartorial
- **Sempre pensa antes de responder** (thinking ON)
- **Nunca inventa** — confirma dados com fontes
- **7 skills ativas**: saudacoes, protocolo-tracker, emolumento-calc, agendamento, segunda-via, lgpd-consent, handoff-humano

---

## 2. Deploy e Atualizações

### 2.1 Como fazer deploy da API?

**Método preferencial**: CI/CD via GitHub Actions (J07 PENDENTE) ou manual via Easypanel.

**Manual (1-2 min)**:
```bash
# 1. Commit + push
git add -A && git commit -m "feat(api): nova feature"
git push origin master

# 2. Easypanel reconstrói automaticamente (webhook configurado)
# Ou forçar: Easypanel UI → cartorio_api → Deploy
```

### 2.2 Como adicionar nova migration Alembic?

```bash
# Local
cd backend
alembic revision --autogenerate -m "add_new_field"

# Editar arquivo gerado em alembic/versions/ (revisar SQL!)

# Testar local
alembic upgrade head

# Push
git add -A && git commit -m "feat(db): add new field migration"
git push origin master

# Em prod, migration roda automaticamente no startup da API
# Se falhar, ver E07_OPENCLAW_CONTEXT_FIX.md (mesmo padrão de recovery)
```

### 2.3 Rollback de deploy?

```bash
# 1. Easypanel UI → cartorio_api → Deployments → Rollback para versão anterior
# Ou via API:
ssh root@100.99.172.84 "docker service rollback cartorio_api"

# 2. Se migration Alembic falhou, downgrade:
ssh root@100.99.172.84 "docker exec \$(docker ps -qf 'name=cartorio_api') alembic downgrade -1"

# 3. Verificar health
sleep 30 && curl -fsS https://api.2notasudi.com.br/health
```

### 2.4 Como atualizar dependências Python?

```bash
# 1. Editar backend/requirements.txt
# 2. Local: pip install -r requirements.txt + rodar testes
cd backend && pip install -r requirements.txt && pytest tests/

# 3. Commit
git add backend/requirements.txt
git commit -m "chore(deps): update fastapi to 0.115"
git push origin master

# 4. CI roda pip-audit automaticamente
```

---

## 3. Bancos de Dados

### 3.1 Quantas tabelas temos?

**134 tabelas totais** (Supabase self-hosted), sendo **13 tabelas core do Cartório**:
- clientes
- protocolos
- atendimentos
- documentos
- emolumentos
- conversas
- agendamentos
- audit_log
- outbox_messages
- webhook_events
- lgpd_consents
- lgpd_audit_anpd
- workflow_publication_outbox

### 3.2 Como ver schema de uma tabela?

```bash
# Via psql
ssh root@100.99.172.84 "docker exec \$(docker ps -qf 'name=cartorio_supabase-db') psql -U postgres -d postgres -c '\d clientes'"

# Via PostgREST (HTTP)
curl -fsS "https://supbase.2notasudi.com.br/rest/v1/clientes?select=*&limit=1" \
  -H "apikey: $SUPABASE_ANON_KEY"
```

### 3.3 Como limpar dados de teste?

```sql
-- ATENÇÃO: NÃO rodar em produção!
-- Primeiro backup
-- Depois limpar tabelas específicas
TRUNCATE TABLE clientes CASCADE;
TRUNCATE TABLE protocolos CASCADE;
TRUNCATE TABLE atendimentos CASCADE;
-- NÃO truncar audit_log! (LGPD exige 5 anos retenção)
```

### 3.4 Como criar nova tabela?

```bash
# 1. Adicionar model SQLAlchemy
# backend/app/models/nova_tabela.py

# 2. Criar migration
cd backend
alembic revision --autogenerate -m "add nova_tabela"

# 3. Revisar SQL gerado (autogenerate nem sempre é perfeito!)

# 4. Aplicar
alembic upgrade head

# 5. Testar
pytest backend/tests/test_nova_tabela.py

# 6. Commit
git add -A && git commit -m "feat(db): add nova_tabela"
git push origin master
```

---

## 4. Integrações

### 4.1 Quais serviços externos estão integrados?

| Serviço | Função | Auth |
|---------|--------|------|
| **Evolution API** | WhatsApp gateway | API key header |
| **OpenClaw** | Agent AI | API key (OpenCode-Go) |
| **Chatwoot** | CRM | OAuth2 + access token |
| **Telegram** | Notificações | Bot token |
| **Supabase** | DB + Auth + Storage | JWT + service role key |
| **Redis** | Cache | Password |
| **Render** | CI/CD preview | API key |
| **Linear** | Gestão de tasks | API key |
| **Jules (Gemini 3.1 Pro)** | Análise de código | API key |

### 4.2 Como adicionar nova integração?

```python
# 1. Adicionar settings em backend/app/config.py
class Settings(BaseSettings):
    novo_servico_url: str
    novo_servico_key: str

# 2. Criar service backend/app/services/novo_servico.py
class NovoServicoClient:
    def __init__(self):
        self.base_url = settings.novo_servico_url
        self.api_key = settings.novo_servico_key
    
    async def call(self, endpoint: str, payload: dict) -> dict:
        async with httpx.AsyncClient() as client:
            r = await client.post(
                f"{self.base_url}/{endpoint}",
                json=payload,
                headers={"Authorization": f"Bearer {self.api_key}"}
            )
            r.raise_for_status()
            return r.json()

# 3. Adicionar endpoint em backend/app/api/v1/router.py

# 4. Testes em backend/tests/test_novo_servico.py

# 5. Documentação em docs/API.md
```

### 4.3 Webhook do Evolution API não está chegando

```bash
# 1. Verificar webhook configurado
curl -fsS "https://whatsapp.2notasudi.com.br/webhook/find/cartorio-2notas" \
  -H "apikey: $EVO_KEY" | jq

# 2. Se vazio, reconfigurar
curl -fsS -X POST "https://whatsapp.2notasudi.com.br/webhook/set/cartorio-2notas" \
  -H "apikey: $EVO_KEY" \
  -H "Content-Type: application/json" \
  -d '{"url": "https://flow.2notasudi.com.br/webhook/evo-in", "events": ["MESSAGES_UPSERT"]}'

# 3. Testar envio de mensagem (de outro WhatsApp)
# 4. Ver logs N8N WF #01
```

---

## 5. Monitoramento e Logs

### 5.1 Como ver logs de um serviço?

```bash
# API
ssh root@100.99.172.84 "docker service logs cartorio_api --tail 100 -f"

# N8N
ssh root@100.99.172.84 "docker service logs cartorio_n8n --tail 100 -f"

# OpenClaw
ssh root@100.99.172.84 "docker service logs cartorio_openclaw-gateway --tail 100 -f"

# Redis
ssh root@100.99.172.84 "docker exec \$(docker ps -qf 'name=cartorio_redis') redis-cli -p 6379 -a \$REDIS_AUTH MONITOR"
```

### 5.2 Como adicionar métrica customizada?

```python
# Backend (prometheus_client)
from prometheus_client import Counter, Histogram

minha_metrica = Counter(
    'cartorio_minha_metrica_total',
    'Descrição da métrica',
    ['label1', 'label2']
)

# Usar:
minha_metrica.labels(label1='valor1', label2='valor2').inc()

# Expor via /metrics endpoint (já configurado em main.py)
```

### 5.3 Como configurar alerta novo?

```bash
# 1. Adicionar template em backend/app/services/telegram.py
# 2. Criar trigger (cron N8N WF ou endpoint chamado de código)
# 3. Testar envio
curl -fsS -X POST "https://api.2notasudi.com.br/api/v1/alertas/test" \
  -H "X-API-Key: $API_KEY" \
  -d '{"template": "service_down", "vars": {"service": "api"}}'
```

---

## 6. LGPD e Compliance

### 6.1 O que é PII?

**PII (Personally Identifiable Information)** = dados que identificam pessoa:
- CPF, RG, CNH, CNS, passaporte
- Telefone, email
- Endereço
- Data de nascimento
- Nome completo + qualquer outro identificador

**Implementado**: PII scrub em `backend/app/middleware/pii_scrub.py` remove PII ANTES de logar.

### 6.2 Quais endpoints expõem dados sensíveis?

Todos os endpoints `/api/v1/clientes/*` e `/api/v1/lgpd/*`:
- **Autenticação obrigatória** (X-API-Key ou JWT)
- **RLS ativo** no Supabase (clientes, protocolos, documentos, audit_log)
- **Audit log** registra toda leitura

### 6.3 Como exportar dados de um cliente (D08)?

```bash
# Cliente pede portabilidade via WhatsApp
# Pietra identifica, confirma dados, e gera export JSON+ZIP

# Manual (admin):
curl -fsS "https://api.2notasudi.com.br/api/v1/lgpd/portabilidade/$CPF" \
  -H "X-API-Key: $API_KEY" \
  -o /tmp/portabilidade-$CPF.zip

# Resposta: ZIP com clientes.json, protocolos.json, atendimentos.json
# Manda para cliente via email (com link S3 assinado 7d)
```

### 6.4 Como excluir dados de cliente (D09)?

```bash
# 1. Cliente pede exclusão
# 2. API registra solicitação (status=PENDING, prazo=30 dias)
# 3. Cron roda diariamente, anonimiza após 30 dias

# Forçar execução manual (emergência):
curl -fsS -X POST "https://api.2notasudi.com.br/api/v1/lgpd/process-exclusions" \
  -H "X-API-Key: $API_KEY"

# Anonimização preserva:
# - audit_log (5 anos - LGPD art. 37)
# - lgpd_audit_anpd (registro da solicitação)
# Remove:
# - nome, CPF, telefone, email → "ANONIMIZADO-{hash}"
# - conversas, protocolos, documentos do cliente
```

---

## 7. Agent AI (Pietra)

### 7.1 Como testar Pietra localmente?

```bash
# 1. Via Telegram (pré-teste)
# Mandar mensagem para @test_cartorio_bot

# 2. Via WebSocket (dev)
python -c "
import websockets, asyncio, json
async def test():
    async with websockets.connect('wss://agent.2notasudi.com.br/v1/chat') as ws:
        await ws.send(json.dumps({'message': 'Olá', 'session_id': 'test-123'}))
        response = await ws.recv()
        print(response)
asyncio.run(test())
"
```

### 7.2 Como adicionar nova skill ao agent?

```bash
# 1. SSH VPS
ssh root@100.99.172.84

# 2. Editar agent config
nano /var/lib/docker/volumes/cartorio_openclaw-gateway_config/_data/agents/main/agent/agent.json

# 3. Adicionar nova skill no array "skills":
{
  "name": "minha-skill",
  "description": "Faz X",
  "triggers": ["keyword1", "keyword2"],
  "handler": "minha_skill_handler"
}

# 4. Restart
docker service update --force cartorio_openclaw-gateway
```

### 7.3 Contexto do agent é 1M mesmo?

**SIM** (corrigido em 2026-06-25 via SSH VPS injection - ver E07_OPENCLAW_CONTEXT_FIX.md).

```bash
# Verificar
ssh root@100.99.172.84 "cat /var/lib/docker/volumes/cartorio_openclaw-gateway_config/_data/agents/main/agent/models.json | jq '.providers.opencode_go.models[0].contextWindow'"
# Esperado: 1048576 (1M)
```

### 7.4 Thinking está ativado?

**SIM** (adaptive ON, budget 10k tokens).

```bash
ssh root@100.99.172.84 "cat /var/lib/docker/volumes/cartorio_openclaw-gateway_config/_data/agents/main/agent/agent.json | jq '.thinking'"
# Esperado: {"enabled": true, "mode": "adaptive", "budget_tokens": 10000}
```

---

## 8. N8N Workflows

### 8.1 Quantos workflows temos?

**34 workflows ativos** (jun/2026), organizados em:
- 1 error handler global (WF #00)
- 14 core atendimento (saudação, protocolo, emolumento, agendamento, etc)
- 8 cron/monitoramento (health, backup, audit, metrics)
- 11 auxiliares (HITL, FAQ, pesquisa, etc)

### 8.2 Como ativar workflow inativo?

```bash
curl -fsS -X PATCH "https://flow.2notasudi.com.br/api/v1/workflows/$WF_ID" \
  -H "X-N8N-API-KEY: $N8N_KEY" \
  -H "Content-Type: application/json" \
  -d '{"active": true}'
```

### 8.3 Como ver execuções com erro?

```bash
curl -fsS "https://flow.2notasudi.com.br/api/v1/executions?status=error&limit=20" \
  -H "X-N8N-API-KEY: $N8N_KEY" | jq '.data[] | {id, workflowId, startedAt, error: .data.resultData.error.message}'
```

### 8.4 WF com timeout

**Default**: 5s para HTTP nodes (B08 aplicado em 130/130 nodes).

**Override por node**:
- LLM calls (OpenClaw): 30s
- File ops (MinIO, Supabase Storage): 60s
- Webhooks: 10s

Configurar no node: Settings → Timeout → 30000 (ms).

---

## 9. Segurança

### 9.1 Como adicionar nova API key?

```bash
# 1. Adicionar ao .env (VPS)
ssh root@100.99.172.84
nano /etc/easypanel/projects/cartorio/api/code/.env
# Adicionar: NOVA_KEY=xxx

# 2. Adicionar ao settings
# backend/app/config.py
nova_key: str = ""

# 3. Reiniciar API
docker service update --force cartorio_api

# 4. Testar
curl -fsS "https://api.2notasudi.com.br/api/v1/health/radar" -H "X-API-Key: $NOVA_KEY"
```

### 9.2 CORS está configurado?

**SIM** (backend/app/main.py):
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "https://admin.2notasudi.com.br",
        "https://app.2notasudi.com.br",
        "https://chat.2notasudi.com.br",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### 9.3 Como rotacionar uma chave?

**ATENÇÃO**: REGRA ABSOLUTA — **NUNCA rotacionar chaves** (Bloco 2.1 SUPER PROMPT v4.0.0).

Se uma chave foi comprometida:
1. Reportar IMEDIATAMENTE para Gustavo
2. Avaliar impacto (exposição em logs, etc)
3. Decisão: Gustavo autoriza rotação manual após análise

---

## 10. Performance

### 10.1 Como medir latência de endpoint?

```bash
# 1 request
time curl -fsS "https://api.2notasudi.com.br/api/v1/clientes?limit=10" \
  -H "X-API-Key: $API_KEY"

# 100 requests (concorrentes=10)
ab -n 100 -c 10 "https://api.2notasudi.com.br/api/v1/clientes?limit=10" \
  -H "X-API-Key: $API_KEY"

# Ver p50, p95, p99 no output
```

### 10.2 Como encontrar query lenta?

```bash
# Endpoint oficial (E8.A16)
curl -fsS "https://api.2notasudi.com.br/admin/slow-queries?limit=20" \
  -H "X-API-Key: $API_KEY" | jq

# Cada item: {path, query, duration_ms, timestamp}
```

### 10.3 Como melhorar performance?

1. **Adicionar índice** na coluna consultada
2. **Cache Redis** (TTL variável conforme criticidade)
3. **Eager loading** SQLAlchemy (joinedload, selectinload)
4. **Paginação** (nunca `SELECT *` sem LIMIT)
5. **Materialized view** para agregações pesadas

Exemplo:
```python
# Ruim (N+1)
clientes = session.query(Cliente).all()
for c in clientes:
    protocolos = c.protocolos  # 1 query por cliente!

# Bom (eager)
from sqlalchemy.orm import joinedload
clientes = session.query(Cliente).options(joinedload(Cliente.protocolos)).all()
```

---

## 11. Recursos Adicionais

| Recurso | Link |
|---------|------|
| **Super Prompt v4.0.0** | /PROMPT.MD |
| **Versionamento** | /docs/VERSIONAMENTO_PROJETO.md |
| **Changelog** | /docs/CHANGELOG.md |
| **Roadmap** | /docs/ROADMAP.md |
| **Task Bank** | /.harness/task-bank-100-melhorias.json |
| **Architecture Diagram** | /docs/platforms/ARCHITECTURE_DIAGRAM.md |
| **Glossário** | /docs/platforms/GLOSSARY.md |
| **API Quick Ref** | /docs/API_QUICK_REFERENCE.md |
| **N8N Docs** | /docs/platforms/N8N.md |
| **Evolution Docs** | /docs/platforms/EVOLUTION.md |
| **Chatwoot Docs** | /docs/platforms/CHATWOOT.md |
| **Supabase Docs** | /docs/platforms/SUPABASE.md |
| **Redis Docs** | /docs/platforms/REDIS.md |
| **OpenClaw Docs** | /docs/platforms/OPENCLAW.md |
| **Troubleshooting** | /docs/TROUBLESHOOTING.md |
| **Monitoring** | /docs/MONITORING_GUIDE.md |
| **Sessões anteriores** | /SESSION_SUMMARY_*.md |

---

**Mantido por**: Pietra (orquestrador)
**Próxima revisão**: 2026-07-02
**Versão**: 1.0.0
