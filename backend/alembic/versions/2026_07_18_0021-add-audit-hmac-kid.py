"""add audit_log.hmac_kid column (G8.19.T2 HMAC key rotation).

Revision ID: 0021
Revises: 0020
Create Date: 2026-07-18

G8.19.T2 — Roteador de chaves HMAC permite rotacionar ``AUDIT_HMAC_KEY``
sem invalidar entries antigos. Cada entry nova referencia qual ``kid``
(key id) assinou. Entries pre-rotacao permanecem com ``hmac_kid IS NULL``
e sao verificadas contra a kid ``legacy`` registrada no bootstrap do
``app.services.audit_keys``.

Schema:
- Adiciona coluna ``audit_log.hmac_kid VARCHAR(64) NULL``
- Indice em ``hmac_kid`` pra forensic queries rapidas
- Idempotente: checa existencia da coluna via information_schema

LGPD Art. 37 (rastreabilidade): kid por entry eh requisito de auditoria.
LGPD Art. 46 (seguranca): rotacao periodica eh boa pratica de gestao de chaves.
LGPD Art. 50 (governanca): preservacao da cadeia atraves de chave historicizada.

Impacto em runtime:
- INSERT novos passam a incluir ``hmac_kid`` (novo campo opcional em row)
- SELECT existentes continuam funcionando (column eh nullable)
- ``verify_chain`` NAO recalcula HMAC (apenas sha256 chain), portanto
  performance e queries pre-existentes nao sao afetadas

Downgrade:
- DROP COLUMN remove coluna; entries existentes perdem o kid mas a
  cadeia de hash (sha256) continua intacta. USE APENAS PARA ROLLBACK
  CONTROLADO. NAO usar em prod sem autorizacao do DPO.

Modified by Gustavo Almeida
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "0021"
down_revision = "0020"
branch_labels = None
depends_on = None


def _column_exists(table: str, column: str) -> bool:
    conn = op.get_bind()
    q = sa.text(
        "SELECT 1 FROM information_schema.columns "
        "WHERE table_name = :t AND column_name = :c"
    )
    return conn.execute(q, {"t": table, "c": column}).scalar() is not None


def _index_exists(table: str, index: str) -> bool:
    conn = op.get_bind()
    q = sa.text(
        "SELECT 1 FROM pg_indexes "
        "WHERE tablename = :t AND indexname = :i"
    )
    return conn.execute(q, {"t": table, "i": index}).scalar() is not None


def upgrade() -> None:
    if not _column_exists("audit_log", "hmac_kid"):
        op.add_column(
            "audit_log",
            sa.Column("hmac_kid", sa.String(length=64), nullable=True),
        )
    if not _index_exists("audit_log", "ix_audit_log_hmac_kid"):
        op.create_index(
            "ix_audit_log_hmac_kid",
            "audit_log",
            ["hmac_kid"],
        )


def downgrade() -> None:
    if _index_exists("audit_log", "ix_audit_log_hmac_kid"):
        op.drop_index("ix_audit_log_hmac_kid", table_name="audit_log")
    if _column_exists("audit_log", "hmac_kid"):
        op.drop_column("audit_log", "hmac_kid")
