import asyncio
from unittest.mock import AsyncMock, patch, MagicMock

async def run_test():
    with patch("app.api.v1.telegram._get_lgpd_consent", new=AsyncMock(return_value=True)):
        import pytest
        # Run pytest inside this block if needed, or simply run pytest with the proper patch directly
