from pydantic import BaseModel, EmailStr
from typing import List, Optional
from datetime import datetime

class AchievementResponse(BaseModel):
    name: str
    description: str
    icon: str

    class Config:
        from_attributes = True


class UserCreate(BaseModel):
    username: str
    email: str
    password: str
    grade: int

class UserResponse(BaseModel):
    id: int
    username: str
    email: Optional[str] = None
    role: str
    grade: int
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
    subject: str
    topic: str
    difficulty: int
    title: str
    description: str
    task_type: str
    options: Optional[List[str]] = None
    is_solved: bool = False
    hints_available: int = 0

    class Config:
        from_attributes = True

class HintResponse(BaseModel):
    hint_text: str
    hint_number: int

class GenerateRequest(BaseModel):
    subject: str
    topic: str
    difficulty: int

class TaskAttempt(BaseModel):
    user_answer: str


class UserShort(BaseModel):
    username: str

    class Config: from_attributes = True


class MatchHistoryResponse(BaseModel):
    id: int
    subject: str
    played_at: datetime
    winner_score: int
    loser_score: int
    winner: Optional[UserShort]
    loser: Optional[UserShort]

    class Config: from_attributes = True