import uuid
from datetime import datetime

from fastapi_users import schemas

from app.modules.users.models.User import UserRole


class UserRead(schemas.BaseUser[uuid.UUID]):
    # Common fields inherited by all role-specific response schemas.
    # BaseUser includes id, email, is_active, is_superuser, is_verified.
    first_name: str
    last_name: str
    role: UserRole
    created_at: datetime
    updated_at: datetime
