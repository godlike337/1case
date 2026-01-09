from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles # <--- ИМПОРТ
from starlette.responses import FileResponse # <--- ИМПОРТ
from contextlib import asynccontextmanager

from sqladmin import Admin, ModelView
from database import engine, Base, get_db
import auth
import tasks
import pvp
from admin_panel import UserAdmin, TaskAdmin, MatchHistoryAdmin
from starlette.middleware.sessions import SessionMiddleware
from admin_auth import AdminAuth
from models import Achievement


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with new_session() as db:
        await auth.create_initial_admin_user(db)
        await auth.create_initial_achievements(db)

    print("--- СЕРВЕР ЗАПУЩЕН, БАЗА ГОТОВА ---")
    yield

class AchievementAdmin(ModelView, model=Achievement):
    name = "Достижение"
    name_plural = "Достижения"
    icon = "fa-solid fa-trophy"
    column_list = [Achievement.name, Achievement.description, Achievement.icon]


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async for db_session in get_db():
        await auth.create_initial_admin_user(db_session)
        await auth.create_initial_achievements(db_session)  # <--- СОЗДАЕМ АЧИВКИ
        break
    yield


app = FastAPI(lifespan=lifespan, title="Платформа для олимпиад")

app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
async def read_index():
    return FileResponse("static/index.html")

app.add_middleware(
    SessionMiddleware,
    secret_key="SECRET_KEY_FOR_COOKIES_123",
    max_age=3600,
    https_only=False,
    same_site="lax"
)
authentication_backend = AdminAuth(secret_key="SECRET_KEY_FOR_COOKIES_123")

admin = Admin(
    app,
    engine,
    title="Админ-панель",
    authentication_backend=authentication_backend
)

admin.add_view(UserAdmin)
admin.add_view(TaskAdmin)
admin.add_view(MatchHistoryAdmin)
admin.add_view(AchievementAdmin)
app.include_router(auth.router)
app.include_router(tasks.router)
app.include_router(pvp.router)
