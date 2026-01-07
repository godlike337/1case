from fastapi import FastAPI
from contextlib import asynccontextmanager

from sqladmin import Admin
from database import engine, Base, get_db
import auth
import tasks
import pvp
from admin_panel import UserAdmin, TaskAdmin
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
admin = Admin(app, engine, title="Админ-панель (Dev Mode)")

admin.add_view(UserAdmin)
admin.add_view(TaskAdmin)

app.include_router(auth.router)
app.include_router(tasks.router)
app.include_router(pvp.router)