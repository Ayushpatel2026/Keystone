import asyncio

from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.core.database import build_engine
from app.modules.auth.manager import password_helper
from app.modules.users.models import (
    SupervisorType,
    SupervisorVerificationStatus,
    User,
    UserRole,
)

# Development-only password shared by all seed users.
# Never run this seed script against a shared or production database.
SEED_PASSWORD = "dev-password-123"

# Development users for testing the Keystone API.
SEED_USERS = [
    {
        "first_name": "Alice",
        "last_name": "Student",
        "email": "alice.student@mcmaster.ca",
        "role": UserRole.STUDENT,
        "is_active": True,
        "is_superuser": False,
    },
    {
        "first_name": "Bob",
        "last_name": "TA",
        "email": "bob.ta@mcmaster.ca",
        "role": UserRole.TA,
        "is_active": True,
        "is_superuser": False,
    },
    {
        "first_name": "Carol",
        "last_name": "Instructor",
        "email": "carol.instructor@mcmaster.ca",
        "role": UserRole.INSTRUCTOR,
        "is_active": True,
        "is_superuser": True,
    },
    {
        "first_name": "David",
        "last_name": "Supervisor",
        "email": "david.supervisor@example.com",
        "role": UserRole.SUPERVISOR,
        "is_active": True,
        "is_superuser": False,
        "supervisor_type": SupervisorType.INTERNAL,
        "supervisor_verification_status": SupervisorVerificationStatus.VERIFIED,
    },
    {
        "first_name": "Emily",
        "last_name": "External Supervisor",
        "email": "emily.external@example.com",
        "role": UserRole.SUPERVISOR,
        # Previously AccountStatus.PENDING: inactive until verified.
        "is_active": False,
        "is_superuser": False,
        "supervisor_type": SupervisorType.EXTERNAL,
        "supervisor_verification_status": SupervisorVerificationStatus.UNVERIFIED,
    },
]


async def seed_users() -> None:
    # Create the database engine.
    engine = build_engine()

    # Create a factory that produces database sessions.
    session_factory = async_sessionmaker(
        engine,
        expire_on_commit=False,
    )

    # Hash once with Argon2; each user gets their own salted hash below.
    try:
        async with session_factory() as session:
            for user_data in SEED_USERS:
                # Normalize emails before checking uniqueness.
                email = str(user_data["email"]).lower()

                # Check whether this user already exists.
                result = await session.execute(select(User).filter_by(email=email))
                existing_user = result.scalar_one_or_none()

                # Skip existing users so running the script repeatedly is safe.
                if existing_user is not None:
                    print(f"Skipping existing user: {email}")
                    continue

                # Create a SQLAlchemy ORM object from the seed data.
                user = User(
                    **{
                        **user_data,
                        "email": email,
                        "hashed_password": password_helper.hash(SEED_PASSWORD),
                        "is_verified": True,
                    }
                )

                session.add(user)

            # Persist all newly added users.
            await session.commit()

            print("User seeding completed.")

    finally:
        # Close the engine and release its resources.
        await engine.dispose()


if __name__ == "__main__":
    # Run the async seed function when this file is executed directly.
    asyncio.run(seed_users())
