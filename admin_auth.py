from sqladmin.authentication import AuthenticationBackend
from starlette.requests import Request
from sqlalchemy import select

from database import new_session
from models import User
from auth import verify_password


class AdminAuth(AuthenticationBackend):
    async def login(self, request: Request) -> bool:
        form = await request.form()
        username = form.get("username")
        password = form.get("password")

        async with new_session() as session:
            result = await session.execute(select(User).where(User.username == username))
            user = result.scalar_one_or_none()

            if user and verify_password(password, user.password) and user.role == "admin":
                request.session.update({"token": user.username})
                return True

        return False

    async def logout(self, request: Request) -> bool:
        request.session.clear()
        return True

    async def authenticate(self, request: Request):
        token = request.session.get("token")
        if not token:
            return None
        return token