# Importing these models ensures SQLAlchemy registers all tables
# with Base.metadata before database initialization/migrations.

from app.modules.users.models.Instructor import Instructor
from app.modules.users.models.InstructorCourse import InstructorCourse
from app.modules.users.models.Student import Student
from app.modules.users.models.Supervisor import Supervisor
from app.modules.users.models.TA import TA
from app.modules.users.models.User import (
    SupervisorType,
    SupervisorVerificationStatus,
    User,
    UserRole,
)

__all__ = [
    "User",
    "UserRole",
    "SupervisorType",
    "SupervisorVerificationStatus",
    "Student",
    "TA",
    "Instructor",
    "InstructorCourse",
    "Supervisor",
]
