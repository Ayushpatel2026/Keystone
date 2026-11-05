import asyncio

from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.core.database import build_engine
from app.modules.users.models import (
    AccountStatus,
    SupervisorType,
    SupervisorVerificationStatus,
    User,
    UserRole,
)

# Development users for testing the Keystone API.
SEED_USERS = [
    {
        "name": "Alice Student",
        "email": "alice.student@mcmaster.ca",
        "role": UserRole.STUDENT,
        "account_status": AccountStatus.ACTIVE,
        "is_admin": False,
    },
    {
        "name": "Bob TA",
        "email": "bob.ta@mcmaster.ca",
        "role": UserRole.TA,
        "account_status": AccountStatus.ACTIVE,
        "is_admin": False,
    },
    {
        "name": "Carol Instructor",
        "email": "carol.instructor@mcmaster.ca",
        "role": UserRole.INSTRUCTOR,
        "account_status": AccountStatus.ACTIVE,
        "is_admin": True,
    },
    {
        "name": "David Supervisor",
        "email": "david.supervisor@example.com",
        "role": UserRole.SUPERVISOR,
        "account_status": AccountStatus.ACTIVE,
        "is_admin": False,
        "supervisor_type": SupervisorType.INTERNAL,
        "supervisor_verification_status": SupervisorVerificationStatus.VERIFIED,
    },
    {
        "name": "Emily External Supervisor",
        "email": "emily.external@example.com",
        "role": UserRole.SUPERVISOR,
        "account_status": AccountStatus.PENDING,
        "is_admin": False,
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

    try:
        # Open a database session.
        async with session_factory() as session:
            # Iterate over the predefined development users.
            for user_data in SEED_USERS:
                # Normalize emails before checking uniqueness.
                email = str(user_data["email"]).lower()

                # Check whether this user already exists.
                result = await session.execute(select(User).where(User.email == email))

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
                    }
                )

                # Add the user to the current transaction.
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
