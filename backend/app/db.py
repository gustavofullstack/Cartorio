"""SQLAlchemy engine + session factory."""

from collections.abc import Iterator
from contextlib import contextmanager

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.config import settings

_is_sqlite = settings.database_url.startswith("sqlite")

# A22: Connection pool tuning expandido
# - pool_size=20: base pool (20 conexoes persistentes)
# - max_overflow=10: ate 10 extras sob pico (total 30)
# - pool_timeout=30: 30s para adquirir conexao (queue timeout)
# - pool_pre_ping=True: testa conexao antes de usar (detecta stale)
# - pool_recycle=3600: recicla a cada 1h (evita conexao morta em pgBouncer/LB)
# - pool_use_lifo=True: LIFO = conexoes recentes优先 (reduz abertura/fechamento)
_engine_kwargs: dict = {
    "pool_pre_ping": True,
    "pool_recycle": 3600,
}
if not _is_sqlite:
    _engine_kwargs.update(
        pool_size=20,
        max_overflow=10,
        pool_timeout=30,
        pool_use_lifo=True,  # LIFO = conexoes recentes优先 (so Postgres)
    )
_engine_kwargs["echo"] = settings.app_env == "development"

engine = create_engine(settings.database_url, **_engine_kwargs)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine, expire_on_commit=False)


def get_pool_stats() -> dict:
    """Retorna estatisticas do pool de conexoes (A22 - observabilidade).

    Returns:
        dict com chaves:
        - pool_size: tamanho base do pool
        - max_overflow: maximo de conexoes extras
        - checked_out: conexoes em uso no momento
        - overflow: conexoes alem do pool_size
        - total_capacity: capacidade maxima (pool_size + max_overflow)
        - utilization_pct: % de utilizacao (checked_out / total_capacity)
        - backend: 'sqlite' ou 'postgresql'
    """
    pool = engine.pool
    backend = "sqlite" if _is_sqlite else "postgresql"

    if _is_sqlite:
        # SQLite nao tem pool - retorna stats zerados
        return {
            "backend": backend,
            "pool_size": 0,
            "max_overflow": 0,
            "checked_out": 0,
            "overflow": 0,
            "total_capacity": 0,
            "utilization_pct": 0.0,
            "note": "SQLite nao usa pool de conexoes",
        }

    checked_out = pool.checkedout()  # type: ignore[attr-defined]
    overflow = pool.overflow()  # type: ignore[attr-defined]
    pool_size = pool.size()  # type: ignore[attr-defined]
    # _max_overflow eh atributo privado do QueuePool, nao Pool base
    max_overflow = getattr(pool, "_max_overflow", 0)
    total_capacity = pool_size + max_overflow
    utilization_pct = round((checked_out / total_capacity) * 100, 2) if total_capacity else 0.0

    return {
        "backend": backend,
        "pool_size": pool_size,
        "max_overflow": max_overflow,
        "checked_out": checked_out,
        "overflow": overflow,
        "total_capacity": total_capacity,
        "utilization_pct": utilization_pct,
    }


def get_db() -> Iterator[Session]:
    """FastAPI dependency para injecao de sessao."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@contextmanager
def session_scope() -> Iterator[Session]:
    """Context manager para uso fora de request (cron, scripts)."""
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
