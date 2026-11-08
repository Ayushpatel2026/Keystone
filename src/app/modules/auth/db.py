import uuid
from collections.abc import AsyncIterator
from typing import Any

from fastapi_users.db import SQLAlchemyUserDatabase

from app.core.database import SessionDep
from app.modules.users.models import User
from app.modules.users.service import create_user_with_profile


class KeystoneUserDatabase(SQLAlchemyUserDatabase[User, uuid.UUID]):
    async def create(self, create_dict: dict[str, Any]) -> User:
        # Override FastAPI Users' default implementation because it would
        # create only the parent User row.
        #
        # Our service also creates the matching role profile, ensuring
        # registration creates both rows in one transaction.
        return await create_user_with_profile(
            self.session,
            create_dict,
        )


async def get_user_db(
    session: SessionDep,
) -> AsyncIterator[SQLAlchemyUserDatabase[User, uuid.UUID]]:

    # Yield the custom database adapter as a FastAPI dependency.
    yield KeystoneUserDatabase(session, User)
