"""Integration checks for team agreement, withdrawal, and instructor/TA rejection."""

import uuid
from collections.abc import AsyncIterator
from dataclasses import dataclass

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.main import create_app
from app.modules.applications import service
from app.modules.applications.lifecycle import (
    ApplicationSnapshot,
    ApplicationStatus,
    ProjectSnapshot,
    find_violations,
)
from app.modules.applications.models import ProjectApplication
from app.modules.auth.users import current_active_user
from app.modules.courses.models import Course, CourseProgram
from app.modules.projects.models import Project, ProjectStatus
from app.modules.teams.models import Team, TeamMember
from app.modules.users.models import (
    TA,
    Instructor,
    InstructorCourse,
    Student,
    Supervisor,
    User,
    UserRole,
)

S = ApplicationStatus


@dataclass
class World:
    supervisor: User  # supervises `project`
    other_supervisor: User
    ta: User
    instructor: User
    student_1: User  # on team_1
    project: Project  # capacity 2
    app_1: ProjectApplication  # team_1 -> project
    app_2: ProjectApplication  # team_2 -> project
    app_3: ProjectApplication  # team_3 -> project
    pending_project: Project
    competing_project: Project
    pending_application: ProjectApplication
    competing_application: ProjectApplication


def _user(role: UserRole, name: str) -> User:
    return User(
        email=f"{name}-{uuid.uuid4().hex[:8]}@example.com",
        hashed_password="x",
        first_name=name,
        last_name="Test",
        role=role,
    )


@pytest_asyncio.fixture
async def world(session: AsyncSession) -> World:
    course = Course(code="SFWRENG 4G06", name="SE Capstone", program=CourseProgram.SE)
    session.add(course)
    await session.flush()

    supervisor = _user(UserRole.SUPERVISOR, "sup")
    supervisor.supervisor = Supervisor()
    other_supervisor = _user(UserRole.SUPERVISOR, "other_sup")
    other_supervisor.supervisor = Supervisor()
    ta = _user(UserRole.TA, "ta")
    ta.ta = TA(course_id=course.id)
    instructor = _user(UserRole.INSTRUCTOR, "inst")
    instructor.instructor = Instructor(course_links=[InstructorCourse(course_id=course.id)])

    students = []
    for i in range(3):
        s = _user(UserRole.STUDENT, f"s{i}")
        s.student = Student(student_number=uuid.uuid4().hex[:10], course_id=course.id)
        students.append(s)

    session.add_all([supervisor, other_supervisor, ta, instructor, *students])
    await session.flush()

    teams = [
        Team(course_id=course.id, name=f"Team {i}", members=[TeamMember(student_id=s.id)])
        for i, s in enumerate(students)
    ]
    project = Project(
        title="P",
        background="bg",
        supervisor_id=supervisor.id,
        course_id=course.id,
        supervisor_capacity=2,
    )
    pending_project = Project(
        title="Pending competitor",
        background="bg",
        supervisor_id=other_supervisor.id,
        course_id=course.id,
        supervisor_capacity=1,
    )
    competing_project = Project(
        title="Reserved competitor",
        background="bg",
        supervisor_id=other_supervisor.id,
        course_id=course.id,
        supervisor_capacity=1,
    )
    session.add_all([*teams, project, pending_project, competing_project])
    await session.flush()

    apps = [ProjectApplication(team_id=t.id, project_id=project.id) for t in teams]
    # Competitors start inactive; individual tests activate the applications they need.
    pending_application = ProjectApplication(
        team_id=teams[0].id, project_id=pending_project.id, status=S.DECLINED_OR_WITHDRAWN
    )
    competing_application = ProjectApplication(
        team_id=teams[0].id, project_id=competing_project.id, status=S.DECLINED_OR_WITHDRAWN
    )
    session.add_all([*apps, pending_application, competing_application])
    # Commit (a savepoint release inside the test transaction) rather than flush: a failed
    # decision rolls the session back, and that must not undo the setup data as well.
    await session.commit()

    return World(
        supervisor=supervisor,
        other_supervisor=other_supervisor,
        ta=ta,
        instructor=instructor,
        student_1=students[0],
        project=project,
        app_1=apps[0],
        app_2=apps[1],
        app_3=apps[2],
        pending_project=pending_project,
        competing_project=competing_project,
        pending_application=pending_application,
        competing_application=competing_application,
    )


