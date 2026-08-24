"""Plugin Registry — Tool Discovery and Management

Discovers, validates, and registers plugins from built-in directories.
Includes the core agentic AI agents (Code Architect, Debugger, Test Generator).
"""

from typing import Dict, List, Optional
import logging
import os
import sys

logger = logging.getLogger(__name__)


class BasePlugin:
    """Common base for all plugins."""

    def __init__(self, name: str, version: str):
        self.name = name
        self.version = version

    @abstractmethod
    def get_tools(self) -> List[Dict[str, Any]]:
        """Return list of tools this plugin provides."""

    def __repr__(self) -> str:
        return f"<Plugin {self.name} v{self.version}>"


class BaseAgent(BasePlugin):
    """Common base for all agentic AI agents."""

    def __init__(self, name: str, version: str = "1.0.0"):
        super().__init__(name, version)

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


class PluginRegistry:
    """Discovers, validates, and registers plugins.

    Plugins are loaded from multiple sources:
    1. Built-in (shipped with the platform)
    2. Community plugins (~/.dap/plugins/)
    3. Enterprise plugins (signed, custom paths)
    """

    def __init__(self):
        self._plugins: Dict[str, BasePlugin] = {}

    def discover_plugins(self) -> List[BasePlugin]:
        """Discover plugins from all configured directories."""

        # 1. Load built-in plugins
        builtin_plugins = self._load_builtin_plugins()

        # 2. Load community plugins (~/.dap/plugins/)
        community_plugins = self._load_community_plugins()

        # 3. Load enterprise plugins (from config)
        enterprise_plugins = self._load_enterprise_plugins()

        all_plugins = builtin_plugins + community_plugins + enterprise_plugins
        return all_plugins

    def register_all(self, plugins: List[BasePlugin]) -> int:
        """Register all discovered plugins. Returns count registered."""
        for plugin in plugins:
            try:
                self.register(plugin)
            except Exception as e:
                logger.error("Failed to register plugin %s: %s", plugin.name, e)

        return len(self._plugins)

    def register(self, plugin: BasePlugin) -> bool:
        """Register a single plugin."""
        # Validate required attributes exist
        if not hasattr(plugin, 'name') or not plugin.name:
            raise ValueError("Plugin must have a name")

        if not hasattr(plugin, 'version') or not plugin.version:
            raise ValueError("Plugin must have a version")

        self._plugins[plugin.name] = plugin
        logger.info("Registered plugin: %s v%s", plugin.name, plugin.version)
        return True

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
        logger.warning("No plugin found for tool: %s", tool_name)
        return None

    def _load_builtin_plugins(self) -> List[BasePlugin]:
        """Load built-in plugins (shipped with platform)."""

        # Import core agentic AI agents
        from .code_architect import CodeArchitectAgent
        from .debugger import DebuggerAgent
        from .test_generator import TestGeneratorAgent

        return [
            CodeArchitectAgent(),
            DebuggerAgent(),
            TestGeneratorAgent(),
        ]

    def _load_community_plugins(self) -> List[BasePlugin]:
        """Load community plugins from ~/.dap/plugins/."""
        import os
        community_dir = os.path.expanduser("~/.dap/plugins")
        if not os.path.exists(community_dir):
            return []

        plugins = []
        for entry in os.listdir(community_dir):
            if entry.endswith('.py'):
                plugin_path = os.path.join(community_dir, entry)
                try:
                    # Dynamically load plugin module
                    spec = __import__('importlib.util', fromlist=['specifier']).util.spec_from_file_location(
                        entry, plugin_path
                    )
                    if spec and spec.loader:
                        module = __import__('importlib.util', fromlist=['specifier']).util.module_from_spec(spec)
                        spec.loader.exec_module(module)

                        # Find plugin class in module
                        for attr_name in dir(module):
                            if not attr_name.startswith('_'):
                                cls = getattr(module, attr_name)
                                if issubclass(cls, BasePlugin):
                                    plugins.append(cls())
                except Exception as e:
                    logger.error("Failed to load community plugin %s: %s", entry, e)

        return plugins

    def _load_enterprise_plugins(self) -> List[BasePlugin]:
        """Load enterprise plugins (from config)."""
        # In production: load from configured paths
        return []

    def export(self) -> Dict[str, Any]:
        """Export all registered plugins as a dictionary."""
        result = {}
        for plugin in self._plugins.values():
            try:
                tools = plugin.get_tools()
                result[plugin.name] = {
                    "name": plugin.name,
                    "version": plugin.version,
                    "tools": tools,
                }
            except Exception as e:
                logger.error("Failed to export plugin %s: %s", plugin.name, e)

        return result


# ─── Convenience functions ──────────────────

def get_plugin_registry() -> PluginRegistry:
    """Get the default plugin registry (with built-in plugins loaded)."""
    registry = PluginRegistry()
    builtin_plugins = registry._load_builtin_plugins()
    registry.register_all(builtin_plugins)
    return registry
