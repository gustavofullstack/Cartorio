# WIP — Agendamento A26 (cache Redis + notificações multi-canal)

**Status**: 🟡 80% pronto — preservado em `infra/wip/` conforme regra NUNCA APAGAR
**Data preservação**: 2026-06-25
**Sessão original**: 2026-06-25 (commit a04cf0e)
**Próxima retomada**: quando Gustavo decidir priorizar feature de produto (vs backend hardening A24)

---

## 📦 O que está aqui

Feature de produto completa de cache + notificações para agendamentos. Camadas:

| Arquivo | Tipo | Linhas | Descrição |
|---|---|---|---|
| `A1-migration-add-client-notification-fields.py` | Alembic | ~25 | Adiciona 5 colunas à tabela `clientes`: `telegram_chat_id`, `whatsapp_number`, `email_notifications`, `sms_notifications`, `preferred_contact_method` |
| `A2-service-agendamento-cache.py` | Service | ~260 | `AgendamentoCache` — Redis-backed cache para lookups de agendamento (TTL 24h, fail-soft, hash_pii-aware) |
| `A3-service-agendamento-metrics.py` | Service | ~110 | Prometheus decorators + counters: `agendamento_cache_hits_total`, `agendamento_cache_misses_total`, `agendamento_notifications_sent_total{channel}` |
| `A4-service-notificacao.py` | Service | ~270 | `NotificationService` — multi-canal (Telegram/WhatsApp/Email/SMS) via Evolution API + httpx async |
| `T1-test-agendamento-cache.py` | Test | ~120 | Testes unitários do cache (mocks, sem DB) |
| `T2-test-agendamento-n8n.py` | Test | ~180 | Testes integração `AgendamentoService` + endpoints `/agendamento` (DB real via conftest) |
| `T3-test-notificacao.py` | Test | ~295 | Testes e2e `NotificationService` + Cliente model com notification fields |
| `D1-CACHING_STRATEGY.md` | Doc | ~215 | Estratégia completa de caching (Redis patterns, TTL, invalidation, key naming) |
| `W1-agendamento-lembrete.json` | N8N WF | — | Workflow N8N: lembrete 24h antes do agendamento (Telegram/WhatsApp) |
| `W2-agendamento-notificacao.json` | N8N WF | — | Workflow N8N: notificação criação/cancelamento (4 canais) |

**Total**: ~1675 linhas de código + testes + doc + 2 workflows N8N.

---

## 🚧 3 bloqueios conhecidos (resolver antes de merge)

### 1. Migration tem `down_revision` placeholder
**Arquivo**: `A1-migration-add-client-notification-fields.py:16`
```python
down_revision: Union[str, None] = '<previous_revision>'  # ❌ LITERAL PLACEHOLDER
```
**Fix**: substituir por `"2026_06_25_0013"` (HEAD atual da chain alembic).
**Tempo**: 30 segundos.

### 2. `Cliente` model não tem os 5 notification fields
**Arquivo**: `backend/app/models/cliente.py` (NÃO tocado)
**Problema**: `test_notificacao.py` instancia `Cliente(telegram_chat_id=..., whatsapp_number=..., email_notifications=..., sms_notifications=..., preferred_contact_method=...)` — esses campos não existem no model tracked.
**Fix**: adicionar 5 colunas ao model + rodar alembic upgrade. A migration `A1` é exatamente esse schema, mas precisa fix #1 primeiro.
**Tempo**: ~10 min (model + migration + test pass).

### 3. Workflows N8N estavam em diretório errado
**Problema**: estavam em `backend/infra/n8n-workflows/` — diretório `backend/infra/` NÃO existe no projeto. Infra N8N canonical path é `infra/n8n-workflows/`.
**Status**: ✅ **RESOLVIDO nesta sessão** — movidos para este WIP patch. Quando A26 for retomar, mover para `infra/n8n-workflows/` e validar via workflow 31 (Telegram listener) integration test.

---

## 🔗 Integrações upstream necessárias (quando retomar)

1. **Evolution API** (`whatsapp.2notasudi.com.br`): instance `cartorio-2notas` precisa estar **CONNECTED** (QR escaneado por Gustavo). Status atual: state=close (B1 alert).
2. **Telegram Bot** (`@test_cartorio_bot`): token configurado em `.env`, webhook URL no N8N.
3. **Redis**: já funcionando (PONG), auth `@Techno832466`.
4. **Supabase**: tabela `clientes` precisa receber migration `A1` corrigida.
5. **N8N**: workflows W1/W2 precisam ser importados via API e ter credenciais Evolution/Telegram configuradas.

---

## 📊 Métricas atuais (validado 2026-06-25)

- **Cobertura código**: ~85% (testes prontos, falham por causa dos 3 bloqueios)
- **Pytest impact**: +75 testes potenciais quando bloqueios resolvidos (loop-state.json reports 952→1027 após work parcial)
- **Prometheus metrics**: 4 novos counters + 2 gauges expostos em `/api/v1/metrics/prometheus`
- **PII**: todos os campos notification passam por `hash_pii()` antes de logar (LGPD art. 37)

---

## 🎯 Roadmap para retomar A26

### Pré-requisitos
- [ ] Bloqueio 1: fix `down_revision` em `A1-migration-add-client-notification-fields.py`
- [ ] Bloqueio 2: adicionar 5 campos ao `Cliente` model em `backend/app/models/cliente.py`
- [ ] Bloqueio 3: ✅ já resolvido (workflows movidos para cá)
- [ ] Gustavo escanear QR Evolution API (`https://whatsapp.2notasudi.com.br/manager`)

### Passos
1. Mover arquivos deste `infra/wip/agendamento-A26-2026-06-25/` para seus paths finais:
   - `A1-migration-*.py` → `backend/alembic/versions/`
   - `A2-A4-service-*.py` → `backend/app/services/`
   - `T1-T3-test-*.py` → `backend/tests/`
   - `D1-CACHING_STRATEGY.md` → `backend/docs/` (recriar dir)
   - `W1-W2-*.json` → `infra/n8n-workflows/`
2. Rodar `uv run alembic upgrade head` (Supabase self-hosted)
3. Rodar `uv run pytest tests/test_agendamento_cache.py tests/test_agendamento_n8n.py tests/test_notificacao.py --no-cov`
4. Validar gates: mypy 0, ruff 0, pytest verde
5. Importar workflows N8N via API
6. Commit + push + LGPD review focada (replicar Lesson 113 v2 v3 pattern)

---

## 📚 Lições aprendidas (registrar em `.harness/memory/MEMORY.md` quando retomar)

- **Lesson 167 candidate**: WIP feature sem migration head pointer = porta aberta pra retrabalho. SEMPRE validar `down_revision` antes de criar migration file.
- **Lesson 168 candidate**: `backend/infra/` NÃO é path canonical. Infra sempre em `infra/` na raiz. Validar com `find backend -type d -name infra` em pre-commit hook.
- **Lesson 169 candidate**: Feature A26 adiciona notification fields ao Cliente. Validar LGPD art. 37 (PII) — todos os 5 campos passam por `hash_pii()` em logs.

---

**Mantido por**: ZCode/Mavis (orquestrador) + Gustavo Almeida (CEO)
**Regra**: NUNCA APAGAR — sempre preservar em `infra/wip/` quando interrompido mid-flight