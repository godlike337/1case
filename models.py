from datetime import datetime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import ForeignKey, Table, Column, Integer
from database import Base

# Связь юзеров и ачивок
user_achievements = Table(
    "user_achievements", Base.metadata,
    Column("user_id", Integer, ForeignKey("users.id"), primary_key=True),
    Column("achievement_id", Integer, ForeignKey("achievements.id"), primary_key=True),
)


class Achievement(Base):
    __tablename__ = "achievements"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(unique=True)
    description: Mapped[str] = mapped_column()
    icon: Mapped[str] = mapped_column()


class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(unique=True)
    email: Mapped[str] = mapped_column(unique=True, nullable=True)
    password: Mapped[str] = mapped_column()
    role: Mapped[str] = mapped_column(default="user")

    # Геймификация
    xp: Mapped[int] = mapped_column(default=0)
    level: Mapped[int] = mapped_column(default=1)
    rating: Mapped[int] = mapped_column(default=1000)
    wins: Mapped[int] = mapped_column(default=0)
    losses: Mapped[int] = mapped_column(default=0)
    matches_played: Mapped[int] = mapped_column(default=0)

    achievements = relationship("Achievement", secondary=user_achievements, lazy="selectin")


class Task(Base):
    __tablename__ = "tasks"
    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column()
    description: Mapped[str] = mapped_column()
    difficulty: Mapped[int] = mapped_column()
    correct_answer: Mapped[str] = mapped_column()
    subject: Mapped[str] = mapped_column(default="python")
    # subject можно сделать Enum или отдельной таблицей в будущем, пока оставим строкой для простоты


# --- НОВАЯ ТАБЛИЦА: КТО ЧТО РЕШИЛ ---
class SolvedTask(Base):
    __tablename__ = "solved_tasks"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    task_id: Mapped[int] = mapped_column(ForeignKey("tasks.id"))
    solved_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)


class MatchHistory(Base):
    __tablename__ = "match_history"
    id: Mapped[int] = mapped_column(primary_key=True)
    winner_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=True)
    loser_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=True)
    winner = relationship("User", foreign_keys=[winner_id])
    loser = relationship("User", foreign_keys=[loser_id])
    subject: Mapped[str] = mapped_column()
    played_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    winner_score: Mapped[int] = mapped_column(default=0)
    loser_score: Mapped[int] = mapped_column(default=0)