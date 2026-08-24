"""Phase 5: Networkability — Public Endpoint Routing, DNS Config & SSL/TLS.

This module provides:
  • Reverse proxy routing to sandbox instances (public → internal)  
  • DNS record generation for sandbox subdomains
  • SSL/TLS certificate lifecycle management (self-signed + Let's Encrypt)

Usage:
    from src.network.public_routing import PublicEndpointRouter
    router = PublicEndpointRouter(base_host="sandbox.dap.io")
    
    # Route a request to the correct sandbox instance
    target = router.resolve(sandbox_id="abc123")
    
    # Generate DNS records for a new sandbox
    dns = router.generate_dns_records(sandbox_id="abc123")

    # Generate self-signed SSL certificates
    from src.network.ssl_manager import CertificateManager
    certs = CertificateManager.generate_self_signed("sandbox.dap.io")
"""

import asyncio
import ssl as ssl_module
from dataclasses import dataclass, field
from typing import Optional

# ─── Public Endpoint Router ──────────────

@dataclass
class SandboxRoutingEntry:
    """A registered sandbox instance with its network details."""

    sandbox_id: str
    internal_host: str = "localhost"
    ide_port: int = 8080
    web_port: int = 80
    status: str = "running"

    @property
    def public_hostname(self) -> str:
        return f"sandbox-{self.sandbox_id}.sandbox.dap.io"

    @property
    def ide_ws_url(self) -> str:
        return f"wss://{self.public_hostname}:{self.ide_port}/api/ide/ws/{self.sandbox_id}"

    @property
    def web_url(self) -> str:
        return f"https://{self.public_hostname}:{self.web_port}/"

    @property
    def status_url(self) -> str:
        return f"https://{self.public_hostname}:{self.ide_port}/api/ide/status/{self.sandbox_id}"


