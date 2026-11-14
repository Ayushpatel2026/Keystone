import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Index, UniqueConstraint, func, text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.modules.applications.lifecycle import (
    HAS_AGREEMENT,
    INITIAL_STATUS,
    ApplicationStatus,
)

# Builds "status IN ('agreed', ...)" from the same set the lifecycle uses, so the partial
# index below can't silently disagree with the code about what counts as an agreement.
# sorted() keeps the output deterministic.
_AGREEMENT_SQL = "status IN (" + ", ".join(f"'{s.value}'" for s in sorted(HAS_AGREEMENT)) + ")"


class ProjectApplication(Base):
    # One team's relationship with one project ("Team on a project").
    __tablename__ = "project_applications"

    # eager_defaults makes SQLAlchemy fetch server-generated values (created_at, updated_at)
    # right after INSERT/UPDATE via RETURNING. Without it, reading them later would trigger a
    # lazy load, which async sessions can't do.
    __mapper_args__ = {"eager_defaults": True}

    __table_args__ = (
        # A team can apply to a given project only once. This is the source of truth for
        # duplicates
        UniqueConstraint("team_id", "project_id"),
        # Partial unique index: among rows in an agreement status, each team may appear at
        # most once. postgresql_where limits the index to matching rows,
        # so a team can still have many applications in other statuses.
        Index(
            "uq_project_applications_one_agreement_per_team",
            "team_id",
            unique=True,
            postgresql_where=text(_AGREEMENT_SQL),
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)

    # No ondelete here, deliberately. teams/projects use CASCADE elsewhere, but cascading
    # would let a deleted team silently vanish while its slot stays counted in
    # projects.slots_reserved. With NO ACTION, deleting a team or project that has
    # applications fails loudly instead.
    team_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("teams.id"))

    # index=True because supervisors and the slot check look up applications by project.
    project_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("projects.id"), index=True)

    status: Mapped[ApplicationStatus] = mapped_column(
        Enum(
            ApplicationStatus,
            name="application_status",
            native_enum=False,  # store as VARCHAR + CHECK, not a Postgres ENUM (easier to migrate)
            create_constraint=True,  # emit the CHECK that restricts values to the enum
            length=40,  # longest value is 30 chars right now
            # Store the enum VALUES ("applied") rather than the member NAMES ("APPLIED").
            values_callable=lambda members: [m.value for m in members],
        ),
        default=INITIAL_STATUS,  # Python-side default for ORM inserts
        server_default=INITIAL_STATUS.value,  # DB-side default for raw SQL and the migration
    )

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
