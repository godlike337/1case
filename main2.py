from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles # <--- ИМПОРТ
from starlette.responses import FileResponse # <--- ИМПОРТ
from contextlib import asynccontextmanager

from sqladmin import Admin
from database import engine, Base, get_db
import auth
import tasks
import pvp # Не забудь, если еще нет
from admin_panel import UserAdmin, TaskAdmin, MatchHistoryAdmin

@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("--- БАЗА ДАННЫХ ПОДКЛЮЧЕНА ---")
    async for db_session in get_db():
        await auth.create_initial_admin_user(db_session)
        break
    yield

app = FastAPI(lifespan=lifespan, title="Платформа для олимпиад")

# --- ПОДКЛЮЧЕНИЕ СТАТИКИ ---
# Теперь папка static доступна по адресу /static
app.mount("/static", StaticFiles(directory="static"), name="static")

# ГЛАВНАЯ СТРАНИЦА отдаем index.html
@app.get("/")
async def read_index():
    return FileResponse("static/index.html")

# --- АДМИНКА ---
admin = Admin(app, engine, title="Админ-панель")
admin.add_view(UserAdmin)
admin.add_view(TaskAdmin)
admin.add_view(MatchHistoryAdmin)

app.include_router(auth.router)
app.include_router(tasks.router)
app.include_router(pvp.router)