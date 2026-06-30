"""merge heads 2026_06_25_0001 (protocolo stats) + 2026_06_25_0009 (trigger update_at) — Sprint 4 S01

Revision ID: 2026_06_25_0010
Revises: 2026_06_25_0001, 2026_06_25_0009
Create Date: 2026-06-25 09:30:00.000000

S0 SQUAD S — merge migration que funde os 2 heads do alembic chain.

Contexto:
- 0000 (base cartorio core tables) e 0001 (protocolo stats materialized view)
  ambos tinham down_revision=2026_06_23_0001 (criados em paralelo por
  agentes diferentes), gerando 2 heads. 0003 merge tentou resolver mas
  alembic_version no DB prod tem 2 rows: 0001 e 0003 — estado corrupto.
- Alem disso, 0004-0009 (RLS, pg_cron, webhooks, storage, realtime,
  graphql, vault, trigger) SHIPPED no master mas NUNCA foram aplicadas
  no DB prod. Cadeia bifurcada alem disso.
- 0010 eh merge NO-OP que funde os 2 heads (0001 e 0009) num unico
  head linear, permitindo alembic upgrade head sem ambiguidade.

Esta migration NAO altera schema. Apenas funde os 2 chains em um
unico head linear para permitir `alembic upgrade head` sem ambiguidade.

LGPD-by-design: zero impacto. Migration noop puro.

Idempotente: pode rodar multiplas vezes sem efeito (nao tem upgrade body).

Modified by Gustavo Almeida
"""

from typing import Sequence, Union

# revision identifiers, used by Alembic.
revision: str = "2026_06_25_0010"
down_revision: Union[str, tuple[str, ...], None] = ("2026_06_25_0001", "2026_06_25_0009")
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Merge: noop. Apenas funde os 2 chains em um head unico."""
    pass


def downgrade() -> None:
    """Merge: noop. Apenas desfaz a fusao (volta a 2 heads)."""
    pass
