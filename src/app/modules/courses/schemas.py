import uuid
from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, StringConstraints

from app.modules.courses.models import CourseProgram

CourseCode = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=20)]
CourseName = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)]


class CourseCreate(BaseModel):
    code: CourseCode
    name: CourseName
    program: CourseProgram


class CourseRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    code: str
    name: str
    program: CourseProgram
    created_at: datetime
    updated_at: datetime
