from enum import Enum
from typing import Set


class Role(str, Enum):
    VIEWER = "viewer"
    MANAGER = "manager"
    SALES_REP = "sales_rep"


class Permission(str, Enum):
    CUSTOMERS_READ = "customers:read"
    SALES_READ = "sales:read"
    DRAFT_CREATE = "draft:create"
    DRAFT_READ = "draft:read"
    DRAFT_APPROVE = "draft:approve"
    DRAFT_SEND = "draft:send"


ROLE_PERMISSIONS: dict[Role, Set[Permission]] = {
    Role.VIEWER: {
        Permission.CUSTOMERS_READ,
        Permission.SALES_READ,
        Permission.DRAFT_READ,
    },
    Role.MANAGER: {
        Permission.CUSTOMERS_READ,
        Permission.SALES_READ,
        Permission.DRAFT_CREATE,
        Permission.DRAFT_READ,
        Permission.DRAFT_APPROVE,
        Permission.DRAFT_SEND,
    },
    Role.SALES_REP: {
        Permission.CUSTOMERS_READ,
        Permission.SALES_READ,
        Permission.DRAFT_CREATE,
        Permission.DRAFT_READ,
    },
}


def has_permission(role: str, permission: Permission) -> bool:
    try:
        r = Role(role)
    except ValueError:
        return False
    return permission in ROLE_PERMISSIONS.get(r, set())
