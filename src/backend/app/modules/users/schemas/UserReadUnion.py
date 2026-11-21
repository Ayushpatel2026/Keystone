from typing import Annotated

from pydantic import Field

from app.modules.users.schemas.InstructorRead import InstructorRead
from app.modules.users.schemas.StudentRead import StudentRead
from app.modules.users.schemas.SupervisorRead import SupervisorRead
from app.modules.users.schemas.TARead import TARead

# Pydantic uses the role field to select the appropriate response schema.
# This prevents unrelated role-specific fields from appearing in responses.
UserReadUnion = Annotated[
    StudentRead | TARead | InstructorRead | SupervisorRead,
    Field(discriminator="role"),
]
