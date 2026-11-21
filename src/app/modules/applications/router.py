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


# Supervisor decisions. The acting supervisor is the authenticated user, never a parameter.
@router.post("/{application_id}/accept", response_model=ApplicationRead)
async def supervisor_accept_endpoint(
    application_id: uuid.UUID, session: SessionDep, user: CurrentUserDep
) -> ProjectApplication:
    try:
        return await service.supervisor_accept(session, user, application_id)
    except service.ProjectCapacityFullError:
        raise HTTPException(
            status.HTTP_409_CONFLICT, detail="The project has no free slots left"
        ) from None
    except service.ProjectNotOpenError as exc:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            detail=f"The project is not accepting teams (status: {exc.args[0]})",
        ) from None
    except _DECISION_ERRORS as exc:
        raise _decision_error(exc) from None


@router.post("/{application_id}/decline", response_model=ApplicationRead)
async def supervisor_decline_endpoint(
    application_id: uuid.UUID, session: SessionDep, user: CurrentUserDep
) -> ProjectApplication:
    try:
        return await service.supervisor_decline(session, user, application_id)
    except _DECISION_ERRORS as exc:
        raise _decision_error(exc) from None


# Errors shared by accept and decline.
_DECISION_ERRORS = (
    service.ApplicationNotFoundError,
    service.NotProjectSupervisorError,
    service.ActorNotPermittedError,
    service.InvalidTransitionError,
)


def _decision_error(exc: Exception) -> HTTPException:
    if isinstance(exc, service.ApplicationNotFoundError):
        return HTTPException(status.HTTP_404_NOT_FOUND, detail="Application not found")
    if isinstance(exc, service.InvalidTransitionError):
        # Typically a stale view: the application was already decided or withdrawn.
        return HTTPException(
            status.HTTP_409_CONFLICT,
            detail=f"This decision is not allowed in the application's current status ({exc})",
        )
    # NotProjectSupervisorError or ActorNotPermittedError.
    return HTTPException(
        status.HTTP_403_FORBIDDEN,
        detail="Only the project's supervisor can accept or decline its applications",
    )


@router.post("/{application_id}/agree", response_model=ApplicationRead)
async def agree_to_project_endpoint(
    application_id: uuid.UUID, session: SessionDep, user: CurrentUserDep
) -> ProjectApplication:
    try:
        return await service.agree_to_project(session, user, application_id)
    except service.ApplicationNotFoundError:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Application not found") from None
    except service.NotTeamMemberError:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN, detail="Only a team member can accept its project offer"
        ) from None
    except (service.InvalidTransitionError, service.TeamAlreadyAgreedError) as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, detail=str(exc)) from None


@router.post("/{application_id}/withdraw", response_model=ApplicationRead)
async def withdraw_application_endpoint(
    application_id: uuid.UUID, session: SessionDep, user: CurrentUserDep
) -> ProjectApplication:
    try:
        return await service.withdraw_application(session, user, application_id)
    except service.ApplicationNotFoundError:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Application not found") from None
    except service.NotTeamMemberError:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN, detail="Only a team member can withdraw its application"
        ) from None
    except service.InvalidTransitionError as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, detail=str(exc)) from None


@router.post("/{application_id}/reject", response_model=ApplicationRead)
async def reject_submission_endpoint(
    application_id: uuid.UUID, session: SessionDep, user: CurrentUserDep
) -> ProjectApplication:
    try:
        return await service.reject_submission(session, user, application_id)
    except service.ApplicationNotFoundError:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Application not found") from None
    except service.CourseAccessDeniedError:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            detail="Only authorized course instructors and TAs can reject submissions",
        ) from None
    except service.InvalidTransitionError as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, detail=str(exc)) from None
