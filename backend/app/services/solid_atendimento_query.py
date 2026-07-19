"""G8.11.T1 — SOLID: query de atendimentos fora do controller.

Padrão: API handler só orquestra; regras de filtro/sort ficam no service.
Testável com rows in-memory (sem SQLAlchemy).

Modified by Gustavo Almeida — Wave 42.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal


StatusFilter = Literal["open", "closed", "all"]


@dataclass(frozen=True, slots=True)
class AtendimentoRow:
    id: str
    status: str
    canal: str


class AtendimentoQueryService:
    """Service desacoplado — controller injeta/usa sem conhecer storage."""

    def __init__(self, rows: list[AtendimentoRow] | None = None) -> None:
        self._rows = list(rows or [])

    def list_open(self, status_filter: StatusFilter = "open") -> list[AtendimentoRow]:
        if status_filter == "all":
            return list(self._rows)
        if status_filter == "open":
            return [r for r in self._rows if r.status in {"open", "pending", "em_andamento"}]
        return [r for r in self._rows if r.status in {"closed", "concluido", "resolved"}]

    def count_by_canal(self) -> dict[str, int]:
        out: dict[str, int] = {}
        for r in self._rows:
            out[r.canal] = out.get(r.canal, 0) + 1
        return out

    def as_api_payload(self, status_filter: StatusFilter = "open") -> dict[str, Any]:
        items = self.list_open(status_filter)
        return {
            "count": len(items),
            "items": [{"id": i.id, "status": i.status, "canal": i.canal} for i in items],
        }


__all__ = ["AtendimentoQueryService", "AtendimentoRow", "StatusFilter"]
