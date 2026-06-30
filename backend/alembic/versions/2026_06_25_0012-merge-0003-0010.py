"""merge heads 0003 (pg_notify outbox) + 0010 (S01 merge)

Revision ID: 2026_06_25_0012
Revises: 2026_06_25_0003, 2026_06_25_0010
Create Date: 2026-06-25 10:13:35.131013

S0 SQUAD S — merge migration que funde o head orphan 0003 (pg_notify
outbox trigger) com o merge head 0010 (S01), eliminando multiple heads
no alembic chain.

Contexto:
- 0003 (add-pg-notify-outbox-trigger-a24) foi criado como filho de
  0002 (soft delete), mas NUNCA foi incluido no merge 0010 (que funde
  apenas 0001 e 0009). Resultado: 2 heads (0003 + 0010).
- 0012 eh merge NO-OP que funde os 2 heads num unico head linear,
  permitindo alembic upgrade head sem ambiguidade.

Esta migration NAO altera schema. Apenas funde os 2 heads em um
unico head linear para permitir `alembic upgrade head` sem ambiguidade.

LGPD-by-design: zero impacto. Migration noop puro.

Idempotente: pode rodar multiplas vezes sem efeito (nao tem upgrade body).

Modified by Gustavo Almeida
"""

from typing import Sequence, Union

# revision identifiers, used by Alembic.
revision: str = "2026_06_25_0012"
down_revision: Union[str, tuple[str, ...], None] = ("2026_06_25_0003", "2026_06_25_0010")
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Merge: noop. Apenas funde os 2 chains em um head unico."""
    pass


def downgrade() -> None:
    """Merge: noop. Apenas desfaz a fusao (volta a 2 heads)."""
    pass
