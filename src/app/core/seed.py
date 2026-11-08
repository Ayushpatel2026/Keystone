import asyncio
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.core.database import build_engine
from app.modules.auth.manager import password_helper
from app.modules.courses.models import Course, CourseProgram
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

# ================================================================
# DEVELOPMENT ONLY
#
# Never use this password or seed script against a production database.
# All seed accounts share this password for convenient local testing.
# ================================================================

SEED_PASSWORD = "dev-password-123"


SE_CODE = "SFWRENG 4G06"
CS_CODE = "COMPSCI 4G06"
TRON_CODE = "MECHTRON 4G06"


# Courses needed for testing.
#
# Existing courses are reused by code. New courses are inserted if missing.
SEED_COURSES = [
    {
        "code": SE_CODE,
        "name": "Software Engineering Capstone",
        "program": CourseProgram.SE,
    },
    {
        "code": CS_CODE,
        "name": "Computer Science Capstone",
        "program": CourseProgram.CS,
    },
    {
        "code": TRON_CODE,
        "name": "Mechatronics Capstone",
        "program": CourseProgram.TRON,
    },
]


STUDENT_NAMES = [
    ("Alice", "Anderson"),
    ("Ben", "Bailey"),
    ("Chloe", "Chen"),
    ("Dev", "Desai"),
    ("Elena", "Evans"),
    ("Farid", "Fox"),
    ("Grace", "Garcia"),
    ("Hiro", "Hayashi"),
]


SEED_USERS: list[dict[str, Any]] = [
    # Student users
    *[
        {
            "first_name": first,
            "last_name": last,
            "email": f"{first}.{last}@mcmaster.ca".lower(),
            "role": UserRole.STUDENT,
            "student_number": f"4000000{index:02d}",
            "course": SE_CODE,
        }
        for index, (first, last) in enumerate(
            STUDENT_NAMES,
            start=1,
        )
    ],
    # TA
    {
        "first_name": "Bob",
        "last_name": "TA",
        "email": "bob.ta@mcmaster.ca",
        "role": UserRole.TA,
        "course": SE_CODE,
    },
    # Instructor with multiple course assignments.
    {
        "first_name": "Carol",
        "last_name": "Instructor",
        "email": "carol.instructor@mcmaster.ca",
        "role": UserRole.INSTRUCTOR,
        "courses": [SE_CODE, TRON_CODE],
        # FastAPI Users' built-in privilege flag.
        "is_superuser": True,
    },
    # Internal verified supervisors.
    {
        "first_name": "David",
        "last_name": "Supervisor",
        "email": "david.supervisor@example.com",
        "role": UserRole.SUPERVISOR,
        "supervisor_type": SupervisorType.INTERNAL,
        "verification_status": SupervisorVerificationStatus.VERIFIED,
    },
    {
        "first_name": "Grace",
        "last_name": "Professor",
        "email": "grace.professor@mcmaster.ca",
        "role": UserRole.SUPERVISOR,
        "supervisor_type": SupervisorType.INTERNAL,
        "verification_status": SupervisorVerificationStatus.VERIFIED,
    },
    # External unverified supervisor.
    {
        "first_name": "Emily",
        "last_name": "External Supervisor",
        "email": "emily.external@example.com",
        "role": UserRole.SUPERVISOR,
        "supervisor_type": SupervisorType.EXTERNAL,
        "verification_status": SupervisorVerificationStatus.UNVERIFIED,
    },
]


def _build_user(
    spec: dict[str, Any],
    courses: dict[str, Course],
) -> User:

    # Build the common User identity first.
    # Role-specific fields are stored in child profile tables.
    user = User(
        first_name=spec["first_name"],
        last_name=spec["last_name"],
        email=spec["email"].lower(),
        role=spec["role"],
        hashed_password=password_helper.hash(SEED_PASSWORD),
        is_active=True,
        is_verified=True,
        # FastAPI Users' built-in admin privilege flag.
        # Defaults to False for every seed user unless explicitly set.
        is_superuser=spec.get("is_superuser", False),
    )

    match spec["role"]:
        case UserRole.STUDENT:
            course_code = normalize_course_code(spec["course"])

            user.student = Student(
                student_number=spec["student_number"],
                course_id=courses[course_code].id,
            )

        case UserRole.TA:
            course_code = normalize_course_code(spec["course"])

            user.ta = TA(
                course_id=courses[course_code].id,
            )

        case UserRole.INSTRUCTOR:
            course_codes = [normalize_course_code(code) for code in spec["courses"]]

            user.instructor = Instructor(
                course_links=[
                    InstructorCourse(
                        course_id=courses[code].id,
                    )
                    for code in dict.fromkeys(course_codes)
                ]
            )

        case UserRole.SUPERVISOR:
            # POC seed users can have any supervisor type/status.
            user.supervisor = Supervisor(
                supervisor_type=spec["supervisor_type"],
                verification_status=spec["verification_status"],
            )

    return user


async def seed_users() -> None:

    engine = build_engine()

    session_factory = async_sessionmaker(
        engine,
        expire_on_commit=False,
    )

    try:
        async with session_factory() as session:
            # ----------------------------------------------------
            # 1. Create/retrieve courses.
            # ----------------------------------------------------

            courses: dict[str, Course] = {}

            for course_data in SEED_COURSES:
                normalized_code = normalize_course_code(course_data["code"])

                course = await session.scalar(select(Course).where(Course.code == normalized_code))

                if course is None:
                    course = Course(
                        **{
                            **course_data,
                            "code": normalized_code,
                        }
                    )

                    session.add(course)

                    # Flush assigns generated UUIDs without committing.
                    await session.flush()

                    print(f"Created course: {normalized_code}")

                else:
                    print(f"Existing course: {normalized_code}")

                courses[normalized_code] = course

            # ----------------------------------------------------
            # 2. Create/retrieve users.
            # ----------------------------------------------------

            for spec in SEED_USERS:
                email = spec["email"].lower()

                existing = await session.scalar(select(User).where(User.email == email))

                # Idempotent seeding: running twice won't create duplicates.
                if existing is not None:
                    print(f"Skipping existing user: {email}")
                    continue

                user = _build_user(spec, courses)

                session.add(user)

                print(f"Created {spec['role'].value}: {email}")

            # Commit all new courses/users/profiles together.
            await session.commit()

            print("User seeding completed successfully.")

    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(seed_users())
