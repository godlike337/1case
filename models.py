from datetime import datetime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import ForeignKey, Table, Column, Integer, JSON
from database import Base

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

    grade: Mapped[int] = mapped_column(default=0)
    xp: Mapped[int] = mapped_column(default=0)
    level: Mapped[int] = mapped_column(default=1)
    rating: Mapped[int] = mapped_column(default=1000)
    wins: Mapped[int] = mapped_column(default=0)
    losses: Mapped[int] = mapped_column(default=0)
    matches_played: Mapped[int] = mapped_column(default=0)
    cor_anws: Mapped[int] = mapped_column(default=0)
    anws: Mapped[int] = mapped_column(default=0)
    total_time_spent: Mapped[float] = mapped_column(default=0.0)

    achievements = relationship("Achievement", secondary=user_achievements, lazy="selectin")


class Task(Base):
    __tablename__ = "tasks"
    id: Mapped[int] = mapped_column(primary_key=True)
    subject: Mapped[str] = mapped_column(default="python")
    topic: Mapped[str] = mapped_column(default="General")
    grade: Mapped[int] = mapped_column
    title: Mapped[str] = mapped_column()
    description: Mapped[str] = mapped_column()
    difficulty: Mapped[int] = mapped_column()
    task_type: Mapped[str] = mapped_column(default="text")
    options: Mapped[list] = mapped_column(JSON, nullable=True)
    correct_answer: Mapped[str] = mapped_column()
    hints: Mapped[list] = mapped_column(JSON, default=list)


class SolvedTask(Base):
    __tablename__ = "solved_tasks"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    task_id: Mapped[int] = mapped_column(ForeignKey("tasks.id"))
    subject: Mapped[str] = mapped_column(default="python")
    topic: Mapped[str] = mapped_column(default="General")

    solved_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)


class MatchHistory(Base):
    __tablename__ = "match_history"
    id: Mapped[int] = mapped_column(primary_key=True)
    p1_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=True)
    p2_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=True)
    player1 = relationship("User", foreign_keys=[p1_id])
    player2 = relationship("User", foreign_keys=[p2_id])
    subject: Mapped[str] = mapped_column()
    played_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)
    p1_score: Mapped[int] = mapped_column(default=0)
    p2_score: Mapped[int] = mapped_column(default=0)