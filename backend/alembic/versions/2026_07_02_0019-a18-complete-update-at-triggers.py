"""A18 COMPLETE: trigger fn_set_updated_at em TODAS as 8 tabelas com updated_at

Revision ID: 0019
Revises: 0018
Create Date: 2026-07-02 20:33:00.000000

SQUAD A A18 (FINAL) — completes the trigger set_updated_at coverage.

Contexto:
- A migration 2026_06_25_0009 (A18 inicial) lista 10 tabelas candidatas, mas
  nunca rodou no DB prod (gap real confirmado por query direta em 2026-07-02
  — ver .harness/reins/cartorio-dev/memory/A18-audit.md).
- DB prod atualmente tem 8 tabelas com `updated_at` e ZERO triggers.
- A 0009 eh broken-by-design: referencia `webhook_events` que soh ganhou
  `updated_at` na migration `0015` posterior — `0009` falharia com
  "column updated_at does not exist" quando aplicada.

Solucao:
- Cria 1 funcao generica `fn_set_updated_at()` (CREATE OR REPLACE, idempotente).
- Cria 8 triggers `trg_set_updated_at_<tabela>` BEFORE UPDATE FOR EACH ROW,
  um por tabela real (auditadas via information_schema em 2026-07-02).
- Idempotente: DROP TRIGGER IF EXISTS antes de cada CREATE TRIGGER.
- downgrade() dropa os 8 triggers + dropa a funcao (IF EXISTS).

LGPD-by-design: Garante audit trail exato (LGPD art. 37 — rastreabilidade
de alteracoes). Quando uma linha eh atualizada via SQL puro (psql, job
batch, n8n direto, etc), `updated_at` ainda eh setado para NOW() — sem
isso, campos ficam stale e o dashboard/observabilidade reporta dados
errados.

Tabelas cobertas (auditadas em 2026-07-02):
    agendamentos, atendimentos, clientes, conversas, documentos,
    outbox_messages, protocolos, webhook_events

Push gate: NAO aplicar em prod sem Gustavo GO (Lesson 110). Migration
versionada no master mas soh roda com autorizacao explicita.

Modified by Gustavo Almeida
"""

from __future__ import annotations

from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "0019"
down_revision: Union[str, None] = "0018"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# Tabelas com `updated_at` confirmadas via information_schema em 2026-07-02
# (ver .harness/reins/cartorio-dev/memory/A18-audit.md)
# NAO inclui emolumentos / lgpd_consents / lgpd_audit_anpd (listadas em 0009
# mas que nao tem a coluna no DB prod real).
TABLES_WITH_UPDATED_AT: tuple[str, ...] = (
    "agendamentos",
    "atendimentos",
    "clientes",
    "conversas",
    "documentos",
    "outbox_messages",
    "protocolos",
    "webhook_events",
)


# Funcao generica: setta NEW.updated_at = NOW() em BEFORE UPDATE.
# CREATE OR REPLACE garante idempotencia (nao da erro se ja existe).
FN_SET_UPDATED_AT_SQL = """
CREATE OR REPLACE FUNCTION fn_set_updated_at() RETURNS trigger AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$
LANGUAGE plpgsql
"""


def upgrade() -> None:
    """Cria funcao generica + 8 triggers idempotentes.

    Cada CREATE TRIGGER eh precedido de DROP TRIGGER IF EXISTS pra
    garantir idempotencia (rodar 2x eh no-op alem de sobrescrever a funcao).
    """
    # 1) Funcao generica (1x, OR REPLACE)
    op.execute(FN_SET_UPDATED_AT_SQL)

    # 2) 1 trigger por tabela
    for table in TABLES_WITH_UPDATED_AT:
        trigger_name = f"trg_set_updated_at_{table}"
        # Idempotente: drop se ja existe (e.g., 0009 rodou parcial em algum DB)
        op.execute(f"DROP TRIGGER IF EXISTS {trigger_name} ON {table}")
        op.execute(
            f"""
            CREATE TRIGGER {trigger_name}
            BEFORE UPDATE ON {table}
            FOR EACH ROW EXECUTE FUNCTION fn_set_updated_at()
            """
        )


def downgrade() -> None:
    """Dropa os 8 triggers + dropa a funcao (IF EXISTS)."""
    for table in TABLES_WITH_UPDATED_AT:
        trigger_name = f"trg_set_updated_at_{table}"
        op.execute(f"DROP TRIGGER IF EXISTS {trigger_name} ON {table}")
    op.execute("DROP FUNCTION IF EXISTS fn_set_updated_at()")
