import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


# TODO - make this more modular to allow for courses from other universities
class CourseProgram(enum.StrEnum):
    SE = "se"
    CS = "cs"
    TRON = "tron"


class Course(Base):
    # A capstone course. Teams and projects belong to a course.
    __tablename__ = "courses"

    __mapper_args__ = {"eager_defaults": True}

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)

    # e.g. "SFWRENG 4G06", unique across courses.
    code: Mapped[str] = mapped_column(String(20), unique=True)
    name: Mapped[str] = mapped_column(String(200))

    program: Mapped[CourseProgram] = mapped_column(
        Enum(
            CourseProgram,
            name="course_program",
            native_enum=False,
            create_constraint=True,
            length=20,
            values_callable=lambda e: [m.value for m in e],
        )
    )

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
