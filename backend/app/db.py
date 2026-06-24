"""SQLAlchemy engine + session factory."""

from collections.abc import Iterator
from contextlib import contextmanager

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.config import settings

_is_sqlite = settings.database_url.startswith("sqlite")

# A15: Connection pool tuning — pool_size=20, max_overflow=10, pre_ping, recycle 1h
_engine_kwargs: dict = {
    "pool_pre_ping": True,
    "pool_recycle": 3600,  # 1h — evita conexao morta em pgBouncer/load balancer
}
if not _is_sqlite:
    # Em SQLite (testes) nao ha pool — pool_size e ignorado
    _engine_kwargs.update(
        pool_size=20,
        max_overflow=10,
        pool_timeout=30,  # 30s para adquirir conexao
    )
_engine_kwargs["echo"] = settings.app_env == "development"

engine = create_engine(settings.database_url, **_engine_kwargs)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine, expire_on_commit=False)


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
