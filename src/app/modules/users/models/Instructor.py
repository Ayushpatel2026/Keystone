# mypy: ignore-errors
import uuid

from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.modules.users.models.User import (
    UserRole,
    _enum_column,
    _role_constraints,
)


class Instructor(Base):
    __tablename__ = "instructors"

    __table_args__ = _role_constraints(UserRole.INSTRUCTOR)

    user_id: Mapped[uuid.UUID] = mapped_column(primary_key=True)

    role: Mapped[UserRole] = mapped_column(
        _enum_column(UserRole, "user_role"),
        default=UserRole.INSTRUCTOR,
        server_default=UserRole.INSTRUCTOR.value,
    )

    # An Instructor can have multiple course links.
    #
    # selectin loads these related rows using a separate query for the
    # collection, rather than multiplying rows in the main User query.
    #
    # delete-orphan ensures removing a link from this collection
    # deletes that association row.
    course_links: Mapped[list["InstructorCourse"]] = relationship(  # noqa: F821
        "InstructorCourse",
        lazy="selectin",
        cascade="all, delete-orphan",
    )
