"""Test suite for the Agentic AI Engine.

Tests:
  • Code Architect agent (scaffolding generation)
  • Debugger agent (error classification & fix suggestions)
  • Test Generator agent (test case generation)
  • Orchestrator (intent classification & routing)
"""

import pytest


# ─── Test Fixtures ──────────────

def test_code_architect():
    """Test the Code Architect agent."""
    from src.agentic.code_architect import CodeArchitectAgent

    agent = CodeArchitectAgent()
    
    # Test REST API scaffolding
    result = agent.execute("req-001", "Build me a REST API for a task manager")
    assert result["project_type"] == "REST API"
    assert len(result["files_created"]) > 0
    print(f"✅ Code Architect — REST API: {len(result['files_created'])} files")

    # Test Web Application scaffolding
    result = agent.execute("req-002", "Create a web application with React")
    assert result["project_type"] == "Web Application"
    print(f"✅ Code Architect — Web App: {len(result['files_created'])} files")

    # Test CLI Tool scaffolding
    result = agent.execute("req-003", "Write a command line tool for data processing")
    assert result["project_type"] == "CLI Tool"
    print(f"✅ Code Architect — CLI: {len(result['files_created'])} files")


def test_debugger():
    """Test the Debugger agent."""
    from src.agentic.debugger import DebuggerAgent

    agent = DebuggerAgent()
    
    # Test TypeError detection
    result = agent.execute("req-01", "I got a TypeError: int() argument")
    assert result["error_type"] == "TypeError"
    print(f"✅ Debugger — TypeError: {result['diagnosis']}")

    # Test KeyError detection
    result = agent.execute("req-02", "KeyError: 'missing_key' not in dictionary")
    assert result["error_type"] == "KeyError"
    print(f"✅ Debugger — KeyError: {result['diagnosis']}")

    # Test ModuleNotFoundError detection
    result = agent.execute("req-03", "ModuleNotFoundError: No module named 'requests'")
    assert result["error_type"] == "ModuleNotFoundError"
    print(f"✅ Debugger — ModuleNotFoundError: {result['diagnosis']}")

    # Test ConnectionError detection
    result = agent.execute("req-04", "ConnectionError: connection refused to database")
    assert result["error_type"] == "ConnectionError"
    print(f"✅ Debugger — ConnectionError: {result['diagnosis']}")

    # Test Traceback detection
    result = agent.execute("req-05", "Traceback (most recent call last):...")
    assert result["error_type"] == "Traceback"
    print(f"✅ Debugger — Traceback: {result['diagnosis']}")


def test_test_generator():
    """Test the Test Generator agent."""
    from src.agentic.test_generator import TestGeneratorAgent

    agent = TestGeneratorAgent()
    
    # Test unit test generation
    result = agent.execute("req-10", "Write tests for the calculate_total function")
    assert result["tests_generated"] > 0
    print(f"✅ Test Generator — Unit tests: {len(result['unit_tests'])} unit tests")
    print(f"   - {result['unit_tests'][0]['name']}")

    # Test integration test generation
    result = agent.execute("req-11", "Write integration tests for the API endpoint")
    assert result["tests_generated"] > 0
    print(f"✅ Test Generator — Integration: {len(result['integration_tests'])} integration tests")

    # Test mixed test generation
    result = agent.execute("req-12", "Write tests for the data processing function")
    assert result["test_type"] == "Unit + Integration"
    print(f"✅ Test Generator — Mixed: {len(result['unit_tests'])} unit + {len(result['integration_tests'])} integration")


def test_orchestrator():
    """Test the Orchestrator (intent classification & routing)."""
    from src.agentic.agent_orchestrator import get_orchestrator

    orchestrator = get_orchestrator()
    
    # Test Code Architect routing
    result = orchestrator.execute("req-20", "Build a REST API for users")
    assert result["agent_type"] == "CODE_ARCHITECT"
    print(f"✅ Orchestrator — CODE_ARCHITECT: {result['agent_type']}")

    # Test Debugger routing
    result = orchestrator.execute("req-21", "Fix this TypeError in my function")
    assert result["agent_type"] == "DEBUGGER"
    print(f"✅ Orchestrator — DEBUGGER: {result['agent_type']}")

    # Test Test Generator routing
    result = orchestrator.execute("req-22", "Write tests for the login function")
    assert result["agent_type"] == "TEST_GENERATOR"
    print(f"✅ Orchestrator — TEST_GENERATOR: {result['agent_type']}")

    # Test available agents list
    agents = orchestrator.list_agents()
    assert len(agents) == 3
    print(f"✅ Orchestrator — {len(agents)} agents available")
