import uuid

from fastapi_users import FastAPIUsers

from app.modules.auth.backend import auth_backend
from app.modules.auth.manager import get_user_manager
from app.modules.users.models import User

fastapi_users = FastAPIUsers[User, uuid.UUID](get_user_manager, [auth_backend])

# Use as: user: User = Depends(current_active_user)
current_active_user = fastapi_users.current_user(active=True)