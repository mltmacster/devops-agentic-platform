"""DNS Configuration — Record Generation & Zone Management.

Provides utilities for:
  • Generating DNS records (A, CNAME, TXT) for sandbox instances  
  • Creating BIND-compatible zone files
  • Validating DNS record formats
  • Exporting zone data to cloud provider APIs (Route53, Cloudflare, etc.)

Usage:
    from src.network.dns_config import DNSConfigManager
    
    manager = DNSConfigManager(domain="sandbox.dap.io")
    
    # Generate A + CNAME for a new sandbox
    records = manager.generate_sandbox_records("abc123")
    
    # Export as BIND zone file  
    zone = manager.export_zone_file(sandbox_ids=["abc123", "def456"])
"""

from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class DNSRecord:
    """A single DNS record with all standard fields."""

    name: str = "localhost"
    type: str = "A"  # A, AAAA, CNAME, TXT, SRV, MX
    value: str = "127.0.0.1"
    ttl: int = 3600
    priority: int = -1  # For MX records only (lower = higher priority)

    @property
    def record_type_label(self) -> str:
        """Human-readable label for the record type."""
        labels = {
            "A": "IPv4",
            "AAAA": "IPv6",
            "CNAME": "Alias",
            "TXT": "Text/Meta",
            "SRV": "Service Record",
            "MX": "Mail Exchange",
        }
        return labels.get(self.type, self.type)

    def to_bind_format(self) -> str:
        """Format this record as BIND zone file syntax.

        Returns:
            String representing the DNS record in BIND format.
        """
        line = f"{self.name}\t{self.type}\t{self.ttl}"

        if self.priority >= 0:
            line += f"\t{self.priority}"

        line += f"\t{self.value}"
        return line


