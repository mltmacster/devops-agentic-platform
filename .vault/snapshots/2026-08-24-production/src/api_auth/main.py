"""Auth Service — REST API for authentication, JWT management, and RBAC checks.

Endpoints:
    POST /auth/login          — Authenticate and receive JWT token
    POST /auth/refresh        — Refresh an expired access token
    GET  /auth/me             — Get current user profile and roles
    POST /auth/check          — Check permission for a resource (RBAC)
"""

from fastapi import FastAPI, Depends, HTTPException, status, Request
from pydantic import BaseModel, EmailStr

# ─── App ──────────────────────────────────────
app = FastAPI(
    title="DAP Auth Service",
    description="OAuth2/OIDC authentication, JWT tokens, and RBAC checks",
    version="1.0.0",
)


# ─── Models ──────────────────────────────────

class LoginRequest(BaseModel):
    """POST /auth/login — login credentials."""
    email: EmailStr
    password: str


class LoginResponse(BaseModel):
    """POST /auth/login — response with tokens."""
    access_token: str
    refresh_token: str
    token_type: str = "Bearer"


class RefreshRequest(BaseModel):
    """POST /auth/refresh — refresh token."""
    refresh_token: str


class RefreshResponse(BaseModel):
    """POST /auth/refresh — new tokens."""
    access_token: str
    refresh_token: str
    token_type: str = "Bearer"


class UserProfile(BaseModel):
    """GET /auth/me — user profile."""
    id: str
    email: str
    role: str
    tenants: list[str]
    workspaces: list[str]


class RBACCheckRequest(BaseModel):
    """POST /auth/check — check permission for a resource."""
    user_id: str
    role: str
    resource_type: str  # e.g. "sandbox", "workspace"
    action: str         # e.g. "create", "read", "delete"


class RBACCheckResponse(BaseModel):
    """POST /auth/check — permission result."""
    user_id: str
    role: str
    resource_type: str
    action: str
    allowed: bool
    reason: str


# ─── Internal helpers (wire up existing modules) ─────────────

from src.api.auth.rbac import RBACEngine, RoleMapper, PermissionAction, PermissionScope
from src.api.auth.session_manager import SessionManager


# Shared instances (in production: injected via DI / env config)
rbac_engine = RBACEngine()
session_mgr = SessionManager(redis_client=None)  # pass real Redis in prod


# ─── Authentication Endpoints ────────────────

@app.post(
    "/auth/login",
    response_model=LoginResponse,
    status_code=status.HTTP_200_OK,
    summary="Authenticate and receive JWT token",
)
async def login(credentials: LoginRequest):
    """
    Authenticate a user and return JWT tokens.

    In production, this would:
      1. Lookup the user in the identity provider (Keycloak/Auth0)
      2. Verify credentials against the password store
      3. Issue a short-lived access token (15 min) and a refresh token (7 days)
    """
    # ── Stub: return mock tokens ───────────────
    # In production, swap this for actual auth provider integration:
    #   token = auth_provider.verify(credentials.email, credentials.password)

    # Record session in the session manager (for audit trail)
    session_mgr.create_session(
        email=credentials.email,
        token_type="access",
    )

    access_token = f"mock_access_token_for_{credentials.email}"
    refresh_token = f"mock_refresh_token_for_{credentials.email}"

    return LoginResponse(
        access_token=access_token,
        refresh_token=refresh_token,
    )


@app.post(
    "/auth/refresh",
    response_model=RefreshResponse,
    status_code=status.HTTP_200_OK,
    summary="Refresh an expired access token",
)
async def refresh(refresh: RefreshRequest):
    """
    Exchange a valid refresh token for a new access + refresh token pair.

    In production:
      1. Validate the refresh token against Redis (or DB)
      2. Check that it hasn't been revoked
      3. Issue fresh tokens with rotated refresh token (one-time use)
    """
    # ── Stub: return mock tokens ───────────────
    access_token = f"fresh_access_token_{refresh.refresh_token}"
    new_refresh_token = f"rotated_refresh_token_for_{refresh.refresh_token}"

    return RefreshResponse(
        access_token=access_token,
        refresh_token=new_refresh_token,
    )


@app.get(
    "/auth/me",
    response_model=UserProfile,
    status_code=status.HTTP_200_OK,
    summary="Get current user profile and roles",
)
async def get_profile(request: Request):
    """
    Return the authenticated user's profile, including role and associated resources.

    In production:
      1. Decode the JWT from Authorization: Bearer <token> header
      2. Query the user profile from the identity provider / DB
      3. Return role, tenants, and workspaces
    """
    # ── Stub: return mock user ────────────────
    return UserProfile(
        id="user-123",
        email="dev@example.com",
        role="developer",
        tenants=["tenant-a"],
        workspaces=["ws-456"],
    )


@app.post(
    "/auth/check",
    response_model=RBACCheckResponse,
    status_code=status.HTTP_200_OK,
    summary="Check permission for a resource (RBAC + ABAC)",
)
async def check_permission(check: RBACCheckRequest):
    """
    Evaluate whether a user has permission to perform an action on a resource.

    Combines role-based permissions with optional ABAC context (IP, device trust).
    """
    # Parse the action string into a PermissionAction enum
    action_map = {
        "create": PermissionAction.CREATE,
        "read": PermissionAction.READ,
        "update": PermissionAction.UPDATE,
        "delete": PermissionAction.DELETE,
        "execute": PermissionAction.EXECUTE,
    }

    action = action_map.get(check.action.lower())
    if not action:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown action: {check.action}. Valid actions: {list(action_map.keys())}",
        )

    # Build a ResourceOwner from the request data
    from src.api.auth.rbac import ResourceOwner

    user = ResourceOwner(user_id=check.user_id, role=check.role)
    
    # Determine the scope based on resource type
    if check.resource_type == "sandbox":
        scope = PermissionScope.SANDBOX
    else:
        scope = PermissionScope.WORKSPACE
    
    has_access = rbac_engine.check_permission(
        user=user,
        resource_type=check.resource_type,
        action=action,
        scope=scope,
    )

    return RBACCheckResponse(
        user_id=check.user_id,
        role=check.role,
        resource_type=check.resource_type,
        action=check.action,
        allowed=has_access,
        reason="Role-based permission granted" if has_access else "Insufficient permissions",
    )


# ─── Health Endpoints ────────────────────────

@app.get("/health/live", status_code=status.HTTP_200_OK)
async def health_live():
    """Liveness probe — simple ping."""
    return {"status": "alive"}


@app.get("/health/ready", status_code=status.HTTP_200_OK)
async def health_ready():
    """Readiness probe — verify dependencies are available."""
    try:
        # In production, check Redis connection for session manager
        return {"status": "ready"}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Not ready: {str(e)}",
        )
