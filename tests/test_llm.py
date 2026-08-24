"""Tests for the agentic engine LLM client and agent LLM integration.

Covers:
  • LLMConfig env parsing (set / unset / defaults)
  • LLMClient.complete / complete_json (mocked httpx — no network)
  • Agent LLM path (mocked LLM response) and heuristic fallback on failure
  • run_blocking sync/async context handling
  • GET /api/agentic/llm/status

No test requires a real API key: the key env is monkeypatched per test.
"""

import json
from types import SimpleNamespace

import httpx
import pytest


# ─── Helpers ──────────────────────────────────

def _fake_response(content: str, status_code: int = 200, body: dict | None = None) -> httpx.Response:
    """Build a canned httpx.Response for a chat completion."""
    if body is None:
        body = {
            "choices": [
                {"message": {"role": "assistant", "content": content}}
            ]
        }
    response = httpx.Response(
        status_code=status_code,
        content=json.dumps(body).encode(),
        request=httpx.Request("POST", "http://test/chat/completions"),
    )
    return response


@pytest.fixture
def llm_env(monkeypatch):
    """Set a fake LLM key + defaults; restored automatically by monkeypatch."""
    monkeypatch.setenv("DAP_LLM_API_KEY", "test-key")
    monkeypatch.setenv("DAP_LLM_BASE_URL", "http://llm.local/v1")
    monkeypatch.setenv("DAP_LLM_MODEL", "test-model")
    monkeypatch.delenv("DAP_LLM_TIMEOUT", raising=False)
    monkeypatch.delenv("DAP_LLM_MAX_TOKENS", raising=False)


def _clear_llm_env(monkeypatch):
    monkeypatch.delenv("DAP_LLM_API_KEY", raising=False)
    monkeypatch.delenv("DAP_LLM_BASE_URL", raising=False)
    monkeypatch.delenv("DAP_LLM_MODEL", raising=False)
    monkeypatch.delenv("DAP_LLM_TIMEOUT", raising=False)
    monkeypatch.delenv("DAP_LLM_MAX_TOKENS", raising=False)


# ─── LLMConfig ──────────────────────────────────

def test_config_defaults_without_key(monkeypatch):
    _clear_llm_env(monkeypatch)
    from src.agentic.llm import LLMConfig

    config = LLMConfig.from_env()
    assert config.api_key == ""
    assert config.base_url == "https://api.openai.com/v1"
    assert config.model == "gpt-4o-mini"
    assert config.timeout_seconds == 60.0
    assert config.max_tokens == 4096


def test_config_reads_env(monkeypatch):
    _clear_llm_env(monkeypatch)
    monkeypatch.setenv("DAP_LLM_API_KEY", "sk-test")
    monkeypatch.setenv("DAP_LLM_BASE_URL", "http://ollama:11434/v1/")
    monkeypatch.setenv("DAP_LLM_MODEL", "llama3")
    monkeypatch.setenv("DAP_LLM_TIMEOUT", "5")
    monkeypatch.setenv("DAP_LLM_MAX_TOKENS", "128")

    from src.agentic.llm import LLMConfig

    config = LLMConfig.from_env()
    assert config.api_key == "sk-test"
    assert config.base_url == "http://ollama:11434/v1"  # trailing slash stripped
    assert config.model == "llama3"
    assert config.timeout_seconds == 5.0
    assert config.max_tokens == 128


def test_client_configured_flag(monkeypatch, llm_env):
    from src.agentic.llm import get_llm_client

    assert get_llm_client().is_configured is True
    _clear_llm_env(monkeypatch)
    assert get_llm_client().is_configured is False


# ─── LLMClient.complete / complete_json (mocked) ─────────────────────────

@pytest.mark.anyio
async def test_complete_returns_content(monkeypatch, llm_env):
    from src.agentic.llm import LLMClient

    async def fake_post(*args, **kwargs):
        return _fake_response('{"ok": true}')

    monkeypatch.setattr(httpx.AsyncClient, "post", fake_post)

    client = LLMClient()
    content = await client.complete("system prompt", "user prompt")
    assert content == '{"ok": true}'


@pytest.mark.anyio
async def test_complete_unconfigured_raises(monkeypatch):
    from src.agentic.llm import LLMClient, LLMError

    _clear_llm_env(monkeypatch)
    client = LLMClient()
    with pytest.raises(LLMError, match="not configured"):
        await client.complete("s", "u")


@pytest.mark.anyio
async def test_complete_http_error_raises(monkeypatch, llm_env):
    from src.agentic.llm import LLMClient, LLMError

    async def fake_post(*args, **kwargs):
        return _fake_response("Internal Server Error", status_code=500)

    monkeypatch.setattr(httpx.AsyncClient, "post", fake_post)

    client = LLMClient()
    with pytest.raises(LLMError, match="500"):
        await client.complete("s", "u")


