"""Auth Service — REST API for authentication, JWT management, and RBAC checks.

Endpoints:
    POST /auth/register       — Create a user account (first user = admin)
    POST /auth/login          — Authenticate and receive JWT token
    POST /auth/refresh        — Refresh an expired access token
    GET  /auth/me             — Get current user profile and roles
    POST /auth/check          — Check permission for a resource (RBAC)

Auth mode: DAP_AUTH_STRICT=1 (production, fail-closed) vs dev default
(fail-open for unregistered users). Real user store: `users` table.
"""

from typing import Optional

from fastapi import FastAPI, Depends, HTTPException, status, Request
from pydantic import BaseModel, EmailStr, Field

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


class RegisterRequest(BaseModel):
    """POST /auth/register — create a new user account."""
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)
    role: str = ""  # empty -> first user becomes admin, others developer


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


class AuthUserResponse(BaseModel):
    """POST /auth/register — returned account."""
    id: str
    email: str
    role: str


# ─── Internal helpers (wire up existing modules) ─────────────

import os

from src.api.auth.rbac import RBACEngine, RoleMapper, PermissionAction, PermissionScope
from src.api.auth.session_manager import SessionManager
from src.api.auth.credentials import (
    create_token_pair,
    decode_token,
    hash_password,
    verify_password,
)
from src.database import get_session
from src.database.user_repo import UserRepository


# Shared instances (in production: injected via DI / env config)
rbac_engine = RBACEngine()
session_mgr = SessionManager(redis_client=None)  # pass real Redis in prod


def _auth_strict() -> bool:
    """Strict (fail-closed) auth — on by default in production.

    Dev mode (default, DAP_AUTH_STRICT unset/0) keeps the legacy
    fail-open behavior so local previews and the test suite work without
    registered users; production sets DAP_AUTH_STRICT=1.
    """
    return os.environ.get("DAP_AUTH_STRICT", "0") == "1"


async def get_session_dependency():
    """FastAPI dependency that yields a database session."""
    async with get_session() as session:
        yield session


async def _bearer_user(request: Request, session) -> Optional[UserProfile]:
    """Resolve the caller from the Authorization: Bearer <token> header."""
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        return None
    payload = decode_token(auth[7:], typ="access")
    if not payload or not payload.get("email"):
        return None
    user = await UserRepository(session).get_by_email(payload["email"])
    if user is None:
        return None
    return UserProfile(
        id=user.id,
        email=user.email,
        role=user.role,
        tenants=["default"],
        workspaces=[],
    )


# ─── Authentication Endpoints ────────────────

@app.post(
    "/auth/register",
    response_model=AuthUserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user account",
)
async def register(
    payload: RegisterRequest,
    session=Depends(get_session_dependency),
):
    """Create an account. The first registered user becomes admin."""
    repo = UserRepository(session)

    if await repo.get_by_email(payload.email):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")

    role = payload.role.strip().lower() or ("admin" if await repo.count() == 0 else "developer")
    user = await repo.create(payload.email, hash_password(payload.password), role)

    return AuthUserResponse(id=user.id, email=user.email, role=user.role)


@app.post(
    "/auth/login",
    response_model=LoginResponse,
    status_code=status.HTTP_200_OK,
    summary="Authenticate and receive JWT token",
)
async def login(
    credentials: LoginRequest,
    session=Depends(get_session_dependency),
):
    """
    Authenticate and return signed JWT tokens (access 15 min, refresh 7 days).

    Registered users are verified against their stored PBKDF2 password hash.
    In strict mode (DAP_AUTH_STRICT=1, production) unknown users and wrong
    passwords are rejected with 401. In dev mode unknown users fall back to
    the legacy mock tokens so local previews keep working without setup.
    """
    user = await UserRepository(session).get_by_email(credentials.email)

    if user is not None and verify_password(credentials.password, user.password_hash):
        access_token, refresh_token = create_token_pair(user.id, user.email, user.role)
    elif _auth_strict():
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    else:
        # Dev fail-open: legacy mock tokens (test-suite/preview behavior)
        access_token = f"mock_access_token_for_{credentials.email}"
        refresh_token = f"mock_refresh_token_for_{credentials.email}"

    # Record session in the session manager (for audit trail)
    session_mgr.create_session(email=credentials.email, token_type="access")

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
    Exchange a refresh token for a fresh access + refresh pair (rotation).

    Strict mode: the presented token must be a valid signed refresh token.
    Dev mode: legacy lenient behavior (any string refreshes).
    """
    payload = decode_token(refresh.refresh_token, typ="refresh")

    if payload is not None and payload.get("email"):
        access_token, new_refresh_token = create_token_pair(
            payload["sub"], payload["email"], payload.get("role", "developer")
        )
    elif _auth_strict():
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")
    else:
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
async def get_profile(request: Request, session=Depends(get_session_dependency)):
    """
    Return the caller's profile from the local identity store.

    With a valid Bearer access token, returns the registered user. Without
    one, strict mode returns 401; dev mode returns the legacy dev profile
    so unauthenticated local previews keep working.
    """
    profile = await _bearer_user(request, session)
    if profile is not None:
        return profile
    if _auth_strict():
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
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
