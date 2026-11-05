from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy import MetaData
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from app.core.config import get_settings

# Consistent names make database constraints easier to identify in migrations.
NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    # All ORM models inherit from Base.
    # SQLAlchemy collects their table definitions in Base.metadata.
    metadata = MetaData(naming_convention=NAMING_CONVENTION)


def build_engine(url: str | None = None) -> AsyncEngine:
    # Read configuration.
    settings = get_settings()

    # Create the engine responsible for database connections.
    return create_async_engine(
        url or settings.database_url,
        pool_pre_ping=True,
    )


async def get_session(request: Request) -> AsyncIterator[AsyncSession]:
    # Retrieve the session factory created when the FastAPI app starts.
    session_factory = request.app.state.session_factory

    # Create one session for this request and close it afterward.
    async with session_factory() as session:
        yield session


# Reusable FastAPI dependency for endpoints requiring database access.
SessionDep = Annotated[AsyncSession, Depends(get_session)]
