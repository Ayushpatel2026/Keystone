from typing import Literal

from app.modules.users.models.User import (
    SupervisorType,
    SupervisorVerificationStatus,
    UserRole,
)
from app.modules.users.schemas.UserRead import UserRead


class SupervisorRead(UserRead):
    role: Literal[UserRole.SUPERVISOR] = UserRole.SUPERVISOR

    supervisor_type: SupervisorType
    supervisor_verification_status: SupervisorVerificationStatus
