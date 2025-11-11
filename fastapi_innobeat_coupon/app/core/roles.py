from __future__ import annotations

from enum import Enum


class RoleCode(str, Enum):
    ADMIN = "ADMIN"
    OPERATOR = "OPERATOR"
    VIEWER = "VIEWER"


DEFAULT_READ_ROLES: set[str] = {
    RoleCode.ADMIN.value,
    RoleCode.OPERATOR.value,
    RoleCode.VIEWER.value,
}


DEFAULT_WRITE_ROLES: set[str] = {
    RoleCode.ADMIN.value,
    RoleCode.OPERATOR.value,
}
