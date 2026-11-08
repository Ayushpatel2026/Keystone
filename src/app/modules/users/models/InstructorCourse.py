import uuid

from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class InstructorCourse(Base):
    # Association table implementing the many-to-many relationship:
    # Instructor <-> Course.
    __tablename__ = "instructor_courses"

    # Composite primary key prevents duplicate instructor/course links.
    instructor_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("instructors.user_id", ondelete="CASCADE"),
        primary_key=True,
    )

    course_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("courses.id", ondelete="CASCADE"),
        primary_key=True,
    )
