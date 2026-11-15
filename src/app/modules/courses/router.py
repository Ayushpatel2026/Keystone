import uuid

from fastapi import APIRouter, HTTPException, status

from app.core.database import SessionDep
from app.modules.courses import service
from app.modules.courses.models import Course
from app.modules.courses.schemas import CourseCreate, CourseRead

router = APIRouter(prefix="/api/courses", tags=["courses"])

# TODO: the PoC has no RBAC, so these endpoints are open. Later, creating a course
# should require an instructor/admin via Depends(current_active_user).


@router.post("", response_model=CourseRead, status_code=status.HTTP_201_CREATED)
async def create_course_endpoint(data: CourseCreate, session: SessionDep) -> Course:
    try:
        return await service.create_course(session, data)
    except service.CourseCodeAlreadyExistsError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"A course with code '{data.code}' already exists",
        ) from None


@router.get("", response_model=list[CourseRead])
async def list_courses_endpoint(session: SessionDep) -> list[Course]:
    return await service.list_courses(session)


@router.get("/{course_id}", response_model=CourseRead)
async def get_course_endpoint(course_id: uuid.UUID, session: SessionDep) -> Course:
    course = await service.get_course(session, course_id)
    if course is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Course not found")
    return course
