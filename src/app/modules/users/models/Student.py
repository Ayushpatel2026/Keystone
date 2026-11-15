import uuid

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.modules.users.models.User import (
    UserRole,
    _enum_column,
    _role_constraints,
)


class Student(Base):
    # A Student profile is separate from the shared User identity.
    __tablename__ = "students"

    # Enforces that this profile belongs to a User whose role is student.
    __table_args__ = _role_constraints(UserRole.STUDENT)

    # Using user_id as the primary key ensures one Student profile
    # per User rather than generating a separate profile identifier.
    user_id: Mapped[uuid.UUID] = mapped_column(primary_key=True)

    # Role is duplicated intentionally for the composite FK constraint.
    role: Mapped[UserRole] = mapped_column(
        _enum_column(UserRole, "user_role"),
        default=UserRole.STUDENT,
        server_default=UserRole.STUDENT.value,
    )

    student_number: Mapped[str] = mapped_column(
        String(20),
        unique=True,
    )

    course_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("courses.id"),
        index=True,
    )
