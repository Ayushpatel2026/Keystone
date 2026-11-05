from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.users.models import User


# TODO - this is just a random query to test the database connection and full workflow.
# this will be modified in the future
async def get_users(session: AsyncSession) -> list[User]:
    # Construct a SELECT query for all users.
    statement = select(User)

    # Execute the query against PostgreSQL.
    result = await session.execute(statement)

    # Convert the result into a Python list of User ORM objects.
    users = result.scalars().all()

    # Return the users to the caller.
    return list(users)
