# Importing this module causes SQLAlchemy to register the User model
# in Base.metadata, which Alembic uses to detect schema changes.
from app.modules.users import models  # noqa: F401

# as Keystone grows, add imports forr other models here:

# e.g.
# from app.modules.projects import models
# from app.modules.teams import models
