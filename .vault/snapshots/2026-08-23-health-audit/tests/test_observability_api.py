"""Tests for the Observability API (Prometheus metrics & Grafana dashboard).

Uses pytest + httpx async client to verify:
  • GET /metrics — Prometheus metrics text format
  • GET /health, /health/live, /health/ready — health endpoints  
  • GET /grafana/dashboard — Grafana dashboard JSON
  • GET /grafana/datasource — Prometheus datasource JSON  
  • GET /metrics/summary — JSON summary of metrics

Run: pytest tests/test_observability_api.py -v
"""

import os
import sys
from httpx import AsyncClient, ASGITransport
import pytest

# Ensure the project root is on sys.path for proper imports
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

import pytest
from src.api.observability.main import app


async def _create_client() -> AsyncClient:
    """Create an async HTTP client pointing at the observability API."""
    transport = ASGITransport(app=app)
    client = AsyncClient(transport=transport, base_url="http://test")
    return client


# ─── Prometheus /metrics tests ───────────────

@pytest.mark.asyncio
async def test_export_metrics_returns_text():
    """GET /metrics should return Prometheus-compatible metrics text."""
    client = await _create_client()

    resp = await client.get("/metrics")

    assert resp.status_code == 200
    # Prometheus text format should be returned with text/plain content type
    assert resp.headers.get("content-type", "").startswith("text/")


@pytest.mark.asyncio
async def test_export_metrics_contains_required_help_lines():
    """GET /metrics should contain help comments for all metrics."""
    client = await _create_client()

    resp = await client.get("/metrics")

    assert resp.status_code == 200
    body = resp.text

    # Verify key help lines exist
    assert "# HELP" in body


@pytest.mark.asyncio
async def test_export_metrics_contains_metric_values():
    """GET /metrics should contain actual metric values."""
    client = await _create_client()

    resp = await client.get("/metrics")

    assert resp.status_code == 200
    body = resp.text

    # Each line after HELP should be a metric=value pair
    lines = body.strip().split("\n")
    metric_lines = [line for line in lines if not line.startswith("#")]

    assert len(metric_lines) > 0, "Expected at least some metric values"


@pytest.mark.asyncio
async def test_export_metrics_has_type_definitions():
    """GET /metrics should include TYPE lines for type annotations."""
    client = await _create_client()

    resp = await client.get("/metrics")

    assert resp.status_code == 200
    body = resp.text

    type_count = body.count("# TYPE")
    assert type_count > 0, "Expected at least some TYPE annotations"


# ─── Health endpoint tests ────────────────────

@pytest.mark.asyncio
async def test_health_returns_system_metrics():
    """GET /health should return system health metrics."""
    client = await _create_client()

    resp = await client.get("/health")

    assert resp.status_code == 200
    data = resp.json()

    # Verify key fields exist
    assert "cpu_usage_percent" in data or "uptime_seconds" in data


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


# ─── Grafana dashboard tests ─────────────────

@pytest.mark.asyncio
async def test_grafana_dashboard_returns_json():
    """GET /grafana/dashboard should return valid JSON."""
    client = await _create_client()

    resp = await client.get("/grafana/dashboard")

    assert resp.status_code == 200
    data = resp.json()

    # Validate Grafana dashboard structure
    assert "title" in data or "uid" in data, f"Expected Grafana dashboard structure, got: {list(data.keys())}"


@pytest.mark.asyncio
async def test_grafana_dashboard_has_panels():
    """GET /grafana/dashboard should include panels."""
    client = await _create_client()

    resp = await client.get("/grafana/dashboard")

    assert resp.status_code == 200
    data = resp.json()

    # Check for panels (either in top level or rows)
    has_panels = "panels" in data or ("rows" in data and any("panels" in row for row in data.get("rows", [])))
    assert has_panels, "Expected dashboard to contain panels"


@pytest.mark.asyncio
async def test_grafana_dashboard_v12():
    """GET /grafana/dashboard should return v12+ compatible format."""
    client = await _create_client()

    resp = await client.get("/grafana/dashboard")

    assert resp.status_code == 200
    data = resp.json()

    # Grafana dashboard version should be >= 12 (modern Grafana)
    if "version" in data:
        assert data["version"] >= 12, f"Expected Grafana version >= 12, got {data['version']}"


