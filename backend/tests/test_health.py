"""Smoke tests for the API process health endpoint."""

import pytest
from backend.api.main import app
from httpx import ASGITransport, AsyncClient


@pytest.mark.asyncio
async def test_liveness_returns_ok() -> None:
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://forgejudge.test"
    ) as client:
        response = await client.get("/health/live")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
