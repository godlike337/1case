from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import DeclarativeBase

DATABASE_URL = "sqlite+aiosqlite:///./olympiad.db"

engine = create_async_engine(DATABASE_URL, echo=True)
new_session = async_sessionmaker(engine, expire_on_commit=False)

class Base(DeclarativeBase):
    pass

#сессия
async def get_db():
    async with new_session() as session:
        yield session