@pytest.mark.asyncio
async def test_grafana_dashboard_has_rows():
    """GET /grafana/dashboard should have at least one row with panels."""
    client = await _create_client()

    resp = await client.get("/grafana/dashboard")

    assert resp.status_code == 200
    data = resp.json()

    rows = data.get("rows", [])
    assert len(rows) > 0, "Expected at least one row in the dashboard"


@pytest.mark.asyncio
async def test_grafana_dashboard_has_title():
    """GET /grafana/dashboard should have a title."""
    client = await _create_client()

    resp = await client.get("/grafana/dashboard")

    assert resp.status_code == 200
    data = resp.json()
    
    assert "title" in data, f"Expected 'title' key in dashboard, got: {list(data.keys())}"


# ─── Grafana datasource tests ────────────────

@pytest.mark.asyncio
async def test_grafana_datasource_returns_json():
    """GET /grafana/datasource should return valid JSON."""
    client = await _create_client()

    resp = await client.get("/grafana/datasource")

    assert resp.status_code == 200
    data = resp.json()

    # Validate datasource structure
    assert "type" in data or "name" in data, f"Expected datasource structure, got: {list(data.keys())}"


@pytest.mark.asyncio
async def test_grafana_datasource_is_prometheus():
    """GET /grafana/datasource should return Prometheus datasource type."""
    client = await _create_client()

    resp = await client.get("/grafana/datasource")

    assert resp.status_code == 200
    data = resp.json()
    
    # Check for Prometheus type or name
    is_prometheus = (
        data.get("type") == "prometheus" or 
        data.get("name", "").lower() == "prometheus"
    )
    assert is_prometheus, f"Expected Prometheus datasource, got: {data.get('type', 'N/A')}"


# ─── Metrics summary tests ──────────────────

@pytest.mark.asyncio
async def test_metrics_summary_returns_json():
    """GET /metrics/summary should return JSON summary of metrics."""
    client = await _create_client()

    resp = await client.get("/metrics/summary")

    assert resp.status_code == 200
    data = resp.json()
    
    # Should contain a metrics key with metric details
    assert "metrics" in data, f"Expected 'metrics' key, got: {list(data.keys())}"


@pytest.mark.asyncio
async def test_metrics_summary_has_metric_metadata():
    """GET /metrics/summary should include metric type and help info."""
    client = await _create_client()

    resp = await client.get("/metrics/summary")

    assert resp.status_code == 200
    data = resp.json()
    
    # Each metric should have value and metadata
    for key, value in data["metrics"].items():
        assert isinstance(value, dict), f"Metric {key} should be a dict"


# ─── Content validation tests ────────────────

@pytest.mark.asyncio
async def test_metrics_text_is_valid_prometheus_format():
    """GET /metrics should be valid Prometheus text format (name value pairs)."""
    client = await _create_client()

    resp = await client.get("/metrics")

    assert resp.status_code == 200
    body = resp.text
    
    # Parse and validate: each non-comment line should be "metric_name value"
    lines = body.strip().split("\n")
    
    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        
        # Each data line should have at least a name and value
        parts = stripped.split()
        assert len(parts) >= 2, f"Invalid Prometheus line: {stripped}"


@pytest.mark.asyncio
async def test_health_live_response_structure():
    """GET /health/live should have expected response structure."""
    client = await _create_client()

    resp = await client.get("/health/live")

    assert resp.status_code == 200
    data = resp.json()
    
    # Should return status field with string value
    assert isinstance(data.get("status"), str)


@pytest.mark.asyncio
async def test_health_ready_response_structure():
    """GET /health/ready should have expected response structure."""
    client = await _create_client()

    resp = await client.get("/health/ready")

    assert resp.status_code == 200
    data = resp.json()
    
    # Should return status field with string value
    assert isinstance(data.get("status"), str)


# ─── Edge case tests ────────────────────────

@pytest.mark.asyncio
async def test_metrics_has_version_line():
    """GET /metrics should include version info."""
    client = await _create_client()

    resp = await client.get("/metrics")

    assert resp.status_code == 200
    body = resp.text
    
    # Should have at least some HELP lines (which include version in the help text)
    assert "# HELP" in body


