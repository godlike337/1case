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