# Lesson 267 — G8.23.T4 N8N Token Rotation Router (2026-07-18)

## Contexto

Tarefa G8.23.T4 — criar roteador de tokens N8N para permitir rotação
do `N8N_API_KEY` sem downtime e sem quebrar integrações em curso.
LGPD Art. 46 (segurança — rotação periódica reduz blast radius de
vazamento), Art. 50 (governança — grace period documentado).

Wave 53, Squad 23 (N8N Auth). Master ahead 49 commits (Wave 52
acaba de fechar em 78/100). Task pega no fluxo G8 cartorio-n8n.

## Decisões arquiteturais

1. **Replica exata do padrão `HmacKeyRouter` (G8.19.T2) para tokens.**
   `N8NTokenRouter` mantem `dict[kid] → {token, status, created_at,
   rotated_at, expires_at}` + `_active_kid`. `threading.RLock`
   interno protege mutações. Singleton via `_ROUTER` +
   `get_router()`. Parity pedagógica com `audit_keys.py`.

2. **Estados: `active | rotating | revoked`.** Diferença do HMAC
   router (que tem `active | rotating | deprecated`): para tokens
   nao ha semantica de "verify de entry historico" — quando o grace
   expira, o token eh simplesmente morto. Active -> Rotating -> Revoked.

3. **Bootstrap lazy via `get_n8n_headers()` lendo
   `settings.n8n_api_key`.** Padrao identico ao `audit_keys`.
   `bootstrap_legacy()` idempotente; chamado no startup ou na
   primeira request HTTP.

4. **Header contract: `X-N8N-API-KEY` (token) + `X-N8N-KEY-ID` (kid).**
   `X-N8N-KEY-ID` eh header novo, ignorado por N8N (nao quebra nada).
   Serve para audit log correlation + debug.

5. **Backward-compat: NAO migrei callers.** `app/api/v1/n8n_metrics.py`
   continua usando `settings.n8n_api_key` direto. Migracao gradual
   fica para G8.24+, um PR por arquivo. Blast radius desta task: zero
   em comportamento existente.

## Padrões / Snippets reaproveitáveis

```python
# Padrao genérico "registry thread-safe com rotacao" (HMAC key, N8N
# token, qualquer credencial de longa duracao)
class TokenishRouter:
    def __init__(self):
        self._lock = threading.RLock()
        self._items: dict[str, dict] = {}
        self._active_kid: str = ""
        self._bootstrapped: bool = False

    def bootstrap_legacy(self, value, kid="legacy"):
        with self._lock:
            existing = self._items.get(kid)
            if existing is not None:
                if existing["value"] == value:
                    self._bootstrapped = True
                    return  # idempotente
                raise ValueError(f"kid={kid} already registered with different value")
            if self._active_kid:
                raise RuntimeError(f"router already bootstrapped")
            # ... register ...

    def rotate(self, new_kid, new_value):
        with self._lock:
            old_kid = self._active_kid
            if not old_kid:
                raise RuntimeError("cannot rotate without active")
            # mark old as rotating, register new as active
```

## Pegadinhas / Notas de cuidado

- **Bug encontrado em testes: check de invariante DEPOIS de mutacao.**
  `register()` original fazia `self._tokens[kid] = {...}` ANTES de
  verificar `if self._active_kid != kid`. Resultado: ainda que o
  `RuntimeError` fosse raised no thread perdedor, o kid ja estava
  em `self._tokens` (estado inconsistente entre threads). Fix: mover
  TODAS as checks de invariante ANTES da mutacao. Coberto por
  `test_thread_safety_register_no_double_active`.

- **Bug encontrado em testes: `bootstrap_legacy` clobberava
  `_active_kid`.** Se o router ja tinha um active (via `register()`
  direto, ex.: testes), chamar `bootstrap_legacy()` no path lazy
  do `get_n8n_headers()` sobrescrevia o active sem warning. Fix:
  bootstrap checa `if self._active_kid` antes de prosseguir, raise
  com mensagem clara. Adicionalmente, `_ensure_bootstrapped()` em
  `integrations/n8n.py` agora noop se ja tem active_kid (defense in
  depth).

