"""Agentic AI Orchestrator — Multi-Agent Coordination

Routes user requests to appropriate agents, aggregates results.
"""

from enum import Enum, auto
from typing import Dict, List, Optional, Any
import logging

from .plugin_interface import BaseAgent

logger = logging.getLogger(__name__)


class AgentType(Enum):
    """Types of agentic AI agents."""
    CODE_ARCHITECT = auto()       # Plans and scaffolds code
    DEBUGGER = auto()             # Traces errors, suggests fixes
    TEST_GENERATOR = auto()       # Writes unit/integration tests


class AgenticAIOrchestrator:
    """Multi-agent AI orchestration layer.

    This is the brain of the agentic AI system. It receives user requests,
    parses intent, and routes to the appropriate agent(s).

    Architecture:
      User Request → Intent Classifier → Agent Router → Execution Engine → Response
    
    The orchestrator can:
      • Single-agent dispatch (most common)
      • Multi-agent collaboration (e.g., Architect + Test Generator)
      • Pipeline execution (debug → fix → test)
    """

    def __init__(self):
        self._active_agents: Dict[str, AgentType] = {}

        # Import agent classes here to avoid circular imports
        from .code_architect import CodeArchitectAgent
        from .debugger import DebuggerAgent
        from .test_generator import TestGeneratorAgent

        self._agents = {
            AgentType.CODE_ARCHITECT: CodeArchitectAgent(),
            AgentType.DEBUGGER: DebuggerAgent(),
            AgentType.TEST_GENERATOR: TestGeneratorAgent(),
        }

    def execute(self, request_id: str, user_query: str) -> Dict[str, Any]:
        """Execute a multi-agent workflow for the given request."""

        # 1. Parse intent
        agent_type = self._classify_intent(user_query)
        logger.info("Intent classified: %s for '%s'", agent_type.name, user_query[:50])

        # 2. Route to appropriate agent(s)
        result = self._execute_agent(agent_type, request_id, user_query)

        # 3. Return result to user
        return {
            "request_id": request_id,
            "status": "completed",
            "agent_type": agent_type.name,
            "result": result,
        }

    def _classify_intent(self, query: str) -> AgentType:
        """Classify the user's request into an agent type."""

        # Debugging intent — highest priority
        if any(kw in query.lower() for kw in [
            "debug", "fix this", "error", "broken", "doesn't work",
            "traceback", "exception", "bug", "crash", "not working",
            "can't find", "cannot import"
        ]):
            return AgentType.DEBUGGER

        # Test generation intent — second priority  
        if any(kw in query.lower() for kw in [
            "write tests", "test this", "add unit test", "integration test",
            "generate tests", "write a test"
        ]):
            return AgentType.TEST_GENERATOR

        # Default: code architect (scaffolding)
        if any(kw in query.lower() for kw in [
            "build", "create", "generate", "make a", "write code"
        ]):
            return AgentType.CODE_ARCHITECT

        # Default fallback
        return AgentType.CODE_ARCHITECT

    def _execute_agent(self, agent_type: AgentType, request_id: str, query: str) -> Dict[str, Any]:
        """Execute the appropriate agent for this request."""

        if agent_type not in self._agents:
            raise ValueError(f"Unknown agent type: {agent_type}")

        logger.info("Executing %s agent for request: %s", agent_type.name, query[:100])
        agent = self._agents[agent_type]
        return agent.execute(request_id, query)

    def get_agents(self) -> Dict[AgentType, BaseAgent]:
        """Get all registered agents."""
        return self._agents.copy()

    def list_agents(self) -> List[Dict[str, str]]:
        """List all available agents with their descriptions."""
        descriptions = {
            AgentType.CODE_ARCHITECT: "Plans and scaffolds application code from natural-language specs",
            AgentType.DEBUGGER: "Traces errors and suggests fixes for debugging issues",
            AgentType.TEST_GENERATOR: "Writes unit/integration tests from specifications or code",
        }
        return [
            {"type": agent_type.name, "description": desc}
            for agent_type, desc in descriptions.items()
        ]


def get_orchestrator() -> AgenticAIOrchestrator:
    """Factory function for the agentic AI orchestrator."""
    return AgenticAIOrchestrator()
