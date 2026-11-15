import uuid

from fastapi import APIRouter

from app.core.database import SessionDep
from app.modules.users.models import User, UserRole
from app.modules.users.schemas import UserReadUnion
from app.modules.users.service import get_users

router = APIRouter(
    prefix="/api/users",
    tags=["users"],
)


# TODO: POC ONLY — this endpoint is currently unauthenticated. Needs to be modified POST POC.
@router.get(
    "",
    response_model=list[UserReadUnion],
)
async def get_users_endpoint(
    session: SessionDep,
    role: UserRole | None = None,
    course_id: uuid.UUID | None = None,
) -> list[User]:

    return await get_users(
        session,
        role=role,
        course_id=course_id,
    )
