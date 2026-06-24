# FAQ - Cartorio Chatbot

> **Troubleshooting dos 20 problemas mais comuns.**
> Ultima atualizacao: 2026-06-24

## Sumario

1. [Backend Python](#backend-python)
2. [Banco de Dados (Supabase)](#banco-de-dados-supabase)
3. [Redis](#redis)
4. [N8N Workflows](#n8n-workflows)
5. [Evolution API (WhatsApp)](#evolution-api-whatsapp)
6. [Chatwoot (CRM)](#chatwoot-crm)
7. [OpenClaw Gateway](#openclaw-gateway)
8. [Easypanel / Deploy](#easypanel--deploy)
9. [LGPD / Auditoria](#lgpd--auditoria)
10. [Testes / CI](#testes--ci)

---

## Backend Python

### P1. pytest falha com "FAIL Required test coverage of 90% not reached"

**Causa**: rodou pytest em 1 arquivo de teste, nao a suite completa.

**Solucao**:
```bash
cd backend
uv run pytest  # suite completa, NAO pytest tests/test_X.py
```

Se o coverage REAL esta abaixo de 90% em alguns arquivos, ver:
```bash
uv run pytest --cov=app --cov-report=term-missing
```
Identifica quais linhas nao tem teste.

### P2. mypy reclama de "Incompatible types in assignment" em dicts aninhados

**Causa**: inferencia cascata do mypy em `self.dict.items()`.

**Solucao** (ja aplicada em metrics.py): usar `cast("TipoExato", self.dict)` antes do loop:
```python
counters: dict[str, dict[str, int]] = cast("dict[str, dict[str, int]]", self.counters)
for name, buckets in counters.items():  # type: ignore[assignment]
    ...
```

Ref: `backend/app/services/metrics.py`

### P3. "StarletteDeprecationWarning: Using httpx with starlette.testclient is deprecated"

**Causa**: lib httpx mudou de API em 2024.

**Status**: warning cosmico, NAO bloqueia testes. 400+ testes passam.

**Solucao definitiva** (Sprint 4+): atualizar `httpx` para `httpx2`. Por enquanto, suprimir com `filterwarnings` em `pyproject.toml`.

### P4. Uvicorn nao sobe: "Address already in use" na porta 8000

**Causa**: outro processo usa porta 8000.

**Diagnostico**:
```bash
lsof -i :8000
# ou
sudo lsof -iTCP:8000 -sTCP:LISTEN
```

**Solucao**:
```bash
# Matar o processo (substituir PID)
kill -9 <PID>

# Ou subir em outra porta
uv run uvicorn app.main:app --reload --port 8001
```

### P5. "ModuleNotFoundError: No module named 'app'"

**Causa**: rodou pytest de fora do venv ou sem `uv run`.

**Solucao**:
```bash
cd backend
uv run pytest  # NAO pytest direto
```

`uv run` ativa o venv automaticamente.

### P6. "ImportError: cannot import name 'X' from 'app.Y'"

**Causa**: refatorou `app/Y.py` e removeu/renomeou `X`.

**Solucao**: verificar git blame e reverter OU ajustar os imports.

```bash
git log --all --oneline -- backend/app/Y.py
git diff HEAD~5 backend/app/Y.py  # ver mudancas recentes
```

---

## Banco de Dados (Supabase)

### P7. "supavisor-1 restart loop" no Easypanel

**Causa conhecida**: postmaster usa `/etc/postgresql/pg_hba.conf` (NAO `/var/lib/postgresql/data/pg_hba.conf`). Trap do Supabase custom image.

**Solucao** (RCA documentada em `MEMORY.md`):
```bash
docker exec cartorio_supabase-db-1 \
  bash -c 'echo "host all all 10.0.0.0/8 trust" >> /etc/postgresql/pg_hba.conf'
docker service update --force cartorio_supabase-db-1
```

Ref: `MEMORY.md` secao "2026-06-23 - Sprint 0.5 hardening".

### P8. "password authentication failed for user supabase_admin"

**Causa**: n8n/Evolution/Chatwoot em outro Swarm service nao tem rede do Supabase.

**Solucao**:
```bash
# 1. Garantir que o servico esta na rede compose do Supabase
docker service update --network-add cartorio_supabase_default cartorio_n8n

# 2. Resetar senha do supabase_admin
docker exec cartorio_supabase-db-1 psql -U supabase_admin -h 127.0.0.1 \
  -c "ALTER USER supabase_admin WITH PASSWORD '<env_pwd>';"
```

Ref: `MEMORY.md` secao "n8n com senha Supabase errada".

### P9. Alembic "Can't locate revision identified by 'XXXX'"

**Causa**: banco tem migration de outra branch, ou versao nao foi aplicada.

**Solucao**:
```bash
cd backend
uv run alembic current    # ver o que o banco tem
uv run alembic history    # ver o que deveria ter
uv run alembic stamp head  # forcar que banco esta atualizado (CUIDADO)
# OU
uv run alembic upgrade head  # aplicar migrations faltantes
```

### P10. "duplicate key value violates unique constraint" em `cliente.cpf_hash`

**Causa**: 2 clientes com mesmo CPF. Ou (mais comum) o hash do CPF esta sendo gerado com salt diferente.

**Diagnostico**:
```sql
-- No Supabase Studio
SELECT cpf_hash, COUNT(*) FROM clientes GROUP BY cpf_hash HAVING COUNT(*) > 1;
```

**Solucao**: verificar que `hash_pii(value, salt)` usa o **mesmo salt** sempre. Salt vem de `settings.cpf_salt` (ou similar) no `.env`.

---

## Redis

### P11. "Connection refused" em redis na porta 6379

**Causa 1**: Redis nao esta rodando.

```bash
docker ps | grep cartorio_redis
# se nao aparecer:
docker service scale cartorio_redis=1
```

**Causa 2**: firewall DOCKER-USER DROP bloqueia 6379 externo.

**Solucao**: usar porta host 1001 (ja exposta):
```bash
redis-cli -h 187.77.236.77 -p 1001 ping
```

**Causa 3**: senha URL-encoded errada.

```bash
# Se a senha tem @, URL-encode para %40
REDIS_URL=redis://default:Techno%40832466@cartorio_redis:6379/0
```

### P12. Rate limit nao esta bloqueando (fail-open sempre)

**Causa**: Redis offline OU configuracao de fail-open intencional.

**Diagnostico**:
```bash
docker logs cartorio_redis 2>&1 | tail -20
curl -s http://localhost:8000/api/v1/health/radar | grep redis
```

**Solucao**:
- Se Redis offline: reiniciar
- Se Redis online mas fail-open: checar logs do backend para "rate_limit: Redis offline"

---

## N8N Workflows

### P13. N8N retorna 401 "Unauthorized" mesmo com X-N8N-API-KEY

**Causa**: header errado ou key expirada.

**Solucao**:
```bash
# Testar a key direto
curl -s -H "X-N8N-API-KEY: $N8N_API_KEY" \
  http://flow.2notasudi.com.br/api/v1/workflows?limit=10 | head -20

# Se 401, a key foi revogada. Criar nova:
# 1. Logar em https://flow.2notasudi.com.br
# 2. Settings > API > Create API Key
# 3. Atualizar .env do backend
```

### P14. Workflow fica "Waiting" para sempre

**Causa**: node de "Wait" sem condicao de saida, ou webhook nao foi chamado.

**Diagnostico**:
```bash
# Ver executions do workflow
curl -s -H "X-N8N-API-KEY: $N8N_API_KEY" \
  "http://flow.2notasudi.com.br/api/v1/executions?workflowId=<ID>&limit=5" \
  | python3 -m json.tool
```

**Solucao**: editar workflow e adicionar timeout no Wait, ou usar Error Workflow.

### P15. "Workflow could not be started" - credencial invalida

**Causa**: credencial Evolution/Chatwoot/Supabase foi revogada ou expirou.

**Solucao**:
1. Abrir workflow no N8N UI
2. No node que falha, clicar em "Create New Credential"
3. Testar com "Test Connection"
4. Salvar e re-executar

Ref: `MEMORY.md` "Workflow #07 sem credential Evolution" (B4 SUI).

---

## Evolution API (WhatsApp)

### P16. Evolution retorna "Instance not found"

**Causa**: instance foi deletada OU nome da instance errado.

**Solucao**:
```bash
# Listar instances
curl -s -H "apikey: $EVOLUTION_API_KEY" \
  http://whatsapp.2notasudi.com.br/instance/fetchInstances | python3 -m json.tool

# Criar nova
curl -s -X POST -H "Content-Type: application/json" -H "apikey: $EVOLUTION_API_KEY" \
  -d '{"instanceName": "cartorio-2notas", "qrcode": true}' \
  http://whatsapp.2notasudi.com.br/instance/create
```

### P17. WhatsApp desconecta sozinho (instance "close")

**Causa 1**: WhatsApp Web multi-device fez logout.

**Causa 2**: container Evolution perdeu conexao (memory, network).

**Solucao**:
```bash
# Restart instance
curl -s -X POST -H "apikey: $EVOLUTION_API_KEY" \
  http://whatsapp.2notasudi.com.br/instance/restart/cartorio-2notas

# Se persistir, recriar:
curl -s -X DELETE -H "apikey: $EVOLUTION_API_KEY" \
  http://whatsapp.2notasudi.com.br/instance/delete/cartorio-2notas
# (recriar via P16)
```

### P18. Webhook Evolution nao chega no backend

**Causa 1**: URL do webhook errada (http vs https, ou porta).

**Causa 2**: firewall bloqueia.

**Solucao**:
```bash
# 1. Ver webhook configurado
curl -s -H "apikey: $EVOLUTION_API_KEY" \
  http://whatsapp.2notasudi.com.br/webhook/find/cartorio-2notas

# 2. Atualizar
curl -s -X POST -H "Content-Type: application/json" -H "apikey: $EVOLUTION_API_KEY" \
  -d '{
    "url": "https://api.2notasudi.com.br/api/v1/webhook/evolution",
    "events": ["MESSAGES_UPSERT", "CONNECTION_UPDATE"]
  }' \
  http://whatsapp.2notasudi.com.br/webhook/set/cartorio-2notas

# 3. Testar
curl -X POST https://api.2notasudi.com.br/api/v1/webhook/evolution \
  -H "Content-Type: application/json" \
  -d '{"event": "test", "instance": "cartorio-2notas"}'
```

---

## Chatwoot (CRM)

### P19. "502 Bad Gateway" em chat.2notasudi.com.br

**Causa 1**: DNS nao configurado para `chatwoot.2notasudi.com.br` (B3 SUI - 10min pra resolver).

**Causa 2**: Chatwoot em restart loop (B1 SUI - ver ADR-015).

**Solucao** (B3):
1. Easypanel UI > Services > cartorio_chatwoot > Domains
2. Add `chatwoot.2notasudi.com.br`
3. Ajustar `FRONTEND_URL` no env

Ref: `MEMORY.md` "DNS typo `supbase` vs `supabase`".

### P20. Chatwoot API retorna 401 mesmo com API key

**Causa**: API key revogada OU key de outra account.

**Solucao**:
```bash
# Testar key
curl -s -H "api_access_token: $CHATWOOT_API_KEY" \
  http://cartorio_chatwoot:3000/api/v1/accounts | head

# Se 401, criar nova key:
# 1. Logar em https://chat.2notasudi.com.br (super_admin)
# 2. Settings > Access Token > Create
```

---

## OpenClaw Gateway

### P21. "Refusing to bind gateway to lan without auth" (OpenClaw crash loop)

**Causa 1**: `OPENCLAW_GATEWAY_TOKEN` nao definido OU `--token` nao passado.

**Causa 2**: config `openclaw.json` nao tem `gateway.mode=local` OU `--allow-unconfigured` nao passado.

**Solucao** (RCA documentada em `MEMORY.md`):
```bash
# 1. Adicionar ao env do servico
OPENCLAW_GATEWAY_TOKEN=<64_hex_chars>

# 2. Mudar args do Swarm service:
# Easypanel UI > cartorio_openclaw-gateway > Edit > Command
# Args: --bind auto --port 18790 --allow-unconfigured
# User: node
```

### P22. OpenClaw context overflow (B2 SUI)

**Sintoma**: OpenClaw reinicia a cada 50-100 mensagens, perdendo contexto.

**Causa**: threshold de contexto nao configurado.

**Solucao** (5min):
1. OpenClaw UI: Settings > Context > Max messages = 50
2. TTL: 24h
3. Compaction manual se necessario: `curl -X POST .../compact`

Ref: `MEMORY.md` "OpenClaw crash loop" + ADR-016.

---

## Easypanel / Deploy

### P23. "Easypanel API 401" - API key expirada

**Causa**: key rotacionada.

**Solucao**:
1. Logar em https://easypanel.2notasudi.com.br
2. Settings > API Keys > Generate New
3. Atualizar `EASYPANEL_API_KEY` em todos os .env (backend, scripts)

### P24. "Service failed to start" no Easypanel

**Causa 1**: imagem Docker nao foi pullada.

**Causa 2**: env vars faltando.

**Diagnostico**:
```bash
# Ver logs do servico
easypanel-cli services logs cartorio_api --tail 100

# OU via UI: Service > Logs
```

**Solucao**:
- Imagem: `docker pull <imagem>` e restart
- Env: comparar com `.env.example` e adicionar o que falta

---

## LGPD / Auditoria

### P25. "Audit chain broken" no `POST /api/v1/audit/verify`

**Causa**: alguma entrada do `audit_log` foi editada OU o hash chain tem inconsistencia.

**Diagnostico**:
```sql
-- No Supabase Studio
SELECT id, hash_anterior, hash_atual, criado_em
FROM audit_log
ORDER BY id DESC
LIMIT 10;

-- Ver o ponto exato de quebra
SELECT id FROM audit_log
WHERE hash_anterior != (
  SELECT hash_atual FROM audit_log a2 WHERE a2.id = audit_log.id - 1
)
LIMIT 5;
```

**Solucao**: audit log e append-only por design. Se foi editado, o sistema esta comprometido. Investigar.

**Prevencao**: `pgcrypto` + permissao de DB `INSERT-only` no role do backend.

### P26. Cliente pede "esqueci meu dado" (direito ao esquecimento, LGPD art. 18 VI)

**Solucao**:
1. Verificar se pedido foi feito por canal autenticado
2. Endpoint: `POST /api/v1/lgpd/direito-esquecimento` (ja existe em `app/services/lgpd/direito_esquecimento.py`)
3. Soft delete + audit log
4. Confirmar ao cliente em <15 dias (prazo LGPD)

---

## Testes / CI

### P27. "Test X is flaky" - passa 9 de 10 vezes

**Causas comuns**:
- Race condition em teste async
- Mock que nao cobre edge case
- Dependencia de timing (sleep)

**Solucao**:
```bash
# Rodar 10x para confirmar flake
for i in {1..10}; do uv run pytest tests/test_X.py::test_flaky --tb=line -q || break; done
```

Se flake for real, substituir `time.sleep()` por `await event.wait()` ou usar `freezegun` para tempo deterministico.

### P28. "pytest -W error" falha por warning de lib externa

**Causa**: FastAPI/OpenTelemetry/httpx emitem DeprecationWarning.

**Solucao**: filtrar warnings especificos em `pyproject.toml`:
```toml
[tool.pytest.ini_options]
filterwarnings = [
    "ignore::DeprecationWarning:opentelemetry",
    "ignore::StarletteDeprecationWarning",
]
```

---

## Precisa de mais ajuda?

- **MEMORY.md** (`.harness/memory/MEMORY.md`) - licoes cross-rein
- **RUNBOOK** (`docs/RUNBOOK_VPS.md`) - comandos de producao
- **ADRs** (`docs/adr/`) - decisoes arquiteturais
- **Logs do backend**: `easypanel services logs cartorio_api --tail 200`

Modified by ZCode/Mavis - 2026-06-24
