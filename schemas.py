from pydantic import BaseModel, EmailStr, Field
from typing import List, Optional
from datetime import datetime
from typing import Dict

class AchievementResponse(BaseModel):
    name: str
    description: str
    icon: str

    class Config:
        from_attributes = True


class UserCreate(BaseModel):
    username: str =  Field(min_length=3, max_length=20)
    email: EmailStr
    password: str = Field(min_length=6)
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
    grade: int
    difficulty: int
    correct_answer: str
    subject: str


class TaskResponse(BaseModel):
    id: int
    subject: str
    topic: str
    grade: int
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

class StatsResponse(BaseModel):
    total_matches: int
    win_rate: float
    total_solved_training: int
    subject_stats: Dict[str, dict]
    correct_answers: int
    avg_solving_time: float

class MatchHistoryResponse(BaseModel):
    id: int
    subject: str
    played_at: datetime
    p1_score: int
    p2_score: int
    player1: Optional[UserShort]
    player2: Optional[UserShort]

    class Config: from_attributes = True