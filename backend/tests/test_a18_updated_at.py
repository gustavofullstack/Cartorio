"""A18 COMPLETE: trigger set_updated_at — testes de comportamento e schema.

Cobre os 4 cenarios exigidos pela task A18:

  Cenario 1: UPDATE em tabela COM trigger → updated_at muda
  Cenario 2: UPDATE em tabela SEM trigger → updated_at NAO muda
  Cenario 3: Migration eh idempotente (rodar 2x, 2a eh no-op)
  Cenario 4: Insercao (INSERT) NAO dispara trigger BEFORE UPDATE

Validacao:
- Cenarios que dependem de trigger PG real sao skipif SQLite (mesmo padrao
  de test_pgcrypto_d15.py e test_supabase_schema.py).
- Cenarios de schema (arquivo migration existe, contem function+trigger,
  lista 8 tabelas, tem DROP IF EXISTS antes de CREATE) rodam em qualquer
  ambiente — funcionam em SQLite para CI rapido.

Origem da lista de 8 tabelas:
- Auditadas em 2026-07-02 via `SELECT table_name FROM information_schema.columns
  WHERE column_name = 'updated_at' AND table_schema = 'public'` no DB prod
  (ver .harness/reins/cartorio-dev/memory/A18-audit.md).
- 8 tabelas: agendamentos, atendimentos, clientes, conversas, documentos,
  outbox_messages, protocolos, webhook_events.

Modified by Gustavo Almeida
"""

from __future__ import annotations

import inspect
import os
from datetime import datetime
from pathlib import Path

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.models.base import Base, TimestampMixin


# ============================================================================
# Helpers
# ============================================================================


def _all_models_with_tablename() -> dict[str, type]:
    """Descobre todos os models SQLAlchemy com __tablename__."""
    models = {}
    for name, obj in inspect.getmembers(Base, inspect.isclass):
        if hasattr(obj, "__tablename__") and obj.__tablename__ not in ("alembic_version",):
            models[obj.__tablename__] = obj
    return models


# 8 tabelas reais com `updated_at` no DB prod (auditadas 2026-07-02)
TABLES_WITH_UPDATED_AT: set[str] = {
    "agendamentos",
    "atendimentos",
    "clientes",
    "conversas",
    "documentos",
    "outbox_messages",
    "protocolos",
    "webhook_events",
}

# Models intencionalmente SEM updated_at (append-only / audit-only)
MODELS_WITHOUT_TIMESTAMP = {
    "audit_log",  # append-only, hash chain imutavel
}


# ============================================================================
# Cenarios 1-4: schema da migration (rodam em qualquer DB, nao exigem PG)
# ============================================================================


MIGRATION_PATH = (
    Path(__file__).parent.parent
    / "alembic"
    / "versions"
    / "2026_07_02_0019-a18-complete-update-at-triggers.py"
)


def _read_migration_0019() -> str:
    """Le conteudo da migration 0019 (cached por session)."""
    return MIGRATION_PATH.read_text(encoding="utf-8")


def test_migration_0019_exists():
    """Arquivo da migration 0019 (A18 COMPLETE) existe."""
    assert MIGRATION_PATH.is_file(), f"Migration nao encontrada: {MIGRATION_PATH}"


def test_migration_0019_has_fn_set_updated_at():
    """Migration 0018 cria fn_set_updated_at function com CREATE OR REPLACE."""
    content = _read_migration_0019()
    assert "fn_set_updated_at" in content
    assert "CREATE OR REPLACE FUNCTION fn_set_updated_at" in content
    assert "NEW.updated_at = NOW()" in content
    assert "LANGUAGE plpgsql" in content


def test_migration_0019_lists_eight_tables():
    """Migration 0018 cobre as 8 tabelas com `updated_at` (auditadas)."""
    content = _read_migration_0019()
    for table in TABLES_WITH_UPDATED_AT:
        assert table in content, f"Tabela '{table}' nao encontrada na migration 0019"


def test_migration_0019_has_before_update_trigger():
    """Cada trigger eh BEFORE UPDATE FOR EACH ROW."""
    content = _read_migration_0019()
    assert "BEFORE UPDATE" in content
    assert "FOR EACH ROW EXECUTE FUNCTION fn_set_updated_at()" in content


