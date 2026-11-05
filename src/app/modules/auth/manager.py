import uuid
from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import Depends
from fastapi_users import BaseUserManager, UUIDIDMixin
from fastapi_users.db import SQLAlchemyUserDatabase
from fastapi_users.password import PasswordHelper
from pwdlib import PasswordHash
from pwdlib.hashers.argon2 import Argon2Hasher

from app.core.config import get_settings
from app.modules.auth.db import get_user_db
from app.modules.users.models import User

password_helper = PasswordHelper(PasswordHash((Argon2Hasher(),)))

# Reusable dependency, same pattern as SessionDep in database.py.
UserDbDep = Annotated[SQLAlchemyUserDatabase, Depends(get_user_db)]


class UserManager(UUIDIDMixin, BaseUserManager[User, uuid.UUID]):
    @property
    def reset_password_token_secret(self) -> str:  # type: ignore[override]
        return get_settings().secret_key

    @property
    def verification_token_secret(self) -> str:  # type: ignore[override]
        return get_settings().secret_key


async def get_user_manager(user_db: UserDbDep) -> AsyncIterator[UserManager]:
    yield UserManager(user_db, password_helper)
