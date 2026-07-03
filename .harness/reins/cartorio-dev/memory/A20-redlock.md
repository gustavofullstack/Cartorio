# A20 — Distributed Lock (Redlock) for Migrations & Seed

**Date**: 2026-07-02
**Squad**: A (API/DB Hardening)
**Status**: ✅ Commitado localmente (5 commits). Aguarda Gustavo GO para push em prod.

## Resumo

Implementado lock distribuido Redis-based (Redlock pattern) para coordenar
migrations Alembic e seed scripts entre multiplas replicas da API durante
deploy rolling update. Sem lock, 2 replicas podem aplicar migrations
simultaneas → race condition → corrupcao de schema.

## Implementacao

### Core: `app/services/redlock.py` (205L)

API publica:
- `acquire_lock(name, ttl_seconds) -> str | None` — Redis SET NX EX
- `release_lock(name, token) -> bool` — Lua script atomico (deleta so se token confere)
- `is_locked(name) -> bool` — EXISTS check (diferencia "outra replica" vs "Redis offline")
- `redlock(name, ttl_seconds, blocking, timeout, poll_interval)` — context manager
- `LockBusyError` — exception customizada

Constantes exportaveis:
- `DEFAULT_LOCK_TTL_SECONDS = int(os.getenv("REDIS_LOCK_TTL_SECONDS", "300"))`
- `DEFAULT_LOCK_PREFIX = os.getenv("REDIS_LOCK_PREFIX", "redlock:")`
- `EXIT_LOCK_BUSY = 75` (EX_TEMPFAIL do BSD sysexits.h)

### Integracoes

#### Alembic (`backend/alembic/env.py`)

```python
ALEMBIC_LOCK_NAME = "alembic:migration"

def run_migrations_online():
    try:
        with redlock(ALEMBIC_LOCK_NAME, blocking=False, timeout=0):
            _run_migrations_online_locked()
    except LockBusyError as e:
        sys.stderr.write(f"[ALEMBIC] Lock ocupado: {e}\n")
        sys.exit(EXIT_LOCK_BUSY)
```

**Modo offline NAO usa lock** (emite SQL sem conectar).

#### Seed (`backend/scripts/seed_vault_secrets.py`)

```python
SEED_LOCK_NAME = "seed:vault_secrets"

def main():
    if not args.skip_lock:
        try:
            with redlock(SEED_LOCK_NAME, blocking=False, timeout=0):
                return _run_seed(args)
        except LockBusyError:
            return EXIT_LOCK_BUSY
```

Flag `--skip-lock` disponivel para debug local.

### Tests (27 tests em `tests/test_redlock_a20_v2.py`)

| Cenario | Testes | Descricao |
|---------|--------|-----------|
| C1 acquire/release | 3 | acquire + release + context manager |
| C2 competing | 3 | timeout=0 fail-fast, timeout>0 wait, timeout expirado |
| C3 TTL | 3 | TTL aplicado, auto-expira (simulado), release pos-expiracao |
| C4 exception | 6 | propaga exception, lock liberado no finally, is_locked broken, offline msg, release fail warning |
| C5 Alembic | 6 | Source check: imports, lock name canonico, redlock() args, sys.exit(75), LGPD-safe, offline sem lock |
| C6 Seed | 3 | success/lock busy/skip-lock |

Usa `fakeredis + lupa` (lua support) para testes realistas.

**Coverage**: 92% em `app/services/redlock.py` (linhas 44-50 = ImportError branch).

## LGPD compliance

Lock name canonico `alembic:migration` / `seed:vault_secrets`:
- NAO expoe dados pessoais (cpf, rg, email, telefone, nome_cliente)
- Apenas identificador tecnico de operacao
- Validado em `test_alembic_lock_name_nao_expoe_pii`

## Decisoes

1. **SET NX EX** (atomic lock) — single Redis instance suficiente para cartorio
   (1 master + replicas). Production-grade Redlock multi-instance NAO necessario.
2. **Lua script atomico** no release — evita race condition onde lock expira entre
   check e delete (token comparison garante que so deleta SE ainda nosso).
3. **blocking=False (fail-fast)** para migrations/seed — exit 75 deixa
   Docker/swarm retry policy fazer backoff. NAO bloqueia worker thread.
4. **LockBusyError com mensagem diagnostica** — diferencia "ocupado" vs "offline"
   via is_locked() check no exception path.
5. **`--skip-lock` flag no seed** — debug local sem coordenar com Redis.

## Recovery em emergencia

Se Redis cair e migrations estao bloqueadas:
```bash
cd backend
uv run alembic upgrade head --sql > /tmp/migration.sql
PGPASSWORD=$DB_PASS psql -h db -U supabase_admin -d cartorio -f /tmp/migration.sql
```

Para forcar release de lock orfao antes do TTL (5min):
```bash
docker exec cartorio_redis redis-cli DEL redlock:alembic:migration
docker exec cartorio_redis redis-cli DEL redlock:seed:vault_secrets
```

## Commits (sequenciais, master)

1. `chore(a20): checkpoint before A20 redlock integration — lesson 022 working-tree reset observed`
2. `feat(backend): A20 redlock context manager + LockBusyError + configurable prefix/TTL`
3. `feat(backend): A20 Alembic env.py acquires redlock before run_migrations_online`
4. `feat(backend): A20 seed_vault_secrets.py acquires redlock before populating vault`
5. `test(backend): A20 v2 — 27 tests covering 6 cenarios (context manager + integration)`
6. `docs(env): A20 — REDIS_LOCK_TTL_SECONDS + REDIS_LOCK_PREFIX + recovery instructions`
7. `chore(deps): A20 — add lupa to dev deps for fakeredis lua support`

## Pendente (NAO APLICAR SEM Gustavo GO)

- [ ] Atualizar `REDIS_LOCK_TTL_SECONDS` + `REDIS_LOCK_PREFIX` no
      `/etc/easypanel/projects/cartorio/api/code/.env` da VPS
      (Lesson 022/050/110: drift entre local e prod = broken)
- [ ] Restart `cartorio_api` para carregar env vars
- [ ] Validar em prod: rodar `alembic upgrade head` em 2 replicas simultaneas
      e confirmar que 1 delas sai com exit 75

## Licoes aprendidas

1. **Lesson 022 working-tree reset** — sprint ativo + agent paralelo = commits racing.
   Usei `--allow-empty` checkpoint + commits atomicos por arquivo (nao batching).
2. **fakeredis lua** — `eval` requer lupa instalado. Adicionado como dev dep.
3. **Alembic env.py nao pode ser loaded como module** em tests (depende de
   `alembic.context.config` que so funciona em alembic CLI). Padrao canon:
   validar via source code regex + testes de comportamento do `redlock()`.
4. **TTL 300s** para migrations = margem suficiente para migrations longas sem
   segurar lock indefinidamente. Alembic 0019 trigger (A18) roda em ~2s; mesmo
   migrations 10x mais lentas cabem em 300s.