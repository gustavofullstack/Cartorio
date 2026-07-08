import pytest
from unittest.mock import patch, MagicMock
from app.integrations.google_calendar import get_scheduled_events


@pytest.mark.asyncio
async def test_get_scheduled_events_no_credentials():
    with patch("app.integrations.google_calendar.settings") as mock_settings:
        mock_settings.google_calendar_id = None
        mock_settings.google_calendar_api_key = None

        result = await get_scheduled_events("segunda")
        assert result == {}


@pytest.mark.asyncio
async def test_get_scheduled_events_success():
    with (
        patch("app.integrations.google_calendar.settings") as mock_settings,
        patch("httpx.AsyncClient.get") as mock_get,
    ):
        mock_settings.google_calendar_id = "test_calendar_id"
        mock_settings.google_calendar_api_key = "test_api_key"

        mock_response = MagicMock()
        mock_response.json.return_value = {
            "items": [
                {
                    "start": {"dateTime": "2023-10-10T09:30:00-03:00"},
                    "end": {"dateTime": "2023-10-10T10:00:00-03:00"},  # Blocks only hour 9
                },
                {
                    "start": {"dateTime": "2023-10-10T10:00:00-03:00"},
                    "end": {"dateTime": "2023-10-10T12:00:00-03:00"},  # Blocks hours 10 and 11
                },
                {
                    "start": {"dateTime": "2023-10-10T14:30:00-03:00"},
                    "end": {"dateTime": "2023-10-10T16:30:00-03:00"},  # Blocks hours 14, 15, 16
                },
                {"start": {"date": "2023-10-10"}},  # All day event should not crash
            ]
        }

        async def mock_get_async(*args, **kwargs):
            return mock_response

        mock_get.side_effect = mock_get_async

        result = await get_scheduled_events("segunda")
        assert result == {9: 1, 10: 1, 11: 1, 14: 1, 15: 1, 16: 1}


@pytest.mark.asyncio
async def test_get_scheduled_events_error():
    with (
        patch("app.integrations.google_calendar.settings") as mock_settings,
        patch("httpx.AsyncClient.get") as mock_get,
    ):
        mock_settings.google_calendar_id = "test_calendar_id"
        mock_settings.google_calendar_api_key = "test_api_key"

        async def mock_get_async(*args, **kwargs):
            raise Exception("API Error")

        mock_get.side_effect = mock_get_async

        result = await get_scheduled_events("segunda")
        assert result == {}
