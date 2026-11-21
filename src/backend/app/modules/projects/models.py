# mypy: ignore-errors
import enum
import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, Enum, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class ProjectStatus(enum.StrEnum):
    # The PoC starts with listed projects; proposal review is outside its scope.
    OPEN = "open"
    FULL = "full"
    CLOSED = "closed"


class Project(Base):
    __tablename__ = "projects"

    __mapper_args__ = {"eager_defaults": True}

    __table_args__ = (
        CheckConstraint("supervisor_capacity > 0", name="positive_supervisor_capacity"),
        # Last line of defence for the slot counter: Postgres rejects any UPDATE that would
        # leave it negative or above capacity, even if application code has a bug.
        # The metadata's naming convention turns this name into
        # ck_projects_slots_reserved_within_capacity.
        CheckConstraint(
            "slots_reserved >= 0 AND slots_reserved <= supervisor_capacity",
            name="slots_reserved_within_capacity",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    title: Mapped[str] = mapped_column(String(200))
    background: Mapped[str] = mapped_column(Text)

    # Listed supervisor-created projects always have a supervisor and course.
    supervisor_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("supervisors.user_id"), index=True)
    course_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("courses.id"), index=True)

    supervisor_capacity: Mapped[int] = mapped_column()

    # Number of slots reserved by supervisor-accepted teams (the R in the lifecycle diagram).
    # Invariants: 0 <= slots_reserved <= supervisor_capacity, and it equals the number of this
    # project's applications whose status holds a slot.
    # default=0 covers Python-side inserts; server_default="0" covers raw SQL and the migration.
    slots_reserved: Mapped[int] = mapped_column(default=0, server_default="0")

    status: Mapped[ProjectStatus] = mapped_column(
        Enum(
            ProjectStatus,
            name="project_status",
            native_enum=False,
            create_constraint=True,
            length=20,
            values_callable=lambda members: [member.value for member in members],
        ),
        default=ProjectStatus.OPEN,
        server_default=ProjectStatus.OPEN.value,
    )

    supervisor: Mapped["Supervisor"] = relationship("Supervisor")  # noqa: F821
    course: Mapped["Course"] = relationship("Course")  # noqa: F821

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
