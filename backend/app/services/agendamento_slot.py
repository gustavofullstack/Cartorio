"""Validacao deterministica de slot de atendimento presencial.

Fonte: dossier oficial (seg-sex 09h-17h, sem sabado comercial).
O bot nunca confirma agenda sozinho — mesmo slot valido nasce HITL/DRAFT.
"""

from __future__ import annotations

from datetime import datetime, time
from typing import Final, TypedDict
from zoneinfo import ZoneInfo

BRT: Final[ZoneInfo] = ZoneInfo("America/Sao_Paulo")
EXPEDIENTE_INICIO: Final[time] = time(9, 0)
EXPEDIENTE_FIM: Final[time] = time(17, 0)
HORARIO_OFICIAL: Final[str] = "segunda a sexta, das 09h as 17h"


class SlotCheck(TypedDict):
    ok: bool
    erro: str | None
    hint: str


def validate_public_slot(data: str, hora: str) -> SlotCheck:
    """Valida data DD/MM/AAAA + hora HH:MM contra o expediente oficial."""
    raw_data = (data or "").strip()
    raw_hora = (hora or "").strip()
    try:
        dt = datetime.strptime(f"{raw_data} {raw_hora}", "%d/%m/%Y %H:%M")
    except ValueError:
        return {
            "ok": False,
            "erro": "data_hora_invalida",
            "hint": (
                "Informe data no formato DD/MM/AAAA e horario HH:MM. "
                f"Expediente: {HORARIO_OFICIAL}."
            ),
        }

    if dt.weekday() >= 5:
        return {
            "ok": False,
            "erro": "fim_de_semana",
            "hint": (
                "Nao ha expediente regular aos sabados, domingos e feriados. "
                f"Atendimento de balcao: {HORARIO_OFICIAL}."
            ),
        }

    if not (EXPEDIENTE_INICIO <= dt.time() < EXPEDIENTE_FIM):
        return {
            "ok": False,
            "erro": "fora_do_expediente",
            "hint": (
                "Horario fora do expediente. "
                f"Atendimento de balcao: {HORARIO_OFICIAL}."
            ),
        }

    agora = datetime.now(BRT).replace(tzinfo=None)
    if dt < agora:
        return {
            "ok": False,
            "erro": "horario_passado",
            "hint": (
                "Esse horario ja passou. Escolha um dia util futuro "
                f"dentro do expediente ({HORARIO_OFICIAL})."
            ),
        }

    return {
        "ok": True,
        "erro": None,
        "hint": (
            "Rascunho de agenda para o escrevente confirmar. "
            "O bot nao marca horario sozinho."
        ),
    }
