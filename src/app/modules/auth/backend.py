import uuid

from fastapi_users.authentication import AuthenticationBackend, BearerTransport, JWTStrategy

from app.core.config import get_settings
from app.modules.users.models import User

bearer_transport = BearerTransport(tokenUrl="auth/login")


def get_jwt_strategy() -> JWTStrategy[User, uuid.UUID]:
    settings = get_settings()
    return JWTStrategy(
        secret=settings.secret_key,
        lifetime_seconds=settings.access_token_lifetime_seconds,
    )


auth_backend = AuthenticationBackend(
    name="jwt",
    transport=bearer_transport,
    get_strategy=get_jwt_strategy,
)
