import uuid

from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.modules.users.models.User import (
    UserRole,
    _enum_column,
    _role_constraints,
)


class TA(Base):
    __tablename__ = "tas"

    # Prevents a non-TA user from having a TA profile.
    __table_args__ = _role_constraints(UserRole.TA)

    user_id: Mapped[uuid.UUID] = mapped_column(primary_key=True)

    role: Mapped[UserRole] = mapped_column(
        _enum_column(UserRole, "user_role"),
        default=UserRole.TA,
        server_default=UserRole.TA.value,
    )

    # A TA belongs to exactly one course.
    course_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("courses.id"),
        index=True,
    )
