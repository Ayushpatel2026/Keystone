import uuid

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.courses.models import Course
from app.modules.courses.schemas import CourseCreate


class CourseCodeAlreadyExistsError(Exception):
    # Raised when a course with the same code already exists.
    pass


class CourseNotFoundError(Exception):
    # Raised when a requested course code does not exist.
    pass


def normalize_course_code(code: str) -> str:
    """
    Normalize a course code before storing or looking it up.

    Example:
        "  sfwreng   4g06 " -> "SFWRENG 4G06"
    """
    return " ".join(code.upper().split())


async def create_course(
    session: AsyncSession,
    data: CourseCreate,
) -> Course:

    # Normalize before inserting to maintain consistent course codes.
    code = normalize_course_code(data.code)

    course = Course(
        code=code,
        name=data.name,
        program=data.program,
    )

    session.add(course)

    try:
        # The unique constraint on Course.code is the source of truth.
        await session.commit()

    except IntegrityError as exc:
        await session.rollback()

        raise CourseCodeAlreadyExistsError(code) from exc

    await session.refresh(course)

    return course


async def get_course(
    session: AsyncSession,
    course_id: uuid.UUID,
) -> Course | None:

    return await session.get(Course, course_id)


async def get_course_by_code(
    session: AsyncSession,
    code: str,
) -> Course | None:

    # Normalize user-provided codes so frontend casing/spacing
    # does not affect lookup.
    normalized_code = normalize_course_code(code)

    result = await session.scalar(select(Course).where(Course.code == normalized_code))

    return result


async def list_courses(
    session: AsyncSession,
) -> list[Course]:

    result = await session.scalars(select(Course).order_by(Course.code))

    return list(result)
