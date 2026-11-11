import uuid

from fastapi import APIRouter, HTTPException, Response, status

from app.core.database import SessionDep
from app.modules.teams import service
from app.modules.teams.models import Team
from app.modules.teams.schemas import TeamCreate, TeamMemberAdd, TeamRead

router = APIRouter(prefix="/api/teams", tags=["teams"])

# TODO: POC ONLY, no RBAC yet. Later, restrict via current_active_user
# (team members, TAs and instructors).


@router.post("", response_model=TeamRead, status_code=status.HTTP_201_CREATED)
async def create_team_endpoint(data: TeamCreate, session: SessionDep) -> Team:
    try:
        return await service.create_team(session, data)
    except service.CourseNotFoundError:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Course not found") from None
    except service.StudentsNotFoundError as exc:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND, detail=f"Students not found: {exc.args[0]}"
        ) from None
    except service.TeamNameAlreadyExistsError:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            detail=f"A team named '{data.name}' already exists in this course",
        ) from None


@router.get("", response_model=list[TeamRead])
async def list_teams_endpoint(
    session: SessionDep, course_id: uuid.UUID | None = None
) -> list[Team]:
    return await service.list_teams(session, course_id)


@router.get("/{team_id}", response_model=TeamRead)
async def get_team_endpoint(team_id: uuid.UUID, session: SessionDep) -> Team:
    team = await service.get_team(session, team_id)
    if team is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Team not found")
    return team


@router.post("/{team_id}/members", response_model=TeamRead)
async def add_member_endpoint(team_id: uuid.UUID, data: TeamMemberAdd, session: SessionDep) -> Team:
    try:
        return await service.add_member(session, team_id, data.student_id)
    except service.TeamNotFoundError:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Team not found") from None
    except service.StudentsNotFoundError:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Student not found") from None


@router.delete("/{team_id}/members/{student_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_member_endpoint(
    team_id: uuid.UUID, student_id: uuid.UUID, session: SessionDep
) -> Response:
    try:
        await service.remove_member(session, team_id, student_id)
    except service.TeamMemberNotFoundError:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail="Member not found") from None
    return Response(status_code=status.HTTP_204_NO_CONTENT)