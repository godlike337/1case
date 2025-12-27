from pydantic import BaseModel


#схема юзеров
class UserCreate(BaseModel):
    username: str
    password: str


class UserResponse(BaseModel):
    id: int
    username: str

    class Config:
        from_attributes = True


#схемы токенов
class Token(BaseModel):
    access_token: str
    token_type: str

class TaskCreate(BaseModel):
    title: str
    description: str
    difficulty: int
    correct_answer: str

class TaskResponse(BaseModel):
    id: int
    title: str
    description: str
    difficulty: int

    class Config:
        from_attributes = True

class TaskAttempt(BaseModel):
    user_answer: str