"""Role-scoped reads of project applications (service.list_applications / get_application).

These tests need PostgreSQL; the `session` fixture lives in tests/integration/conftest.py.
"""

import uuid
from collections.abc import AsyncIterator
from dataclasses import dataclass

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.main import create_app
from app.modules.applications import service
from app.modules.applications.lifecycle import ApplicationStatus
from app.modules.applications.models import ProjectApplication
from app.modules.auth.users import current_active_user
from app.modules.courses.models import Course, CourseProgram
from app.modules.projects.models import Project
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


@dataclass
class World:
    course_a: Course
    course_b: Course
    # Instructor of both courses, and one of course B only.
    instructor_ab: User
    instructor_b: User
    ta_a: User
    # sup_1 supervises project_1 (course A) and project_3 (course B); sup_2 supervises project_2.
    sup_1: User
    sup_2: User
    # student_1 and student_2 are on team_1, student_3 on team_2 (both course A),
    # student_4 on team_3 (course B).
    student_1: User
    student_3: User
    student_4: User
    team_1: Team
    team_2: Team
    project_1: Project
    project_2: Project
    project_3: Project
    t1_p1: ProjectApplication
    t1_p2: ProjectApplication
    t2_p1: ProjectApplication
    t3_p3: ProjectApplication


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
    course_a = Course(code="SFWRENG 4G06", name="SE Capstone", program=CourseProgram.SE)
    course_b = Course(code="MECHTRON 4TB6", name="TRON Capstone", program=CourseProgram.TRON)
    session.add_all([course_a, course_b])
    await session.flush()

    def student(name: str, course: Course) -> User:
        u = _user(UserRole.STUDENT, name)
        u.student = Student(student_number=uuid.uuid4().hex[:10], course_id=course.id)
        return u

    def supervisor(name: str) -> User:
        u = _user(UserRole.SUPERVISOR, name)
        u.supervisor = Supervisor()
        return u

    instructor_ab = _user(UserRole.INSTRUCTOR, "inst_ab")
    instructor_ab.instructor = Instructor(
        course_links=[
            InstructorCourse(course_id=course_a.id),
            InstructorCourse(course_id=course_b.id),
        ]
    )
    instructor_b = _user(UserRole.INSTRUCTOR, "inst_b")
    instructor_b.instructor = Instructor(course_links=[InstructorCourse(course_id=course_b.id)])
    ta_a = _user(UserRole.TA, "ta_a")
    ta_a.ta = TA(course_id=course_a.id)

    sup_1, sup_2 = supervisor("sup_1"), supervisor("sup_2")
    student_1 = student("s1", course_a)
    student_2 = student("s2", course_a)
    student_3 = student("s3", course_a)
    student_4 = student("s4", course_b)

    session.add_all(
        [
            instructor_ab,
            instructor_b,
            ta_a,
            sup_1,
            sup_2,
            student_1,
            student_2,
            student_3,
            student_4,
        ]
    )
    await session.flush()

    def team(name: str, course: Course, *members: User) -> Team:
        return Team(
            course_id=course.id,
            name=name,
            members=[TeamMember(student_id=m.id) for m in members],
        )

    team_1 = team("Team 1", course_a, student_1, student_2)
    team_2 = team("Team 2", course_a, student_3)
    team_3 = team("Team 3", course_b, student_4)

    def project(title: str, course: Course, sup: User) -> Project:
        return Project(
            title=title,
            background="bg",
            supervisor_id=sup.id,
            course_id=course.id,
            supervisor_capacity=2,
        )

    project_1 = project("P1", course_a, sup_1)
    project_2 = project("P2", course_a, sup_2)
    project_3 = project("P3", course_b, sup_1)
    session.add_all([team_1, team_2, team_3, project_1, project_2, project_3])
    await session.flush()

    def app(t: Team, p: Project) -> ProjectApplication:
        return ProjectApplication(team_id=t.id, project_id=p.id)

    t1_p1, t1_p2, t2_p1, t3_p3 = (
        app(team_1, project_1),
        app(team_1, project_2),
        app(team_2, project_1),
        app(team_3, project_3),
    )
    session.add_all([t1_p1, t1_p2, t2_p1, t3_p3])
    await session.flush()

    return World(
        course_a=course_a,
        course_b=course_b,
        instructor_ab=instructor_ab,
        instructor_b=instructor_b,
        ta_a=ta_a,
        sup_1=sup_1,
        sup_2=sup_2,
        student_1=student_1,
        student_3=student_3,
        student_4=student_4,
        team_1=team_1,
        team_2=team_2,
        project_1=project_1,
        project_2=project_2,
        project_3=project_3,
        t1_p1=t1_p1,
        t1_p2=t1_p2,
        t2_p1=t2_p1,
        t3_p3=t3_p3,
    )


def _ids(apps: list[ProjectApplication]) -> set[uuid.UUID]:
    return {a.id for a in apps}


# ---------------------------------------------------------------------------
# Who sees what
# ---------------------------------------------------------------------------


async def test_student_sees_only_their_teams_applications(
    session: AsyncSession, world: World
) -> None:
    w = world
    assert _ids(await service.list_applications(session, w.student_1)) == {w.t1_p1.id, w.t1_p2.id}
    assert _ids(await service.list_applications(session, w.student_3)) == {w.t2_p1.id}
    assert _ids(await service.list_applications(session, w.student_4)) == {w.t3_p3.id}


async def test_supervisor_sees_all_applications_to_their_projects(
    session: AsyncSession, world: World
) -> None:
    w = world
    # Across courses: a supervisor is not tied to one course.
    assert _ids(await service.list_applications(session, w.sup_1)) == {
        w.t1_p1.id,
        w.t2_p1.id,
        w.t3_p3.id,
    }
    assert _ids(await service.list_applications(session, w.sup_2)) == {w.t1_p2.id}


