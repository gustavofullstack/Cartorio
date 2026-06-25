"""rename lgpd_consent_log to lgpd_consents + create lgpd_audit_anpd + missing spec columns

Revision ID: 2026_06_25_0011
Revises: 2026_06_24_0003
Create Date: 2026-06-25 09:45:00.000000

S0 SQUAD S — Sprint 4 S01 Phase 2: alinha schema com spec canonica.

Acoes idempotentes:

1. RENAME TABLE lgpd_consent_log -> lgpd_consents
   (Sprint 0 manual criou com nome antigo. 4 migrations subsequentes
   0004, 0005, 0007, 0009 referenciam nome canonico lgpd_consents.
   Renomear eh mais simples que ajustar 4 migrations.)

2. CREATE TABLE lgpd_audit_anpd (LGPD art. 48 + ANPD regulamento)
   Campos:
   - id BIGSERIAL PK
   - anpd_protocolo VARCHAR(64) - numero do protocolo na ANPD
   - evento VARCHAR(64) NOT NULL - tipo de evento (encerramento, vazamento, etc)
   - dados_jsonb JSONB - payload do evento
   - ip_truncated INET - IP truncado /24 (LGPD art. 5 I)
   - user_agent_truncated VARCHAR(512)
   - created_at TIMESTAMPTZ DEFAULT NOW()

3. ADD COLUMN granted_at, revoked_at, version em lgpd_consents
   Spec S01 pede esses campos alem do created_at. Sao nullable para
   nao quebrar dados existentes. version eh para LGPD versioning
   do termo de consentimento (mudou texto, nova versao, paciente
   precisa re-consentir).

LGPD-by-design:
- ip_truncated: /24 (IPv4) ou /32 (IPv6) - dado pessoal mas truncado
- user_agent_truncated: truncado em 256 chars max
- granted/revoked: booleans de estado LGPD
- anpd_protocolo: rastreabilidade para ANPD (lei 13.709 art. 48)

Idempotente: cada operacao usa IF EXISTS ou IF NOT EXISTS.

Modified by Gustavo Almeida
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "2026_06_25_0011"
down_revision: Union[str, None] = "2026_06_24_0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Rename + create + add columns. Idempotente."""
    bind = op.get_bind()
    is_pg = bind.dialect.name == "postgresql"

    # ========================================================================
    # 1. RENAME lgpd_consent_log -> lgpd_consents
    # ========================================================================
    inspector = sa.inspect(bind)
    existing_tables = set(inspector.get_table_names())

    if "lgpd_consent_log" in existing_tables and "lgpd_consents" not in existing_tables:
        op.execute("ALTER TABLE lgpd_consent_log RENAME TO lgpd_consents")
    elif "lgpd_consents" in existing_tables:
        # Ja renomeado em run anterior (idempotente)
        pass
    else:
        # Nenhum dos dois existe - cria lgpd_consents do zero
        op.create_table(
            "lgpd_consents",
            sa.Column("id", sa.dialects.postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column("cliente_id", sa.dialects.postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column("conversation_id", sa.dialects.postgresql.UUID(as_uuid=True), nullable=True),
            sa.Column("consent_type", sa.String(length=64), nullable=False),
            sa.Column("granted", sa.Boolean, nullable=False, server_default="false"),
            sa.Column("ip_truncated", sa.dialects.postgresql.INET, nullable=True),
            sa.Column("user_agent_truncated", sa.String(length=512), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        )
        op.create_index("ix_lgpd_consents_cliente_id", "lgpd_consents", ["cliente_id"])
        op.create_index("ix_lgpd_consents_created_at", "lgpd_consents", ["created_at"])

    # ========================================================================
    # 2. ADD COLUMN granted_at, revoked_at, version em lgpd_consents (spec S01)
    # ========================================================================
    if is_pg:
        op.execute("ALTER TABLE lgpd_consents ADD COLUMN IF NOT EXISTS granted_at TIMESTAMPTZ")
        op.execute("ALTER TABLE lgpd_consents ADD COLUMN IF NOT EXISTS revoked_at TIMESTAMPTZ")
        op.execute("ALTER TABLE lgpd_consents ADD COLUMN IF NOT EXISTS version VARCHAR(32)")

    # ========================================================================
    # 3. CREATE TABLE lgpd_audit_anpd
    # ========================================================================
    if "lgpd_audit_anpd" not in inspector.get_table_names():
        op.create_table(
            "lgpd_audit_anpd",
            sa.Column("id", sa.BigInteger, primary_key=True, autoincrement=True),
            sa.Column("anpd_protocolo", sa.String(length=64), nullable=True),
            sa.Column("evento", sa.String(length=64), nullable=False),
            sa.Column("dados_jsonb", postgresql.JSONB, nullable=True),
            sa.Column("ip_truncated", sa.dialects.postgresql.INET, nullable=True),
            sa.Column("user_agent_truncated", sa.String(length=512), nullable=True),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        )
        op.create_index("ix_lgpd_audit_anpd_evento", "lgpd_audit_anpd", ["evento"])
        op.create_index("ix_lgpd_audit_anpd_created_at", "lgpd_audit_anpd", ["created_at"])
        op.create_index("ix_lgpd_audit_anpd_anpd_protocolo", "lgpd_audit_anpd", ["anpd_protocolo"])


def downgrade() -> None:
    """Reverse: drop lgpd_audit_anpd + columns + rename back."""
    bind = op.get_bind()

    # Drop lgpd_audit_anpd
    if "lgpd_audit_anpd" in sa.inspect(bind).get_table_names():
        op.drop_table("lgpd_audit_anpd")

    # Drop columns from lgpd_consents (if we added them)
    inspector = sa.inspect(bind)
    if "lgpd_consents" in inspector.get_table_names():
        existing_cols = {c["name"] for c in inspector.get_columns("lgpd_consents")}
        for col in ("version", "revoked_at", "granted_at"):
            if col in existing_cols:
                op.drop_column("lgpd_consents", col)

    # Rename back: lgpd_consents -> lgpd_consent_log
    if "lgpd_consents" in inspector.get_table_names() and "lgpd_consent_log" not in inspector.get_table_names():
        op.execute("ALTER TABLE lgpd_consents RENAME TO lgpd_consent_log")
