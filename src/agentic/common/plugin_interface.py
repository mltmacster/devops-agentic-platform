"""Plugin Interface — Abstract Base for All Plugins

All plugins (development stacks, tools, integrations) must implement this interface.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List


class BasePlugin(ABC):
    """All plugins must implement this interface."""

    name: str = "base"
    version: str = "1.0.0"

    @abstractmethod
    def initialize(self, config: Dict[str, Any]) -> bool:
        """Initialize with platform config. Return False to fail gracefully."""
        ...

    @abstractmethod
    def get_tools(self) -> List[Dict[str, Any]]:
        """Return list of tools this plugin provides (for AI agent consumption)."""
        ...

    @abstractmethod
    def execute(self, tool_name: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a tool. Must validate params against schema."""
        ...

    @abstractmethod
    def health_check(self) -> Dict[str, Any]:
        """Return plugin health status."""
        ...


class StackModule(BasePlugin):
    """A full development stack (e.g., 'Python + FastAPI + SQLite')."""

    required_tools: List[str] = []

    @abstractmethod
    def provision(self, sandbox_id: str) -> bool:
        """Provision all required tools in a sandbox instance."""
        ...


# ============================================================
# Example: Python Stack Plugin
# ============================================================

class PythonStack(StackModule):
    """Python 3.12 + FastAPI + SQLite development stack."""

    name = "python"
    version = "1.0.0"
    required_tools = ["git", "python3", "pip", "fastapi", "uvicorn", "sqlite3"]

    def initialize(self, config: Dict[str, Any]) -> bool:
        logger = logging.getLogger(__name__)
        logger.info("Initializing Python stack plugin")
        return True

    def get_tools(self) -> List[Dict[str, Any]]:
        return [
            {
                "name": "python_run",
                "description": "Run a Python script in the sandbox",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "file_path": {"type": "string", "description": "Path to Python file"},
                        "args": {"type": "array", "items": {"type": "string"}},
                    },
                },
            },
            {
                "name": "pip_install",
                "description": "Install a Python package via pip",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "package": {"type": "string", "description": "Package name"},
                    },
                },
            },
        ]

    def execute(self, tool_name: str, params: Dict[str, Any]) -> Dict[str, Any]:
        # In production: call sandbox shell to execute the tool
        return {"status": "ok", "tool": tool_name}

    def health_check(self) -> Dict[str, Any]:
        return {"healthy": True, "python_version": "3.12"}

    def provision(self, sandbox_id: str) -> bool:
        # In production: install Python stack in the sandbox
        return True


# ============================================================
# Example: Rust Stack Plugin
# ============================================================

class RustStack(StackModule):
    """Rust 1.70+ + Cargo + Actix development stack."""

    name = "rust"
    version = "1.0.0"
    required_tools = ["git", "rustc", "cargo", "actix-web"]

    def initialize(self, config: Dict[str, Any]) -> bool:
        logger = logging.getLogger(__name__)
        logger.info("Initializing Rust stack plugin")
        return True

    def get_tools(self) -> List[Dict[str, Any]]:
        return [
            {
                "name": "rust_build",
                "description": "Build a Rust project with cargo build",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "project_path": {"type": "string"},
                    },
                },
            },
        ]

    def execute(self, tool_name: str, params: Dict[str, Any]) -> Dict[str, Any]:
        return {"status": "ok", "tool": tool_name}

    def health_check(self) -> Dict[str, Any]:
        return {"healthy": True, "rust_version": "1.70"}

    def provision(self, sandbox_id: str) -> bool:
        return True


# ============================================================
# Example: ML/Data Stack Plugin
# ============================================================

class MLStack(StackModule):
    """Python + pgVector 0.8.0 + Ollama + LangGraph ML stack."""

    name = "ml"
    version = "1.0.0"
    required_tools = [
        "python3", "pip", "pgvector", "ollama", "langgraph",
        "pandas", "numpy", "scikit-learn"
    ]

    def initialize(self, config: Dict[str, Any]) -> bool:
        logger = logging.getLogger(__name__)
        logger.info("Initializing ML stack plugin")
        return True

    def get_tools(self) -> List[Dict[str, Any]]:
        return [
            {
                "name": "ollama_generate",
                "description": "Generate text using Ollama LLM",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "model": {"type": "string"},
                        "prompt": {"type": "string"},
                    },
                },
            },
        ]

    def execute(self, tool_name: str, params: Dict[str, Any]) -> Dict[str, Any]:
        return {"status": "ok", "tool": tool_name}

    def health_check(self) -> Dict[str, Any]:
        return {"healthy": True}

    def provision(self, sandbox_id: str) -> bool:
        return True


# ============================================================
# Plugin Registry (simple in-memory implementation)
# ============================================================

class PluginRegistry:
    """Discovers and registers plugins."""

    def __init__(self):
        self._plugins: Dict[str, BasePlugin] = {}

    def register(self, plugin: BasePlugin) -> None:
        """Register a plugin by name."""
        self._plugins[plugin.name] = plugin

    def get(self, name: str) -> Optional[BasePlugin]:
        """Get a plugin by name."""
        return self._plugins.get(name)

    def list_plugins(self) -> List[BasePlugin]:
        """List all registered plugins."""
        return list(self._plugins.values())

    def get_all_tools(self) -> List[Dict[str, Any]]:
        """Get all tools from all plugins."""
        tools = []
        for plugin in self._plugins.values():
            try:
                tools.extend(plugin.get_tools())
            except Exception as e:
                logger.error("Failed to get tools from %s: %s", plugin.name, e)
        return tools

    def resolve(self, tool_name: str) -> Optional[BasePlugin]:
        """Find which plugin provides a given tool."""
        for plugin in self._plugins.values():
            tools = plugin.get_tools()
            for tool in tools:
                if tool["name"] == tool_name:
                    return plugin
        return None


# Initialize with default plugins
_DEFAULT_REGISTRY = PluginRegistry()
_DEFAULT_REGISTRY.register(PythonStack())
_DEFAULT_REGISTRY.register(RustStack())
_DEFAULT_REGISTRY.register(MLStack())


def get_plugin_registry() -> PluginRegistry:
    """Get the default plugin registry (with built-in stacks)."""
    return _DEFAULT_REGISTRY
