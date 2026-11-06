from fastapi import APIRouter

from app.modules.auth.backend import auth_backend
from app.modules.auth.users import fastapi_users
from app.modules.users.schemas import UserCreate, UserRead

router = APIRouter(prefix="/auth", tags=["auth"])

# POST /auth/login and POST /auth/logout
router.include_router(fastapi_users.get_auth_router(auth_backend))

# POST /auth/register
router.include_router(fastapi_users.get_register_router(UserRead, UserCreate))