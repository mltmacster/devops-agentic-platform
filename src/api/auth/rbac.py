"""RBAC Engine — Role-Based Access Control with ABAC Extensions

This module implements the RBAC engine that governs access control for all platform resources.
"""

from enum import Enum, auto
from typing import Set, Dict, Optional
import logging

logger = logging.getLogger(__name__)


class PermissionScope(Enum):
    """Granularity levels for permission checks."""
    SYSTEM = auto()          # Platform-wide
    TENANT = auto()          # Tenant-level
    WORKSPACE = auto()       # Workspace-level
    SANDBOX = auto()         # Sandbox/instance level


class PermissionAction(Enum):
    """Standard action verbs."""
    CREATE = auto()
    READ = auto()
    UPDATE = auto()
    DELETE = auto()
    EXECUTE = auto()         # For agentic AI / tool execution


class RoleMapper:
    """Maps role names to their associated permission scopes."""

    _ROLES = {
        "ga": PermissionScope.SYSTEM,
        "team_admin": PermissionScope.WORKSPACE,
        "developer": PermissionScope.SANDBOX,
        "readonly": PermissionScope.WORKSPACE,  # read anywhere
    }

    @classmethod
    def get(cls, role: str) -> Optional[str]:
        """Return the scope for a given role name."""
        return cls._ROLES.get(role)


class ResourceOwner:
    """Represents who can access what."""

    def __init__(self, user_id: str, role: str):
        self.user_id = user_id
        self.role = role

    @property
    def is_team_admin(self) -> bool:
        return self.role in ("team_admin", "ga")

    @property
    def is_developer(self) -> bool:
        return self.role in ("developer", "team_admin", "ga")


class ABACContext:
    """Contextual data for ABAC evaluation (IP, time, etc)."""

    def __init__(
        self,
        ip_address: Optional[str] = None,
        device_trust_score: float = 1.0,
        time_of_day: str = "business_hours",  # business_hours / after_hours
    ):
        self.ip_address = ip_address
        self.device_trust_score = device_trust_score
        self.time_of_day = time_of_day


class RBACEngine:
    """RBAC engine with ABAC extensions."""

    def __init__(self):
        self._permissions: Dict[str, Set[PermissionAction]] = {}

    def check_permission(
        self,
        user: ResourceOwner,
        resource_type: str,
        action: PermissionAction,
        scope: PermissionScope = PermissionScope.WORKSPACE,
    ) -> bool:
        """Check if user has permission to perform action on resource."""

        logger.debug(
            "RBAC check: user=%s role=%s action=%s resource=%s scope=%s",
            user.user_id, user.role, action.name, resource_type, scope.name,
        )

        # 1. Check role-based permissions
        base_perms = self._get_role_permissions(user.role)

        # 2. Check scope constraints
        if not self._check_scope(user, resource_type, scope):
            logger.warning("RBAC denied: scope mismatch")
            return False

        # 3. Check action permissions
        if action in base_perms:
            logger.info("RBAC granted")
            return True

        # 4. Check ABAC extensions (e.g., IP allowlist, time-based)
        # In production: would use ABACContext here

        logger.warning("RBAC denied")
        return False

    def _get_role_permissions(self, role: str) -> Set[PermissionAction]:
        """Map roles to their base permissions."""
        role_perms = {
            "ga": {PermissionAction.CREATE, PermissionAction.READ,
                   PermissionAction.UPDATE, PermissionAction.DELETE,
                   PermissionAction.EXECUTE},
            "team_admin": {PermissionAction.CREATE, PermissionAction.READ,
                          PermissionAction.UPDATE, PermissionAction.DELETE},
            "developer": {PermissionAction.CREATE, PermissionAction.READ,
                         PermissionAction.UPDATE},
            "readonly": {PermissionAction.READ},
        }
        return role_perms.get(role, set())

    def _check_scope(self, user: ResourceOwner, resource_type: str, scope: PermissionScope) -> bool:
        """Check if user's access level is sufficient for the requested scope."""

        # GA can do everything at any scope
        if user.role == "ga":
            return True

        # Team admin can do workspace-level ops on their team's resources
        if user.role == "team_admin":
            return scope in (PermissionScope.WORKSPACE, PermissionScope.SANDBOX)

        # Developer can only do sandbox-level ops on their own resources
        if user.role == "developer":
            return scope in (PermissionScope.SANDBOX,)

        # Read-only can only read at any scope
        if user.role == "readonly":
            return True  # readonly can read at any scope

        return False


def get_rbac_engine() -> RBACEngine:
    """Factory function for the RBAC engine."""
    return RBACEngine()
