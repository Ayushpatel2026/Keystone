import uuid
from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

TeamName = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)]


class TeamCreate(BaseModel):
    name: TeamName
    course_id: uuid.UUID
    # Optional initial members: the student's user id.
    student_ids: list[uuid.UUID] = Field(default_factory=list)


class TeamMemberAdd(BaseModel):
    student_id: uuid.UUID


class UserSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    first_name: str
    last_name: str
    email: str


class TeamMemberRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    user: UserSummary
    student_number: str | None
    joined_at: datetime


class TeamRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    course_id: uuid.UUID
    members: list[TeamMemberRead]
    created_at: datetime
    updated_at: datetime