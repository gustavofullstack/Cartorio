"""merge heads 2026_06_24_0000 (BASE) + 2026_06_24_0002 (outbox DLQ)

Revision ID: 2026_06_24_0003
Revises: 2026_06_24_0000, 2026_06_24_0002
Create Date: 2026-06-24 23:55:00.000000

Resolve o "Multiple heads" causado pela D0.1:
- 2026_06_24_0000 (BASE 9 tabelas) - down_revision=2026_06_23_0001
- 2026_06_24_0002 (outbox DLQ)   - down_revision=2026_06_24_0001

Esta migration NAO altera schema. Apenas funde os 2 chains em um
unico head linear para permitir `alembic upgrade head` sem ambiguidade.

NOTA: 2026_06_24_0000 foi criada com down_revision="2026_06_23_0001"
(nao None como briefing original pediu) porque 2026_06_23_0001 JÁ
tinha down_revision=None — alembic nao permite 2 migrations raiz no
mesmo branch. Resultado: chain agora linear
  None → 2026_06_23_0001 → 2026_06_24_0001 → 2026_06_24_0002
                            └→ 2026_06_24_0000 → 2026_06_24_0003 (merge)

Modified by Gustavo Almeida
"""
from typing import Sequence, Union


# revision identifiers, used by Alembic.
revision: str = "2026_06_24_0003"
down_revision: Union[str, tuple[str, ...], None] = ("2026_06_24_0000", "2026_06_24_0002")
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Merge: noop. Apenas funde os 2 chains em um head unico."""
    pass


def downgrade() -> None:
    """Split: noop. Reverte o merge (alembic cria 2 heads)."""
    pass