async def _refresh(session: AsyncSession, *objs: object) -> None:
    # A failed decision rolls the session back, which expires every loaded object. Async
    # sessions can't lazy-load, so reload explicitly before reading attributes again.
    for obj in objs:
        await session.refresh(obj)


async def _assert_consistent(session: AsyncSession) -> None:
    projects = (await session.scalars(select(Project))).all()
    apps = (await session.scalars(select(ProjectApplication))).all()
    violations = find_violations(
        [
            ProjectSnapshot(p.id, p.supervisor_capacity, p.slots_reserved, p.status)
            for p in projects
        ],
        [ApplicationSnapshot(a.team_id, a.project_id, a.status) for a in apps],
    )
    assert violations == []


@pytest_asyncio.fixture
async def http(session: AsyncSession) -> AsyncIterator[tuple[AsyncClient, dict[str, User]]]:
    app = create_app()
    acting: dict[str, User] = {}

    async def _session() -> AsyncIterator[AsyncSession]:
        yield session

    app.dependency_overrides[get_session] = _session
    app.dependency_overrides[current_active_user] = lambda: acting["user"]
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test/api") as c:
        yield c, acting


async def _offer(session: AsyncSession, world: World) -> None:
    # Prepare a full project with one offered place for this team's application.
    world.project.supervisor_capacity = 1
    world.project.slots_reserved = 1
    world.project.status = ProjectStatus.FULL
    world.app_1.status = S.SUPERVISOR_ACCEPTS
    world.app_2.status = S.DECLINED_OR_WITHDRAWN
    world.app_3.status = S.DECLINED_OR_WITHDRAWN
    await session.commit()


# ---------------------------------------------------------------------------
# Agreement
# ---------------------------------------------------------------------------


async def test_agreement_closes_competitors(
    session: AsyncSession, world: World, http: tuple[AsyncClient, dict[str, User]]
) -> None:
    # Agreement keeps its slot, closes pending competitors, and frees competing reservations.
    await _offer(session, world)
    pending_project, pending = world.pending_project, world.pending_application
    reserved_project, reserved = world.competing_project, world.competing_application
    pending.status = S.APPLIED
    reserved.status = S.SUPERVISOR_ACCEPTS
    reserved_project.slots_reserved = 1
    reserved_project.status = ProjectStatus.FULL
    await session.commit()
    client, acting = http
    acting["user"] = world.student_1
    response = await client.post(f"/applications/{world.app_1.id}/agree")
    assert response.status_code == 200
    assert response.json()["status"] == "agreed"
    await _refresh(session, world.project, pending_project, reserved_project, pending, reserved)
    assert (world.project.slots_reserved, world.project.status) == (1, ProjectStatus.FULL)
    assert pending.status == reserved.status == S.DECLINED_OR_WITHDRAWN
    assert pending_project.slots_reserved == reserved_project.slots_reserved == 0
    assert pending_project.status == reserved_project.status == ProjectStatus.OPEN
    await _assert_consistent(session)


@pytest.mark.parametrize(
    ("initial", "reserved", "project_status"),
    [(S.APPLIED, 0, ProjectStatus.OPEN), (S.AGREED, 1, ProjectStatus.FULL)],
)
async def test_invalid_agreement_preserves_state(
    session: AsyncSession,
    world: World,
    http: tuple[AsyncClient, dict[str, User]],
    initial: S,
    reserved: int,
    project_status: ProjectStatus,
) -> None:
    # Accepting before an offer or accepting twice returns 409 without changing reservations.
    world.project.supervisor_capacity = 1
    world.app_1.status = initial
    world.app_2.status = world.app_3.status = S.DECLINED_OR_WITHDRAWN
    world.project.slots_reserved = reserved
    world.project.status = project_status
    await session.commit()
    app_id = world.app_1.id
    client, acting = http
    acting["user"] = world.student_1
    assert (await client.post(f"/applications/{app_id}/agree")).status_code == 409
    await _refresh(session, world.app_1, world.project)
    assert world.app_1.status == initial
    assert world.project.slots_reserved == reserved
    assert world.project.status == project_status
    await _assert_consistent(session)


