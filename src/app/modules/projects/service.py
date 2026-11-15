import uuid

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.courses.models import Course
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
