"""DAP Main Application — FastAPI entry point.

Combines all microservices into a single deployable application
for local development. In production, each service would be its own container.

To run: uvicorn main:app --host 0.0.0.0 --port 8000
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from src.database import init_db
from src.sandbox_engine import SandboxLifecycleManager

# ─── Strict-mode route guard (SOLUTION 39) ──
from src.api.auth.route_guard import StrictAuthMiddleware

# ─── Microservices (import each service's app) ──
from src.api.auth.main import app as auth_app
from src.api.workspace.main import app as workspace_app
from src.api.sandbox.main import app as sandbox_app
from src.api.ide.main import app as ide_app
from src.api.observability.main import app as observability_app
from src.api.agentic.main import app as agentic_app

# ─── Phase 5: Networkability ──────────────
from src.network import (
    NetworkConfig, build_ide_config_urls, format_sandbox_response_urls,
    PublicEndpointRouter, SandboxRoutingEntry,
    DNSConfigManager, DNSRecord,
    CertificateManager, CertificateBundle,
)

# ─── Root Application ──────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup: ensure database schema exists (idempotent create_all)."""
    try:
        await init_db()
    except Exception as exc:  # never block boot on DB issues; log and continue
        import logging
        logging.getLogger(__name__).error("DB init failed: %s", exc)
    yield


app = FastAPI(
    lifespan=lifespan,
    title="DevOps Agentic Platform (DAP)",
    description=(
        "Multi-tenant SaaS coding sandbox with embedded IDE and agentic AI assistants.\n\n"
        "Microservices:\n"
        "  • /api/auth — Authentication & RBAC\n"
        "  • /api/workspace — Workspace lifecycle management\n"
        "  • /api/sandbox — Sandbox VM lifecycle (boot/stop/suspend/resume)\n"
        "  • /api/ide — Embedded IDE API (Monaco + LSP)\n"
        "  • /api/observability — Metrics collection & Prometheus export\n"
        "  • /api/agentic — Agentic AI Engine (code architect, debugger, test gen)\n"
        "  • /api/network — Networkability (Phase 5: routing, DNS, SSL)\n"
    ),
    version="1.0.0",
)

# ─── Strict-mode route guard (SOLUTION 39) ──────────────
# Added BEFORE the CORS registration so CORS stays outermost and its
# headers still frame the guard's 401 responses. No-op in dev mode.
app.add_middleware(StrictAuthMiddleware)

# ─── CORS Middleware ──────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Restrict in production!
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─── Include Microservice Routes (non-decorator form) ─────────────

app.include_router(auth_app.router, prefix="/api/auth")
app.include_router(workspace_app.router, prefix="/api/workspace")
app.include_router(sandbox_app.router, prefix="/api/sandbox")
app.include_router(ide_app.router, prefix="/api/ide")
app.include_router(observability_app.router, prefix="/api/observability")
app.include_router(agentic_app.router, prefix="/api/agentic")

# ─── Phase 5: Networkability API ──────────────
from fastapi import APIRouter

network_router = APIRouter(prefix="/api/network")


# ─── Network Management Models ──────────────

class RouterConfig(BaseModel):
    """Configuration for the public endpoint router."""
    base_host: str = "sandbox.dap.io"


class RouterStatus(BaseModel):
    """Health status of the public endpoint router."""
    base_host: str
    registered_sandboxes: int
    running_sandboxes: int


# ─── Network Router Endpoints ──────────────

