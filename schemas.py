from typing import List, Optional
from pydantic import BaseModel, EmailStr


class AchievementResponse(BaseModel):
    name: str
    description: str
    icon: str

    class Config:
        from_attributes = True


class UserCreate(BaseModel):
    username: str
    email: str  # <--- NEW
    password: str


class UserResponse(BaseModel):
    id: int
    username: str
    email: Optional[str] = None
    role: str

    rating: int
    xp: int
    level: int
    wins: int
    losses: int

    achievements: List[AchievementResponse] = []

    class Config:
        from_attributes = True



class Token(BaseModel):
    access_token: str
    token_type: str


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
    is_solved: bool = False

    class Config:
        from_attributes = True


class TaskAttempt(BaseModel):
    user_answer: str


class UserShort(BaseModel):
    username: str

    class Config: from_attributes = True


class MatchHistoryResponse(BaseModel):
    id: int
    subject: str
    played_at: str
    winner_score: int
    loser_score: int
    winner: Optional[UserShort]
    loser: Optional[UserShort]

    class Config: from_attributes = True