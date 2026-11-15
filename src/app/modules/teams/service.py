import uuid

from sqlalchemy import Select, delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.modules.courses.models import Course
from app.modules.courses.service import CourseNotFoundError
from app.modules.teams.models import Team, TeamMember
from app.modules.teams.schemas import TeamCreate
from app.modules.users.models import Student

__all__ = [
    "CourseNotFoundError",
    "StudentsNotFoundError",
    "TeamMemberNotFoundError",
    "TeamNameAlreadyExistsError",
    "TeamNotFoundError",
]


class StudentsNotFoundError(Exception):
    pass


class TeamNotFoundError(Exception):
    pass


class TeamMemberNotFoundError(Exception):
    pass


class TeamNameAlreadyExistsError(Exception):
    # Raised when the course already has a team with this name.
    pass


def _team_query() -> Select[tuple[Team]]:
    # Async sessions can't lazy-load, so load members up front.
    # TeamMember.user (and its student profile) is joined-loaded by the model.
    return select(Team).options(selectinload(Team.members))


async def _require_students(session: AsyncSession, student_ids: list[uuid.UUID]) -> None:
    if not student_ids:
        return
    result = await session.scalars(select(Student.user_id).where(Student.user_id.in_(student_ids)))
    found = set(result)
    if found != set(student_ids):
        raise StudentsNotFoundError(sorted(set(student_ids) - found))


async def get_team(session: AsyncSession, team_id: uuid.UUID) -> Team | None:
    # populate_existing makes sure we return fresh data after writes.
    result = await session.execute(
        _team_query().where(Team.id == team_id).execution_options(populate_existing=True)
    )
    return result.scalar_one_or_none()


async def list_teams(session: AsyncSession, course_id: uuid.UUID | None = None) -> list[Team]:
    query = _team_query().order_by(Team.name)
    if course_id is not None:
        query = query.where(Team.course_id == course_id)
    return list((await session.scalars(query)).all())


# TODO: rule checks go in create_team and add_member:
#   - member's Student.course_id must equal the team's course_id
#   - a student may be on only one team per course
#   - team size limits
async def create_team(session: AsyncSession, data: TeamCreate) -> Team:
    if await session.get(Course, data.course_id) is None:
        raise CourseNotFoundError(str(data.course_id))

    # Drop duplicate ids while keeping order.
    student_ids = list(dict.fromkeys(data.student_ids))
    await _require_students(session, student_ids)

    team = Team(
        course_id=data.course_id,
        name=data.name,
        members=[TeamMember(student_id=sid) for sid in student_ids],
    )
    session.add(team)
    try:
        # The unique (course_id, name) constraint is the source of truth.
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise TeamNameAlreadyExistsError(data.name) from exc

    created = await get_team(session, team.id)
    assert created is not None
    return created


async def add_member(session: AsyncSession, team_id: uuid.UUID, student_id: uuid.UUID) -> Team:
    team = await get_team(session, team_id)
    if team is None:
        raise TeamNotFoundError(str(team_id))

    await _require_students(session, [student_id])

    # Adding an existing member is a no-op.
    if not any(member.student_id == student_id for member in team.members):
        session.add(TeamMember(team_id=team_id, student_id=student_id))
        await session.commit()

    updated = await get_team(session, team_id)
    assert updated is not None
    return updated


async def remove_member(session: AsyncSession, team_id: uuid.UUID, student_id: uuid.UUID) -> None:
    result = await session.execute(
        delete(TeamMember).where(TeamMember.team_id == team_id, TeamMember.student_id == student_id)
    )
    if result.rowcount == 0:  # type: ignore[attr-defined]
        await session.rollback()
        raise TeamMemberNotFoundError(str(student_id))
    await session.commit()