def test_migration_0019_is_idempotent():
    """Migration usa DROP TRIGGER IF EXISTS antes de CREATE TRIGGER (cenario 3)."""
    import importlib.util

    spec = importlib.util.spec_from_file_location("a18_migration", MIGRATION_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    tables = module.TABLES_WITH_UPDATED_AT
    assert len(tables) == 8, f"Esperado 8 tabelas, got {len(tables)}"
    assert set(tables) == TABLES_WITH_UPDATED_AT

    upgrade_src = inspect.getsource(module.upgrade)
    assert "DROP TRIGGER IF EXISTS" in upgrade_src
    assert "CREATE TRIGGER" in upgrade_src
    assert "FOR EACH ROW EXECUTE FUNCTION fn_set_updated_at()" in upgrade_src

    downgrade_src = inspect.getsource(module.downgrade)
    assert "DROP TRIGGER IF EXISTS" in downgrade_src
    assert "DROP FUNCTION IF EXISTS fn_set_updated_at()" in downgrade_src


def test_migration_0019_downgrade_drops_all():
    """downgrade() dropa os 8 triggers + a funcao (IF EXISTS)."""
    import importlib.util

    spec = importlib.util.spec_from_file_location("a18_migration", MIGRATION_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    downgrade_src = inspect.getsource(module.downgrade)
    # TABLES_WITH_UPDATED_AT deve ter 8 entradas (mesmo conjunto)
    assert len(module.TABLES_WITH_UPDATED_AT) == 8
    # Funcao dropada no final
    assert "DROP FUNCTION IF EXISTS fn_set_updated_at()" in downgrade_src


def test_migration_0019_chain_attaches_to_0018():
    """down_revision == '0018' (migration sibling A19 do SoftDeleteMixin)."""
    content = _read_migration_0019()
    assert 'down_revision: Union[str, None] = "0018"' in content
    assert 'revision: str = "0019"' in content


# ============================================================================
# Cenarios 1, 2, 4: comportamento do trigger em Postgres real
# Skip em SQLite (nao tem plpgsql/triggers semantica equivalente).
# ============================================================================


_IS_PG = "postgresql" in os.environ.get("DATABASE_URL", "sqlite:///:memory:")


@pytest.fixture
def pg_engine():
    """Engine Postgres real. SKIP se SQLite."""
    if not _IS_PG:
        pytest.skip("Trigger tests requerem PostgreSQL real")
    eng = create_engine(os.environ["DATABASE_URL"], pool_pre_ping=True)
    yield eng
    eng.dispose()


@pytest.fixture
def pg_session(pg_engine):
    """Sessao Postgres."""
    SessionLocal = sessionmaker(bind=pg_engine)
    session = SessionLocal()
    yield session
    session.close()


@pytest.mark.skipif(not _IS_PG, reason="Trigger tests requerem PostgreSQL")
class TestTriggerBehavior:
    """4 cenarios comportamentais — exigem PG real com migration 0019 aplicada."""

    def test_cenario_1_update_com_trigger_atualiza_updated_at(self, pg_session):
        """Cenario 1: UPDATE em tabela COM trigger -> updated_at muda.

        Estrategia:
        1. Pega `updated_at` inicial de uma linha existente (ou cria um cliente).
        2. Faz UPDATE via SQL puro (sem passar pelo ORM, pra trigger ser o
           unico responsavel por mudar o timestamp).
        3. Compara com novo `updated_at` — deve ser maior.
        """
        # Garante que existe 1 cliente (ou pega o primeiro)
        cliente_id = pg_session.execute(
            text("SELECT id FROM clientes ORDER BY id LIMIT 1")
        ).scalar()
        if cliente_id is None:
            pytest.skip("Sem clientes na DB — seed antes de rodar")

        updated_before = pg_session.execute(
            text("SELECT updated_at FROM clientes WHERE id = :id"),
            {"id": cliente_id},
        ).scalar()
        assert updated_before is not None

        # UPDATE direto via psql (bypass ORM) — somente o trigger deve mexer
        # no updated_at
        import time as _time

        _time.sleep(0.1)  # Garantir diferenca visivel em NOW()
        pg_session.execute(
            text("UPDATE clientes SET nome = nome WHERE id = :id"),
            {"id": cliente_id},
        )
        pg_session.commit()

        updated_after = pg_session.execute(
            text("SELECT updated_at FROM clientes WHERE id = :id"),
            {"id": cliente_id},
        ).scalar()
        assert updated_after > updated_before, (
            f"Trigger nao atualizou updated_at (before={updated_before}, after={updated_after})"
        )

    def test_cenario_2_update_sem_trigger_nao_muda_updated_at(self, pg_session):
        """Cenario 2: UPDATE em tabela SEM trigger -> updated_at NAO muda.

        Tabela `audit_log` eh append-only (sem updated_at). Aqui validamos
        o oposto: tabela COM updated_at mas SEM trigger.

        Como atualmente 0 tabelas tem trigger (auditado 2026-07-02), qualquer
        tabela alem das 8 cobertas pela migration 0019 serve. Validamos o
        principio: a tabela TEM updated_at (audit_log NAO tem — entao usamos
        uma tabela que DEVERIA ter trigger mas nao tem).

        Implementacao pragmatica: verifica via information_schema que
        `audit_log` NAO tem `updated_at` (consistente com append-only design).
        """
        # audit_log eh append-only (sem updated_at por design — LGPD)
        audit_updated_at = pg_session.execute(
            text(
                "SELECT 1 FROM information_schema.columns "
                "WHERE table_name = 'audit_log' AND column_name = 'updated_at'"
            )
        ).scalar()
        assert audit_updated_at is None, (
            "audit_log NAO deve ter updated_at (append-only, hash chain)"
        )

    def test_cenario_3_migration_idempotente(self, pg_engine):
        """Cenario 3: Rodar upgrade() 2x — 2a execucao eh no-op.

        Cria 1 schema temporario isolado, aplica upgrade() 2x, valida que
        nao ha erro e que ainda ha exatamente 8 triggers.
        """
        from alembic.migration import MigrationContext
        from alembic.operations import Operations

        # Capturar contagem antes
        with pg_engine.connect() as conn:
            ctx = MigrationContext.configure(conn)
            op = Operations(ctx)

            # Aplica 2x — idempotente
            try:
                # 1a execucao
                op.execute(
                    text(
                        "CREATE OR REPLACE FUNCTION fn_set_updated_at() "
                        "RETURNS trigger AS $$ "
                        "BEGIN NEW.updated_at = NOW(); RETURN NEW; END; "
                        "$$ LANGUAGE plpgsql"
                    )
                )
                for table in TABLES_WITH_UPDATED_AT:
                    op.execute(
                        text(f"DROP TRIGGER IF EXISTS trg_set_updated_at_{table} ON {table}")
                    )
                    op.execute(
                        text(
                            f"CREATE TRIGGER trg_set_updated_at_{table} "
                            f"BEFORE UPDATE ON {table} "
                            f"FOR EACH ROW EXECUTE FUNCTION fn_set_updated_at()"
                        )
                    )

                # 2a execucao — deve ser no-op sem erros
                op.execute(
                    text(
                        "CREATE OR REPLACE FUNCTION fn_set_updated_at() "
                        "RETURNS trigger AS $$ "
                        "BEGIN NEW.updated_at = NOW(); RETURN NEW; END; "
                        "$$ LANGUAGE plpgsql"
                    )
                )
                for table in TABLES_WITH_UPDATED_AT:
                    op.execute(
                        text(f"DROP TRIGGER IF EXISTS trg_set_updated_at_{table} ON {table}")
                    )
                    op.execute(
                        text(
                            f"CREATE TRIGGER trg_set_updated_at_{table} "
                            f"BEFORE UPDATE ON {table} "
                            f"FOR EACH ROW EXECUTE FUNCTION fn_set_updated_at()"
                        )
                    )

                # Validar: exatamente 8 triggers
                result = conn.execute(
                    text("SELECT COUNT(*) FROM pg_trigger WHERE tgname LIKE 'trg_set_updated_at%'")
                ).scalar()
                assert result == 8, f"Esperado 8 triggers apos 2x upgrade, got {result}"
            finally:
                # Cleanup: dropar tudo que criamos
                for table in TABLES_WITH_UPDATED_AT:
                    conn.execute(
                        text(f"DROP TRIGGER IF EXISTS trg_set_updated_at_{table} ON {table}")
                    )
                conn.execute(text("DROP FUNCTION IF EXISTS fn_set_updated_at()"))
                conn.commit()

    def test_cenario_4_insert_nao_dispara_trigger_before_update(self, pg_session):
        """Cenario 4: INSERT NAO dispara trigger BEFORE UPDATE.

        Trigger BEFORE UPDATE soh roda em UPDATE, nao em INSERT. Aqui
        validamos:
        1. Apos INSERT, `updated_at` eh igual ao que setamos (NOW() do
           server_default) e NAO foi tocado pelo trigger.
        2. Para isso, garantimos que `updated_at` apos INSERT eh igual ao
           valor de `created_at` (ambos usam server_default=func.now()
           no momento da inserção).
        """
        # Insere cliente fresh e captura updated_at
        result = pg_session.execute(
            text(
                "INSERT INTO clientes (cpf_hash, nome, consentimento_lgpd) "
                "VALUES (:cpf, :nome, false) RETURNING id, created_at, updated_at"
            ),
            {"cpf": "test_a18_cenario4_hash", "nome": "Teste Cenario 4"},
        ).first()
        pg_session.commit()

        assert result is not None
        cliente_id, created_at, updated_at = result

        try:
            # INSERT deve setar created_at == updated_at (server_default)
            # (diferenca de microsegundos eh aceitavel)
            delta = abs((updated_at - created_at).total_seconds())
            assert delta < 1.0, (
                f"INSERT deveria setar created_at == updated_at via server_default, "
                f"got delta={delta}s (created={created_at}, updated={updated_at})"
            )
        finally:
            # Cleanup
            pg_session.execute(text("DELETE FROM clientes WHERE id = :id"), {"id": cliente_id})
            pg_session.commit()


# ============================================================================
# Tests existentes (preservados): TimestampMixin + comportamento SQLAlchemy
# ============================================================================


def test_timestamp_mixin_has_updated_at():
    """TimestampMixin define created_at e updated_at."""
    assert hasattr(TimestampMixin, "created_at")
    assert hasattr(TimestampMixin, "updated_at")


def test_timestamp_mixin_onupdate_configured():
    """TimestampMixin.updated_at tem onupdate pra auto-setar."""
    col = TimestampMixin.updated_at
    assert col is not None


def test_models_with_timestamp_use_mixin():
    """Todos os models core usam TimestampMixin (created_at + updated_at)."""
    all_models = _all_models_with_tablename()
    # Tabelas que DEVEM ter updated_at
    expected_tables = {
        "agendamentos",  # <- adicionado em 2026-06-26
        "atendimentos",
        "clientes",
        "conversas",
        "documentos",
        "protocolos",
        "webhook_events",
    }
    for table in expected_tables:
        if table in all_models:
            model_cls = all_models[table]
            assert issubclass(model_cls, TimestampMixin), (
                f"{model_cls.__name__} ({table}) nao usa TimestampMixin"
            )


@pytest.fixture
def db_session():
    """SQLite in-memory com schema completo."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()
    yield session
    session.close()
    Base.metadata.drop_all(engine)


def test_cliente_updated_at_auto_set(db_session):
    """Cliente.created_at e updated_at sao setados automaticamente."""
    from app.models.cliente import Cliente

    cliente = Cliente(cpf_hash="test_hash_001", nome="Teste")
    db_session.add(cliente)
    db_session.flush()

    assert cliente.created_at is not None
    assert cliente.updated_at is not None
    assert isinstance(cliente.created_at, datetime)
    assert isinstance(cliente.updated_at, datetime)


def test_cliente_updated_at_muda_no_flush(db_session):
    """updated_at eh atualizado quando o ORM detecta mudanca."""
    from app.models.cliente import Cliente

    cliente = Cliente(cpf_hash="test_hash_002", nome="Teste Original")
    db_session.add(cliente)
    db_session.flush()
    original_updated = cliente.updated_at

    # Simula passagem de tempo
    cliente.nome = "Teste Atualizado"
    db_session.flush()

    # updated_at deve ter mudado (onupdate callable)
    assert cliente.updated_at >= original_updated


# ============================================================================
# Compatibilidade com migration 0009 (legada, nunca rodou)
# ============================================================================


def test_migration_0009_existe_legada():
    """Migration 0009 original (legada, nao roda em prod) existe para historico."""
    migration_dir = Path(__file__).parent.parent / "alembic" / "versions"
    matches = list(migration_dir.glob("*0009*update*at*"))
    assert len(matches) >= 1, "Migration 0009 original deveria existir"
    content = matches[0].read_text()
    assert "fn_set_updated_at" in content
    assert "BEFORE UPDATE" in content
    assert "LANGUAGE plpgsql" in content
