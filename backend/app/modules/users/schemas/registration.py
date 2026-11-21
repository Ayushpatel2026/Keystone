from typing import Annotated

from pydantic import Field

from app.modules.users.schemas.InstructorCreate import InstructorCreate
from app.modules.users.schemas.StudentCreate import StudentCreate
from app.modules.users.schemas.SupervisorCreate import SupervisorCreate
from app.modules.users.schemas.TaCreate import TaCreate

# A discriminated union tells Pydantic to select the correct schema
# based on the "role" field.
#
# i.e. if the request body contains "role": "student", Pydantic will use StudentCreate.
# This avoids one huge UserCreate class with many optional fields.
UserCreate = Annotated[
    StudentCreate | TaCreate | InstructorCreate | SupervisorCreate,
    Field(discriminator="role"),
]
