import uuid
from typing import Literal

from app.modules.users.models.User import UserRole
from app.modules.users.schemas.UserRead import UserRead


class StudentRead(UserRead):
    # Literal makes the role statically fixed for this response schema.
    role: Literal[UserRole.STUDENT] = UserRole.STUDENT

    # Student-specific API response field.
    course_id: uuid.UUID