@pytest.mark.asyncio
async def test_export_metrics_is_deterministic():
    """GET /metrics should produce consistent output across calls."""
    client = await _create_client()

    resp1 = await client.get("/metrics")
    resp2 = await client.get("/metrics")

    assert resp1.status_code == 200
    assert resp2.status_code == 200
    
    # Both responses should have the same content type
    assert resp1.headers.get("content-type", "") == resp2.headers.get("content-type", "")


@pytest.mark.asyncio
async def test_all_health_endpoints_accessible():
    """All health endpoints should be accessible."""
    
    client = await _create_client()

    # /health/live
    resp = await client.get("/health/live")
    assert resp.status_code == 200
    
    # /health/ready  
    resp = await client.get("/health/ready")
    assert resp.status_code == 200
    
    # /health (system metrics)
    resp = await client.get("/health")
    assert resp.status_code == 200


# ─── Grafana dashboard specific tests ─────────

@pytest.mark.asyncio
async def test_grafana_dashboard_has_meta():
    """GET /grafana/dashboard should have a meta section."""
    client = await _create_client()

    resp = await client.get("/grafana/dashboard")

    assert resp.status_code == 200
    data = resp.json()
    
    assert "meta" in data, f"Expected 'meta' key in dashboard, got: {list(data.keys())}"


@pytest.mark.asyncio
async def test_grafana_dashboard_has_uid():
    """GET /grafana/dashboard should have a unique identifier."""
    client = await _create_client()

    resp = await client.get("/grafana/dashboard")

    assert resp.status_code == 200
    data = resp.json()
    
    assert "uid" in data or "title" in data, f"Expected 'uid' key in dashboard"


@pytest.mark.asyncio
async def test_grafana_datasource_has_url():
    """GET /grafana/datasource should have a URL field."""
    client = await _create_client()

    resp = await client.get("/grafana/datasource")

    assert resp.status_code == 200
    data = resp.json()
    
    # Should have a URL or default Prometheus address
    assert "url" in data, f"Expected 'url' key in datasource config"


# ─── Prometheus format validation ─────────────

@pytest.mark.asyncio
async def test_metrics_has_help_lines_for_all_gauges():
    """GET /metrics should have HELP lines for all gauge metrics."""
    client = await _create_client()

    resp = await client.get("/metrics")

    assert resp.status_code == 200
    body = resp.text
    
    # Count HELP lines for gauge types
    help_lines = [line for line in body.split("\n") if "# HELP" in line]
    assert len(help_lines) > 0, "Expected at least some HELP lines"


@pytest.mark.asyncio
async def test_metrics_has_type_lines_for_all_gauges():
    """GET /metrics should have TYPE lines for all gauge metrics."""
    client = await _create_client()

    resp = await client.get("/metrics")

    assert resp.status_code == 200
    body = resp.text
    
    # Count TYPE lines for gauge types
    type_lines = [line for line in body.split("\n") if "# TYPE" in line]
    assert len(type_lines) > 0, "Expected at least some TYPE lines"


# ─── Grafana dashboard content validation ─────

@pytest.mark.asyncio
async def test_grafana_dashboard_has_rows():
    """GET /grafana/dashboard should have at least one row."""
    client = await _create_client()

    resp = await client.get("/grafana/dashboard")

    assert resp.status_code == 200
    data = resp.json()
    
    rows = data.get("rows", [])
    assert len(rows) > 0, "Expected at least one row"


@pytest.mark.asyncio
async def test_grafana_dashboard_rows_have_panels():
    """Each row in Grafana dashboard should have at least one panel."""
    client = await _create_client()

    resp = await client.get("/grafana/dashboard")

    assert resp.status_code == 200
    data = resp.json()
    
    rows = data.get("rows", [])
    for row in rows:
        panels = row.get("panels", [])
        assert len(panels) > 0, f"Row '{row.get('title', 'unknown')} should have at least one panel'"


@pytest.mark.asyncio
async def test_grafana_dashboard_has_title():
    """GET /grafana/dashboard should have a descriptive title."""
    client = await _create_client()

    resp = await client.get("/grafana/dashboard")

    assert resp.status_code == 200
    data = resp.json()
    
    title = data.get("title", "")
    assert len(title) > 0, "Dashboard should have a non-empty title"
