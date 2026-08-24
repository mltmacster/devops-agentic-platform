"""Network Module — Unified network utilities for the DAP platform.

Provides:
  • URL formatting for sandbox IDE endpoints (Phase 1)  
  • Public endpoint routing (Phase 5)
  • DNS configuration management (Phase 5)  
  • SSL/TLS certificate lifecycle management (Phase 5)

Usage:
    from src.network import NetworkConfig, build_ide_url, PublicEndpointRouter
    
    # Build IDE WebSocket URL for external access
    url = build_ide_url(sandbox_id="abc123", base_host="sandbox.dap.io")
    print(url)  # ws://sandbox-abc123.sandbox.dap.io:8080/api/ide/ws/abc123
"""

# Phase 1 — URL Formatting (from url_formatter.py)  
from src.network.url_formatter import (
    NetworkConfig,
    build_ide_url,
    build_sandbox_http_url, 
    build_ide_config_urls,
    format_sandbox_response_urls,
)

# Phase 5 — Networkability (public routing, DNS, SSL/TLS)  
from src.network.public_routing import PublicEndpointRouter, SandboxRoutingEntry
from src.network.dns_config import DNSConfigManager, DNSRecord
from src.network.ssl_manager import CertificateManager, CertificateBundle

__all__ = [
    # Phase 1 — URL Formatting
    "NetworkConfig",
    "build_ide_url",
    "build_sandbox_http_url",
    "build_ide_config_urls",
    "format_sandbox_response_urls",
    
    # Phase 5 — Networkability  
    "PublicEndpointRouter",
    "SandboxRoutingEntry",
    "DNSConfigManager",
    "DNSRecord",
    "CertificateManager",
    "CertificateBundle",
]
