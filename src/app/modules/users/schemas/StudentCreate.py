from typing import Annotated, Literal

from fastapi_users import schemas
from pydantic import StringConstraints

from app.modules.users.models.User import UserRole

StudentNumber = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True,
        min_length=1,
        max_length=20,
    ),
]

CourseCode = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True,
        min_length=1,
        max_length=20,
    ),
]


class StudentCreate(schemas.BaseUserCreate):
    first_name: Annotated[
        str,
        StringConstraints(strip_whitespace=True, min_length=1, max_length=100),
    ]

    last_name: Annotated[
        str,
        StringConstraints(strip_whitespace=True, min_length=1, max_length=100),
    ]

    role: Literal[UserRole.STUDENT] = UserRole.STUDENT

    student_number: StudentNumber

    course_code: CourseCode
