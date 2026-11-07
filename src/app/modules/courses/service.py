import uuid

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.courses.models import Course
from app.modules.courses.schemas import CourseCreate


class CourseCodeAlreadyExistsError(Exception):
    # Raised when a course with the same code already exists.
    pass


async def create_course(session: AsyncSession, data: CourseCreate) -> Course:
    course = Course(code=data.code, name=data.name, program=data.program)
    session.add(course)
    try:
        # The unique constraint on code is the source of truth, so we rely on it
        # instead of a check-then-insert, which would race.
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise CourseCodeAlreadyExistsError(data.code) from exc
    await session.refresh(course)
    return course


async def get_course(session: AsyncSession, course_id: uuid.UUID) -> Course | None:
    return await session.get(Course, course_id)


async def list_courses(session: AsyncSession) -> list[Course]:
    result = await session.scalars(select(Course).order_by(Course.code))
    return list(result)
