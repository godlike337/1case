from fastapi import FastAPI
from contextlib import asynccontextmanager

from database import engine, Base
import auth
import tasks
@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("--- БАЗА ДАННЫХ ПОДКЛЮЧЕНА ---")
    yield

app = FastAPI(lifespan=lifespan, title="платформа для умных")
app.include_router(auth.router)

@app.get("/")
def root():
    return {"message": "оно работает аухеть!"}
app.include_router(auth.router)
app.include_router(tasks.router)