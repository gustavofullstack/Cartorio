# N8N Token Rotation — Cartório (G8.23.T4)

**Status:** implementado 2026-07-18 | **Cartório:** 2º Serviço Notarial de Uberlândia
**Wave:** 53 (Squad 23 — N8N Auth) | **Tasks:** G8.23.T4 | **Review:** cartorio-lgpd pendente
**LGPD Art.** 46 (segurança) + Art. 50 (governança)

> Parity com [`HMAC_KEY_ROTATION_G8.md`](./HMAC_KEY_ROTATION_G8.md) —
> mesmo padrão `kid`-tracking + grace period, aplicado a tokens de
> autenticação N8N.

---

## TL;DR

Permite **rotacionar o `N8N_API_KEY` sem downtime e sem quebrar
integrações em curso**. Cada chamada HTTP ao N8N carrega `X-N8N-KEY-ID`
(kid) + `X-N8N-API-KEY` (token ativo). Operação **zero-downtime**:
novo kid entra como ACTIVE, antigo vira ROTATING e continua aceito até
o grace period expirar; depois disso, `revoke_old()` promove para
REVOKED.

Implementação: `app/services/n8n_token_router.py:1` (singleton
thread-safe) + `app/integrations/n8n.py:1` (helper HTTP).

---

## Motivação

- **LGPD Art. 46** exige sigilo e segurança — token de serviço é
  credencial de longa duração (risco de blast radius em caso de
  vazamento). Rotação periódica reduz exposição.
- **LGPD Art. 50** exige governança e resposta a incidentes — chave
  comprometida precisa ser revogada rapidamente sem perder
  rastreabilidade de quem usou qual kid quando.
- **Operacional**: N8N hoje sobe e expõe apenas um token (`X-N8N-API-KEY`,
  configurado em `settings.n8n_api_key`). Qualquer rotacao exige redeploy
  + janela de manutencao. Com o router, troca é runtime via
  `router.rotate(new_kid, new_token)`.

Antes desta task, `settings.n8n_api_key` era **string única lida do
env**; única forma de "rotacionar" era redeployar, gerando downtime de
~30s no `/api/v1/n8n/metrics/prometheus` e em qualquer chamada que
forwardasse para N8N.

---

## Arquitetura

### Registry singleton thread-safe

