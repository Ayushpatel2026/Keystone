from fastapi import FastAPI

from app.core.config import get_settings
from app.modules.health.router import router as health_router


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title=settings.app_name)

    # Router aggregation: each module exposes a `router`, registered here.
    app.include_router(health_router)

    return app


app = create_app()
