"""Sprint 4 S01 - Supabase schema validation tests.

Validates que o DB rodando tem as 10 tabelas S01 com colunas principais,
3 functions, RLS ativo, alembic head linear. Idempotente (read-only).

NAO altera DB. Se rodar contra DB desatualizado, falha. Usar pra:
- Pre-deploy gate (rodar antes de deploy)
- CI smoke test (rodar em CI contra staging)
- Post-migration verification (rodar apos alembic upgrade head)

S00 setup: requer DATABASE_URL apontando para o DB Supabase self-hosted.
Em CI/dev, pode usar sqlite :memory: com schema mockado (NÃO IMPLEMENTADO -
  este teste so funciona contra Postgres real).

Modified by Gustavo Almeida
"""
from __future__ import annotations

import os

import pytest
import sqlalchemy as sa
from sqlalchemy import create_engine, text


# Skip se DATABASE_URL nao configurado (CI sem DB)
DATABASE_URL = os.environ.get("DATABASE_URL", "")
if not DATABASE_URL or "sqlite" in DATABASE_URL:
    pytest.skip(
        "test_supabase_schema requer DATABASE_URL Postgres (sqlite nao suporta RLS/pg_cron)",
        allow_module_level=True,
    )


@pytest.fixture(scope="module")
def engine():
    """Engine Postgres conectado ao DB Supabase. Read-only."""
    eng = create_engine(DATABASE_URL, pool_pre_ping=True)
    yield eng
    eng.dispose()


@pytest.fixture(scope="module")
def inspector(engine):
    """SQLAlchemy Inspector para introspection de schema."""
    return sa.inspect(engine)


# ============================================================================
# Tabelas canonicas S01
# ============================================================================

S01_TABLES = {
    "clientes": [
        "id", "cpf_hash", "nome", "email", "telefone_hash",
        "consentimento_lgpd", "consentimento_em", "consentimento_ip",
        "deleted_at", "created_at", "updated_at", "motivo_encerramento",
    ],
    "protocolos": [
        "id", "numero", "cliente_id", "tipo", "status", "valor_base",
        "valor_adicional", "valor_total", "tabela_referencia", "prazo_dias",
        "created_at", "updated_at", "deleted_at",
    ],
    "atendimentos": [
        "id", "protocolo_id", "cliente_id", "canal", "external_id",
        "chatwoot_conversation_id", "chatwoot_inbox_id", "chatwoot_agent_id",
        "status", "tipo", "contexto_scrubbed", "iniciado_em", "concluido_em",
        "handoff_para_humano", "created_at", "updated_at", "deleted_at",
    ],
    "documentos": [
        "id", "protocolo_id", "tipo", "storage_path", "storage_provider",
        "tamanho_bytes", "mime_type", "hash_sha256", "uploaded_by",
        "uploaded_by_tipo", "validado_por", "validado_em", "validacao_notas",
        "created_at", "updated_at", "deleted_at",
    ],
    "emolumentos": [
        "id", "tipo_servico", "complexidade", "valor", "tabela_mg_2026",
        "created_at", "updated_at",
    ],
    "audit_log": [
        "id", "actor_id", "actor_type", "action", "resource", "payload",
        "ip", "user_agent", "request_id", "prev_hash", "hash",
        "hmac_signature", "timestamp", "canal", "ip_truncated",
    ],
    "webhook_events": [
        "id", "source", "event_id", "received_at", "payload_hash",
    ],
    "outbox_messages": [
        "id", "queue", "payload", "status", "attempts", "last_error",
        "next_retry_at", "created_at", "updated_at",
    ],
    "lgpd_consents": [
        "id", "cliente_id", "conversation_id", "consent_type", "granted",
        "ip_truncated", "user_agent_truncated", "created_at",
        "granted_at", "revoked_at", "version",
    ],
    "lgpd_audit_anpd": [
        "id", "anpd_protocolo", "evento", "dados_jsonb", "ip_truncated",
        "user_agent_truncated", "created_at",
    ],
}


