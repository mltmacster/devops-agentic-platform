"""Pytest configuration for DAP — enables asyncio mode and shared fixtures."""

import os

import pytest


# ─── Shared project path fixture ──────────────

@pytest.fixture(scope="session")
def project_root():
    """Return the absolute path to the DAP project root."""
    return os.path.dirname(os.path.abspath(__file__))


# ─── HTTP client fixtures for API tests ────────────────────────

@pytest.fixture(scope="module")
async def ide_client(project_root):
    """Async HTTP client pointing at the IDE API."""
    import sys

    sys.path.insert(0, project_root)

    from httpx import AsyncClient, ASGITransport
    from src.api.ide.main import app

    transport = ASGITransport(app=app)
    client = AsyncClient(transport=transport, base_url="http://test")
    yield client


@pytest.fixture(scope="module")
async def obs_client(project_root):
    """Async HTTP client pointing at the observability API."""
    import sys

    sys.path.insert(0, project_root)

    from httpx import AsyncClient, ASGITransport
    from src.api.observability.main import app

    transport = ASGITransport(app=app)
    client = AsyncClient(transport=transport, base_url="http://test")
    yield client
