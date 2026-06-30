"""pgcrypto encryption at-rest (D15)

Revision ID: 2026_06_25_0014
Revises: 2026_06_25_0013
Create Date: 2026-06-25 00:00:00.000000

D15 LGPD — Encriptação at-rest com pgcrypto.

1. Ativa extensão pgcrypto (se não existir)
2. Cria função encrypt_pii() para encriptar dados sensíveis
3. Cria função decrypt_pii() para desencriptar (apenas interno)
4. Adiciona colunas cpf_encrypted e rg_encrypted na tabela clientes

LGPD art. 46 — Medidas técnicas para proteção de dados pessoais.
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers
revision: str = "2026_06_25_0014"
down_revision: Union[str, None] = "2026_06_25_0013"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Ativar extensão pgcrypto (idempotente)
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")

    # 2. Criar função encrypt_pii — encripta dados com AES-256
    op.execute("""
        CREATE OR REPLACE FUNCTION encrypt_pii(plaintext TEXT)
        RETURNS TEXT AS $$
        BEGIN
            IF plaintext IS NULL OR plaintext = '' THEN
                RETURN NULL;
            END IF;
            RETURN encode(
                pgcrypto.pgp_sym_encrypt(
                    plaintext,
                    current_setting('app.pii_key', true)
                ),
                'base64'
            );
        END;
        $$ LANGUAGE plpgsql IMMUTABLE SECURITY DEFINER;
    """)

    # 3. Criar função decrypt_pii — desencripta (apenas interno)
    op.execute("""
        CREATE OR REPLACE FUNCTION decrypt_pii(encrypted TEXT)
        RETURNS TEXT AS $$
        BEGIN
            IF encrypted IS NULL OR encrypted = '' THEN
                RETURN NULL;
            END IF;
            RETURN pgcrypto.pgp_sym_decrypt(
                decode(encrypted, 'base64'),
                current_setting('app.pii_key', true)
            );
        END;
        $$ LANGUAGE plpgsql IMMUTABLE SECURITY DEFINER;
    """)

    # 4. Adicionar colunas encriptadas na tabela clientes
    op.add_column(
        "clientes",
        sa.Column("cpf_encrypted", sa.Text, nullable=True, comment="CPF encriptado pgcrypto"),
    )
    op.add_column(
        "clientes",
        sa.Column("rg_encrypted", sa.Text, nullable=True, comment="RG encriptado pgcrypto"),
    )

    # 5. Índices para buscas por hash (LGPD art. 46)
    op.create_index("ix_clientes_cpf_encrypted", "clientes", ["cpf_encrypted"])
    op.create_index("ix_clientes_rg_encrypted", "clientes", ["rg_encrypted"])


def downgrade() -> None:
    op.drop_index("ix_clientes_rg_encrypted")
    op.drop_index("ix_clientes_cpf_encrypted")
    op.drop_column("clientes", "rg_encrypted")
    op.drop_column("clientes", "cpf_encrypted")
    op.execute("DROP FUNCTION IF EXISTS decrypt_pii")
    op.execute("DROP FUNCTION IF EXISTS encrypt_pii")
    op.execute("DROP EXTENSION IF EXISTS pgcrypto")
