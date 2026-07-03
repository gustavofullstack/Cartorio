"""Alembic env.py - configuracao para rodar migrations no Cartorio.

Lendo a URL do banco do app.config.settings (mesma fonte do SQLAlchemy session).

A20 — Distributed Lock (Redlock)
=================================
Durante deploy rolling update, multiplas replicas podem tentar rodar
`alembic upgrade head` simultaneamente. Para evitar race conditions
(2 migrations concorrentes no mesmo DB), este env.py adquire um lock
distribuido via Redis antes de executar migrations em modo online.

LGPD: o nome do lock `alembic:migration` NAO expoe dados pessoais —
e apenas um identificador tecnico de operacao.

Fluxo:
1. Carrega settings (DATABASE_URL + REDIS_URL)
2. Tenta adquirir lock `alembic:migration` com TTL 300s
3. Se sucesso: roda migrations e libera lock automaticamente
4. Se ocupado: exit code 75 (EX_TEMPFAIL sysv init) — Docker restart policy
   vai retentar com backoff

EMERGENCIA: se Redis esta down e voce PRECISA rodar migration na mao:
    cd backend
    uv run alembic upgrade head --sql > migration.sql
    # aplicar manualmente:
    PGPASSWORD=$DB_PASS psql -h db -U supabase_admin -d cartorio -f migration.sql
"""

from logging.config import fileConfig
import sys

from sqlalchemy import engine_from_config, pool

from alembic import context

# Importa settings + Base do app
from app.config import settings  # noqa: E402
from app.models.base import Base  # noqa: E402
import app.models  # noqa: E402,F401  - ensure all models are registered with Base.metadata

# A20: Importa helper de Redlock
from app.services.redlock import (  # noqa: E402
    DEFAULT_LOCK_TTL_SECONDS,
    EXIT_LOCK_BUSY,
    LockBusyError,
    redlock,
)

# Nome canonico do lock de migrations. NUNCA colocar PII aqui.
ALEMBIC_LOCK_NAME = "alembic:migration"

# Alembic Config object
config = context.config

# Sobrescreve sqlalchemy.url com a do settings
config.set_main_option("sqlalchemy.url", settings.database_url)

# Configura logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Metadata alvo para autogenerate
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode (emite SQL sem conectar).

    Modo offline NAO precisa de lock (apenas gera SQL).
    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        compare_server_default=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode (conecta no DB).

    A20: Adquire redlock antes de conectar. Se outra replica ja esta
    migrando, exit 75 para que Docker/swarm orquestrador possa retentar.
    """
    # A20: adquirir lock distribuido. Blocking=False (fail-fast):
    # migrations devem rodar 1x por vez. Se outra replica ja migrou,
    # ela libera o lock e nos pegamos na proxima tentativa (restart policy).
    try:
        with redlock(
            ALEMBIC_LOCK_NAME,
            ttl_seconds=DEFAULT_LOCK_TTL_SECONDS,
            blocking=False,
            timeout=0,
        ):
            _run_migrations_online_locked()
    except LockBusyError as e:
        sys.stderr.write(
            f"\n[ALEMBIC] Lock distribuido ocupado: {e}\n"
            f"[ALEMBIC] Outra replica provavelmente ja esta migrando.\n"
            f"[ALEMBIC] Saindo com codigo {EXIT_LOCK_BUSY} (EX_TEMPFAIL) "
            f"para que o orquestrador possa retentar.\n"
        )
        sys.exit(EXIT_LOCK_BUSY)


def _run_migrations_online_locked() -> None:
    """Implementacao real de run_migrations_online (apos lock adquirido)."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            compare_server_default=True,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
