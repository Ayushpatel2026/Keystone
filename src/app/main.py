from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.core.config import get_settings
from app.core.database import build_engine
from app.modules.auth.router import router as auth_router
from app.modules.courses.router import router as courses_router
from app.modules.health.router import router as health_router
from app.modules.teams.router import router as teams_router
from app.modules.users.router import router as users_router


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    # Startup happens before the yield.
    yield

    # Shutdown happens after the yield.
    # Dispose of the engine and release database connections.
    await app.state.engine.dispose()


def create_app() -> FastAPI:
    # Load application configuration.
    settings = get_settings()

    # Create the FastAPI application.
    app = FastAPI(
        title=settings.app_name,
        lifespan=lifespan,
    )

    # Create the SQLAlchemy engine.
    engine = build_engine()

    # Store the engine so request dependencies can access it.
    app.state.engine = engine

    # Create a reusable factory for database sessions.
    app.state.session_factory = async_sessionmaker(
        engine,
        expire_on_commit=False,
    )

    # Register the endpoints from the routers
    app.include_router(users_router)
    app.include_router(health_router)
    app.include_router(auth_router)
    app.include_router(courses_router)
    app.include_router(teams_router)

    return app


app = create_app()