@pytest.mark.parametrize("table_name,expected_columns", list(S01_TABLES.items()))
def test_s01_table_exists_with_columns(table_name, expected_columns, inspector):
    """Todas as 10 tabelas S01 existem com colunas principais."""
    assert table_name in inspector.get_table_names(), (
        f"Tabela S01 '{table_name}' nao encontrada no DB. "
        f"Esperada em: backend/alembic/versions/"
    )
    actual_columns = {c["name"] for c in inspector.get_columns(table_name)}
    missing = set(expected_columns) - actual_columns
    assert not missing, (
        f"Tabela '{table_name}' sem colunas esperadas: {sorted(missing)}. "
        f"Colunas presentes: {sorted(actual_columns)}"
    )


# ============================================================================
# Functions canonicas
# ============================================================================

S01_FUNCTIONS = [
    "fn_audit_chain_verify",  # S08 - valida chain HMAC
    "fn_set_updated_at",      # A18 - trigger updated_at
    "fn_auto_audit",          # S10 - pgAudit-equivalente
]


@pytest.mark.parametrize("func_name", S01_FUNCTIONS)
def test_s01_function_exists(func_name, engine):
    """3 functions canonicas existem no schema public."""
    # SQLAlchemy Inspector.get_functions() nao existe em todas versoes.
    # Fallback: query direta em information_schema.routines.
    with engine.connect() as conn:
        result = conn.execute(
            text(
                "SELECT routine_name FROM information_schema.routines "
                "WHERE routine_schema = 'public'"
            )
        ).fetchall()
    funcs = {r[0] for r in result}
    assert func_name in funcs, (
        f"Function '{func_name}' nao encontrada. "
        f"Esperada em migration 0004/0009. Presentes: {sorted(funcs)}"
    )


# ============================================================================
# RLS (Row Level Security) - LGPD by design
# ============================================================================

@pytest.mark.parametrize("table_name", list(S01_TABLES.keys()))
def test_s01_rls_enabled(table_name, inspector):
    """RLS habilitado em todas as 10 tabelas S01 (LGPD art. 6 VIII)."""
    # SQLAlchemy Inspector nao expoe RLS diretamente - usar SQL raw via engine
    from sqlalchemy import create_engine
    eng = create_engine(DATABASE_URL)
    with eng.connect() as conn:
        result = conn.execute(
            text(
                "SELECT relrowsecurity FROM pg_class "
                "WHERE relname = :t AND relnamespace = 'public'::regnamespace"
            ),
            {"t": table_name},
        ).scalar()
    assert result is True, (
        f"RLS nao habilitado em '{table_name}'. "
        f"Esperado: True (LGPD-by-design)"
    )


# ============================================================================
# Alembic head linear
# ============================================================================

def test_alembic_head_linear(engine):
    """alembic_version tem 1 row (linear chain) - nao multi-head."""
    with engine.connect() as conn:
        rows = conn.execute(
            text("SELECT version_num FROM alembic_version")
        ).fetchall()
    assert len(rows) == 1, (
        f"alembic_version tem {len(rows)} rows (esperado 1 = chain linear). "
        f"Rows: {[r[0] for r in rows]}. "
        f"Fix: alembic stamp <revision> apos resolver multi-head."
    )


def test_alembic_head_is_0012(engine):
    """DB no head canonico Sprint 4 S01 (2026_06_25_0012 = merge final)."""
    with engine.connect() as conn:
        head = conn.execute(
            text("SELECT version_num FROM alembic_version")
        ).scalar()
    assert head == "2026_06_25_0012", (
        f"DB alembic head = {head!r}, esperado '2026_06_25_0012'. "
        f"0012 merge 0003 (pg_notify outbox) + 0010 (S01 merge)."
        f"Rodar alembic upgrade head para aplicar pending migrations."
    )
