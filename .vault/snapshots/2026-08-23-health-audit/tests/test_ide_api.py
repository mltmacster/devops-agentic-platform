"""Tests for the IDE API (Monaco Editor + LSP).

Uses pytest + httpx async client to verify:
  • POST /config — editor configuration with validation
  • GET /lsp/capabilities — LSP capability advertisement  
  • GET /health/live and /health/ready — health probes

Run: pytest tests/test_ide_api.py -v
"""

import os
import sys
from httpx import AsyncClient, ASGITransport
import pytest

# Ensure the project root is on sys.path for proper imports
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

import pytest
from src.api.ide.main import app


async def _create_client() -> AsyncClient:
    """Create an async HTTP client pointing at the IDE API."""
    transport = ASGITransport(app=app)
    client = AsyncClient(transport=transport, base_url="http://test")
    return client


# ─── Configuration tests ──────────────────────

@pytest.mark.asyncio
async def test_configure_editor_dark_theme_python():
    """POST /config should accept dark theme and python language."""
    client = await _create_client()

    resp = await client.post(
        "/config",
        json={"theme": "dark", "language": "python"},
    )

    assert resp.status_code == 200
    data = resp.json()
    assert data["theme"] == "dark"
    assert data["language"] == "python"
    assert data["lsp_enabled"] is True


@pytest.mark.asyncio
async def test_configure_editor_with_extensions():
    """POST /config should accept a list of extensions."""
    client = await _create_client()

    extensions = ["eslint-plugin", "prettier", "debugger-extension"]

    resp = await client.post(
        "/config",
        json={"theme": "light", "language": "typescript", "extensions": extensions},
    )

    assert resp.status_code == 200
    data = resp.json()
    assert data["theme"] == "light"
    assert data["language"] == "typescript"
    assert data["extensions"] == extensions


@pytest.mark.asyncio
async def test_configure_editor_invalid_theme():
    """POST /config should reject an invalid theme."""
    client = await _create_client()

    resp = await client.post(
        "/config",
        json={"theme": "neon", "language": "python"},
    )

    assert resp.status_code == 400
    data = resp.json()
    assert "Invalid theme" in data["detail"]


@pytest.mark.asyncio
async def test_configure_editor_invalid_language():
    """POST /config should reject an invalid language."""
    client = await _create_client()

    resp = await client.post(
        "/config",
        json={"theme": "dark", "language": "ruby"},
    )

    assert resp.status_code == 400
    data = resp.json()
    assert "Invalid language" in data["detail"]


@pytest.mark.asyncio
async def test_configure_editor_all_supported_languages():
    """POST /config should accept all supported languages."""
    client = await _create_client()

    supported = ["python", "typescript", "javascript", "java", "rust", "go", "cpp", "csharp"]

    for lang in supported:
        resp = await client.post(
            "/config",
            json={"theme": "dark", "language": lang},
        )

        assert resp.status_code == 200, f"Failed for language: {lang}"


# ─── LSP tests ────────────────────────────────

@pytest.mark.asyncio
async def test_lsp_capabilities():
    """GET /lsp/capabilities should return supported LSP features."""
    client = await _create_client()

    resp = await client.get("/lsp/capabilities")

    assert resp.status_code == 200
    data = resp.json()
    assert "version" in data
    assert "capabilities" in data


@pytest.mark.asyncio
async def test_lsp_info():
    """GET /lsp/info should return server identity."""
    client = await _create_client()

    resp = await client.get("/lsp/info")

    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "DAP Language Server"
    assert data["version"] == "1.0.0"
    assert "python" in data["supportedLanguages"]


# ─── Health probe tests ──────────────────────

@pytest.mark.asyncio
async def test_health_live():
    """GET /health/live should return alive status."""
    client = await _create_client()

    resp = await client.get("/health/live")

    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "alive"


@pytest.mark.asyncio
async def test_health_ready():
    """GET /health/ready should return ready when service is initialized."""
    client = await _create_client()

    resp = await client.get("/health/ready")

    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ready"


# ─── Stats tests ──────────────────────────────

@pytest.mark.asyncio
async def test_stats():
    """GET /stats should return IDE service statistics."""
    client = await _create_client()

    resp = await client.get("/stats")

    assert resp.status_code == 200
    data = resp.json()
    assert "active_sessions" in data


# ─── Current config test ──────────────────────

@pytest.mark.asyncio
async def test_get_current_config():
    """GET /config/current should return the last applied config or defaults."""
    client = await _create_client()

    resp = await client.get("/config/current")

    assert resp.status_code == 200
    data = resp.json()
    assert "theme" in data
    assert "language" in data
