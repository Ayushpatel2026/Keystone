import uuid

from sqlalchemy import CheckConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.modules.users.models.User import (
    SupervisorType,
    SupervisorVerificationStatus,
    UserRole,
    _enum_column,
    _role_constraints,
)


class Supervisor(Base):
    __tablename__ = "supervisors"

    __table_args__ = (
        *_role_constraints(UserRole.SUPERVISOR),
        # Internal supervisors are required to be verified.
        # This is a database-level constraint, not just API validation.
        CheckConstraint(
            "supervisor_type IS DISTINCT FROM 'internal' OR verification_status = 'verified'",
            name="internal_supervisor_verified",
        ),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(primary_key=True)

    role: Mapped[UserRole] = mapped_column(
        _enum_column(UserRole, "user_role"),
        default=UserRole.SUPERVISOR,
        server_default=UserRole.SUPERVISOR.value,
    )

    supervisor_type: Mapped[SupervisorType] = mapped_column(
        _enum_column(SupervisorType, "supervisor_type"),
        default=SupervisorType.EXTERNAL,
        server_default=SupervisorType.EXTERNAL.value,
    )

    verification_status: Mapped[SupervisorVerificationStatus] = mapped_column(
        _enum_column(
            SupervisorVerificationStatus,
            "supervisor_verification_status",
        ),
        default=SupervisorVerificationStatus.UNVERIFIED,
        server_default=SupervisorVerificationStatus.UNVERIFIED.value,
    )
