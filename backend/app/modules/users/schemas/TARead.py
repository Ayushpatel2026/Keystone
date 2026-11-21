import uuid
from typing import Literal

from app.modules.users.models.User import UserRole
from app.modules.users.schemas.UserRead import UserRead


class TARead(UserRead):
    role: Literal[UserRole.TA] = UserRole.TA

    course_id: uuid.UUID
