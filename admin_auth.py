from starlette.requests import Request
from sqladmin.authentication import AuthenticationBackend
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from database import new_session
from models import User
from auth import verify_password


class AdminAuth(AuthenticationBackend):
    async def login(self, request: Request) -> bool:
        form = await request.form()
        username = form.get("username")
        password = form.get("password")

        print(f"DEBUG: Попытка входа в админку. Логин: {username}")

        async with new_session() as db_session:
            result = await db_session.execute(select(User).where(User.username == username))
            user = result.scalar_one_or_none()

            if not user:
                print("DEBUG: ОШИБКА - Пользователь не найден в базе!")
                return False

            print(f"DEBUG: Пользователь найден. ID: {user.id}, Роль: {user.role}")

            if not verify_password(password, user.password):
                print("DEBUG: ОШИБКА - Неверный пароль!")
                return False

            if user.role != "admin":
                print(f"DEBUG: ОШИБКА - Роль пользователя '{user.role}', а нужен 'admin'!")
                return False

            # Если мы тут, значит всё ок
            print("DEBUG: УСПЕХ! Вход разрешен.")
            request.session["admin_user_id"] = user.id
            return True

    async def logout(self, request: Request) -> bool:
        request.session.clear()
        return True

    async def authenticate(self, request: Request):
        # Читаем ID из сессии
        user_id = request.session.get("admin_user_id")

        # ОТЛАДКА: Смотрим, что пришло от браузера
        if not user_id:
            print(f"DEBUG AUTH: Сессия пустая! Куки не пришли. Path: {request.url.path}")
            return None

        print(f"DEBUG AUTH: Найден ID в сессии: {user_id}")

        async with new_session() as db_session:
            result = await db_session.execute(select(User).where(User.id == user_id))
            user = result.scalar_one_or_none()

            if user and user.role == "admin":
                return user.username

        return None

