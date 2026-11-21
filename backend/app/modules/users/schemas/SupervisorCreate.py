from typing import Annotated, Literal

from fastapi_users import schemas
from pydantic import StringConstraints

from app.modules.users.models.User import (
    SupervisorType,
    SupervisorVerificationStatus,
    UserRole,
)


class SupervisorCreate(schemas.BaseUserCreate):
    first_name: Annotated[
        str,
        StringConstraints(strip_whitespace=True, min_length=1, max_length=100),
    ]

    last_name: Annotated[
        str,
        StringConstraints(strip_whitespace=True, min_length=1, max_length=100),
    ]

    # TODO: POC ONLY - users can self-select their role. Remove this POST POC.
    role: Literal[UserRole.SUPERVISOR] = UserRole.SUPERVISOR

    # TODO: POC ONLY - users can self-select their supervisor. Remove this POST POC.
    supervisor_type: SupervisorType = SupervisorType.EXTERNAL

    # TODO: POC ONLY — users can self-verify. Remove this POST POC.
    verification_status: SupervisorVerificationStatus = SupervisorVerificationStatus.UNVERIFIED
