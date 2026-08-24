"""Observability Metrics Collector

Collects and exports metrics from sandboxes, agentic AI engine, and IDE sessions.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional
import time
import logging

logger = logging.getLogger(__name__)


@dataclass
class SandboxMetrics:
    """Metrics collected from a sandbox instance."""

    sandbox_id: str = ""
    cpu_usage_percent: float = 0.0
    memory_used_mb: float = 0.0
    disk_used_gb: float = 0.0
    network_egress_mbps: float = 0.0
    process_count: int = 0


@dataclass
class AgenticAIMetrics:
    """Metrics collected from the agentic AI engine."""

    tokens_used_total: int = 0
    tokens_used_current_minute: int = 0
    requests_total: int = 0
    requests_failed: int = 0
    avg_latency_ms: float = 0.0
    p95_latency_ms: float = 0.0


@dataclass
class IDEMetrics:
    """Metrics collected from the embedded IDE."""

    active_sessions: int = 0
    lsp_avg_response_ms: float = 0.0
    editor_memory_mb: float = 0.0


@dataclass
class PlatformMetrics:
    """Aggregate platform metrics."""

    total_sandboxes: int = 0
    active_sandboxes: int = 0
    total_cpu_cores_allocated: float = 0.0
    total_memory_allocated_gb: float = 0.0
    active_users: int = 0


class MetricsCollector:
    """Collects and exports platform metrics."""

    def __init__(self):
        self._sandbox_metrics: Dict[str, SandboxMetrics] = {}
        self._ai_metrics = AgenticAIMetrics()
        self._ide_metrics = IDEMetrics()

    def collect_sandbox_metrics(self, sandbox_id: str, metrics: SandboxMetrics) -> None:
        """Record or update sandbox metrics."""
        self._sandbox_metrics[sandbox_id] = metrics

    def collect_ai_metrics(self, tokens: int = 0, latency_ms: float = 0.0) -> None:
        """Collect agentic AI engine metrics."""
        self._ai_metrics.tokens_used_total += tokens
        self._ai_metrics.requests_total += 1

        if latency_ms:
            latencies = [self._ai_metrics.avg_latency_ms] + [latency_ms] if self._ai_metrics.requests_total > 1 else [latency_ms]
            self._ai_metrics.avg_latency_ms = sum(latencies) / len(latencies)

    def collect_ide_metrics(self, sessions: int = 0, lsp_latency_ms: float = 0.0) -> None:
        """Collect IDE metrics."""
        self._ide_metrics.active_sessions = sessions
        if lsp_latency_ms:
            self._ide_metrics.lsp_avg_response_ms = (
                (self._ide_metrics.lsp_avg_response_ms * 10 + lsp_latency_ms) / 11
            )

    def get_platform_metrics(self) -> PlatformMetrics:
        """Calculate aggregate platform metrics."""
        running_sandboxes = [m for m in self._sandbox_metrics.values() if m.sandbox_id]
        total_sandboxes = len(self._sandbox_metrics)

        return PlatformMetrics(
            total_sandboxes=total_sandboxes,
            active_sandboxes=len(running_sandboxes),
            total_cpu_cores_allocated=sum(m.cpu_usage_percent / 100 for m in self._sandbox_metrics.values()),
            total_memory_allocated_gb=sum(m.memory_used_mb / 1024 for m in self._sandbox_metrics.values()),
            active_users=0,  # Would be populated from auth service
        )

    def export_prometheus_metrics(self) -> str:
        """Export metrics in Prometheus text format."""

        lines = []
        now = time.time()

        # Sandbox metrics
        for sb_id, m in self._sandbox_metrics.items():
            lines.append(f"# HELP sandbox_cpu_usage_percent CPU usage percentage for a sandbox")
            lines.append(f"sandbox_cpu_usage_percent{{sandbox_id=\"{sb_id}\"} {m.cpu_usage_percent}")
            lines.append(f"# HELP sandbox_memory_used_mb Memory used in MB for a sandbox")
            lines.append(f"sandbox_memory_used_mb{{sandbox_id=\"{sb_id}\"} {m.memory_used_mb}")
            lines.append(f"# HELP sandbox_disk_used_gb Disk used in GB for a sandbox")
            lines.append(f"sandbox_disk_used_gb{{sandbox_id=\"{sb_id}\"} {m.disk_used_gb}")

        # AI metrics
        lines.append(f"# HELP ai_tokens_used_total Total tokens used by the agentic AI engine")
        lines.append(f"ai_tokens_used_total {self._ai_metrics.tokens_used_total}")

        lines.append(f"# HELP ai_requests_total Total requests to the agentic AI engine")
        lines.append(f"ai_requests_total {self._ai_metrics.requests_total}")

        lines.append(f"# HELP ai_avg_latency_ms Average latency in milliseconds")
        lines.append(f"ai_avg_latency_ms {self._ai_metrics.avg_latency_ms}")

        # IDE metrics
        lines.append(f"# HELP ide_active_sessions Number of active IDE sessions")
        lines.append(f"ide_active_sessions {self._ide_metrics.active_sessions}")

        lines.append(f"# HELP ide_lsp_avg_response_ms Average LSP response time in milliseconds")
        lines.append(f"ide_lsp_avg_response_ms {self._ide_metrics.lsp_avg_response_ms}")

        # Platform aggregate
        pm = self.get_platform_metrics()
        lines.append(f"# HELP platform_active_sandboxes Number of active sandboxes")
        lines.append(f"platform_active_sandboxes {pm.active_sandboxes}")

        return "\n".join(lines) + "\n"


# ─── Service Singleton (in production: DI-injected) ──
_metrics_collector = MetricsCollector()
