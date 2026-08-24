"""Tests for the Agentic AI Engine — agent orchestration and API."""

import os
import sys
from httpx import AsyncClient, ASGITransport
import pytest

# Ensure the project root is on sys.path for proper imports
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from src.main import app as main_app
from src.agentic.agent_orchestrator import AgenticAIOrchestrator, AgentType


@pytest.mark.anyio
async def _get_client():
    """Create an async HTTP client pointing at the main app."""
    transport = ASGITransport(app=main_app)
    client = AsyncClient(transport=transport, base_url="http://test")
    return client


# ─── Agent Orchestrator Tests ──────────────

class TestAgentOrchestrator:
    """Tests for the AgenticAIOrchestrator class."""

    def test_intent_classification_debugging(self):
        """Debug queries should route to Debugger agent."""
        orchestrator = AgenticAIOrchestrator()
        result = orchestrator._classify_intent("fix this broken code")

        assert result == AgentType.DEBUGGER

    def test_intent_classification_test_generation(self):
        """Test generation queries should route to Test Generator."""
        orchestrator = AgenticAIOrchestrator()
        result = orchestrator._classify_intent("write tests for this module")

        assert result == AgentType.TEST_GENERATOR

    def test_intent_classification_code_architect(self):
        """Build/scaffold queries should route to Code Architect."""
        orchestrator = AgenticAIOrchestrator()
        result = orchestrator._classify_intent("build a REST API for users")

        assert result == AgentType.CODE_ARCHITECT

    def test_intent_classification_fallback(self):
        """Unknown queries should default to Code Architect."""
        orchestrator = AgenticAIOrchestrator()
        result = orchestrator._classify_intent("help me with the project")

        assert result == AgentType.CODE_ARCHITECT


# ─── Code Architect Agent Tests ──────────────

class TestCodeArchitectAgent:
    """Tests for the Code Architect agent."""

    def test_scaffold_rest_api(self):
        """Should generate REST API scaffold files."""
        from src.agentic.code_architect import CodeArchitectAgent

        agent = CodeArchitectAgent()
        result = agent.execute("req-1", "build a REST API for users")

        assert result["project_type"] == "REST API"
        assert "/workspace/app/main.py" in result["files_created"]

    def test_scaffold_web_app(self):
        """Should generate Web Application scaffold files."""
        from src.agentic.code_architect import CodeArchitectAgent

        agent = CodeArchitectAgent()
        result = agent.execute("req-2", "create a web application dashboard")

        assert result["project_type"] == "Web Application"
        assert "/workspace/app/src/index.tsx" in result["files_created"]

    def test_scaffold_cli(self):
        """Should generate CLI scaffold files."""
        from src.agentic.code_architect import CodeArchitectAgent

        agent = CodeArchitectAgent()
        result = agent.execute("req-3", "generate a CLI tool for backups")

        assert result["project_type"] == "CLI Tool"
        assert "/workspace/main.py" in result["files_created"]

    def test_scaffold_microservice(self):
        """Should generate microservice scaffold files."""
        from src.agentic.code_architect import CodeArchitectAgent

        agent = CodeArchitectAgent()
        result = agent.execute("req-4", "create a microservice for payments")

        assert result["project_type"] == "Microservice"
        assert "/workspace/app/services/health.py" in result["files_created"]


# ─── Debugger Agent Tests ──────────────

class TestDebuggerAgent:
    """Tests for the Debugger agent."""

    def test_classify_traceback(self):
        """Traceback errors should be classified as Traceback."""
        from src.agentic.debugger import DebuggerAgent

        agent = DebuggerAgent()
        error_type = agent._classify_error("got a traceback from my code")

        assert error_type == "Traceback"

    def test_classify_key_error(self):
        """Key errors should be classified as Key Error."""
        from src.agentic.debugger import DebuggerAgent

        agent = DebuggerAgent()
        error_type = agent._classify_error("got a key error on this dict")

        assert error_type == "Key Error"

    def test_classify_connection_error(self):
        """Connection errors should be classified as Connection Error."""
        from src.agentic.debugger import DebuggerAgent

        agent = DebuggerAgent()
        error_type = agent._classify_error("connection timed out")

        assert error_type == "Connection Error"

    def test_diagnose_error(self):
        """Should return a diagnosis with actionable fix."""
        from src.agentic.debugger import DebuggerAgent

        agent = DebuggerAgent()
        result = agent.execute("req-1", "fix this broken code")

        assert "error_type" in result
        assert "diagnosis" in result
        assert "fix_suggestion" in result


# ─── Test Generator Agent Tests ────────────

class TestTestGeneratorAgent:
    """Tests for the Test Generator agent."""

    def test_generate_unit_tests(self):
        """Should generate unit + integration test cases for simple functions."""
        from src.agentic.test_generator import TestGeneratorAgent

        agent = TestGeneratorAgent()
        result = agent.execute("req-1", "write tests for this function")

        # At least 3 unit test cases should be generated
        assert result["tests_generated"] >= 3
        assert len(result["test_cases"]) == result["tests_generated"]

    def test_generate_integration_tests(self):
        """Should generate integration test cases for API calls."""
        from src.agentic.test_generator import TestGeneratorAgent

        agent = TestGeneratorAgent()
        result = agent.execute("req-2", "test this API endpoint")

        # At least 2 integration test cases should be generated
        assert result["tests_generated"] >= 2
        assert len(result["test_cases"]) == result["tests_generated"]


# ─── API Endpoint Tests ──────────────

class TestAgenticAPI:
    """Tests for the /api/agentic API endpoints."""

    @pytest.mark.anyio
    async def test_health_live(self):
        """Health live endpoint should return alive status."""
        client = await _get_client()
        resp = await client.get("/api/agentic/health/live")
        assert resp.status_code == 200

    @pytest.mark.anyio
    async def test_health_ready(self):
        """Health ready endpoint should return ready status."""
        client = await _get_client()
        resp = await client.get("/api/agentic/health/ready")
        assert resp.status_code == 200

    @pytest.mark.anyio
    async def test_run_agentic_code_architect(self):
        """POST /agentic/run should route to Code Architect for scaffolding requests."""
        client = await _get_client()
        resp = await client.post(
            "/api/agentic/run",
            json={"sandbox_id": "test-sandbox-123", "query": "build a REST API for users"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["agent_type"] == "CODE_ARCHITECT"

    @pytest.mark.anyio
    async def test_run_agentic_debugger(self):
        """POST /agentic/run should route to Debugger for error reports."""
        client = await _get_client()
        resp = await client.post(
            "/api/agentic/run",
            json={"sandbox_id": "test-sandbox-123", "query": "fix this error, the code is broken"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["agent_type"] == "DEBUGGER"

    @pytest.mark.anyio
    async def test_run_agentic_test_generator(self):
        """POST /agentic/run should route to Test Generator for test requests."""
        client = await _get_client()
        resp = await client.post(
            "/api/agentic/run",
            json={"sandbox_id": "test-sandbox-123", "query": "write tests for this function"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["agent_type"] == "TEST_GENERATOR"

    @pytest.mark.anyio
    async def test_run_agentic_response_structure(self):
        """Response should have all required fields."""
        client = await _get_client()
        resp = await client.post(
            "/api/agentic/run",
            json={"sandbox_id": "test-sandbox-123", "query": "build me something"},
        )
        data = resp.json()

        assert "request_id" in data
        assert "status" in data
        assert "agent_type" in data
        assert "result" in data