@pytest.mark.anyio
async def test_complete_bad_shape_raises(monkeypatch, llm_env):
    from src.agentic.llm import LLMClient, LLMError

    async def fake_post(*args, **kwargs):
        return _fake_response("nope", body={"unexpected": True})

    monkeypatch.setattr(httpx.AsyncClient, "post", fake_post)

    client = LLMClient()
    with pytest.raises(LLMError):
        await client.complete("s", "u")


@pytest.mark.anyio
async def test_complete_json_strips_fences(monkeypatch, llm_env):
    from src.agentic.llm import LLMClient

    fenced = '```json\n{"error_type": "TypeError"}\n```'

    async def fake_post(*args, **kwargs):
        return _fake_response(fenced)

    monkeypatch.setattr(httpx.AsyncClient, "post", fake_post)

    client = LLMClient()
    data = await client.complete_json("s", "u")
    assert data == {"error_type": "TypeError"}


@pytest.mark.anyio
async def test_complete_json_invalid_json_raises(monkeypatch, llm_env):
    from src.agentic.llm import LLMClient, LLMError

    async def fake_post(*args, **kwargs):
        return _fake_response("not json at all")

    monkeypatch.setattr(httpx.AsyncClient, "post", fake_post)

    client = LLMClient()
    with pytest.raises(LLMError, match="invalid JSON"):
        await client.complete_json("s", "u")


@pytest.mark.anyio
async def test_json_mode_sends_response_format(monkeypatch, llm_env):
    from src.agentic.llm import LLMClient

    captured = {}

    async def fake_post(*args, **kwargs):
        captured["payload"] = kwargs.get("json")
        return _fake_response("{}")

    monkeypatch.setattr(httpx.AsyncClient, "post", fake_post)

    client = LLMClient()
    await client.complete("s", "u", json_mode=True)
    assert captured["payload"]["response_format"] == {"type": "json_object"}


# ─── Agent LLM integration ──────────────────────────────────

@pytest.mark.anyio
async def test_debugger_uses_llm_when_configured(monkeypatch, llm_env):
    from src.agentic.debugger import DebuggerAgent

    llm_json = {
        "error_type": "ValueError",
        "diagnosis": "The model returned a value in the wrong range.",
        "root_cause": "Unvalidated user input.",
        "fix_suggestion": "Validate the value before use.",
        "example": "fixed",
    }

    async def fake_post(*args, **kwargs):
        return _fake_response(json.dumps(llm_json))

    monkeypatch.setattr(httpx.AsyncClient, "post", fake_post)

    result = await DebuggerAgent().execute_async("req-x", "value out of range")
    assert result["engine"] == "llm"
    assert result["error_type"] == "ValueError"
    assert result["fix_suggestion"] == "Validate the value before use."


@pytest.mark.anyio
async def test_debugger_falls_back_on_llm_failure(monkeypatch, llm_env):
    from src.agentic.debugger import DebuggerAgent

    async def fake_post(*args, **kwargs):
        return _fake_response("boom", status_code=500)

    monkeypatch.setattr(httpx.AsyncClient, "post", fake_post)

    result = await DebuggerAgent().execute_async("req-x", "I got a TypeError: int() argument")
    assert result["engine"] == "heuristic"
    assert result["error_type"] == "TypeError"


@pytest.mark.anyio
async def test_debugger_heuristic_when_unconfigured(monkeypatch):
    _clear_llm_env(monkeypatch)
    from src.agentic.debugger import DebuggerAgent

    result = await DebuggerAgent().execute_async("req-x", "KeyError: 'missing'")
    assert result["engine"] == "heuristic"
    assert result["error_type"] == "KeyError"


@pytest.mark.anyio
async def test_architect_uses_llm_when_configured(monkeypatch, llm_env):
    from src.agentic.code_architect import CodeArchitectAgent

    llm_json = {
        "project_type": "REST API",
        "tech_stack": ["Python", "FastAPI"],
        "files": [
            {"path": "/workspace/app/main.py", "description": "entry"},
            {"path": "/workspace/app/routes.py", "description": "routes"},
            {"path": "/workspace/app/models.py", "description": "models"},
            "not-a-dict",
        ],
    }

    async def fake_post(*args, **kwargs):
        return _fake_response(json.dumps(llm_json))

    monkeypatch.setattr(httpx.AsyncClient, "post", fake_post)

    result = await CodeArchitectAgent().execute_async("req-x", "build a REST API for users")
    assert result["engine"] == "llm"
    assert result["project_type"] == "REST API"
    assert result["files_created"] == [
        "/workspace/app/main.py",
        "/workspace/app/routes.py",
        "/workspace/app/models.py",
    ]


