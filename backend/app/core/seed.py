import asyncio
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.database import build_engine
from app.modules.auth.manager import password_helper
from app.modules.courses.models import Course, CourseProgram
from app.modules.courses.service import normalize_course_code
from app.modules.projects.models import Project, ProjectStatus
from app.modules.teams.models import Team, TeamMember
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


SEED_PROJECTS = [
    (
        "Smart Campus Navigation",
        "Help users find accessible routes across campus.",
        1,
        "david.supervisor@example.com",
    ),
    (
        "Automated Assembly Line",
        "Automate an assembly line using sensors and process controls.",
        1,
        "david.supervisor@example.com",
    ),
    (
        "Autonomous Waste Sorting System",
        "Identify and sort recyclable materials using computer vision and robotics.",
        2,
        "grace.professor@mcmaster.ca",
    ),
]


SEED_TEAMS = [
    ("Team Amazing Engineers", STUDENT_NAMES[:3]),
    ("Team Fantastic Coders", STUDENT_NAMES[3:6]),
    ("Team Capstone Legends", STUDENT_NAMES[6:]),
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


async def seed_courses(session: AsyncSession) -> dict[str, Course]:
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
    return courses


async def seed_users(session: AsyncSession, courses: dict[str, Course]) -> dict[str, User]:
    users: dict[str, User] = {}
    for spec in SEED_USERS:
        email = spec["email"].lower()

        existing = await session.scalar(select(User).where(User.email == email))

        # Idempotent seeding: running twice won't create duplicates.
        if existing is not None:
            users[email] = existing
            print(f"Skipping existing user: {email}")
            continue

        user = _build_user(spec, courses)

        session.add(user)
        users[email] = user

        print(f"Created {spec['role'].value}: {email}")
    await session.flush()
    return users


async def seed_projects(
    session: AsyncSession, courses: dict[str, Course], users: dict[str, User]
) -> None:
    course = courses[normalize_course_code(SE_CODE)]
    # Reuse the projects from the PoC plan without resetting existing demo progress.
    for title, background, capacity, email in SEED_PROJECTS:
        project = await session.scalar(
            select(Project).where(Project.course_id == course.id, Project.title == title)
        )
        if project is None:
            session.add(
                Project(
                    title=title,
                    background=background,
                    supervisor_id=users[email].id,
                    course_id=course.id,
                    supervisor_capacity=capacity,
                    slots_reserved=0,
                    status=ProjectStatus.OPEN,
                )
            )
            print(f"Created project: {title}")
        else:
            print(f"Existing project: {title}")


async def seed_teams(
    session: AsyncSession, courses: dict[str, Course], users: dict[str, User]
) -> None:
    course = courses[normalize_course_code(SE_CODE)]
    # Three demo teams share the eight seeded students, with no duplicate membership.
    for name, members in SEED_TEAMS:
        team = await session.scalar(
            select(Team).where(Team.course_id == course.id, Team.name == name)
        )
        if team is not None:
            print(f"Existing team: {name}")
            continue
        team = Team(course_id=course.id, name=name)
        session.add(team)
        await session.flush()
        for first, last in members:
            student = users[f"{first}.{last}@mcmaster.ca".lower()]
            membership = await session.scalar(
                select(TeamMember).where(TeamMember.student_id == student.id).limit(1)
            )
            if membership is None:
                session.add(TeamMember(team_id=team.id, student_id=student.id))
            else:
                print(f"Keeping existing team membership: {student.email}")
        print(f"Created team: {name}")


async def seed_all() -> None:
    engine = build_engine()
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    try:
        async with session_factory() as session:
            courses = await seed_courses(session)
            users = await seed_users(session, courses)
            await seed_projects(session, courses, users)
            await seed_teams(session, courses, users)
            # Save all seed data together.
            await session.commit()
            print("Development seeding completed successfully.")
    finally:
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(seed_all())
