import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.core.database import SessionDep
from app.modules.applications import service
from app.modules.applications.lifecycle import ApplicationStatus
from app.modules.applications.models import ProjectApplication
from app.modules.applications.schemas import ApplicationCreate, ApplicationRead
from app.modules.auth.users import current_active_user
from app.modules.users.models import User

router = APIRouter(prefix="/api/applications", tags=["applications"])

# The signed-in user, from the bearer token. Requests without a valid token get a 401.
CurrentUserDep = Annotated[User, Depends(current_active_user)]

# TODO: POC ONLY - student_id is an explicitly chosen actor, not proof of identity.
# After the PoC, take it from the authenticated user (Depends(current_active_user)).


@router.post("", response_model=ApplicationRead, status_code=status.HTTP_201_CREATED)
async def apply_to_project_endpoint(
    data: ApplicationCreate,
    # A plain parameter that isn't part of the pydantic body model is read by FastAPI from
    # the query string: POST /api/applications?student_id=<uuid>
    student_id: uuid.UUID,
    session: SessionDep,
) -> ProjectApplication:
    # Each domain error becomes an HTTP status.
    # `from None` hides the internal exception chain from the response and logs.
    try:
        return await service.apply_to_project(session, data, student_id)
    except service.TeamNotFoundError:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Team not found") from None
    except service.ProjectNotFoundError:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Project not found") from None
    except service.NotTeamMemberError:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN, detail="Only a member of the team can apply on its behalf"
        ) from None
    except service.CourseMismatchError:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="The team and the project belong to different courses",
        ) from None
    except service.ProjectNotOpenError as exc:
        # exc.args[0] is the project's current status ("full" or "closed").
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            detail=f"Project is not open for applications (status: {exc.args[0]})",
        ) from None
    except service.TeamAlreadyAgreedError:
        raise HTTPException(
            status.HTTP_409_CONFLICT, detail="The team has already agreed to a project"
        ) from None
    except service.DuplicateApplicationError:
        raise HTTPException(
            status.HTTP_409_CONFLICT, detail="The team has already applied to this project"
        ) from None


# Unlike the PoC write endpoints above, reads are scoped to the authenticated user: a caller
# only ever sees the applications their role allows (see service.list_applications).
@router.get("", response_model=list[ApplicationRead])
async def list_applications_endpoint(
    session: SessionDep,
    user: CurrentUserDep,
    course_id: uuid.UUID | None = None,
    project_id: uuid.UUID | None = None,
    team_id: uuid.UUID | None = None,
    # Named status_filter so it doesn't shadow fastapi's `status` module; the query
    # parameter is still ?status=...
    status_filter: Annotated[ApplicationStatus | None, Query(alias="status")] = None,
) -> list[ProjectApplication]:
    try:
        return await service.list_applications(
            session,
            user,
            course_id=course_id,
            project_id=project_id,
            team_id=team_id,
            status=status_filter,
        )
    except service.CourseAccessDeniedError:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN, detail="You are not a member of this course"
        ) from None


@router.get("/{application_id}", response_model=ApplicationRead)
async def get_application_endpoint(
    application_id: uuid.UUID, session: SessionDep, user: CurrentUserDep
) -> ProjectApplication:
    try:
        return await service.get_application(session, user, application_id)
    except service.ApplicationNotFoundError:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Application not found") from None
