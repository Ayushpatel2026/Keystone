from fastapi import APIRouter

from app.core.database import SessionDep
from app.modules.users.models import User
from app.modules.users.schemas import UserResponse
from app.modules.users.service import get_users

router = APIRouter(
    prefix="/api",
    tags=["users"],
)


# TODO - this is just a random endpoint to test the full workflow of
# fast api, sqlalchemy, and postgresql. This will be modified in the future.
@router.get("/getUsers", response_model=list[UserResponse])
async def get_users_endpoint(session: SessionDep) -> list[User]:
    # Ask the service layer to retrieve users from PostgreSQL.
    users = await get_users(session)

    # FastAPI converts the ORM User objects into UserResponse JSON objects.
    return users
