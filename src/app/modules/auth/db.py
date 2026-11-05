from collections.abc import AsyncIterator

from fastapi_users.db import SQLAlchemyUserDatabase

from app.core.database import SessionDep
from app.modules.users.models import User


async def get_user_db(session: SessionDep) -> AsyncIterator[SQLAlchemyUserDatabase]:
    yield SQLAlchemyUserDatabase(session, User)