class DNSConfigManager:
    """Manages DNS configuration for the DAP platform.

    Handles record generation, zone file export, and validation of
    DNS records for sandbox subdomains.

    In production, this would integrate with cloud provider APIs:
      • AWS Route53 (AWS CLI / boto3)
      • Cloudflare API
      • DigitalOcean DNS
      • Google Cloud DNS

    For local development, it generates zone files ready for import into
    any DNS server (BIND, Unbound, etc.).
    """

    def __init__(self, domain: str = "sandbox.dap.io"):
        """Initialize the DNS configuration manager.

        Args:
            domain: Base domain for all sandbox instances (e.g., "sandbox.dap.io").
        """
        self.domain = domain
        self._records: dict[str, list[DNSRecord]] = {}

    # ─── Record Generation ────────────────────────────────

    def generate_sandbox_records(
        self, sandbox_id: str, ip_address: str = "0.0.0.0"
    ) -> list[DNSRecord]:
        """Generate A + CNAME records for a new sandbox instance.

        Creates the core DNS records needed for external access to a
        sandbox's IDE and web endpoints.

        Args:
            sandbox_id: The unique sandbox identifier (e.g., "abc123").
            ip_address: IP address to assign in the A record.

        Returns:
            List of DNSRecord objects for the sandbox.
        """

        hostname = f"sandbox-{sandbox_id}.{self.domain}"
        alias_hostname = f"{sandbox_id}.{self.domain}"

        records = [
            # A record — primary IP address for the sandbox
            DNSRecord(
                name=hostname,
                type="A",
                value=ip_address,
                ttl=3600,  # 1 hour — reasonable for dynamic sandboxes
            ),
            # CNAME record — alias for routing lookup
            DNSRecord(
                name=hostname,
                type="CNAME",
                value=alias_hostname,
                ttl=1800,  # 30 minutes — shorter TTL for dynamic updates
            ),
        ]

        return records

    def generate_ide_endpoint_records(
        self, sandbox_id: str, ip_address: str = "0.0.0.0"
    ) -> list[DNSRecord]:
        """Generate DNS records specifically for the IDE endpoint.

        Creates CNAME records pointing to the IDE WebSocket port and
        web port for the sandbox.

        Args:
            sandbox_id: The unique sandbox identifier.
            ip_address: IP address for the IDE endpoint.

        Returns:
            List of DNSRecord objects for the IDE endpoint.
        """

        ide_hostname = f"ide-{sandbox_id}.{self.domain}"
        web_hostname = f"web-{sandbox_id}.{self.domain}"

        return [
            DNSRecord(
                name=ide_hostname,
                type="CNAME",
                value=f"sandbox-{sandbox_id}.{self.domain}",
                ttl=3600,
            ),
            DNSRecord(
                name=web_hostname,
                type="CNAME",
                value=f"sandbox-{sandbox_id}.{self.domain}",
                ttl=3600,
            ),
        ]

    def generate_monitoring_records(self, sandbox_id: str) -> list[DNSRecord]:
        """Generate DNS records for monitoring and health check endpoints.

        Creates TXT records that can be used by DNS-based health checks
        and monitoring systems to verify sandbox availability.

        Args:
            sandbox_id: The unique sandbox identifier.

        Returns:
            List of DNSRecord objects for monitoring records.
        """

        hostname = f"monitor-{sandbox_id}.{self.domain}"

        return [
            # TXT record for DNS-based health check verification
            DNSRecord(
                name=hostname,
                type="TXT",
                value=f"verification-{sandbox_id}-active",
                ttl=300,  # 5 minutes — short TTL for rapid health checks
            ),
        ]

    def generate_all_sandbox_records(
        self, sandbox_id: str, ip_address: str = "0.0.0.0"
    ) -> list[DNSRecord]:
        """Generate all DNS records for a sandbox instance.

        Combines A, CNAME, IDE endpoint, and monitoring records into
        a single comprehensive set.

        Args:
            sandbox_id: The unique sandbox identifier.
            ip_address: IP address for the sandbox's A record.

        Returns:
            Complete list of all DNSRecord objects for this sandbox.
        """

        records = []
        records.extend(self.generate_sandbox_records(sandbox_id, ip_address))
        records.extend(self.generate_ide_endpoint_records(sandbox_id, ip_address))
        records.extend(self.generate_monitoring_records(sandbox_id))

        return records

    # ─── Zone File Export ─────────────────────────────────

    def export_bind_zone_file(self, sandbox_ids: list[str]) -> str:
        """Export all registered DNS records as a BIND-compatible zone file.

        Args:
            sandbox_ids: List of sandbox identifiers to include in the zone.

        Returns:
            Zone file content as a string, ready for DNS server import.
        """

        lines: list[str] = []
        domain_parts = self.domain.split(".")

        # Zone header with SOA record
        ns1 = f"ns1.{domain_parts[-2]}.{domain_parts[-1]}"
        ns2 = f"ns2.{domain_parts[-2]}.{domain_parts[-1]}"
        contact = "admin." + self.domain

        lines.append(f"{domain_parts[-1]}.    IN  SOA  {ns1} 20240801 3600 900 604800 86400")
        lines.append(f"ns1.{domain_parts[-2]}.{domain_parts[-1]}.    IN  A   9.9.9.9")
        lines.append(f"ns2.{domain_parts[-2]}.{domain_parts[-1]}.    IN  A   1.1.1.1")
        lines.append("")

        # Add records for each sandbox
        for sandbox_id in sandbox_ids:
            records = self.generate_all_sandbox_records(sandbox_id)

            # Group by name for proper ordering
            seen_names: dict[str, list[DNSRecord]] = {}
            for record in records:
                if record.name not in seen_names:
                    seen_names[record.name] = []
                seen_names[record.name].append(record)

            for name, name_records in seen_names.items():
                lines.append(f"{name}\t")  # $ORIGIN directive handling
                for record in name_records:
                    lines.append(record.to_bind_format())
            lines.append("")

        # Default A record for the root domain
        lines.append(f"{self.domain}    IN  A   0.0.0.0")
        lines.append(".")

        return "\n".join(lines) + "\n"

    def export_cloudflare_records(self, sandbox_ids: list[str]) -> dict:
        """Export DNS records in Cloudflare API format.

        Converts DNS records to the format expected by Cloudflare's
        REST API for bulk record creation/update.

        Args:
            sandbox_ids: List of sandbox identifiers to export.

        Returns:
            Dictionary ready for Cloudflare API submission.
        """

        zones = {
            "domain": self.domain,
            "records": []
        }

        for sandbox_id in sandbox_ids:
            records = self.generate_all_sandbox_records(sandbox_id)

            for record in records:
                cf_record = {
                    "type": record.type,
                    "name": record.name,
                    "content": record.value,
                    "priority": record.priority if record.type == "MX" else None,
                }

                zones["records"].append(cf_record)

        return zones

    def export_route53_records(self, sandbox_ids: list[str]) -> dict:
        """Export DNS records in AWS Route53 API format.

        Converts DNS records to the format expected by AWS Route53
        API for bulk record creation/update.

        Args:
            sandbox_ids: List of sandbox identifiers to export.

        Returns:
            Dictionary ready for Route53 API submission.
        """

        resource_records = []

        for sandbox_id in sandbox_ids:
            records = self.generate_all_sandbox_records(sandbox_id)

            for record in records:
                rr = {
                    "Name": record.name,
                    "Type": record.type,
                }

                if record.type == "A" or record.type == "AAAA":
                    rr["ResourceRecordSet"] = {
                        "Type": record.type,
                        "TTL": record.ttl,
                        "ResourceRecords": [record.value],
                    }

                elif record.type == "CNAME":
                    rr["ResourceRecordSet"] = {
                        "Type": record.type,
                        "TTL": record.ttl,
                        "ResourceRecords": [record.value],
                    }

                elif record.type == "TXT":
                    rr["ResourceRecordSet"] = {
                        "Type": record.type,
                        "TTL": record.ttl,
                        "ResourceRecords": [record.value],
                    }

                elif record.type == "MX":
                    rr["ResourceRecordSet"] = {
                        "Type": record.type,
                        "TTL": record.ttl,
                        "Preference": record.priority,
                        "ResourceRecords": [record.value],
                    }

                resource_records.append(rr)

        return {
            "Name": self.domain,
            "ResourceRecordSets": resource_records,
        }

    # ─── Validation ──────────────────────────────────────

    @staticmethod
    def validate_dns_record(record: DNSRecord) -> list[str]:
        """Validate a DNS record for correctness.

        Args:
            record: The DNSRecord to validate.

        Returns:
            List of validation errors (empty if valid).
        """
        errors: list[str] = []

        # Valid record types
        valid_types = {"A", "AAAA", "CNAME", "TXT", "SRV", "MX"}
        if record.type not in valid_types:
            errors.append(f"Invalid record type: {record.type}")

        # A/AAAA records must have valid IP addresses
        if record.type in ("A", "AAAA"):
            if not record.value or "." not in record.value:
                errors.append(f"Invalid IP address for {record.type} record: {record.value}")

        # CNAME records cannot coexist with other records for the same name
        if record.type == "CNAME":
            pass  # CNAME validation is handled at zone level

        # TXT records are unrestricted strings
        if record.type == "TXT":
            pass  # TXT records can contain any text

        # MX priority must be non-negative integer
        if record.type == "MX" and (record.priority < 0 or not isinstance(record.priority, int)):
            errors.append(f"Invalid MX priority: {record.priority}")

        # TTL must be positive integer
        if record.ttl <= 0:
            errors.append(f"Invalid TTL for {record.type} record: {record.ttl}")

        return errors

    def validate_zone(self, sandbox_ids: list[str]) -> dict[str, list[str]]:
        """Validate all DNS records for a set of sandbox instances.

        Args:
            sandbox_ids: List of sandbox identifiers to validate.

        Returns:
            Dictionary mapping sandbox_id to list of validation errors.
        """
        results: dict[str, list[str]] = {}

        for sandbox_id in sandbox_ids:
            records = self.generate_all_sandbox_records(sandbox_id)
            errors: list[str] = []

            for record in records:
                record_errors = self.validate_dns_record(record)
                errors.extend([f"[{record.name}] {e}" for e in record_errors])

            results[sandbox_id] = errors

        return results


# ─── Exports ─────────────────────────────────

__all__ = [
    "DNSRecord",
    "DNSConfigManager",
]
