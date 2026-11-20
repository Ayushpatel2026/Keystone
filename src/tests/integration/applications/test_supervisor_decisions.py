"""Supervisor accept / decline of applications (service.supervisor_accept / supervisor_decline).

These tests need PostgreSQL; the `session` fixture lives in tests/integration/conftest.py.
After every scenario the lifecycle invariant checker runs against the real rows.
"""

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
    session.add_all([*teams, project])
    await session.flush()

    apps = [ProjectApplication(team_id=t.id, project_id=project.id) for t in teams]
    session.add_all(apps)
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


# ---------------------------------------------------------------------------
# Accept
# ---------------------------------------------------------------------------


async def test_accept_reserves_a_slot(session: AsyncSession, world: World) -> None:
    w = world
    result = await service.supervisor_accept(session, w.supervisor, w.app_1.id)

    assert result.status == S.SUPERVISOR_ACCEPTS
    await _refresh(session, w.project, w.app_2)
    assert w.project.slots_reserved == 1
    assert w.project.status == ProjectStatus.OPEN
    # Other teams are untouched while slots remain.
    assert w.app_2.status == S.APPLIED
    await _assert_consistent(session)


async def test_filling_the_last_slot_makes_project_full_and_closes_pending(
    session: AsyncSession, world: World
) -> None:
    w = world
    await service.supervisor_accept(session, w.supervisor, w.app_1.id)
    await service.supervisor_accept(session, w.supervisor, w.app_2.id)

    await _refresh(session, w.project, w.app_3)
    assert w.project.slots_reserved == 2
    assert w.project.status == ProjectStatus.FULL
    # The remaining pending application was closed by the system.
    assert w.app_3.status == S.DECLINED_OR_WITHDRAWN
    await _assert_consistent(session)

    # It can no longer be accepted.
    await _refresh(session, w.supervisor)
    with pytest.raises(service.InvalidTransitionError):
        await service.supervisor_accept(session, w.supervisor, w.app_3.id)


async def test_accept_on_closed_project_is_rejected(session: AsyncSession, world: World) -> None:
    w = world
    w.project.status = ProjectStatus.CLOSED
    await session.commit()

    with pytest.raises(service.ProjectNotOpenError):
        await service.supervisor_accept(session, w.supervisor, w.app_1.id)

    await _refresh(session, w.app_1, w.project)
    assert w.app_1.status == S.APPLIED
    assert w.project.slots_reserved == 0


# ---------------------------------------------------------------------------
# Decline
# ---------------------------------------------------------------------------


async def test_decline_pending_application(session: AsyncSession, world: World) -> None:
    w = world
    result = await service.supervisor_decline(session, w.supervisor, w.app_1.id)

    assert result.status == S.DECLINED_OR_WITHDRAWN
    await _refresh(session, w.project)
    assert w.project.slots_reserved == 0
    await _assert_consistent(session)


async def test_decline_after_accept_releases_slot_and_reopens_project(
    session: AsyncSession, world: World
) -> None:
    w = world
    await service.supervisor_accept(session, w.supervisor, w.app_1.id)
    await service.supervisor_accept(session, w.supervisor, w.app_2.id)

    result = await service.supervisor_decline(session, w.supervisor, w.app_1.id)

    assert result.status == S.DECLINED_OR_WITHDRAWN
    await _refresh(session, w.project)
    assert w.project.slots_reserved == 1
    assert w.project.status == ProjectStatus.OPEN
    await _assert_consistent(session)


async def test_decline_twice_is_a_conflict(session: AsyncSession, world: World) -> None:
    w = world
    await service.supervisor_decline(session, w.supervisor, w.app_1.id)
    with pytest.raises(service.InvalidTransitionError):
        await service.supervisor_decline(session, w.supervisor, w.app_1.id)


async def test_supervisor_cannot_decline_after_team_agreed(
    session: AsyncSession, world: World
) -> None:
    # Per the lifecycle table, once both sides agreed only the team can withdraw.
    w = world
    await service.supervisor_accept(session, w.supervisor, w.app_1.id)
    w.app_1.status = S.AGREED
    await session.commit()

    with pytest.raises(service.InvalidTransitionError):
        await service.supervisor_decline(session, w.supervisor, w.app_1.id)


# ---------------------------------------------------------------------------
# Who may decide
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("who", ["student_1", "ta", "instructor"])
async def test_only_the_projects_supervisor_can_decide(
    session: AsyncSession, world: World, who: str
) -> None:
    # These users can see the application but aren't its supervisor.
    user: User = getattr(world, who)
    with pytest.raises(service.NotProjectSupervisorError):
        await service.supervisor_accept(session, user, world.app_1.id)

    await _refresh(session, world.app_1, world.project)
    assert world.app_1.status == S.APPLIED
    assert world.project.slots_reserved == 0


async def test_other_supervisor_gets_not_found(session: AsyncSession, world: World) -> None:
    w = world
    with pytest.raises(service.ApplicationNotFoundError):
        await service.supervisor_accept(session, w.other_supervisor, w.app_1.id)
    await _refresh(session, w.other_supervisor, w.app_1)
    with pytest.raises(service.ApplicationNotFoundError):
        await service.supervisor_decline(session, w.other_supervisor, w.app_1.id)


# ---------------------------------------------------------------------------
# HTTP layer
# ---------------------------------------------------------------------------


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


async def test_http_accept_and_decline(
    session: AsyncSession, http: tuple[AsyncClient, dict[str, User]], world: World
) -> None:
    client, acting = http
    w = world
    app_1, app_2 = str(w.app_1.id), str(w.app_2.id)

    acting["user"] = w.supervisor
    resp = await client.post(f"/applications/{app_1}/accept")
    assert resp.status_code == 200
    assert resp.json()["status"] == "supervisor_accepts"

    resp = await client.post(f"/applications/{app_2}/decline")
    assert resp.status_code == 200
    assert resp.json()["status"] == "declined_or_withdrawn"

    # Deciding again on a declined application is a conflict.
    assert (await client.post(f"/applications/{app_2}/accept")).status_code == 409

    await _refresh(session, w.student_1)
    acting["user"] = w.student_1
    assert (await client.post(f"/applications/{app_1}/decline")).status_code == 403

    await _refresh(session, w.supervisor)
    acting["user"] = w.supervisor
    assert (await client.post(f"/applications/{uuid.uuid4()}/accept")).status_code == 404


async def test_http_decisions_require_authentication(client: AsyncClient) -> None:
    assert (await client.post(f"/applications/{uuid.uuid4()}/accept")).status_code == 401
    assert (await client.post(f"/applications/{uuid.uuid4()}/decline")).status_code == 401
