from sqlalchemy.orm import Mapped, mapped_column
from database import Base

class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(unique=True)
    password: Mapped[str] = mapped_column() #хеш
    # role: Mapped[str] = mapped_column(default="user") задел
class Task(Base):
        __tablename__ = "tasks"

        id: Mapped[int] = mapped_column(primary_key=True)
        title: Mapped[str] = mapped_column()  # Название
        description: Mapped[str] = mapped_column()  # Текст задачи
        difficulty: Mapped[int] = mapped_column()  # Сложность (1-10)
        correct_answer: Mapped[str] = mapped_column()  # Правильный ответ (скрыт)