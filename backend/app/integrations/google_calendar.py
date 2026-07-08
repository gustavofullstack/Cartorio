import logging
from datetime import date, timedelta, datetime
import httpx
from typing import Dict
from app.config import settings

logger = logging.getLogger(__name__)

DIAS_SEMANA = {
    "segunda": 0,
    "terca": 1,
    "quarta": 2,
    "quinta": 3,
    "sexta": 4,
    "sabado": 5,
    "domingo": 6,
}


def get_next_date_for_weekday(dia_str: str) -> date:
    """Retorna a proxima data correspondente ao dia da semana."""
    today = date.today()
    target_weekday = DIAS_SEMANA.get(dia_str.lower(), 0)
    days_ahead = target_weekday - today.weekday()
    if days_ahead < 0:
        days_ahead += 7
    return today + timedelta(days=days_ahead)


async def get_scheduled_events(dia: str) -> Dict[int, int]:
    """
    Busca eventos no Google Calendar para o dia da semana especificado
    e retorna um dicionario de {hora: numero_de_eventos}.
    """
    if not settings.google_calendar_id or not settings.google_calendar_api_key:
        return {}

    target_date = get_next_date_for_weekday(dia)

    time_min = f"{target_date.isoformat()}T00:00:00Z"
    time_max = f"{target_date.isoformat()}T23:59:59Z"

    url = f"https://www.googleapis.com/calendar/v3/calendars/{settings.google_calendar_id}/events"
    params = {
        "key": settings.google_calendar_api_key,
        "timeMin": time_min,
        "timeMax": time_max,
        "singleEvents": "true",
        "orderBy": "startTime",
    }

    scheduled_per_hour = {}
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(url, params=params)
            resp.raise_for_status()
            data = resp.json()

            for item in data.get("items", []):
                start = item.get("start", {})
                end = item.get("end", {})
                start_dt_str = start.get("dateTime")
                end_dt_str = end.get("dateTime")

                if start_dt_str and end_dt_str:
                    try:
                        # Ex: 2023-10-10T14:30:00-03:00
                        start_dt = datetime.fromisoformat(start_dt_str.replace("Z", "+00:00"))
                        end_dt = datetime.fromisoformat(end_dt_str.replace("Z", "+00:00"))

                        start_hour = start_dt.hour
                        # Se o evento termina em hora exata (ex: 15:00), nao deve bloquear a hora 15
                        # A menos que o inicio tambem seja 15
                        end_hour = end_dt.hour
                        if end_dt.minute == 0 and end_dt.second == 0 and end_hour > start_hour:
                            end_hour -= 1

                        for h in range(start_hour, end_hour + 1):
                            scheduled_per_hour[h] = scheduled_per_hour.get(h, 0) + 1
                    except ValueError:
                        pass
    except Exception as e:
        logger.error(f"Erro ao buscar Google Calendar API: {e}")

    return scheduled_per_hour