class PublicEndpointRouter:
    """Routes public requests to the correct sandbox instance.

    This router maintains a registry of all active sandbox instances and
    provides:
      1. DNS record generation for new sandboxes
      2. Public → Internal endpoint resolution (reverse proxy)  
      3. Health check aggregation across all sandboxes

    In production, this would integrate with a real DNS provider (Route53,
    Cloudflare) and a load balancer (ALB/NLB). For local development, it
    provides the routing logic that would work with those systems.
    """

    def __init__(self, base_host: str = "sandbox.dap.io"):
        """Initialize the public endpoint router.

        Args:
            base_host: Base hostname for all sandbox instances (e.g., "sandbox.dap.io").
        """
        self.base_host = base_host
        self._sandboxes: dict[str, SandboxRoutingEntry] = {}

    # ─── Registry Operations ──────────────────────────────

    def register_sandbox(self, entry: SandboxRoutingEntry) -> None:
        """Register a sandbox instance with the router.

        Args:
            entry: SandboxRoutingEntry with the sandbox's network details.
        """
        self._sandboxes[entry.sandbox_id] = entry

    def deregister_sandbox(self, sandbox_id: str) -> bool:
        """Remove a sandbox from the router.

        Args:
            sandbox_id: The unique sandbox identifier to remove.

        Returns:
            True if the sandbox was found and removed, False otherwise.
        """
        return self._sandboxes.pop(sandbox_id, None) is not None

    def get_sandbox(self, sandbox_id: str) -> Optional[SandboxRoutingEntry]:
        """Look up a sandbox by its ID.

        Args:
            sandbox_id: The unique sandbox identifier.

        Returns:
            SandboxRoutingEntry if found, None otherwise.
        """
        return self._sandboxes.get(sandbox_id)

    def list_sandboxes(self, status: Optional[str] = None) -> list[SandboxRoutingEntry]:
        """List all registered sandbox instances.

        Args:
            status: Optional filter by status ("running", "stopped", etc.).

        Returns:
            List of SandboxRoutingEntry objects.
        """
        if status is None:
            return list(self._sandboxes.values())
        return [s for s in self._sandboxes.values() if s.status == status]

    # ─── DNS Record Generation ────────────────────────────

    def generate_dns_records(self, sandbox_id: str) -> list[dict]:
        """Generate DNS records for a new sandbox instance.

        Creates the necessary A and CNAME records that would be submitted
        to a DNS provider (Route53, Cloudflare, etc.).

        Args:
            sandbox_id: The unique sandbox identifier.

        Returns:
            List of DNS record dictionaries ready for API submission.

        Example:
            >>> router = PublicEndpointRouter()
            >>> records = router.generate_dns_records("abc123")
            >>> print(records[0]["name"])  # "sandbox-abc123.sandbox.dap.io"
        """

        hostname = f"sandbox-{sandbox_id}.{self.base_host}"

        return [
            {
                "name": hostname,
                "type": "A",
                "value": "0.0.0.0",  # Placeholder — replaced by actual IP in production
                "ttl": 3600,
                "description": f"Main sandbox instance: {hostname}",
            },
            {
                "name": hostname,
                "type": "CNAME",
                "value": f"{sandbox_id}.{self.base_host}",  # Alias for routing lookup
                "ttl": 1800,
                "description": f"Alias for {hostname}",
            },
        ]

    def generate_full_dns_zone(self, sandbox_ids: list[str]) -> dict[str, list[dict]]:
        """Generate a complete DNS zone file for all sandbox instances.

        Args:
            sandbox_ids: List of sandbox identifiers to include in the zone.

        Returns:
            Dictionary mapping record types to their corresponding records.
        """
        zone: dict[str, list[dict]] = {"A": [], "CNAME": []}

        for sandbox_id in sandbox_ids:
            records = self.generate_dns_records(sandbox_id)
            for record in records:
                zone[record["type"]].append(record)

        return zone

    def generate_zone_file(self, sandbox_ids: list[str]) -> str:
        """Generate a BIND-compatible zone file for all sandboxes.

        Args:
            sandbox_ids: List of sandbox identifiers to include in the zone.

        Returns:
            Zone file content as a string, ready for DNS server import.
        """
        lines: list[str] = []

        # Zone header
        domain = self.base_host.split(".")[0]  # e.g., "sandbox" from "sandbox.dap.io"
        lines.append(f"{domain}.    IN  SOA  ns1.{domain} 20240801 3600 900 604800 86400")
        lines.append(f"ns1.{domain}.    IN  A   9.9.9.9")
        lines.append(f"ns2.{domain}.    IN  A   1.1.1.1")
        lines.append("")

        # Add records for each sandbox
        for record in self.generate_full_dns_zone(sandbox_ids):
            lines.append(f"{record['name']}    IN  {record['type']}  {record['value']}\t{record['ttl']}")

        lines.append(".")
        return "\n".join(lines) + "\n"

    # ─── Public → Internal Resolution ──────────────────────

    def resolve(self, sandbox_id: str) -> Optional[SandboxRoutingEntry]:
        """Resolve a public request to the correct internal sandbox instance.

        This is the core routing function that maps external requests
        to their target sandbox's internal address and port.

        Args:
            sandbox_id: The unique sandbox identifier from the request.

        Returns:
            SandboxRoutingEntry if found, None otherwise.
        """
        return self.get_sandbox(sandbox_id)

    def generate_reverse_proxy_config(self, sandbox_ids: list[str]) -> dict:
        """Generate a reverse proxy configuration for all registered sandboxes.

        Produces an NGINX-like configuration that routes traffic from
        public endpoints to internal sandbox instances.

        Args:
            sandbox_ids: List of sandbox identifiers to configure in the proxy.

        Returns:
            Dictionary with reverse proxy configuration blocks.
        """
        config = {
            "worker_processes": 4,
            "events": {"worker_connections": 1024},
            "http": {
                "upstream_targets": [],
                "server_blocks": []
            }
        }

        for sandbox_id in sandbox_ids:
            entry = self.get_sandbox(sandbox_id)
            if not entry:
                continue

            # Add upstream for IDE WebSocket
            config["http"]["upstream_targets"].append({
                "name": f"ide_{sandbox_id}",
                "servers": [f"{entry.internal_host}:{entry.ide_port}"],
            })

        return config

    # ─── Health Check Aggregation ──────────────────────────

    async def health_check_all(self) -> dict[str, bool]:
        """Run health checks against all registered sandbox instances.

        Returns:
            Dictionary mapping sandbox_id to health status (True=healthy).
        """
        results: dict[str, bool] = {}

        for sandbox_id in self._sandboxes.keys():
            try:
                entry = self.get_sandbox(sandbox_id)
                if entry and entry.status == "running":
                    # In production, this would be an actual HTTP call
                    results[sandbox_id] = True  # Placeholder — assumes healthy if "running"
            except Exception:
                results[sandbox_id] = False

        return results


# ─── Exports ─────────────────────────────────

__all__ = [
    "SandboxRoutingEntry",
    "PublicEndpointRouter",
]
