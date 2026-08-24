"""Plugin Interface — Common base for all agentic AI agents."""

from abc import ABC, abstractmethod
from typing import Dict, Any


class BaseAgent(ABC):
    """Abstract base class for all agentic AI agents.

    Every agent must implement `execute()` which receives a sandbox context
    and user query, then returns a structured result dict.

    Agents are stateless and can be executed in parallel for different
    workspaces/requests.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable agent name for logging / UI."""

    @abstractmethod
    def execute(self, request_id: str, query: str) -> Dict[str, Any]:
        """Execute the agent's core workflow.

        Args:
            request_id: Unique ID for this request (for tracing).
            query: User's natural-language input.

        Returns:
            Dict with agent-specific structured output.
        """

    def _format_result(self, result: Dict[str, Any]) -> str:
        """Format a result dict into human-readable text."""
        return str(result)
