from fastapi import APIRouter, HTTPException, Request, status
from fastapi_users import exceptions

from app.modules.auth.backend import auth_backend
from app.modules.auth.manager import UserManagerDep
from app.modules.auth.users import fastapi_users
from app.modules.users.models import User
from app.modules.users.schemas import (
    UserCreate,
    UserReadUnion,
)
from app.modules.users.service import (
    CourseNotFoundError,
    RegistrationConflictError,
)

router = APIRouter(
    prefix="/auth",
    tags=["auth"],
)


# POST /auth/login and POST /auth/logout
router.include_router(fastapi_users.get_auth_router(auth_backend))


# ================================================================
# TODO: POC ONLY — registration permits users to select their own role.
#
# Production must derive or authorize roles through institutional
# identity, enrollment records, or an administrator-controlled process.
#
# TODO: POC ONLY — SupervisorCreate allows users to select INTERNAL
# and VERIFIED. This must be replaced with trusted verification logic.
# ================================================================
@router.post(
    "/register",
    response_model=UserReadUnion,
    status_code=status.HTTP_201_CREATED,
)
async def register(
    request: Request,
    user_create: UserCreate,
    user_manager: UserManagerDep,
) -> User:

    try:
        # safe=True prevents users from setting FastAPI Users'
        # protected fields, including is_superuser, through registration.
        #
        # UserCreate itself does not expose is_superuser.
        return await user_manager.create(
            user_create,
            safe=True,
            request=request,
        )

    except exceptions.UserAlreadyExists:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "REGISTER_USER_ALREADY_EXISTS",
        ) from None

    except exceptions.InvalidPasswordException as exc:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            {
                "code": "REGISTER_INVALID_PASSWORD",
                "reason": exc.reason,
            },
        ) from None

    except CourseNotFoundError as exc:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            f"Course not found: {exc}",
        ) from None

    except RegistrationConflictError as exc:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            str(exc),
        ) from None