@network_router.get("/")
async def network_root():
    """Networkability API — Phase 5 endpoints for public routing, DNS & SSL."""
    return {
        "version": "1.0",
        "description": "Networkability API — Public endpoint routing, DNS config, SSL/TLS",
        "endpoints": {
            # Public Endpoint Routing
            "router-config": "/api/network/router/config",
            "router-status": "/api/network/router/status",
            "router-sandbox-add": "/api/network/router/sandboxes/{sandbox_id}",
            "router-sandbox-remove": "/api/network/router/sandboxes/{sandbox_id}",
            "router-list-sandboxes": "/api/network/router/sandboxes",

            # DNS Configuration  
            "dns-records": "/api/network/dns/records",
            "dns-zone-file": "/api/network/dns/zone-file",

            # SSL/TLS Certificates
            "ssl-certs": "/api/network/ssl/certificates",
            "ssl-generate-self-signed": "/api/network/ssl/generate/self-signed",
        }
    }


@network_router.get("/router/config")
async def router_config(config: RouterConfig = NetworkConfig(base_host="sandbox.dap.io")):
    """Get the public endpoint router configuration."""
    return {
        "base_host": config.base_host,
        "description": "Base hostname for all sandbox instances"
    }


@network_router.post("/router/config")
async def update_router_config(config: RouterConfig):
    """Update the public endpoint router configuration."""
    return {
        "base_host": config.base_host,
        "message": "Router configuration updated"
    }


@network_router.get("/router/status")
async def router_status():
    """Get the public endpoint router health status."""

    global _router  # Get from the router instance created below

    running = len([s for s in _router.list_sandboxes() if s.status == "running"])
    total = len(_router.list_sandboxes())

    return RouterStatus(
        base_host=_router.base_host,
        registered_sandboxes=total,
        running_sandboxes=running,
    )


@network_router.post("/router/sandboxes/{sandbox_id}")
async def register_sandbox(sandbox_id: str, internal_host: str = "localhost", ide_port: int = 8080, web_port: int = 80):
    """Register a sandbox instance with the public endpoint router."""

    entry = SandboxRoutingEntry(
        sandbox_id=sandbox_id,
        internal_host=internal_host,
        ide_port=ide_port,
        web_port=web_port,
        status="running",
    )

    _router.register_sandbox(entry)

    return {
        "sandbox_id": sandbox_id,
        "public_hostname": entry.public_hostname,
        "ide_ws_url": entry.ide_ws_url,
        "web_url": entry.web_url,
        "status": entry.status,
    }


@network_router.delete("/router/sandboxes/{sandbox_id}")
async def deregister_sandbox(sandbox_id: str):
    """Remove a sandbox instance from the public endpoint router."""

    removed = _router.deregister_sandbox(sandbox_id)

    if not removed:
        raise HTTPException(status_code=404, detail=f"Sandbox {sandbox_id} not found")

    return {"message": f"Sandbox {sandbox_id} deregistered"}


@network_router.get("/router/sandboxes")
async def list_sandboxes(status: str | None = None):
    """List all registered sandbox instances."""

    sandboxes = _router.list_sandboxes(status=status)

    return {
        "sandboxes": [
            {
                "sandbox_id": s.sandbox_id,
                "public_hostname": s.public_hostname,
                "ide_ws_url": s.ide_ws_url,
                "web_url": s.web_url,
                "status": s.status,
            }
            for s in sandboxes
        ]
    }


# ─── DNS Configuration Endpoints ──────────────

@network_router.get("/dns/records")
async def generate_dns_records(sandbox_id: str = Query(..., description="Sandbox ID"), ip_address: str = "0.0.0.0"):
    """Generate DNS records for a sandbox instance."""

    global dns_manager
    
    manager = dns_manager
    records = manager.generate_all_sandbox_records(sandbox_id, ip_address)

    return {
        "sandbox_id": sandbox_id,
        "records": [
            {
                "name": r.name,
                "type": r.type,
                "value": r.value,
                "ttl": r.ttl,
            }
            for r in records
        ]
    }


@network_router.get("/dns/zone-file")
async def export_dns_zone_file(sandbox_ids: list[str] = Query(..., description="List of sandbox IDs")):
    """Export DNS records as a BIND-compatible zone file."""

    global dns_manager
    
    manager = dns_manager
    zone_file = manager.export_bind_zone_file(sandbox_ids)

    return {"zone_file": zone_file}


