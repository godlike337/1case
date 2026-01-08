from pydantic import BaseModel
from datetime import datetime
from typing import Optional

# --- ПОЛЬЗОВАТЕЛИ ---
class UserCreate(BaseModel):
    username: str
    password: str


class UserResponse(BaseModel):
    id: int
    username: str
    role: str

    # Поля статистики
    rating: int
    wins: int
    losses: int
    matches_played: int

    class Config:
        from_attributes = True


# --- ТОКЕНЫ ---
class Token(BaseModel):
    access_token: str
    token_type: str


# --- ЗАДАЧИ ---
class TaskCreate(BaseModel):
    title: str
    description: str
    difficulty: int
    correct_answer: str
    subject: str


class TaskResponse(BaseModel):
    id: int
    title: str
    description: str
    difficulty: int
    subject: str

    class Config:
        from_attributes = True


# --- ВОТ ЭТОГО НЕ ХВАТАЛО ---
class TaskAttempt(BaseModel):
    user_answer: str


class UserShort(BaseModel):
    username: str

    class Config:
        from_attributes = True


# Схема одной записи истории
class MatchHistoryResponse(BaseModel):
    id: int
    subject: str
    played_at: datetime
    winner_score: int
    loser_score: int

    # Вложенные объекты (кто выиграл, кто проиграл)
    winner: Optional[UserShort]
    loser: Optional[UserShort]

    class Config:
        from_attributes = True