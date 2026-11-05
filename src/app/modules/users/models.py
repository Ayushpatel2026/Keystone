import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Enum,
    String,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class UserRole(enum.StrEnum):
    # User roles supported by Keystone.
    STUDENT = "student"
    TA = "ta"
    INSTRUCTOR = "instructor"
    SUPERVISOR = "supervisor"


class AccountStatus(enum.StrEnum):
    # Lifecycle status of an account.
    ACTIVE = "active"
    DISABLED = "disabled"
    PENDING = "pending"


class SupervisorType(enum.StrEnum):
    # Internal supervisors are McMaster faculty.
    INTERNAL = "internal"

    # External supervisors are industry sponsors.
    EXTERNAL = "external"


"""
Indicates whether an external supervisor's account has been verified by the course instructor.
'unverified' means project proposal has not been approved.
"""


class SupervisorVerificationStatus(enum.StrEnum):
    # Supervisor verification state.
    UNVERIFIED = "unverified"
    VERIFIED = "verified"


def _enum_column(enum_type: type[enum.Enum], name: str) -> Enum:
    # Store enum values as VARCHAR with a CHECK constraint.
    # This avoids PostgreSQL native enum types, which are harder to evolve.
    return Enum(
        enum_type,
        name=name,
        native_enum=False,
        create_constraint=True,
        length=20,
        values_callable=lambda members: [member.value for member in members],
    )


class User(Base):
    # All Keystone user types share this table.
    __tablename__ = "users"

    # Tell SQLAlchemy to eagerly fetch generated database defaults.
    __mapper_args__ = {"eager_defaults": True}

    __table_args__ = (
        # Admin permissions are restricted to instructors and TAs.
        CheckConstraint(
            "NOT is_admin OR role IN ('instructor', 'ta')",
            name="admin_only_staff",
        ),
        # Supervisor-only attributes must exist exactly when role is supervisor.
        CheckConstraint(
            "(role = 'supervisor' AND supervisor_type IS NOT NULL"
            " AND verification_status IS NOT NULL)"
            " OR (role <> 'supervisor' AND supervisor_type IS NULL"
            " AND verification_status IS NULL)",
            name="supervisor_fields_match_role",
        ),
        # Internal supervisors must always be verified.
        CheckConstraint(
            "supervisor_type IS DISTINCT FROM 'internal' OR verification_status = 'verified'",
            name="internal_supervisor_verified",
        ),
    )

    # UUID primary key generated in Python.
    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,
    )

    # User's display name.
    name: Mapped[str] = mapped_column(String(200))

    # Email address, which must be unique.
    email: Mapped[str] = mapped_column(String(320), unique=True)

    # Null for accounts authenticated by SSO or external identity providers.
    password_hash: Mapped[str | None] = mapped_column(String(255))

    # User's Keystone role.
    role: Mapped[UserRole] = mapped_column(_enum_column(UserRole, "user_role"))

    # Account status defaults to active in Python and PostgreSQL.
    account_status: Mapped[AccountStatus] = mapped_column(
        _enum_column(AccountStatus, "account_status"),
        default=AccountStatus.ACTIVE,
        server_default=AccountStatus.ACTIVE.value,
    )

    # Whether the account has administrative permissions.
    is_admin: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        server_default=text("false"),
    )

    # Only supervisors have supervisor-specific attributes.
    supervisor_type: Mapped[SupervisorType | None] = mapped_column(
        _enum_column(SupervisorType, "supervisor_type")
    )

    # Only supervisors have verification status.
    supervisor_verification_status: Mapped[SupervisorVerificationStatus | None] = mapped_column(
        _enum_column(SupervisorVerificationStatus, "supervisor_verification_status")
    )

    # PostgreSQL automatically assigns the creation timestamp.
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    # PostgreSQL assigns the initial timestamp; SQLAlchemy updates it on changes.
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )
