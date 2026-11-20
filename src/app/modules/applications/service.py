import uuid

from sqlalchemy import ColumnElement, Select, false, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.applications.lifecycle import (
    INITIAL_STATUS,
    ApplicationStatus,
    has_agreement,
)
from app.modules.applications.models import ProjectApplication
from app.modules.applications.schemas import ApplicationCreate
from app.modules.projects.models import Project
from app.modules.projects.service import (
    ProjectNotFoundError,
    ProjectNotOpenError,
    lock_project,
    require_open_for_applications,
)
from app.modules.teams.models import TeamMember
from app.modules.teams.service import TeamNotFoundError, is_member, lock_team
from app.modules.users.models import User, UserRole

# Re-exported so the router can write service.TeamNotFoundError etc.
__all__ = [
    "ProjectNotFoundError",
    "ProjectNotOpenError",
    "TeamNotFoundError",
    "NotTeamMemberError",
    "CourseMismatchError",
    "TeamAlreadyAgreedError",
    "DuplicateApplicationError",
    "ApplicationNotFoundError",
    "CourseAccessDeniedError",
    "apply_to_project",
    "list_applications",
    "get_application",
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


class ApplicationNotFoundError(Exception):
    # No application with this id exists, OR it exists but the user may not read it. The two
    # cases are deliberately indistinguishable so ids outside the user's scope aren't revealed.
    pass


class CourseAccessDeniedError(Exception):
    # A course filter names a course the user is not a member of (MIS: Unauthorized).
    pass


# ---------------------------------------------------------------------------
# Reading applications (MIS listApplications).
# Visibility follows the SRS table: an application is readable by its participants (members
# of the applying team and the project's supervisor) and by the course's instructors and TAs.
# ---------------------------------------------------------------------------


def _member_course_ids(user: User) -> set[uuid.UUID] | None:
    # The courses the user belongs to, or None for roles that aren't tied to a course
    # (supervisors). Instructors can have several courses, students and TAs exactly one.
    # Only the profile matching the role is touched: async sessions can't lazy-load, so
    # probing the other profiles (as User.course_id does) could fail on a partly loaded user.
    match user.role:
        case UserRole.INSTRUCTOR:
            if user.instructor is None:
                return set()
            return {link.course_id for link in user.instructor.course_links}
        case UserRole.STUDENT:
            return {user.student.course_id} if user.student is not None else set()
        case UserRole.TA:
            return {user.ta.course_id} if user.ta is not None else set()
        case _:
            return None


def _visible_to(user: User) -> ColumnElement[bool]:
    # A WHERE clause selecting exactly the applications this user may read. Expects the query
    # to have Project joined, since project-side roles are scoped through the project.
    match user.role:
        case UserRole.STUDENT:
            # Applications made by any team the student is on.
            return ProjectApplication.team_id.in_(
                select(TeamMember.team_id).where(TeamMember.student_id == user.id)
            )
        case UserRole.SUPERVISOR:
            # Every application to a project they supervise.
            return Project.supervisor_id == user.id
        case UserRole.INSTRUCTOR | UserRole.TA:
            # Every application in a course they teach or assist.
            course_ids = _member_course_ids(user) or set()
            return Project.course_id.in_(course_ids) if course_ids else false()
        case _:
            # Unknown role: show nothing rather than everything.
            return false()


def _visible_applications_query(user: User) -> Select[tuple[ProjectApplication]]:
    # Applications don't store a course; it comes from the project. A team can only apply
    # within its own course, so the project's course is also the team's course.
    return (
        select(ProjectApplication)
        .join(Project, Project.id == ProjectApplication.project_id)
        .where(_visible_to(user))
    )


async def list_applications(
    session: AsyncSession,
    user: User,
    course_id: uuid.UUID | None = None,
    project_id: uuid.UUID | None = None,
    team_id: uuid.UUID | None = None,
    status: ApplicationStatus | None = None,
) -> list[ProjectApplication]:
    # Filters only ever narrow the user's visible set, so filtering on a project or team the
    # user can't see returns an empty list rather than leaking anything.
    if course_id is not None:
        member_courses = _member_course_ids(user)
        # Supervisors aren't course members, so for them the course is just a filter.
        if member_courses is not None and course_id not in member_courses:
            raise CourseAccessDeniedError(str(course_id))

    query = _visible_applications_query(user)

    if course_id is not None:
        query = query.where(Project.course_id == course_id)
    if project_id is not None:
        query = query.where(ProjectApplication.project_id == project_id)
    if team_id is not None:
        query = query.where(ProjectApplication.team_id == team_id)
    if status is not None:
        query = query.where(ProjectApplication.status == status)

    # Newest first; id breaks ties so the order is stable across requests.
    query = query.order_by(ProjectApplication.created_at.desc(), ProjectApplication.id)
    return list((await session.scalars(query)).all())


async def get_application(
    session: AsyncSession, user: User, application_id: uuid.UUID
) -> ProjectApplication:
    application = await session.scalar(
        _visible_applications_query(user).where(ProjectApplication.id == application_id)
    )
    if application is None:
        raise ApplicationNotFoundError(str(application_id))
    return application


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
    except IntegrityError as exc:  # broad wrapper for any database integrity error
        await session.rollback()

        # PostgreSQL code '23505' stands for unique_violation
        if getattr(exc.orig, "pgcode", None) == "23505":
            raise DuplicateApplicationError(str(data.project_id)) from exc
        else:
            raise

    except Exception:
        # Any domain error above (not open, not a member, ...) arrives here. Roll back
        # explicitly so the row locks are released now rather than when the session closes.
        await session.rollback()
        raise

    # Reload so server-generated fields (created_at, updated_at) are populated after commit.
    await session.refresh(application)
    return application
