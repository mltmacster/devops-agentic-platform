"""URL Formatting & Network Configuration — Centralized network utilities.

Provides:
- URL formatter for sandbox IDE endpoints (WebSocket + HTTP)  
- Network configuration management (base host, port mapping)
- Sandbox endpoint URL generation for external access

Usage:
    from src.network import NetworkConfig, build_ide_url
    
    # Build IDE WebSocket URL for external access
    url = build_ide_url(sandbox_id="abc123", base_host="sandbox.dap.io")
    print(url)  # ws://sandbox-abc123.sandbox.dap.io:8080/api/ide/ws/abc123
"""

from dataclasses import dataclass, field
from typing import Optional


@dataclass(frozen=True)
class NetworkConfig:
    """Network configuration for sandbox instances.

    All network-related settings are centralized here so that:
      - URL formatting is consistent across the platform
      - External access URLs are generated from a single source of truth
      - Sandbox instances can be accessed from any external address

    Attributes:
        base_host: Base hostname for all sandbox instances (e.g., "sandbox.dap.io")
        default_port: Default HTTP port for sandbox web stacks (e.g., 80)
        ide_base_port: Default WebSocket port for IDE connections (e.g., 8080)
        enable_https: Whether to use HTTPS instead of HTTP
    """

    base_host: str = "sandbox.dap.io"
    default_port: int = 80
    ide_base_port: int = 8080
    enable_https: bool = False

    @property
    def ide_scheme(self) -> str:
        """Return the scheme for IDE URLs (ws or wss)."""
        return "wss" if self.enable_https else "ws"

    @property
    def scheme(self) -> str:
        """Return the scheme for HTTP URLs (https or http)."""
        return "https" if self.enable_https else "http"


def build_ide_url(
    sandbox_id: str,
    base_host: str = "sandbox.dap.io",
    port: int = 8080,
    use_https: bool = False,
) -> str:
    """Build an IDE WebSocket URL for external access.

    This generates the full URL that a remote Monaco Editor instance would use
    to connect to this sandbox's IDE endpoint.

    Args:
        sandbox_id: The unique identifier for the sandbox instance.
        base_host: Base hostname (e.g., "sandbox.dap.io").
        port: Port for the IDE WebSocket server (default 8080).
        use_https: Whether to use wss:// instead of ws://.

    Returns:
        Full WebSocket URL for the sandbox's IDE endpoint.

    Example:
        >>> build_ide_url("abc123", "sandbox.dap.io")
        'ws://sandbox-abc123.sandbox.dap.io:8080/api/ide/ws/abc123'
    """

    scheme = "wss" if use_https else "ws"
    hostname = f"sandbox-{sandbox_id}.{base_host}"

    return f"{scheme}://{hostname}:{port}/api/ide/ws/{sandbox_id}"


def build_sandbox_http_url(
    sandbox_id: str,
    base_host: str = "sandbox.dap.io",
    port: int = 80,
    use_https: bool = False,
) -> str:
    """Build an HTTP URL for a sandbox's web stack.

    This generates the full URL that external clients would use to access
    a sandbox's web application.

    Args:
        sandbox_id: The unique identifier for the sandbox instance.
        base_host: Base hostname (e.g., "sandbox.dap.io").
        port: Port for the sandbox web stack (default 80).
        use_https: Whether to use https:// instead of http://.

    Returns:
        Full HTTP URL for the sandbox's web endpoint.

    Example:
        >>> build_sandbox_http_url("abc123", "sandbox.dap.io")
        'http://sandbox-abc123.sandbox.dap.io:80/'
    """

    scheme = "https" if use_https else "http"
    hostname = f"sandbox-{sandbox_id}.{base_host}"

    return f"{scheme}://{hostname}:{port}/"


def build_ide_config_urls(
    sandbox_id: str,
    base_host: str = "sandbox.dap.io",
    ide_port: int = 8080,
    web_port: int = 80,
    use_https: bool = False,
) -> dict[str, str]:
    """Build all IDE-related URLs for a sandbox instance.

    Generates the complete set of URLs needed to connect an external
    Monaco Editor to this sandbox's IDE endpoint.

    Args:
        sandbox_id: The unique identifier for the sandbox instance.
        base_host: Base hostname (e.g., "sandbox.dap.io").
        ide_port: Port for the IDE WebSocket server (default 8080).
        web_port: Port for the sandbox web stack (default 80).
        use_https: Whether to use HTTPS.

    Returns:
        Dictionary of URL names to URLs.

    Example:
        >>> urls = build_ide_config_urls("abc123")
        >>> urls["websocket"]
        'ws://sandbox-abc123.sandbox.dap.io:8080/api/ide/ws/abc123'
        >>> urls["web"]
        'http://sandbox-abc123.sandbox.dap.io:80/'
    """

    scheme = "https" if use_https else "http"
    id_scheme = "wss" if use_https else "ws"
    hostname = f"sandbox-{sandbox_id}.{base_host}"

    return {
        "websocket": f"{id_scheme}://{hostname}:{ide_port}/api/ide/ws/{sandbox_id}",
        "web": f"{scheme}://{hostname}:{web_port}/",
        "status": f"{scheme}://{hostname}:{ide_port}/api/ide/status/{sandbox_id}",
        "config": f"{scheme}://{hostname}:{ide_port}/api/ide/config",
    }


def format_sandbox_response_urls(
    sandbox_id: str,
    config: Optional[NetworkConfig] = None,
) -> dict[str, str]:
    """Add network URLs to a sandbox response.

    This function adds the full set of accessible URLs for a sandbox instance,
    making it immediately usable by external clients and IDEs.

    Args:
        sandbox_id: The unique identifier for the sandbox instance.
        config: Optional NetworkConfig to override default settings.

    Returns:
        Dictionary of URL names to URLs.

    Example:
        >>> urls = format_sandbox_response_urls("abc123")
        >>> print(urls["websocket"])
        'ws://sandbox-abc123.sandbox.dap.io:8080/api/ide/ws/abc123'
    """

    if config is None:
        config = NetworkConfig()

    return build_ide_config_urls(
        sandbox_id=sandbox_id,
        base_host=config.base_host,
        ide_port=config.ide_base_port,
        web_port=config.default_port,
        use_https=config.enable_https,
    )
