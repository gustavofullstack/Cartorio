"""S0 S08: Supabase Vault secrets bootstrap (estrutura + GRANTs)

Revision ID: 2026_06_25_0008
Revises: 2026_06_25_0007
Create Date: 2026-06-25 07:00:00.000000

SQUAD S0 S08 - estrutura do Supabase Vault (pgsodium).

IMPORTANTE: Esta migration NAO cria os secrets em si (LGPD: secrets nao
podem ficar em migrations versionadas). Cria apenas:
1. Extensao pgsodium (necessaria para vault)
2. Schema vault
3. GRANTs para service_role ter acesso total ao vault
4. Funcao helper vault_get_or_create(name) que retorna placeholder
   'AWAITING_OPERATOR' se o secret nao existir (fail-loud)

Os 11 secrets (cartorio_api_key, audit_hmac_key, opencode_go_api_key,
chatwoot_api_key, evolution_api_key, n8n_api_key, n8n_webhook_secret,
telegram_bot_token, jules_api, render_api, linear_api) devem ser criados
pelo operador via script:
  uv run python backend/scripts/seed_vault_secrets.py
(le /Users/gustavoalmeida/projetos/Cartorio/.secrets/*.env e chama
vault.create_secret() para cada um).

A API backend le os secrets via SELECT vault.secrets -> helper. Em prod,
o backend le de env vars (ja funciona) E consulta vault como fallback
via app/services/vault_client.py (criado em E4 squad).
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op


revision: str = "2026_06_25_0008"
down_revision: Union[str, None] = "2026_06_25_0007"
branch_labels: Union[str, Sequence[str, None], None] = None
depends_on: Union[str, Sequence[str, None], None] = None


def upgrade() -> None:
    # pgsodium eh a dependencia do vault
    op.execute("CREATE EXTENSION IF NOT EXISTS pgsodium")

    # Schema vault (Supabase ja cria, idempotente)
    op.execute("CREATE SCHEMA IF NOT EXISTS vault")

    # GRANTs para service_role
    op.execute("GRANT USAGE ON SCHEMA vault TO service_role, supabase_admin")
    op.execute("GRANT ALL ON ALL TABLES IN SCHEMA vault TO service_role, supabase_admin")
    op.execute("GRANT ALL ON ALL SEQUENCES IN SCHEMA vault TO service_role, supabase_admin")
    op.execute("GRANT ALL ON ALL FUNCTIONS IN SCHEMA vault TO service_role, supabase_admin")

    # Funcao helper: fail-loud se secret nao existir
    op.execute(
        """
        CREATE OR REPLACE FUNCTION vault_get_or_create(p_name TEXT)
        RETURNS TEXT
        LANGUAGE plpgsql
        STABLE
        SECURITY DEFINER
        AS $$
        DECLARE
            v_decrypted TEXT;
        BEGIN
            SELECT decrypted_secret INTO v_decrypted
            FROM vault.decrypted_secrets
            WHERE name = p_name
            LIMIT 1;

            IF v_decrypted IS NULL THEN
                RAISE WARNING 'Vault secret % nao encontrado. Rode seed_vault_secrets.py', p_name;
                RETURN 'AWAITING_OPERATOR';
            END IF;

            RETURN v_decrypted;
        END;
        $$
        """
    )


def downgrade() -> None:
    op.execute("DROP FUNCTION IF EXISTS vault_get_or_create(TEXT)")
    # Nao dropa pgsodium/vault (outros sistemas podem depender)
