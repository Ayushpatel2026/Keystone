import enum
import uuid
from datetime import datetime

# mypy: ignore-errors
from fastapi_users.db import SQLAlchemyBaseUserTableUUID
from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKeyConstraint,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class UserRole(enum.StrEnum):
    STUDENT = "student"
    TA = "ta"
    INSTRUCTOR = "instructor"
    SUPERVISOR = "supervisor"


class SupervisorType(enum.StrEnum):
    INTERNAL = "internal"
    EXTERNAL = "external"


class SupervisorVerificationStatus(enum.StrEnum):
    UNVERIFIED = "unverified"
    VERIFIED = "verified"


def _enum_column(enum_type: type[enum.Enum], name: str) -> Enum:
    # values_callable stores enum values ("student") instead of enum member
    # names ("STUDENT"), matching the API and database representation.
    return Enum(
        enum_type,
        name=name,
        native_enum=False,
        create_constraint=True,
        length=20,
        values_callable=lambda members: [member.value for member in members],
    )


def _role_constraints(
    role: UserRole,
) -> tuple[ForeignKeyConstraint, CheckConstraint]:
    # Composite FK ensures the profile's user_id AND role match the parent.
    # The CHECK ensures a Student profile cannot claim to be a TA, etc.
    return (
        ForeignKeyConstraint(
            ["user_id", "role"],
            ["users.id", "users.role"],
            ondelete="CASCADE",
        ),
        CheckConstraint(
            f"role = '{role.value}'",
            name="role_matches_profile",
        ),
    )


class User(SQLAlchemyBaseUserTableUUID, Base):
    # FastAPI Users supplies id, email, hashed_password, is_active,
    # is_superuser, and is_verified.
    __tablename__ = "users"

    __mapper_args__ = {"eager_defaults": True}

    __table_args__ = (
        # Required because child tables reference the composite (id, role).
        UniqueConstraint("id", "role", name="uq_users_id_role"),
    )

    first_name: Mapped[str] = mapped_column(String(100))
    last_name: Mapped[str] = mapped_column(String(100))

    role: Mapped[UserRole] = mapped_column(_enum_column(UserRole, "user_role"))

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )

    # Each relationship lets SQLAlchemy navigate from the shared User
    # object to its role-specific profile table.
    #
    # uselist=False represents a one-to-one relationship: one User has
    # at most one profile of each type.
    #
    # lazy="joined" loads the profile with the User in the same query,
    # avoiding unexpected lazy-loading operations in async code.
    #
    # cascade="all, delete-orphan" means deleting a User also deletes
    # its associated profile.
    student: Mapped["Student | None"] = relationship(  # noqa: F821
        "Student",
        uselist=False,
        lazy="joined",
        cascade="all, delete-orphan",
    )

    ta: Mapped["TA | None"] = relationship(  # noqa: F821
        "TA",
        uselist=False,
        lazy="joined",
        cascade="all, delete-orphan",
    )

    instructor: Mapped["Instructor | None"] = relationship(  # noqa: F821
        "Instructor",
        uselist=False,
        lazy="joined",
        cascade="all, delete-orphan",
    )

    supervisor: Mapped["Supervisor | None"] = relationship(  # noqa: F821
        "Supervisor",
        uselist=False,
        lazy="joined",
        cascade="all, delete-orphan",
    )

    # @property exposes profile data as a normal User attribute.
    # These are NOT database columns; they delegate to the profile.
    # This is useful when the API needs a flattened response.

    @property
    def course_id(self) -> uuid.UUID | None:
        # Students and TAs have exactly one course.
        if self.student is not None:
            return self.student.course_id

        if self.ta is not None:
            return self.ta.course_id

        return None

    @property
    def course_ids(self) -> list[uuid.UUID] | None:
        # Instructors can belong to multiple courses.
        # InstructorCourse is the association table storing these links.
        if self.instructor is None:
            return None

        return [link.course_id for link in self.instructor.course_links]

    @property
    def supervisor_type(self) -> SupervisorType | None:
        # Exposes supervisor-only data without requiring the API
        # serializer to manually navigate user.supervisor.
        if self.supervisor is None:
            return None

        return self.supervisor.supervisor_type

    @property
    def supervisor_verification_status(
        self,
    ) -> SupervisorVerificationStatus | None:
        # Same flattened-access pattern for verification status.
        if self.supervisor is None:
            return None

        return self.supervisor.verification_status
