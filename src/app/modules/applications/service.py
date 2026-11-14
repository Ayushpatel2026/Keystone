import uuid

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.applications.lifecycle import (
    INITIAL_STATUS,
    has_agreement,
)
from app.modules.applications.models import ProjectApplication
from app.modules.applications.schemas import ApplicationCreate
from app.modules.projects.service import (
    ProjectNotFoundError,
    ProjectNotOpenError,
    lock_project,
    require_open_for_applications,
)
from app.modules.teams.service import TeamNotFoundError, is_member, lock_team

# Re-exported so the router can write service.TeamNotFoundError etc.
__all__ = [
    "ProjectNotFoundError",
    "ProjectNotOpenError",
    "TeamNotFoundError",
    "NotTeamMemberError",
    "CourseMismatchError",
    "TeamAlreadyAgreedError",
    "DuplicateApplicationError",
    "apply_to_project",
]


class NotTeamMemberError(Exception):
    # The acting student is not on the team they are applying for.
    pass


class CourseMismatchError(Exception):
    # Team and project belong to different courses.
    pass


class TeamAlreadyAgreedError(Exception):
    # The team has already agreed to a project, so it can't apply to more.
    pass


class DuplicateApplicationError(Exception):
    # The team already applied to this project.
    pass


async def _apply(
    session: AsyncSession, data: ApplicationCreate, student_id: uuid.UUID
) -> ProjectApplication:
    # Lock the team first (lock order: team, then project). This serialises this team's actions.
    team = await lock_team(session, data.team_id)

    # The actor must be on the team.
    if not await is_member(session, team.id, student_id):
        raise NotTeamMemberError(str(student_id))

    # Lock the project row. Any supervisor accept or other apply on it now waits for us,
    # so "is it open?" below can't change before our insert is committed. This is what
    # keeps "a full project has no pending applications" true under concurrency.
    project = await lock_project(session, data.project_id)

    # Teams can only apply within their own course.
    if team.course_id != project.course_id:
        raise CourseMismatchError(
            f"team course {team.course_id} != project course {project.course_id}"
        )

    # Only OPEN projects take applications. FULL and CLOSED raise ProjectNotOpenError.
    require_open_for_applications(project)

    # Look at what this team has already done. Safe from races because we hold the team lock.
    rows = await session.execute(
        select(ProjectApplication.project_id, ProjectApplication.status).where(
            ProjectApplication.team_id == team.id
        )
    )
    existing = rows.all()

    # Checked before the agreement rule so a repeat apply gets the more specific error.
    if any(project_id == project.id for project_id, _ in existing):
        raise DuplicateApplicationError(str(project.id))

    # A team in an agreement is committed to one project and must hold no pending applications.
    if any(has_agreement(status) for _, status in existing):
        raise TeamAlreadyAgreedError(str(team.id))

    # Create the application. Applying does NOT touch the project as no slot is reserved,
    # slots_reserved and status are unchanged, and other teams can still apply.
    application = ProjectApplication(team_id=team.id, project_id=project.id, status=INITIAL_STATUS)
    session.add(application)
    return application


async def apply_to_project(
    session: AsyncSession, data: ApplicationCreate, student_id: uuid.UUID
) -> ProjectApplication:
    # Transaction boundary for the whole apply action. The locks taken in _apply are held
    # until commit or rollback. Everything in _apply runs in the one transaction the session
    # opened on its first query ("autobegin"), so the checks and the insert are atomic.
    try:
        application = await _apply(session, data, student_id)
        await session.commit()  # INSERT happens at commit/flush; all locks released here
    except IntegrityError as exc:
        # This is raised when the unique constraint on (team_id, project_id) fired.
        # The pre-check should already have caught it, so this only triggers on a
        #  bug or a bypass of the team lock.
        await session.rollback()
        raise DuplicateApplicationError(str(data.project_id)) from exc
    except Exception:
        # Any domain error above (not open, not a member, ...) arrives here. Roll back
        # explicitly so the row locks are released now rather than when the session closes.
        await session.rollback()
        raise

    # Reload so server-generated fields (created_at, updated_at) are populated after commit.
    await session.refresh(application)
    return application
