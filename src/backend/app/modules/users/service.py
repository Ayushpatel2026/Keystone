import uuid
from collections.abc import Collection
from typing import Any

from sqlalchemy import exists, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.courses.models import Course
from app.modules.courses.service import normalize_course_code
from app.modules.users.models import (
    TA,
    Instructor,
    InstructorCourse,
    Student,
    Supervisor,
    SupervisorType,
    SupervisorVerificationStatus,
    User,
    UserRole,
)


class CourseNotFoundError(Exception):
    # Raised when a registration references a course that doesn't exist.
    pass


class RegistrationConflictError(Exception):
    # Raised when the email or student number already exists.
    pass


async def get_users(
    session: AsyncSession,
    role: UserRole | None = None,
    course_id: uuid.UUID | None = None,
) -> list[User]:

    stmt = select(User).order_by(User.last_name, User.first_name)

    if role is not None:
        stmt = stmt.where(User.role == role)

    if course_id is not None:
        stmt = stmt.where(
            or_(
                exists().where(
                    Student.user_id == User.id,
                    Student.course_id == course_id,
                ),
                exists().where(
                    TA.user_id == User.id,
                    TA.course_id == course_id,
                ),
                exists().where(
                    InstructorCourse.instructor_id == User.id,
                    InstructorCourse.course_id == course_id,
                ),
            )
        )

    return list((await session.scalars(stmt)).all())


async def get_courses_by_codes(
    session: AsyncSession,
    course_codes: Collection[str],
) -> dict[str, Course]:

    # Normalize all codes so casing and spacing differences don't matter.
    normalized_codes = {normalize_course_code(code) for code in course_codes}

    if not normalized_codes:
        return {}

    result = await session.scalars(select(Course).where(Course.code.in_(normalized_codes)))

    courses = list(result)

    # Key by normalized course code for easy lookup by the registration
    # payload's course_code/course_codes fields.
    courses_by_code = {normalize_course_code(course.code): course for course in courses}

    missing = normalized_codes - courses_by_code.keys()

    if missing:
        raise CourseNotFoundError(", ".join(sorted(missing)))

    return courses_by_code


def build_user(
    data: dict[str, Any],
    courses: dict[str, Course],
) -> User:

    # Remove role-specific registration fields before constructing User.
    data = dict(data)

    student_number = data.pop("student_number", None)
    course_code = data.pop("course_code", None)
    course_codes = data.pop("course_codes", None)

    supervisor_type = data.pop(
        "supervisor_type",
        SupervisorType.EXTERNAL,
    )

    verification_status = data.pop(
        "verification_status",
        SupervisorVerificationStatus.UNVERIFIED,
    )

    user = User(**data)

    match UserRole(data["role"]):
        case UserRole.STUDENT:
            if student_number is None or course_code is None:
                raise ValueError("A student needs a student_number and course_code")

            normalized_code = normalize_course_code(course_code)

            user.student = Student(
                student_number=student_number,
                course_id=courses[normalized_code].id,
            )

        case UserRole.TA:
            if course_code is None:
                raise ValueError("A TA needs a course_code")

            normalized_code = normalize_course_code(course_code)

            user.ta = TA(
                course_id=courses[normalized_code].id,
            )

        case UserRole.INSTRUCTOR:
            if not course_codes:
                raise ValueError("An instructor needs at least one course")

            # Resolve course codes to IDs while avoiding duplicate links.
            normalized_codes = dict.fromkeys(normalize_course_code(code) for code in course_codes)

            user.instructor = Instructor(
                course_links=[
                    InstructorCourse(
                        course_id=courses[code].id,
                    )
                    for code in normalized_codes
                ]
            )

        case UserRole.SUPERVISOR:
            # TODO: POC ONLY — users can choose their supervisor type
            # and verification status. Remove this POST POC.
            user.supervisor = Supervisor(
                supervisor_type=supervisor_type,
                verification_status=verification_status,
            )

    return user


async def create_user_with_profile(
    session: AsyncSession,
    data: dict[str, Any],
) -> User:

    # Gather every course code required by this registration.
    requested_codes = set(data.get("course_codes") or [])

    if data.get("course_code") is not None:
        requested_codes.add(data["course_code"])

    # Resolve courses before creating the User, preventing registration
    # from proceeding if any referenced course is missing.
    courses = await get_courses_by_codes(
        session,
        requested_codes,
    )

    user = build_user(data, courses)

    session.add(user)

    try:
        await session.flush()

        user_id = user.id

        await session.commit()

    except IntegrityError as exc:
        await session.rollback()

        raise RegistrationConflictError("Email or student number is already registered") from exc

    # Re-query to populate relationships needed for API serialization.
    result = await session.execute(
        select(User)
        .where(User.id == user_id)  # type: ignore[arg-type]
        .execution_options(populate_existing=True)
    )

    return result.scalar_one()
