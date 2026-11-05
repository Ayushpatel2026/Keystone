import enum
from datetime import datetime

from fastapi_users.db import SQLAlchemyBaseUserTableUUID
from sqlalchemy import CheckConstraint, DateTime, Enum, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class UserRole(enum.StrEnum):
    STUDENT = "student"
    TA = "ta"
    INSTRUCTOR = "instructor"
    SUPERVISOR = "supervisor"


class SupervisorType(enum.StrEnum):
    INTERNAL = "internal"  # McMaster faculty
    EXTERNAL = "external"  # industry sponsors


class SupervisorVerificationStatus(enum.StrEnum):
    # 'unverified' means the project proposal has not been approved.
    UNVERIFIED = "unverified"
    VERIFIED = "verified"


def _enum_column(enum_type: type[enum.Enum], name: str) -> Enum:
    return Enum(
        enum_type,
        name=name,
        native_enum=False,
        create_constraint=True,
        length=20,
        values_callable=lambda members: [member.value for member in members],
    )


class User(SQLAlchemyBaseUserTableUUID, Base):
    # Provides: id, email, hashed_password, is_active, is_superuser, is_verified
    __tablename__ = "users"
    __mapper_args__ = {"eager_defaults": True}

    __table_args__ = (
        CheckConstraint(
            "NOT is_superuser OR role IN ('instructor', 'ta')",
            name="admin_only_staff",
        ),
        CheckConstraint(
            "(role = 'supervisor' AND supervisor_type IS NOT NULL"
            " AND supervisor_verification_status IS NOT NULL)"
            " OR (role <> 'supervisor' AND supervisor_type IS NULL"
            " AND supervisor_verification_status IS NULL)",
            name="supervisor_fields_match_role",
        ),
        CheckConstraint(
            "supervisor_type IS DISTINCT FROM 'internal'"
            " OR supervisor_verification_status = 'verified'",
            name="internal_supervisor_verified",
        ),
    )

    name: Mapped[str] = mapped_column(String(200))

    # Defaults to student so public registration never needs to choose a role.
    role: Mapped[UserRole] = mapped_column(
        _enum_column(UserRole, "user_role"),
        default=UserRole.STUDENT,
        server_default=UserRole.STUDENT.value,
    )

    supervisor_type: Mapped[SupervisorType | None] = mapped_column(
        _enum_column(SupervisorType, "supervisor_type")
    )
    supervisor_verification_status: Mapped[SupervisorVerificationStatus | None] = mapped_column(
        _enum_column(SupervisorVerificationStatus, "supervisor_verification_status")
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )