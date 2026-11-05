from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.core.config import get_settings
from app.core.database import build_engine
from app.modules.health.router import router as health_router
from app.modules.users.router import router as users_router

from app.modules.auth.backend import auth_backend
from app.modules.auth.users import fastapi_users
from app.modules.users.schemas import UserCreate, UserRead, UserUpdate

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
    # POST /auth/login, POST /auth/logout
    app.include_router(
        fastapi_users.get_auth_router(auth_backend), prefix="/auth", tags=["auth"]
    )
    # POST /auth/register
    app.include_router(
        fastapi_users.get_register_router(UserRead, UserCreate), prefix="/auth", tags=["auth"]
    )  


    return app


app = create_app()