@pytest.mark.anyio
async def test_test_generator_uses_llm_when_configured(monkeypatch, llm_env):
    from src.agentic.test_generator import TestGeneratorAgent

    llm_json = {
        "test_type": "Unit",
        "unit_tests": [
            {"name": "test_add_happy", "description": "d", "assertion": "a", "setup": "s"},
            {"name": "test_add_edge", "description": "d", "assertion": "a", "setup": "s"},
        ],
        "integration_tests": [],
    }

    async def fake_post(*args, **kwargs):
        return _fake_response(json.dumps(llm_json))

    monkeypatch.setattr(httpx.AsyncClient, "post", fake_post)

    result = await TestGeneratorAgent().execute_async("req-x", "write tests for add")
    assert result["engine"] == "llm"
    assert result["tests_generated"] == 2
    assert len(result["test_cases"]) == 2
    assert result["test_cases"][0]["name"] == "test_add_happy"


@pytest.mark.anyio
async def test_test_generator_rejects_invalid_type(monkeypatch, llm_env):
    from src.agentic.test_generator import TestGeneratorAgent

    llm_json = {"test_type": "Chaos", "unit_tests": [], "integration_tests": []}

    async def fake_post(*args, **kwargs):
        return _fake_response(json.dumps(llm_json))

    monkeypatch.setattr(httpx.AsyncClient, "post", fake_post)

    # Invalid LLM output must fall back to heuristics, not propagate
    result = await TestGeneratorAgent().execute_async("req-x", "write unit tests for parse")
    assert result["engine"] == "heuristic"


# ─── Orchestrator async path ──────────────────────────────────

@pytest.mark.anyio
async def test_orchestrator_execute_async_heuristic(monkeypatch):
    _clear_llm_env(monkeypatch)
    from src.agentic.agent_orchestrator import AgenticAIOrchestrator

    result = await AgenticAIOrchestrator().execute_async("req-1", "fix this error in my code")
    assert result["status"] == "completed"
    assert result["agent_type"] == "DEBUGGER"
    assert result["result"]["engine"] == "heuristic"


# ─── run_blocking ──────────────────────────────────

def test_run_blocking_inline_without_loop():
    from src.agentic.llm import run_blocking

    assert run_blocking(lambda: 21 * 2) == 42


@pytest.mark.anyio
async def test_run_blocking_in_worker_thread():
    from src.agentic.llm import run_blocking

    assert run_blocking(lambda: 21 * 2) == 42


# ─── API: /llm/status + /run ──────────────────────────────────

@pytest.mark.anyio
async def test_llm_status_endpoint_unconfigured(monkeypatch):
    _clear_llm_env(monkeypatch)
    import os
    import sys

    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    sys.path.insert(0, project_root)

    from httpx import AsyncClient, ASGITransport
    from src.main import app as main_app

    client = AsyncClient(transport=ASGITransport(app=main_app), base_url="http://test")
    resp = await client.get("/api/agentic/llm/status")
    await client.aclose()

    assert resp.status_code == 200
    data = resp.json()
    assert data["configured"] is False
    assert data["engine"] == "heuristic"


@pytest.mark.anyio
async def test_llm_status_endpoint_configured(monkeypatch, llm_env):
    import os
    import sys

    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    sys.path.insert(0, project_root)

    from httpx import AsyncClient, ASGITransport
    from src.main import app as main_app

    client = AsyncClient(transport=ASGITransport(app=main_app), base_url="http://test")
    resp = await client.get("/api/agentic/llm/status")
    await client.aclose()

    assert resp.status_code == 200
    data = resp.json()
    assert data["configured"] is True
    assert data["engine"] == "llm"
    assert data["model"] == "test-model"


@pytest.mark.anyio
async def test_run_endpoint_engine_field_heuristic(monkeypatch):
    _clear_llm_env(monkeypatch)
    import os
    import sys

    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    sys.path.insert(0, project_root)

    from httpx import AsyncClient, ASGITransport
    from src.main import app as main_app

    client = AsyncClient(transport=ASGITransport(app=main_app), base_url="http://test")
    resp = await client.post(
        "/api/agentic/run",
        json={"sandbox_id": "sb-1", "query": "build a REST API for users"},
    )
    await client.aclose()

    assert resp.status_code == 200
    data = resp.json()
    assert data["agent_type"] == "CODE_ARCHITECT"
    assert data["result"]["engine"] == "heuristic"