`app/services/n8n_token_router.py:1` define `N8NTokenRouter`,
singleton mantido em memória (init de processo). Toda mutação passa por
`threading.RLock` interno — seguro em ambiente multi-thread (uvicorn
workers, scheduler, dead-man's-switch, handlers de webhook).

```
              +-------------------------------+
              |     N8NTokenRouter            |
              |     (_lock: RLock)            |
              +-------------------------------+
                | kid=legacy (active)         | ← get_token() retorna
                | kid=2026-q3 (rotating)      | ← grace 7 dias
                | kid=2026-q2 (rotating)      | ← grace 7 dias
                | kid=2026-q1 (revoked)       | ← get_token() recusa
              +-------------------------------+
                            |
              +-------------+--------------+
              |                            |
        get_n8n_headers()         rotate(new_kid, new_token)
        (X-N8N-API-KEY + KID)    (atomic: old=ROTATING,
                                  new=ACTIVE)
```

### Estados de um kid

| Estado    | Quem define                     | Pode ser usado?            |
| --------- | ------------------------------- | -------------------------- |
| `active`  | `bootstrap_legacy` ou `rotate`  | Sim — `get_token()`        |
| `rotating`| `rotate()` no kid anterior      | Não (`get_token()` recusa) mas ainda nao foi revogado de fato |
| `revoked` | `revoke_old()` apos grace       | Não (`get_token()` recusa) |

> Nota: durante ROTATING, o kid antigo NAO eh mais usado pelo cartorio.
> "Rotating" eh um estado intermedio (grace) que existe apenas para
> documentacao em audit log + `snapshot()`. A decisao real eh:
> active -> revoked. Isso difere do HMAC key rotation (onde rotating
> ainda eh usado para verify de entries historicos).

### Header contract

Toda requisicao HTTP ao N8N agora envia dois headers:

| Header            | Valor                          | Proposito                       |
| ----------------- | ------------------------------ | ------------------------------- |
| `X-N8N-API-KEY`   | token ativo do registry        | autenticacao N8N                |
| `X-N8N-KEY-ID`    | kid do token (ex.: `legacy`)   | audit log + debug (correlation) |

`X-N8N-KEY-ID` nao quebra nada no N8N (header desconhecido eh
ignorado). Servers legados (pre-router) que nao enviam `X-N8N-KEY-ID`
continuam funcionando — o backend passa a usar o router quando
`get_n8n_headers()` eh chamado.

---

## API publica

### `app.services.n8n_token_router`

```python
from app.services.n8n_token_router import (
    get_router,
    N8NTokenRouter,
    TokenStatus,
    DEFAULT_LEGACY_KID,
    DEFAULT_TTL_DAYS,
    DEFAULT_GRACE_PERIOD_DAYS,
)

router = get_router()

# Bootstrap inicial (settings.n8n_api_key na primeira chamada)
router.bootstrap_legacy(token="...", kid="legacy")  # idempotente

# Registrar kid adicional (state != ACTIVE)
router.register("k2", "...", status=TokenStatus.ROTATING)

# Rotacao (atomic, kid anterior vira ROTATING)
old_kid = router.rotate("k3", "new-token", ttl_days=30)

# Obter token ativo (uso normal em HTTP clients)
kid, token = router.get_token()  # ("k3", "new-token")

# Limpar tokens em grace expirado
router.revoke_old(grace_period_days=7)  # ROTATING -> REVOKED

# Snapshot sem expor tokens (para audit)
router.snapshot()  # tokens mascarados com sha256[:8]
```

### `app.integrations.n8n`

```python
from app.integrations.n8n import (
    get_n8n_headers,
    get_n8n_base_url,
    bootstrap_from_settings,
)

# Forca bootstrap no startup (opcional, lazy ja cobre)
bootstrap_from_settings()

# Headers para chamada HTTP
headers = get_n8n_headers()
# {"X-N8N-API-KEY": "abc...", "X-N8N-KEY-ID": "legacy"}

# Base URL do N8N configurada em settings
base = get_n8n_base_url()  # "http://cartorio_n8n:5678"
```

---

## Migration playbook (zero-downtime)

### Quando rodar

- Periodicidade recomendada: **a cada 90 dias** (alinhado com
  [`cartorio_api_key` rotation](./DEPLOYMENT.md#api-key-rotation)).
- Imediatamente em caso de incidente (token vazado em log, Git, Slack).

### Passo a passo

1. **Gerar novo token no N8N** (Settings > API > Create API Key).
2. **Carregar no env via Supabase Vault** (zero redeploy):
   ```sql
   INSERT INTO vault.n8n_tokens (kid, token_hash, token_value, expires_at)
   VALUES ('k_2026_q3', encode(sha256('new-token'), 'hex'), 'new-token', now() + interval '30 days');
   ```
   Nao exponha `token_value` em logs. O codigo do backend le via
   `get_secret()` (ja implementado em waves anteriores).
3. **Chamar `rotate()` na manutencao**:
   ```python
   from app.services.n8n_token_router import get_router
   get_router().rotate(
       new_kid="k_2026_q3",
       new_token="new-token",
       ttl_days=30,
   )
   ```
   Old kid vira ROTATING instantaneamente. Novas chamadas usam o novo.
4. **Aguardar grace period (7 dias)** para rolling-deploy de qualquer
   chamada em voo.
5. **Rodar `revoke_old()`** (cron opcional ou manual):
   ```python
   get_router().revoke_old(grace_period_days=7)
   ```
   Promove ROTATING -> REVOKED. Snapshot registra a transicao.
6. **Revogar token antigo no N8N** (apos grace) — agora seguro.

### Codigo de incident response

```python
from app.services.n8n_token_router import get_router, TokenStatus

# Compromisso detectado — revogar imediatamente
router = get_router()
active = router._active_kid  # nao usar para prod, so demonstracao
router._tokens[active]["status"] = TokenStatus.REVOKED  # noqa: SLF001
# A partir daqui get_token() falha ate novo register/rotate
```

Em prod, use um endpoint admin dedicado (ver backlog G8.24).

---

## LGPD-by-design

- **Art. 37** (rastreabilidade): snapshot eh serializavel e hash-only;
  audit log pode referenciar `kid` (ex.: `actor="n8n:legacy"`) para
  rastrear quem usou qual token.
- **Art. 46** (seguranca): rotacao periodica + grace documentado.
  Token nunca eh logado; snapshot usa `sha256[:8]` (LGPD-safe).
- **Art. 50** (governanca): playbook de incident response acima.
  Grace period documentado (7 dias) — alinhado com cartorio-api-key.

---

## Test coverage

33 testes em `tests/test_n8n_token_router_g8.py:1`. Resumo dos
cobrindo regressao:

| Categoria               | Teste                                  |
| ----------------------- | -------------------------------------- |
| Registro                | `test_register_*` (6 testes)            |
| Bootstrap               | `test_bootstrap_legacy_*` (5 testes)   |
| Rotacao                 | `test_rotate_*` (4 testes)             |
| Get token               | `test_get_token_*` (3 testes)          |
| Grace period            | `test_revoke_old_*` (4 testes)         |
| Integracao HTTP         | `test_integration_*` (3 testes)        |
| Snapshot + misc         | `test_snapshot_*` (6 testes)           |
| Thread-safety (smoke)   | `test_thread_safety_*` (2 testes)      |

Coverage gate: ainda 90% (regredir eh fail-fast via `make qa`).

---

## Compatibilidade + risco

### Backward-compat

- Codigo pre-router (ex.: `app/api/v1/n8n_metrics.py:50`) continua
  usando `settings.n8n_api_key` direto. **Nao foi modificado** nesta
  wave para minimizar blast radius.
- Migracao gradual recomendada (G8.24+): substituir
  `{"X-N8N-API-KEY": settings.n8n_api_key}` por `get_n8n_headers()`
  nos callers. PR isolado por arquivo.

### Failure modes

- `settings.n8n_api_key` vazio e nenhum kid registrado ->
  `RuntimeError` na primeira chamada HTTP (logado, fail-fast).
- Tentativa de registrar 2 ACTIVE -> `RuntimeError` (use `rotate()`).
- Tentativa de `rotate()` sem ACTIVE -> `RuntimeError`.
- Token em REVOKED + `get_token()` -> `RuntimeError` (consistente).

### Failure modes evitados

- **Nao** permite dois kids `active` simultaneos (verificado por
  `test_thread_safety_register_no_double_active`).
- **Nao** permite clobber do active kid em bootstrap (verificado por
  reordenacao das checks em `bootstrap_legacy`).
- **Nao** expoe tokens em `snapshot()` (apenas sha256[:8]).

---

## Referencias

- [`docs/HMAC_KEY_ROTATION_G8.md`](./HMAC_KEY_ROTATION_G8.md) — padrao
  gem (HMAC key rotation, G8.19.T2). Mesmo design.
- `app/services/audit_keys.py:1` — implementacao de referencia para
  pattern paralelo.
- `backend/app/services/openclaw_cred_rotation.py:1` — outro exemplo
  de rotacao de credencial (OpenClaw).
- `lesson-258-g8-19-t2-hmac-rotation` — memoria do squad crypto.
- `lesson-267-g8-23-t4-n8n-token-rotation` (Wave 53) — esta task.

---

Modified by Gustavo Almeida + cartorio-n8n — G8.23.T4 (Wave 53).
