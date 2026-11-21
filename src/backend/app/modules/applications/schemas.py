import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.modules.applications.lifecycle import ApplicationStatus


# Note that the acting student is NOT in the body. It is a query parameter (see the router)
class ApplicationCreate(BaseModel):
    # extra="forbid" rejects unknown JSON fields with a 422 instead of silently ignoring a typo.
    model_config = ConfigDict(extra="forbid")

    team_id: uuid.UUID
    project_id: uuid.UUID


class ApplicationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    team_id: uuid.UUID
    project_id: uuid.UUID
    status: ApplicationStatus
    created_at: datetime
    updated_at: datetime