async def test_second_agreement_is_rejected(
    session: AsyncSession, world: World, http: tuple[AsyncClient, dict[str, User]]
) -> None:
    # A team already committed elsewhere cannot agree to a second supervisor's offer.
    await _offer(session, world)
    project, other = world.competing_project, world.competing_application
    other.status = S.SUPERVISOR_ACCEPTS
    project.slots_reserved = 1
    project.status = ProjectStatus.FULL
    await session.commit()
    other.status = S.AGREED
    await session.commit()
    app_id = world.app_1.id
    client, acting = http
    acting["user"] = world.student_1
    assert (await client.post(f"/applications/{app_id}/agree")).status_code == 409
    await _refresh(session, world.app_1, world.project, project, other)
    assert world.app_1.status == S.SUPERVISOR_ACCEPTS
    assert other.status == S.AGREED
    assert world.project.slots_reserved == project.slots_reserved == 1


# ---------------------------------------------------------------------------
# Withdrawal
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("initial", [S.APPLIED, S.SUPERVISOR_ACCEPTS, S.AGREED])
async def test_withdrawal_releases_only_held_slot(
    session: AsyncSession, world: World, http: tuple[AsyncClient, dict[str, User]], initial: S
) -> None:
    # Withdrawal closes the application and releases exactly one slot only when it held one.
    await _offer(session, world)
    world.app_1.status = initial
    world.project.slots_reserved = int(initial != S.APPLIED)
    world.project.status = ProjectStatus.OPEN if initial == S.APPLIED else ProjectStatus.FULL
    await session.commit()
    client, acting = http
    acting["user"] = world.student_1
    response = await client.post(f"/applications/{world.app_1.id}/withdraw")
    assert response.status_code == 200
    assert response.json()["status"] == "declined_or_withdrawn"
    await _refresh(session, world.project)
    assert world.project.slots_reserved == 0
    assert world.project.status == ProjectStatus.OPEN
    await _assert_consistent(session)


@pytest.mark.parametrize("initial", [S.DECLINED_OR_WITHDRAWN, S.APPROVED])
async def test_invalid_withdrawal_preserves_state(
    session: AsyncSession, world: World, http: tuple[AsyncClient, dict[str, User]], initial: S
) -> None:
    # Repeated withdrawal and withdrawal after approval return 409 without freeing another slot.
    await _offer(session, world)
    world.app_1.status = initial
    world.project.slots_reserved = int(initial == S.APPROVED)
    world.project.status = ProjectStatus.FULL if initial == S.APPROVED else ProjectStatus.OPEN
    await session.commit()
    app_id = world.app_1.id
    client, acting = http
    acting["user"] = world.student_1
    assert (await client.post(f"/applications/{app_id}/withdraw")).status_code == 409
    await _refresh(session, world.app_1, world.project)
    assert world.app_1.status == initial
    assert world.project.slots_reserved == int(initial == S.APPROVED)
    await _assert_consistent(session)


# ---------------------------------------------------------------------------
# Rejection
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("staff", ["instructor", "ta"])
async def test_staff_rejection_releases_slot(
    session: AsyncSession, world: World, http: tuple[AsyncClient, dict[str, User]], staff: str
) -> None:
    # Both course instructors and TAs can reject an under-review submission and reopen its project.
    await _offer(session, world)
    world.app_1.status = S.TEAM_PROJECT_UNDER_REVIEW
    await session.commit()
    client, acting = http
    acting["user"] = getattr(world, staff)
    response = await client.post(f"/applications/{world.app_1.id}/reject")
    assert response.status_code == 200
    assert response.json()["status"] == "team_project_rejected"
    await _refresh(session, world.project)
    assert world.project.slots_reserved == 0
    assert world.project.status == ProjectStatus.OPEN
    await _assert_consistent(session)


@pytest.mark.parametrize("initial", [S.APPLIED, S.AGREED, S.APPROVED, S.TEAM_PROJECT_REJECTED])
async def test_rejection_requires_review(
    session: AsyncSession, world: World, http: tuple[AsyncClient, dict[str, User]], initial: S
) -> None:
    # Instructor rejection outside Under Review returns 409 and preserves status and capacity.
    await _offer(session, world)
    world.app_1.status = initial
    reserved = int(initial in {S.AGREED, S.APPROVED})
    world.project.slots_reserved = reserved
    world.project.status = ProjectStatus.FULL if reserved else ProjectStatus.OPEN
    await session.commit()
    app_id = world.app_1.id
    client, acting = http
    acting["user"] = world.instructor
    assert (await client.post(f"/applications/{app_id}/reject")).status_code == 409
    await _refresh(session, world.app_1, world.project)
    assert world.app_1.status == initial
    assert world.project.slots_reserved == reserved
    await _assert_consistent(session)


