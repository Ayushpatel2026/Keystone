import uuid

from sqlalchemy import ColumnElement, Select, false, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.applications.lifecycle import (
    INITIAL_STATUS,
    PENDING,
    Actor,
    ActorNotPermittedError,
    ApplicationEvent,
    ApplicationStatus,
    InvalidTransitionError,
    apply_event,
    has_agreement,
)
from app.modules.applications.models import ProjectApplication
from app.modules.applications.schemas import ApplicationCreate
from app.modules.projects.models import Project, ProjectStatus
from app.modules.projects.service import (
    ProjectCapacityFullError,
    ProjectNotFoundError,
    ProjectNotOpenError,
    lock_project,
    lock_projects,
    release_slot,
    require_open_for_applications,
    reserve_slot,
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
    "NotProjectSupervisorError",
    "ProjectCapacityFullError",
    "InvalidTransitionError",
    "ActorNotPermittedError",
    "apply_to_project",
    "list_applications",
    "get_application",
    "supervisor_accept",
    "supervisor_decline",
    "agree_to_project",
    "withdraw_application",
    "reject_submission",
    "InvalidTransitionError",
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


class NotProjectSupervisorError(Exception):
    # The user can see the application (e.g. a team member, TA or instructor) but is not the
    # supervisor of its project, so they can't accept or decline it.
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


# ---------------------------------------------------------------------------
# Supervisor decisions (SRS FR_DeclineTeam, MIS respondToApplication, supervisor side).
# Accept:  Applied -> Supervisor Accepts, reserving one of the project's slots.
# Decline: Applied or Supervisor Accepts -> Declined or withdrawn, releasing the slot if held.
# Which moves are legal, and what they do to the slot count, is decided by lifecycle.py.
# ---------------------------------------------------------------------------


async def _lock_application(session: AsyncSession, application_id: uuid.UUID) -> ProjectApplication:
    # Lock the application row and re-read it, so its status can't change (or be stale)
    # between the lifecycle check and the write.
    application = await session.scalar(
        select(ProjectApplication)
        .where(ProjectApplication.id == application_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    if application is None:
        raise ApplicationNotFoundError(str(application_id))
    return application


async def _close_pending_applications(
    session: AsyncSession, project_id: uuid.UUID, keep_id: uuid.UUID
) -> None:
    # Called once a project is Full. A full project must have no applications still waiting for
    # a decision (lifecycle invariant FULL_WITH_PENDING_APPS), so each one is closed by the
    # system. The caller holds the project lock, so no new application can arrive meanwhile.
    # keep_id is the application the caller just decided on; it is excluded explicitly rather
    # than relying on autoflush having already written its new status before this SELECT.
    # Filtering on PENDING in SQL also means only rows we will actually close get locked.
    pending = await session.scalars(
        select(ProjectApplication)
        .where(
            ProjectApplication.project_id == project_id,
            ProjectApplication.id != keep_id,
            ProjectApplication.status.in_(PENDING),
        )
        .order_by(ProjectApplication.id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    for other in pending:
        closed = apply_event(other.status, ApplicationEvent.SYSTEM_CLOSE, Actor.SYSTEM)
        other.status = closed.new_status


async def _supervisor_decide(
    session: AsyncSession, user: User, application_id: uuid.UUID, event: ApplicationEvent
) -> ProjectApplication:
    # Unlocked lookup first, scoped to what the user may read: an application outside their
    # scope is reported as not found, exactly like GET /applications/{id}.
    found = await session.scalar(
        _visible_applications_query(user).where(ProjectApplication.id == application_id)
    )
    if found is None:
        raise ApplicationNotFoundError(str(application_id))

    # Reject non-supervisors before taking any locks, so they can't hold up other requests.
    if user.role != UserRole.SUPERVISOR:
        raise NotProjectSupervisorError(str(application_id))

    # Same lock order as apply_to_project (team, then project) so the two can't deadlock.
    # The team lock serialises this against the team's own actions, the project lock
    # against other decisions and applications on the same project.
    await lock_team(session, found.team_id)
    project = await lock_project(session, found.project_id)

    # Second line of defence: _visible_applications_query already hides other supervisors'
    # applications (404), but re-check ownership against the freshly locked project row.
    if project.supervisor_id != user.id:
        raise NotProjectSupervisorError(str(application_id))

    application = await _lock_application(session, application_id)

    # Raises InvalidTransitionError when the status doesn't allow the decision, e.g. accepting
    # an application that was already declined or withdrawn.
    outcome = apply_event(application.status, event, Actor.SUPERVISOR)

    # Change the slot count first: reserve_slot raises if the project is Closed or has no
    # free slot, and nothing has been modified yet at that point.
    if outcome.slot_delta > 0:
        reserve_slot(project)
    elif outcome.slot_delta < 0:
        release_slot(project)
    application.status = outcome.new_status

    if project.status == ProjectStatus.FULL:
        await _close_pending_applications(session, project.id, keep_id=application.id)

    return application


async def _commit_decision(
    session: AsyncSession, user: User, application_id: uuid.UUID, event: ApplicationEvent
) -> ProjectApplication:
    # Transaction boundary: the locks taken in _supervisor_decide are held until commit or
    # rollback, so the checks, the slot change and the status change are atomic.
    try:
        application = await _supervisor_decide(session, user, application_id, event)
        await session.commit()
    except Exception:
        await session.rollback()
        raise

    await session.refresh(application)
    return application


async def supervisor_accept(
    session: AsyncSession, user: User, application_id: uuid.UUID
) -> ProjectApplication:
    return await _commit_decision(session, user, application_id, ApplicationEvent.SUPERVISOR_ACCEPT)


async def supervisor_decline(
    session: AsyncSession, user: User, application_id: uuid.UUID
) -> ProjectApplication:
    return await _commit_decision(
        session, user, application_id, ApplicationEvent.SUPERVISOR_DECLINE
    )


async def agree_to_project(
    session: AsyncSession, user: User, application_id: uuid.UUID
) -> ProjectApplication:
    # PoC: uses the signed-in team member without an additional re-verification challenge.
    try:
        # Find the application and lock its team.
        application = await get_application(session, user, application_id)
        team_id = application.team_id
        await lock_team(session, team_id)
        # Only a student on this team can agree.
        if user.role != UserRole.STUDENT or not await is_member(session, team_id, user.id):
            raise NotTeamMemberError(str(user.id))

        # Get the IDs of every project this team applied to.
        project_ids = list(
            await session.scalars(
                select(ProjectApplication.project_id).where(ProjectApplication.team_id == team_id)
            )
        )
        # Lock those projects and look them up by ID.
        projects = {p.id: p for p in await lock_projects(session, project_ids)}
        # Lock and reload the team's applications with their latest statuses.
        applications = list(
            await session.scalars(
                select(ProjectApplication)
                .where(ProjectApplication.team_id == team_id)
                .order_by(ProjectApplication.id)
                .with_for_update(of=ProjectApplication)
                .execution_options(populate_existing=True)
            )
        )
        # Find the application the team wants to accept.
        selected = next((a for a in applications if a.id == application_id), None)
        if selected is None:
            raise ApplicationNotFoundError(str(application_id))
        application = selected
        # The team cannot agree to a second project.
        if any(a.id != application_id and has_agreement(a.status) for a in applications):
            raise TeamAlreadyAgreedError(str(team_id))

        # Check the transition and mark this application as Agreed.
        outcome = apply_event(application.status, ApplicationEvent.TEAM_ACCEPT, Actor.TEAM)
        application.status = outcome.new_status
        # Close the team's other pending or supervisor-accepted applications.
        for other in applications:
            if other.id == application_id or other.status not in {
                ApplicationStatus.APPLIED,
                ApplicationStatus.SUPERVISOR_ACCEPTS,
            }:
                continue
            outcome = apply_event(other.status, ApplicationEvent.SYSTEM_CLOSE, Actor.SYSTEM)
            # Free a competing reservation only if it held a slot.
            if outcome.slot_delta == -1:
                release_slot(projects[other.project_id])
            other.status = outcome.new_status
        # Save the agreement, withdrawals, and slot changes together.
        await session.commit()
    except Exception:
        # Undo all changes if any part fails.
        await session.rollback()
        raise

    # Reload and return the saved application.
    await session.refresh(application)
    return application


async def _lock_application_for_action(
    session: AsyncSession, user: User, application_id: uuid.UUID
) -> tuple[ProjectApplication, Project]:
    # Check visibility before locking the team, project, and application in that order.
    visible = await get_application(session, user, application_id)
    team_id, project_id = visible.team_id, visible.project_id
    await lock_team(session, team_id)
    project = await lock_project(session, project_id)
    application = await session.scalar(
        select(ProjectApplication)
        .where(ProjectApplication.id == application_id)
        .with_for_update(of=ProjectApplication)
        .execution_options(populate_existing=True)
    )
    if application is None:
        raise ApplicationNotFoundError(str(application_id))
    return application, project


async def withdraw_application(
    session: AsyncSession, user: User, application_id: uuid.UUID
) -> ProjectApplication:
    try:
        application, project = await _lock_application_for_action(session, user, application_id)
        # Only a student on the applying team may withdraw.
        if user.role != UserRole.STUDENT or not await is_member(
            session, application.team_id, user.id
        ):
            raise NotTeamMemberError(str(user.id))

        # The lifecycle rejects repeated withdrawals and withdrawal after approval.
        outcome = apply_event(application.status, ApplicationEvent.TEAM_WITHDRAW, Actor.TEAM)
        if outcome.slot_delta == -1:
            release_slot(project)
        application.status = outcome.new_status
        # Save the withdrawal and any slot release together.
        await session.commit()
    except Exception:
        await session.rollback()
        raise

    await session.refresh(application)
    return application


async def reject_submission(
    session: AsyncSession, user: User, application_id: uuid.UUID
) -> ProjectApplication:
    # PoC: a simple decision without feedback or an additional re-verification challenge.
    try:
        application, project = await _lock_application_for_action(session, user, application_id)
        # Only instructors and TAs assigned to this course may reject.
        if user.role not in {UserRole.INSTRUCTOR, UserRole.TA} or project.course_id not in (
            _member_course_ids(user) or set()
        ):
            raise CourseAccessDeniedError(str(project.course_id))

        actor = Actor.INSTRUCTOR if user.role == UserRole.INSTRUCTOR else Actor.TA
        # Rejection is allowed only while the team project is under review.
        outcome = apply_event(application.status, ApplicationEvent.INSTRUCTOR_REJECT, actor)
        if outcome.slot_delta == -1:
            release_slot(project)
        application.status = outcome.new_status
        # Save the rejection and slot release together.
        await session.commit()
    except Exception:
        await session.rollback()
        raise

    await session.refresh(application)
    return application