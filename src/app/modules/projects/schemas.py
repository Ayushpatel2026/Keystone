import uuid
from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, field_validator

from app.modules.projects.models import ProjectStatus

ProjectTitle = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)
]
ProjectBackground = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
ProjectCapacity = Annotated[int, Field(gt=0, strict=True)]


class ProjectCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: ProjectTitle
    background: ProjectBackground
    course_id: uuid.UUID
    supervisor_capacity: ProjectCapacity


class ProjectRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    title: str
    background: str
    supervisor_id: uuid.UUID
    course_id: uuid.UUID
    supervisor_capacity: int
    status: ProjectStatus
    created_at: datetime
    updated_at: datetime


class ProjectUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: ProjectTitle | None = None
    background: ProjectBackground | None = None
    course_id: uuid.UUID | None = None
    supervisor_capacity: ProjectCapacity | None = None

    @field_validator("title", "background", "course_id", "supervisor_capacity", mode="before")
    @classmethod
    def reject_null(cls, value: object) -> object:
        # PATCH may omit fields, but cannot clear non-nullable database columns.
        # Services should apply model_dump(exclude_unset=True).
        if value is None:
            raise ValueError("Omit this field to leave it unchanged; null is not allowed")
        return value
