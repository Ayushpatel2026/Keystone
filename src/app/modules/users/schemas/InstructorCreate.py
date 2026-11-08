from typing import Annotated, Literal

from fastapi_users import schemas
from pydantic import Field, StringConstraints

CourseCode = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True,
        min_length=1,
        max_length=20,
    ),
]


class InstructorCreate(schemas.BaseUserCreate):
    first_name: Annotated[
        str,
        StringConstraints(strip_whitespace=True, min_length=1, max_length=100),
    ]

    last_name: Annotated[
        str,
        StringConstraints(strip_whitespace=True, min_length=1, max_length=100),
    ]

    role: Literal["instructor"] = "instructor"

    # An instructor may belong to multiple courses.
    course_codes: list[CourseCode] = Field(min_length=1)
