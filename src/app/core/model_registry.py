# Importing this module causes SQLAlchemy to register the model
# in Base.metadata, which Alembic uses to detect schema changes.
# as Keystone grows, add imports for other models here:
from app.modules.courses import models as course_models
from app.modules.teams import models as team_models
from app.modules.users import models as user_models

__all__ = ["user_models", "course_models", "team_models"]
