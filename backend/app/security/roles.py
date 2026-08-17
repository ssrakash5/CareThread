"""
Demo RBAC (spec section 16). Not real auth — identity/role come from
request headers, which is fine for a hackathon demo but must be replaced
with real auth before any deployment.
"""
from enum import Enum

from fastapi import Header, HTTPException


class Role(str, Enum):
    CLINICIAN = "CLINICIAN"
    CARE_COORDINATOR = "CARE_COORDINATOR"
    ADMINISTRATOR = "ADMINISTRATOR"
    AUDITOR = "AUDITOR"


APPROVAL_ROLES = {Role.CLINICIAN, Role.ADMINISTRATOR}


class CurrentUser:
    def __init__(self, user_id: str, role: Role):
        self.user_id = user_id
        self.role = role


def get_current_user(
    x_user_id: str = Header(default="demo_clinician"),
    x_user_role: Role = Header(default=Role.CLINICIAN),
) -> CurrentUser:
    return CurrentUser(user_id=x_user_id, role=x_user_role)


def require_approval_role(user: CurrentUser):
    if user.role not in APPROVAL_ROLES:
        raise HTTPException(status_code=403, detail="Role not permitted to approve consequential actions")
