import uuid
from datetime import datetime

from fastapi_users import schemas

from app.modules.users.models import (
    SupervisorType,
    SupervisorVerificationStatus,
    UserRole,
)


class UserRead(schemas.BaseUser[uuid.UUID]):
    first_name: str
    last_name: str
    role: UserRole
    supervisor_type: SupervisorType | None = None
    supervisor_verification_status: SupervisorVerificationStatus | None = None
    created_at: datetime
    updated_at: datetime


class UserCreate(schemas.BaseUserCreate):
    first_name: str
    last_name: str


class UserUpdate(schemas.BaseUserUpdate):
    first_name: str | None = None
    last_name: str | None = None
