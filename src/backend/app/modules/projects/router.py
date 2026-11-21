import uuid

from fastapi import APIRouter, HTTPException, status

from app.core.database import SessionDep
from app.modules.projects import service
from app.modules.projects.models import Project, ProjectStatus
from app.modules.projects.schemas import ProjectCreate, ProjectRead, ProjectUpdate

router = APIRouter(prefix="/api/projects", tags=["projects"])

# TODO: POC ONLY - supervisor_id is an explicitly selected actor, not proof of
# identity. Anyone can select an actor. After the PoC, derive it from the
# authenticated user and enforce role/course access rules for all endpoints.


@router.post("", response_model=ProjectRead, status_code=status.HTTP_201_CREATED)
async def create_project_endpoint(
    data: ProjectCreate,
    supervisor_id: uuid.UUID,
    session: SessionDep,
) -> Project:
    try:
        return await service.create_project(session, data, supervisor_id)
    except service.CourseNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Course not found"
        ) from None
    except service.SupervisorNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Supervisor not found"
        ) from None


@router.get("", response_model=list[ProjectRead])
async def list_projects_endpoint(
    session: SessionDep,
    course_id: uuid.UUID | None = None,
    supervisor_id: uuid.UUID | None = None,
    status: ProjectStatus | None = None,
) -> list[Project]:
    return await service.list_projects(
        session, course_id=course_id, supervisor_id=supervisor_id, status=status
    )


@router.get("/{project_id}", response_model=ProjectRead)
async def get_project_endpoint(project_id: uuid.UUID, session: SessionDep) -> Project:
    project = await service.get_project(session, project_id)
    if project is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    return project


@router.patch("/{project_id}", response_model=ProjectRead)
async def update_project_endpoint(
    project_id: uuid.UUID,
    data: ProjectUpdate,
    supervisor_id: uuid.UUID,
    session: SessionDep,
) -> Project:
    try:
        return await service.update_project(session, project_id, data, supervisor_id)
    except service.ProjectNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Project not found"
        ) from None
    except service.CourseNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Course not found"
        ) from None
    except service.ProjectOwnershipError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the project's supervisor can update it",
        ) from None
    except service.CapacityChangeNotSupportedError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc)) from None