# ─── SSL/TLS Certificate Endpoints ──────────────

@network_router.get("/ssl/certificates")
async def list_ssl_certificates(warn_days: int = Query(30, description="Days before expiry to warn")):
    """List all certificates and their status."""

    global _ssl_manager
    
    manager = _ssl_manager
    
    bundles = []
    
    # FIX: Move issues outside the loop so it's always defined (even when no certs exist)
    issues = manager.cleanup_expired(warn_days)

    for cert_file in manager.cert_dir.glob("*.crt"):
        try:
            hostname = cert_file.stem.replace(".crt", "").replace("ca-", "")
            key_file = manager.cert_dir / f"{cert_file.stem}.key"
            ca_file = manager.cert_dir / f"{cert_file.stem}_ca.crt"

            bundle = CertificateBundle(
                cert_path=str(cert_file),
                key_path=str(key_file) if key_file.exists() else "",
                ca_cert_path=str(ca_file) if ca_file.exists() else None,
                hostname=hostname,
            )

            cert_info = manager.validate_cert_path(bundle.cert_path)
            bundle.is_valid = cert_info.is_valid

            bundles.append({
                **bundle.to_dict(),
                "is_valid": bundle.is_valid,
                "hostname": bundle.hostname,
            })
        except Exception as e:
            print(f"Error reading {cert_file}: {e}")

    return {
        "certificates": bundles,
        "issues": issues,
    }


@network_router.post("/ssl/generate/self-signed")
async def generate_self_signed_cert(hostname: str = Query(..., description="Hostname for the certificate"), days: int = 365):
    """Generate a self-signed SSL certificate for development."""

    global _ssl_manager
    
    manager = _ssl_manager
    bundle = manager.generate_self_signed(hostname, validity_days=days)

    return {
        "hostname": hostname,
        "cert_path": bundle.cert_path,
        "key_path": bundle.key_path,
        "ca_cert_path": bundle.ca_cert_path,
    }


@network_router.post("/ssl/generate/ca-signed")
async def generate_ca_signed_cert(hostname: str = Query(..., description="Hostname for the certificate")):
    """Generate a CA-signed SSL certificate."""

    global _ssl_manager
    
    manager = _ssl_manager
    bundle = manager.generate_ca_signed(hostname)

    return {
        "hostname": hostname,
        "cert_path": bundle.cert_path,
        "key_path": bundle.key_path,
        "ca_cert_path": bundle.ca_cert_path,
    }


# ─── Include Network Router Endpoints ──────────────

app.include_router(network_router)


# ─── Initialize Network Components ──────────────

# Global instances (in production, these would be injected via DI)
dns_manager = DNSConfigManager(domain="sandbox.dap.io")
_ssl_manager = CertificateManager()

# Public endpoint router — initialized with default config
_router = PublicEndpointRouter(base_host="sandbox.dap.io")

# ─── Root Endpoint ──────────────
@app.get("/")
async def root():
    """DAP API Root — health check and service info."""
    return {
        "name": "DevOps Agentic Platform",
        "version": "1.0.0",
        "status": "healthy",
        "endpoints": {
            "auth": "/api/auth",
            "workspace": "/api/workspace",
            "sandbox": "/api/sandbox",
            "ide": "/api/ide",
            "observability": "/api/observability/metrics",
            "agentic": "/api/agentic/run",
            # Phase 5: Networkability
            "network": {
                "docs": "/api/network",
                "router-status": "/api/network/router/status",
                "dns-records": "/api/network/dns/records",
                "ssl-certs": "/api/network/ssl/certificates",
            },
        },
    }


@app.get("/health")
async def health():
    """Global health check (incl. selected sandbox execution backend)."""
    return {
        "status": "healthy",
        "service": "dap-main",
        "sandbox_runtime": SandboxLifecycleManager().backend.name,
    }
