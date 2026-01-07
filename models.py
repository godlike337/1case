from datetime import datetime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import ForeignKey, DateTime
from database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(unique=True)
    password: Mapped[str] = mapped_column()
    role: Mapped[str] = mapped_column(default="user")

    #Поля статистики
    rating: Mapped[int] = mapped_column(default=1000)
    wins: Mapped[int] = mapped_column(default=0)
    losses: Mapped[int] = mapped_column(default=0)
    matches_played: Mapped[int] = mapped_column(default=0)


class Task(Base):
    __tablename__ = "tasks"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column()
    description: Mapped[str] = mapped_column()
    difficulty: Mapped[int] = mapped_column()
    correct_answer: Mapped[str] = mapped_column()

    #Предмет
    subject: Mapped[str] = mapped_column(default="None")


#История
class MatchHistory(Base):
    __tablename__ = "match_history"

    id: Mapped[int] = mapped_column(primary_key=True)
    winner_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    loser_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    subject: Mapped[str] = mapped_column()
    played_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)