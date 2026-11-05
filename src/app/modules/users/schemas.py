import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.modules.users.models import (
    AccountStatus,
    SupervisorType,
    SupervisorVerificationStatus,
    UserRole,
)


class UserResponse(BaseModel):
    # Allow Pydantic to read values directly from SQLAlchemy ORM objects.
    model_config = ConfigDict(from_attributes=True)

    # Public user information returned by the API.
    id: uuid.UUID
    name: str
    email: str
    role: UserRole
    account_status: AccountStatus
    is_admin: bool

    # These fields are null for non-supervisors.
    supervisor_type: SupervisorType | None
    supervisor_verification_status: SupervisorVerificationStatus | None = Field(
        default=None,
        description="Indicates whether an external supervisor's account has been "
        "verified by the course instructor. "
        "'unverified' means project proposal has not been approved.",
    )

    # Database timestamps.
    created_at: datetime
    updated_at: datetime