# ---------------------------------------------------------------------------
# Permissions and missing applications
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "action,actor,expected",
    [
        ("agree", "supervisor", 403),
        ("withdraw", "instructor", 403),
        ("reject", "student_1", 403),
        ("reject", "supervisor", 403),
        ("agree", "other_supervisor", 404),
        ("withdraw", "other_supervisor", 404),
    ],
)
async def test_wrong_actor_is_denied(
    session: AsyncSession,
    world: World,
    http: tuple[AsyncClient, dict[str, User]],
    action: str,
    actor: str,
    expected: int,
) -> None:
    # Visible but unauthorized actors receive 403; users outside application scope receive 404.
    await _offer(session, world)
    app_id = world.app_1.id
    client, acting = http
    acting["user"] = getattr(world, actor)
    assert (await client.post(f"/applications/{app_id}/{action}")).status_code == expected
    await _refresh(session, world.app_1, world.project)
    assert world.app_1.status == S.SUPERVISOR_ACCEPTS
    assert world.project.slots_reserved == 1


@pytest.mark.parametrize("action", ["agree", "withdraw", "reject"])
async def test_unknown_application_returns_404(
    world: World, http: tuple[AsyncClient, dict[str, User]], action: str
) -> None:
    # An authenticated caller receives 404 for a nonexistent application.
    client, acting = http
    acting["user"] = world.student_1
    assert (await client.post(f"/applications/{uuid.uuid4()}/{action}")).status_code == 404


@pytest.mark.parametrize("action", ["agree", "withdraw", "reject"])
async def test_team_actions_require_authentication(client: AsyncClient, action: str) -> None:
    # Requests without a bearer token are rejected before the action executes.
    assert (await client.post(f"/applications/{uuid.uuid4()}/{action}")).status_code == 401


@pytest.mark.parametrize(
    "action,role",
    [
        ("agree", UserRole.STUDENT),
        ("withdraw", UserRole.STUDENT),
        ("reject", UserRole.INSTRUCTOR),
        ("reject", UserRole.TA),
    ],
)
async def test_nonmember_or_other_course_is_hidden(
    session: AsyncSession,
    world: World,
    http: tuple[AsyncClient, dict[str, User]],
    action: str,
    role: UserRole,
) -> None:
    # Nonmembers and staff from another course cannot discover or change this application.
    await _offer(session, world)
    course = Course(code="OTHER", name="Other course", program=CourseProgram.SE)
    session.add(course)
    await session.flush()
    user = _user(role, "outsider")
    if role == UserRole.STUDENT:
        user.student = Student(
            student_number=uuid.uuid4().hex[:10], course_id=world.project.course_id
        )
    elif role == UserRole.INSTRUCTOR:
        user.instructor = Instructor(course_links=[InstructorCourse(course_id=course.id)])
    else:
        user.ta = TA(course_id=course.id)
    session.add(user)
    await session.commit()
    app_id = world.app_1.id
    client, acting = http
    acting["user"] = user
    assert (await client.post(f"/applications/{app_id}/{action}")).status_code == 404
    await _refresh(session, world.app_1, world.project)
    assert world.app_1.status == S.SUPERVISOR_ACCEPTS
    assert world.project.slots_reserved == 1


# ---------------------------------------------------------------------------
# Rollback
# ---------------------------------------------------------------------------


async def test_agreement_rolls_back_on_release_failure(
    session: AsyncSession, world: World, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Failure after a slot release rolls back the chosen agreement and all competing changes.
    await _offer(session, world)
    project, other = world.competing_project, world.competing_application
    other.status = S.SUPERVISOR_ACCEPTS
    project.slots_reserved = 1
    project.status = ProjectStatus.FULL
    await session.commit()
    app_id = world.app_1.id
    original_release = service.release_slot

    def fail_after_release(project: Project) -> None:
        original_release(project)
        raise RuntimeError("simulated failure")

    monkeypatch.setattr(service, "release_slot", fail_after_release)
    with pytest.raises(RuntimeError, match="simulated failure"):
        await service.agree_to_project(session, world.student_1, app_id)
    await _refresh(session, world.app_1, world.project, project, other)
    assert world.app_1.status == other.status == S.SUPERVISOR_ACCEPTS
    assert world.project.slots_reserved == project.slots_reserved == 1
    assert project.status == ProjectStatus.FULL
    await _assert_consistent(session)
