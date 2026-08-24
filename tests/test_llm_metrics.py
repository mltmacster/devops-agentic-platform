"""Tests for real LLM usage metrics wired into /metrics and /metrics/summary.

The LLMStats registry in src/agentic/llm.py is the single source of truth:
record real-looking calls and assert the observability endpoints reflect them.
"""

import os
import sys
from httpx import AsyncClient, ASGITransport

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

import pytest

from src.agentic.llm import get_llm_stats, reset_llm_stats
from src.api.observability.main import app


async def _client() -> AsyncClient:
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


@pytest.fixture(autouse=True)
def clean_stats():
    reset_llm_stats()
    yield
    reset_llm_stats()


def _record_calls():
    stats = get_llm_stats()
    stats.record_call(0.05, 100, 20, ok=True)
    stats.record_call(1.2, 50, 30, ok=True)
    stats.record_call(30.0, 10, 5, ok=False)


@pytest.mark.asyncio
async def test_metrics_zero_before_any_calls():
    client = await _client()
    resp = await client.get("/metrics")
    assert resp.status_code == 200
    body = resp.text
    assert "dap_ai_tokens_total 0" in body
    assert "dap_ai_requests_total 0" in body
    assert "dap_ai_latency_seconds_count 0" in body


@pytest.mark.asyncio
async def test_metrics_reflect_recorded_calls():
    _record_calls()
    client = await _client()
    resp = await client.get("/metrics")
    body = resp.text

    assert "dap_ai_tokens_total 215" in body  # (100+20) + (50+30) + (10+5)
    assert "dap_ai_requests_total 3" in body
    assert "dap_ai_latency_seconds_count 3" in body
    assert "dap_ai_latency_seconds_sum 31.2500" in body


@pytest.mark.asyncio
async def test_metrics_histogram_buckets():
    _record_calls()
    client = await _client()
    resp = await client.get("/metrics")
    body = resp.text

    # 0.05s -> all buckets; 1.2s -> buckets >= 5.0; 30s -> buckets >= 60.0
    assert "dap_ai_latency_seconds_bucket 0.1 1" in body
    assert "dap_ai_latency_seconds_bucket 0.5 1" in body
    assert "dap_ai_latency_seconds_bucket 1.0 1" in body
    assert "dap_ai_latency_seconds_bucket 5.0 2" in body
    assert "dap_ai_latency_seconds_bucket 10.0 2" in body
    assert "dap_ai_latency_seconds_bucket 60.0 3" in body
    assert "dap_ai_latency_seconds_bucket +Inf 3" in body


@pytest.mark.asyncio
async def test_metrics_summary_reflects_recorded_calls():
    _record_calls()
    client = await _client()
    resp = await client.get("/metrics/summary")
    assert resp.status_code == 200
    metrics = resp.json()["metrics"]
    assert metrics["dap_ai_tokens_total"]["value"] == 215
    assert metrics["dap_ai_requests_total"]["value"] == 3
    assert metrics["dap_ai_tokens_total"]["type"] == "counter"


@pytest.mark.asyncio
async def test_metrics_summary_zero_before_any_calls():
    client = await _client()
    resp = await client.get("/metrics/summary")
    metrics = resp.json()["metrics"]
    assert metrics["dap_ai_tokens_total"]["value"] == 0
    assert metrics["dap_ai_requests_total"]["value"] == 0
