import uuid
from datetime import datetime

from fastapi_users import schemas

from app.modules.users.models import (
    SupervisorType,
    SupervisorVerificationStatus,
    UserRole,
)


class UserRead(schemas.BaseUser[uuid.UUID]):
    name: str
    role: UserRole
    supervisor_type: SupervisorType | None = None
    supervisor_verification_status: SupervisorVerificationStatus | None = None
    created_at: datetime
    updated_at: datetime


class UserCreate(schemas.BaseUserCreate):
    name: str
    # No `role` here on purpose: otherwise anyone could register as an instructor.


class UserUpdate(schemas.BaseUserUpdate):
    name: str | None = None
