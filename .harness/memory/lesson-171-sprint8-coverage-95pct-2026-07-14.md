# Lesson 171 — Sprint 8 coverage push: 94.09% → 95.04% (gate --cov-fail-under=95 passed) — 2026-07-14

## TL;DR

Sprint 8 focado no **bottom 5 modulos backend** (targets identificados por
`coverage.json` `missing_lines` ordenado DESC). 48 testes focados
(happy + 2-3 edges cada) em **um unico arquivo**
`tests/test_sprint8_coverage.py`. Resultado: **+0.95pp** (94.09% →
95.04%), gate passa. 0 erros ruff no meu arquivo / 0 erros mypy global.

Bottom 5 modules identificados (Sprint 8 entry):

| Modulo | Antes | Depois | Delta |
|---|---|---|---|
| `app/services/notificacao.py` | 90.7% | **100%** | +9.3pp |
| `app/services/protocolo.py` | 89.6% | **100%** | +10.4pp |
| `app/services/backup_v2.py` | 92.1% | **100%** | +7.9pp |
| `app/api/v1/ws/atendimentos.py` | 87.0% | 96.3% | +9.3pp |
| `app/api/v1/integrations.py` | 95.4% | 99.5% | +4.1pp |
| `app/api/deps.py` | 91.2% | 97.5% | +6.3pp |
| `app/api/v1/lgpd_direitos_v2.py` | 90.1% | 95.1% | +5.0pp |
| `app/main.py` | 83.2% | 91.9% | +8.7pp |

## Estrategia que funcionou

### 1. Identificar bottom N por `missing_lines` (NAO por `%`)

Coverage.py JSON `files[X].missing_lines` eh **lista de numeros de
linhas nao executadas**. Ordenar DESC pelo `len(missing_lines)`
(filtrado `stmt_count >= 20` para evitar modulos minimos) e nao
por `percent_covered` pois:

- 229 linhas faltando em `app/api/v1/router.py` (80% — 1163 stmts)
  seria o "vencedor" mas eh router dispatcher com 80 endpoints
  distribuidos — testes sao low ROI/low signal
- Concentrar nos 5-8 modulos com 5-25 missing lines + `pct < 95%`
  da ROI alto: cada teste cobre 1-3 edges criticos

### 2. Helpers privados sao ROI excelente

`_truncate_ip_for_response`, `_parse_payload`, `_scrub_payload_pii`
em `app/api/v1/lgpd_direitos_v2.py`: 9 testes cobrem **11 linhas**
(15 min total). vs routes que exigem JWT + DB + auth fixtures
(30 min para 3-5 linhas).

**Padrao: helpers puros primeiro, routes depois.**

### 3. Exception handlers via mocks side_effect

`try/except RuntimeError` branches em
`notificacao.enviar_whatsapp_reaction/poll/media`:
um unico pattern `_AsyncCtxExplode` (fake httpx.AsyncClient que
explode no `__aenter__`) cobre **6 linhas em 3 funcoes**.
3 classes parametrizadas x 2 edges (with/without api_key) = 6 testes.

### 4. Lifespan asynchrono — _dead_mans_switch_loop

`app/main._dead_mans_switch_loop()` tinha 9 linhas mortas
(lifecycle do Redlock). Patch em **3 pontos**:

- `app.services.redlock.acquire_lock` (lazy-imported dentro da func)
- `app.services.redlock.release_lock`
- `app.db.session_scope` (referenciado por `from app.db import session_scope`
  na linha 31) — patch no modulo original E no `app.main.session_scope`

Alem de mockar `asyncio.sleep` da loop para nao esperar 30s
iniciais. Template reusavel para outras loops de background.

### 5. HMAC signature no n8n_error fail-soft test

`POST /api/v1/integrations/n8n/error` exige HMAC valido. Pattern
existente em `test_n8n_error_endpoint.py`:

```python
secret = "n8n-webhook-test-secret-2026-07-13"
body = json.dumps(payload).encode("utf-8")
sig = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
with patch.dict(os.environ, {"N8N_WEBHOOK_SECRET": secret}):
    resp = client.post(URL, content=body, headers={"X-N8N-Signature": sig})
```

**NUNCA usar `json=payload` no TestClient** — FastAPI reserializa e
o body muda. Usar `content=body` (raw bytes) para HMAC.

### 6. Settings monkeypatch pre-init para lifespan

`settings.audit_dead_mans_switch_minutes`/`retencao_enabled`
sao snapshots no import (pydantic-settings cache). Pattern:

```python
from app.config import settings
monkeypatch.setattr(settings, "audit_dead_mans_switch_minutes", 0)
```

NAO funciona com `os.environ.setenv(...)` direto — precisa do
`monkeypatch.setattr(settings, ...)` para alterar o singleton.

## Constraints honrados

- **NO real LLM calls**: conftest `LLM_DEFAULT_PROVIDER="opencode_go"`
  permanece intocado
- **fakeredis**: autouse fixture `_mock_redis_from_url` em conftest
  mocka `redis.from_url` globalmente
- **pii.py NAO modificado**: todos os tests adicionados chamam
  paths existentes (pii hash, scrub, gateway integrations) sem
  propor alteracao semantica — cartorio-lgpd sign-off NAO necessario

## Workflow AGENTS.md seguido

analisar → testar → corrigir → melhorar → otimizar → documentar
→ salvar na memoria (este lesson + PROGRESS.md entry)

## Como aplicar (proximo round)

Candidatos para Sprint 9:

| Modulo | % atual | Miss | ROI |
|---|---|---|---|
| `app/services/rate_limit_by_key.py` | 92.2% | 10 | MEDIO — Redis sliding window edge cases |
| `app/api/v1/bot_lgpd.py` | 92.5% | 9 | MEDIO — testar marcacao deleted |
| `app/api/v1/router.py` | 80.3% | 229 | BAIXO — 80 endpoints distribuídos |
| `app/api/v1/jules*` integration | ~85% | varies | BAIXO |

Ou: introduzir `--cov-fail-under=96` como novo gate (após 5 rounds
de coverage gain → meta incremental).

## Refs

- `tests/test_sprint8_coverage.py` — 48 testes em 9 classes
- Coverage JSON diff: `/tmp/sprint8-cov-before.json` →
  `/tmp/sprint8-cov-final2.json`
- Compatível com [[2026-07-13-yolo-round-7-b07095f]] (R7 R7-1: bot_lgpd)
  e [[2026-07-13-yolo-round-6-99c06ab]] (R6 coverage gap sprint)
- [[2026-07-13-multi-agent-orchestration-loop]]

Modified by Gustavo Almeida — 2026-07-14 02:50 BRT