async def test_supervisor_course_filter_narrows_without_membership_check(
    session: AsyncSession, world: World
) -> None:
    w = world
    result = await service.list_applications(session, w.sup_1, course_id=w.course_a.id)
    assert _ids(result) == {w.t1_p1.id, w.t2_p1.id}


async def test_ta_sees_every_application_in_their_course(
    session: AsyncSession, world: World
) -> None:
    w = world
    expected = {w.t1_p1.id, w.t1_p2.id, w.t2_p1.id}
    assert _ids(await service.list_applications(session, w.ta_a)) == expected
    # Filtering by their own course is allowed and gives the same result.
    assert _ids(await service.list_applications(session, w.ta_a, course_id=w.course_a.id)) == (
        expected
    )


async def test_instructor_sees_all_their_courses_and_can_filter_by_course(
    session: AsyncSession, world: World
) -> None:
    w = world
    every = {w.t1_p1.id, w.t1_p2.id, w.t2_p1.id, w.t3_p3.id}
    assert _ids(await service.list_applications(session, w.instructor_ab)) == every

    course_a = await service.list_applications(session, w.instructor_ab, course_id=w.course_a.id)
    assert _ids(course_a) == {w.t1_p1.id, w.t1_p2.id, w.t2_p1.id}

    course_b = await service.list_applications(session, w.instructor_ab, course_id=w.course_b.id)
    assert _ids(course_b) == {w.t3_p3.id}

    # An instructor of only course B never sees course A.
    assert _ids(await service.list_applications(session, w.instructor_b)) == {w.t3_p3.id}


@pytest.mark.parametrize("who", ["ta_a", "instructor_b", "student_1"])
async def test_course_filter_outside_membership_is_denied(
    session: AsyncSession, world: World, who: str
) -> None:
    user: User = getattr(world, who)
    other_course = world.course_b if who in {"ta_a", "student_1"} else world.course_a
    with pytest.raises(service.CourseAccessDeniedError):
        await service.list_applications(session, user, course_id=other_course.id)


# ---------------------------------------------------------------------------
# Filters
# ---------------------------------------------------------------------------


async def test_project_team_and_status_filters(session: AsyncSession, world: World) -> None:
    w = world
    inst = w.instructor_ab

    by_project = await service.list_applications(session, inst, project_id=w.project_1.id)
    assert _ids(by_project) == {w.t1_p1.id, w.t2_p1.id}

    by_team = await service.list_applications(session, inst, team_id=w.team_1.id)
    assert _ids(by_team) == {w.t1_p1.id, w.t1_p2.id}

    w.t2_p1.status = ApplicationStatus.SUPERVISOR_ACCEPTS
    await session.flush()
    by_status = await service.list_applications(
        session, inst, status=ApplicationStatus.SUPERVISOR_ACCEPTS
    )
    assert _ids(by_status) == {w.t2_p1.id}


async def test_filters_cannot_widen_visibility(session: AsyncSession, world: World) -> None:
    w = world
    # A student asking for another team's applications gets nothing, not an error.
    assert await service.list_applications(session, w.student_1, team_id=w.team_2.id) == []
    # A supervisor asking about someone else's project gets nothing.
    assert await service.list_applications(session, w.sup_2, project_id=w.project_1.id) == []


# ---------------------------------------------------------------------------
# Single application
# ---------------------------------------------------------------------------


async def test_get_application_in_scope(session: AsyncSession, world: World) -> None:
    w = world
    for user in (w.student_1, w.sup_1, w.ta_a, w.instructor_ab):
        assert (await service.get_application(session, user, w.t1_p1.id)).id == w.t1_p1.id


async def test_get_application_out_of_scope_looks_like_not_found(
    session: AsyncSession, world: World
) -> None:
    w = world
    for user in (w.student_3, w.sup_2, w.instructor_b):
        with pytest.raises(service.ApplicationNotFoundError):
            await service.get_application(session, user, w.t1_p1.id)
    with pytest.raises(service.ApplicationNotFoundError):
        await service.get_application(session, w.instructor_ab, uuid.uuid4())


# ---------------------------------------------------------------------------
# HTTP layer
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture
async def http(session: AsyncSession) -> AsyncIterator[tuple[AsyncClient, dict[str, User]]]:
    # The test sets acting["user"] to choose who is signed in.
    app = create_app()
    acting: dict[str, User] = {}

    async def _session() -> AsyncIterator[AsyncSession]:
        yield session

    app.dependency_overrides[get_session] = _session
    app.dependency_overrides[current_active_user] = lambda: acting["user"]
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test/api") as c:
        yield c, acting


async def test_http_list_and_get(http: tuple[AsyncClient, dict[str, User]], world: World) -> None:
    client, acting = http
    w = world

    acting["user"] = w.instructor_ab
    resp = await client.get("/applications", params={"course_id": str(w.course_b.id)})
    assert resp.status_code == 200
    assert [a["id"] for a in resp.json()] == [str(w.t3_p3.id)]

    resp = await client.get("/applications", params={"status": "applied"})
    assert resp.status_code == 200
    assert len(resp.json()) == 4

    acting["user"] = w.instructor_b
    resp = await client.get("/applications", params={"course_id": str(w.course_a.id)})
    assert resp.status_code == 403

    acting["user"] = w.student_3
    assert (await client.get(f"/applications/{w.t2_p1.id}")).status_code == 200
    assert (await client.get(f"/applications/{w.t1_p1.id}")).status_code == 404


async def test_http_requires_authentication(client: AsyncClient) -> None:
    assert (await client.get("/applications")).status_code == 401
    assert (await client.get(f"/applications/{uuid.uuid4()}")).status_code == 401
