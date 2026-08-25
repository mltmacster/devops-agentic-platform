"""Strict-mode route guard — fails closed on every non-public API route.

The auth *endpoints* (register/login/refresh/me) validate credentials
themselves, but the data routes (workspace, sandbox, ide, agentic,
network) previously carried no auth dependency at all: a deployed
production stack would let anonymous visitors create sandboxes and
drive the LLM engine (SOLUTION 39).

This module adds the missing enforcement as a pure ASGI middleware:

  • `DAP_AUTH_STRICT=1` (the production default, set by
    templates/docker/DOCKERCOMPOSE_PROD.yml): every HTTP route must
    present a valid signed JWT access token, and every WebSocket
    connection must present one as `?token=`, UNLESS the path is on
    the public allowlist below.
  • Dev mode (strict off): the middleware is a no-op, so local
    previews and the test suite keep their legacy fail-open behavior.

Public allowlist (deliberately small and read-only):
  • `/`, `/docs`, `/redoc`, `/openapi.json` — service discovery
  • `/health` and any `*health*` segment — liveness/readiness probes
  • `/api/auth/auth/*` — the auth flow (self-guarding; register is
    the first-user bootstrap)
  • `/api/observability/metrics` and `/api/observability/health` —
    the live dashboard polls these without a browser token
"""

from urllib.parse import unquote, urlsplit

from starlette.datastructures import Headers
from starlette.responses import JSONResponse

from src.api.auth.main import _auth_strict
from src.api.auth.credentials import decode_token

# Static public paths (exact or prefix).
_PUBLIC_EXACT = {"/", "/docs", "/redoc", "/openapi.json"}
_PUBLIC_PREFIXES = (
    "/api/auth/auth/",
    "/api/observability/metrics",
    "/api/observability/health",
)


def _is_public_path(path: str) -> bool:
    p = unquote(path).rstrip("/") or "/"
    if p in _PUBLIC_EXACT:
        return True
    if p.startswith(_PUBLIC_PREFIXES):
        return True
    # Any health probe (global /health, per-service /api/<svc>/health[...]).
    return "health" in [s for s in p.split("/") if s]


class StrictAuthMiddleware:
    """Require a signed JWT on every non-public route when strict.

    Pure ASGI (not BaseHTTPMiddleware) so it also sees websocket
    scopes; HTTP gets the Authorization header, websockets get a
    `?token=` query parameter (browsers cannot set headers on
    WebSocket upgrades).
    """

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        # Dev mode: pass through untouched (no-op, zero cost).
        if not _auth_strict():
            await self.app(scope, receive, send)
            return

        if scope["type"] == "http":
            path = scope.get("path", "")
            if scope.get("method") == "OPTIONS" or _is_public_path(path):
                await self.app(scope, receive, send)
                return
            headers = Headers(scope=scope)
            token = self._bearer_token(headers.get("Authorization"))
        elif scope["type"] == "websocket":
            path = scope.get("path", "")
            if _is_public_path(path):
                await self.app(scope, receive, send)
                return
            query = scope.get("query_string", b"")
            token = self._query_token(query)
        else:  # lifespan & co.
            await self.app(scope, receive, send)
            return

        payload = decode_token(token, typ="access") if token else None
        if payload is None or not payload.get("email"):
            # Reject and short-circuit (the app is never invoked). For a
            # websocket scope this is the ASGI-sanctioned pre-accept HTTP
            # rejection of the upgrade.
            response = JSONResponse(
                status_code=401,
                content={"detail": "Authentication required: present a valid JWT access token."},
            )
            await response(scope, receive, send)
            return
        await self.app(scope, receive, send)

    @staticmethod
    def _bearer_token(auth_header):
        if not auth_header or not auth_header.startswith("Bearer "):
            return None
        return auth_header[7:].strip() or None

    @staticmethod
    def _query_token(query_bytes):
        for pair in query_bytes.split(b"&"):
            key, _, value = pair.partition(b"=")
            if key == b"token" and value:
                return unquote(value.decode("utf-8"))
        return None