- **`Threading.RLock` vs `Lock`.** Para singleton com multiplas
  operacoes, `RLock` eh overkill (mesmo thread raramente chama
  multiplas operacoes recursivamente). Mas eh o pattern do
  `audit_keys.py`, entao replica por parity. Se houver deadlock
  futuro, trocar eh trivial — interface nao muda.

- **`_ensure_bootstrapped()` lazy eh sutil.** Chamar em `get_n8n_headers()`
  significa que o bootstrap eh demandado na primeira request. Em
  testes que registram diretamente, o bootstrap nunca dispara —
  importante para isolar `r.register(...)` sem mock de settings.
  Cubra com testes explicitos (`test_integration_with_n8n_headers`).

- **`patch("app.config.settings")` em testes.** Funciona porque
  `integrations/n8n.py` faz `from app.config import settings`
  lazy dentro de funcao. Se a import for movida pra top-level,
  patch funciona da mesma forma, mas quebra testes que fazem
  `importlib.reload`. Manter lazy por enquanto.

## Decisoes de escopo (fora desta task, fila para G8.24+)

- **Endpoint admin `/admin/n8n/rotate`** — chamar `router.rotate()`
  via HTTP com DPO auth. Por enquanto eh programatico.
- **Endpoint `/admin/n8n/revoke-old`** — cron + manual trigger
  para `revoke_old()`. Ja possivel via script; URI HTTP formal fica
  pra G8.24.
- **Migracao gradual de callers em `n8n_metrics.py` e outros.** Cada
  `httpx.get(url, headers={"X-N8N-API-KEY": settings.n8n_api_key})`
  vira `headers=get_n8n_headers()`. PR isolado por arquivo.
- **Metric Prometheus `n8n_token_rotation_total{kid, event}`.** Para
  alerting em rotacao excessiva (indicativo de incidente).
- **Persistencia do registry em Redis.** Hoje o singleton eh
  per-process. Em multi-worker (4 uvicorn workers), cada worker tem
  seu proprio registry. Rotacao via endpoint admin so afeta 1 worker.
  Solucao: persistir em Redis com pub/sub para invalidacao. Complexo,
  G8.25+.

## Compatibilidade LGPD

- **Art. 46** (seguranca): ok — rotacao documentada, grace explicit,
  revogacao disponivel. Tokens nunca logados (snapshot usa
  `sha256[:8]`).
- **Art. 50** (governanca): ok — playbook de incident response
  documentado em `docs/N8N_TOKEN_ROTATION_G8.md#migration-playbook-zero-downtime`.
- **Art. 37** (rastreabilidade): parcialmente — `X-N8N-KEY-ID` ja
  vai em todo request. Falta metric Prometheus para detectar
  rotacoes anormais. Backlog G8.25.

## Cross-references

- `docs/HMAC_KEY_ROTATION_G8.md` — design gem (rotacao de chaves
  HMAC do audit log, G8.19.T2).
- `lesson-258-g8-19-t2-hmac-rotation` — memoria do squad crypto.
  Lida em paralelo ao implementar esta task; ambos compartilham o
  mesmo padrao de registry.
- `app/services/openclaw_cred_rotation.py` — terceiro exemplo de
  rotacao de credencial (OpenClaw). Todos os tres seguem o mesmo
  pattern de singleton + kid tracking + grace. Documentacao
  canonica em `docs/N8N_TOKEN_ROTATION_G8.md`.

## Honesty Gate

- 33 testes em `tests/test_n8n_token_router_g8.py`: **PASS**.
- `pytest --no-cov -q -k n8n`: 259 passed (vs baseline 226, +33
  desta task).
- `ruff check app/services/n8n_token_router.py
  app/integrations/n8n.py tests/test_n8n_token_router_g8.py`: 0
  errors.
- Backward-compat: NAO foi modificado nenhum caller existente.
  Blast radius em prod: zero. Migracao gradual agendada para G8.24+.

---

Modified by Gustavo Almeida + cartorio-n8n — G8.23.T4 (Wave 53).
