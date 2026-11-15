import uuid
from typing import Literal

from app.modules.users.models.User import UserRole
from app.modules.users.schemas.UserRead import UserRead


class InstructorRead(UserRead):
    role: Literal[UserRole.INSTRUCTOR] = UserRole.INSTRUCTOR

    # Instructor courses are represented as a list because the relationship
    # is many-to-many
    course_ids: list[uuid.UUID]
