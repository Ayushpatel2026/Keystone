import uuid

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.courses.models import Course
from app.modules.projects.lifecycle import (
    CapacityInvariantError,
    accepts_applications,
    derive_status,
)
from app.modules.projects.models import Project, ProjectStatus
from app.modules.projects.schemas import ProjectCreate, ProjectUpdate
from app.modules.users.models import Supervisor


# TODO: After PoC, create global exception handler to avoid redundancy.
class CourseNotFoundError(Exception):
    pass


class SupervisorNotFoundError(Exception):
    pass


class ProjectNotFoundError(Exception):
    pass


class ProjectOwnershipError(Exception):
    # Only the project's supervisor may update it.
    pass


class CapacityChangeNotSupportedError(Exception):
    # Capacity changes must account for reservations once applications exist.
    pass


class ProjectNotOpenError(Exception):
    # Raised when an action needs an OPEN project but it is FULL or CLOSED.
    pass


class ProjectCapacityFullError(Exception):
    # Raised when a supervisor tries to reserve a slot on a project with none free.
    # Also a 409. It is the "a supervisor cannot accept a team if no capacity remains" rule.
    pass


async def create_project(
    session: AsyncSession,
    data: ProjectCreate,
    supervisor_id: uuid.UUID,
) -> Project:
    # The caller supplies the acting supervisor separately from the request body.
    # Authentication or PoC actor selection belongs in the router.
    if await session.get(Supervisor, supervisor_id) is None:
        raise SupervisorNotFoundError(supervisor_id)

    if await session.get(Course, data.course_id) is None:
        raise CourseNotFoundError(data.course_id)

    project = Project(
        **data.model_dump(),
        supervisor_id=supervisor_id,
        status=ProjectStatus.OPEN,
    )
    session.add(project)

    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        raise

    await session.refresh(project)
    return project


async def get_project(session: AsyncSession, project_id: uuid.UUID) -> Project | None:
    return await session.get(Project, project_id)


async def list_projects(
    session: AsyncSession,
    course_id: uuid.UUID | None = None,
    supervisor_id: uuid.UUID | None = None,
    status: ProjectStatus | None = None,
) -> list[Project]:
    statement = select(Project).order_by(Project.title, Project.id)

    if course_id is not None:
        statement = statement.where(Project.course_id == course_id)
    if supervisor_id is not None:
        statement = statement.where(Project.supervisor_id == supervisor_id)
    if status is not None:
        statement = statement.where(Project.status == status)

    return list(await session.scalars(statement))


async def update_project(
    session: AsyncSession,
    project_id: uuid.UUID,
    data: ProjectUpdate,
    supervisor_id: uuid.UUID,
) -> Project:
    project = await get_project(session, project_id)
    if project is None:
        raise ProjectNotFoundError(project_id)
    if project.supervisor_id != supervisor_id:
        raise ProjectOwnershipError(project_id)

    changes = data.model_dump(exclude_unset=True)

    # Do not modify the object until all checks pass.
    # TODO: After PoC, allow capacity changes if reserved teams still fit.
    # Update Open/Full status, or return an error if capacity is too low.
    if (
        "supervisor_capacity" in changes
        and changes["supervisor_capacity"] != project.supervisor_capacity
    ):
        raise CapacityChangeNotSupportedError(
            "Capacity is set at creation; editing it requires reservation checks"
        )

    if "course_id" in changes and await session.get(Course, changes["course_id"]) is None:
        raise CourseNotFoundError(changes["course_id"])

    if not changes:
        return project

    for field, value in changes.items():
        setattr(project, field, value)

    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        raise

    await session.refresh(project)
    return project


async def lock_projects(session: AsyncSession, project_ids: list[uuid.UUID]) -> list[Project]:
    # Load projects and take a row lock on each until the transaction ends.
    # Two requests touching the same
    # project (e.g. a supervisor accepting while a team applies) queue up here instead of
    # reading the same stale state and both writing.

    # Deduplicate, then sort. Locks are always requested in id order so that two
    # transactions locking overlapping sets can't each wait on the other (deadlock).
    ordered_ids = sorted(set(project_ids))
    if not ordered_ids:
        return []

    query = (
        select(Project)
        .where(Project.id.in_(ordered_ids))
        # ORDER BY makes Postgres acquire the row locks in this exact order.
        .order_by(Project.id)
        # Emits SELECT ... FOR UPDATE: other transactions trying to lock or modify these
        # rows block until we commit or roll back. of=Project restricts the lock to the
        # projects table (no other joined tables get locked).
        .with_for_update(of=Project)
        # SQLAlchemy keeps one Python object per row in the session's identity map and
        # normally reuses it without overwriting its fields. populate_existing forces it to
        # overwrite them with what the database says now, so the status and slot count
        # we are about to reason about aren't stale values cached earlier in this session.
        .execution_options(populate_existing=True)
    )
    projects = list((await session.scalars(query)).all())

    # Fewer rows than ids means at least one id doesn't exist.
    if len(projects) != len(ordered_ids):
        missing = set(ordered_ids) - {p.id for p in projects}
        raise ProjectNotFoundError(str(sorted(missing)))
    return projects


async def lock_project(session: AsyncSession, project_id: uuid.UUID) -> Project:
    # Single-project convenience wrapper around lock_projects.
    # The one-element unpack also asserts exactly one row came back.
    (project,) = await lock_projects(session, [project_id])
    return project


def require_open_for_applications(project: Project) -> None:
    # Business rule check for "can a team apply to this project right now?".
    # Run it on a project loaded via lock_project, so the status can't change between
    # this check and the insert that follows it.
    if not accepts_applications(project.status):
        raise ProjectNotOpenError(project.status.value)


def reserve_slot(project: Project) -> None:
    # A supervisor accepted a team: one more slot is taken. Call only on a project returned
    # by lock_project, inside the transaction that also changes the application status.
    #
    # This lock matters because `project.slots_reserved += 1` does NOT emit
    # "SET slots_reserved = slots_reserved + 1". SQLAlchemy reads the value into Python, adds
    # one, and emits "SET slots_reserved = <slots_reserved + 1>". Without the row lock, two requests
    # could both read 1 and both write 2, losing an update.
    if project.status == ProjectStatus.CLOSED:
        raise ProjectNotOpenError(project.status.value)

    if project.slots_reserved >= project.supervisor_capacity:
        raise ProjectCapacityFullError(str(project.id))

    project.slots_reserved += 1
    # Recompute the status from the new count, so the counter and the status always move
    # together. Nothing is written yet, so if the transaction rolls back,
    # the status will roll back too.
    project.status = derive_status(
        project.status, project.supervisor_capacity, project.slots_reserved
    )


def release_slot(project: Project) -> None:
    # A team's slot is freed. declined, withdrawn, or rejected.
    # Same locking rules as reserve_slot. The applications service calls this exactly when
    # an application leaves the set of slot-holding statuses, which is how withdraw and
    # every other exit path stays consistent.

    # Note that we do not check for CLOSED here. Closed implies that selection period is over
    # a team may still withdraw from a project.
    if project.slots_reserved <= 0:
        # Releasing when nothing is reserved means a caller released twice or released for
        # an application that never held a slot
        raise CapacityInvariantError(
            f"cannot release a slot on project {project.id}: none are reserved"
        )
    project.slots_reserved -= 1
    project.status = derive_status(
        project.status, project.supervisor_capacity, project.slots_reserved
    )
