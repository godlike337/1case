from datetime import datetime, timedelta
from schemas import UserCreate, UserResponse, Token, MatchHistoryResponse
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from models import MatchHistory, User
from sqlalchemy import or_, select
from sqlalchemy.orm import selectinload
from database import get_db
from schemas import UserCreate, UserResponse, Token, MatchHistoryResponse
from models import User, Achievement

#настройки
SECRET_KEY = "secret_key"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 240
ADMIN_USERNAME = "huesos"
ADMIN_PASSWORD = "pidor123456"
#роутер
router = APIRouter(tags=["auth"])
#безопастность
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")
#функции
def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

#защита
async def get_current_user(token: str = Depends(oauth2_scheme), db: AsyncSession = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    result = await db.execute(select(User).where(User.username == username))
    user = result.scalar_one_or_none()
    if user is None:
        raise credentials_exception
    return user

#проверка админа
async def get_current_admin_user(current_user: User = Depends(get_current_user)):
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Недостаточно прав. Только для администраторов.",
        )
    return current_user
#создание админки
async def create_initial_admin_user(db: AsyncSession):
    result = await db.execute(select(User).where(User.username == ADMIN_USERNAME))
    admin_user = result.scalar_one_or_none()

    if not admin_user:
        hashed_password = get_password_hash(ADMIN_PASSWORD)
        new_admin = User(username=ADMIN_USERNAME, password=hashed_password, role="admin")
        db.add(new_admin)
        await db.commit()
        await db.refresh(new_admin)
        print(f"--- Создан первый администратор: {ADMIN_USERNAME} с паролем: {ADMIN_PASSWORD} ---")
    else:
        print(f"--- Администратор {ADMIN_USERNAME} уже существует ---")

#эндпоиты

router.post("/register", response_model=UserResponse)


async def register(user: UserCreate, db: AsyncSession = Depends(get_db)):
    existing = await db.execute(select(User).where(User.username == user.username))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Username already taken")

    existing_email = await db.execute(select(User).where(User.email == user.email))
    if existing_email.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Email already registered")

    # ЗАГЛУШКА
    print(f"📧 [STUB] Sending confirmation email to: {user.email}")

    new_user = User(
        username=user.username,
        email=user.email,  # Сохраняем почту
        password=get_password_hash(user.password)
    )
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)
    return new_user

@router.post("/token", response_model=Token)
async def login(form_data: OAuth2PasswordRequestForm = Depends(), db: AsyncSession = Depends(get_db)):
    #поиск юзера
    result = await db.execute(select(User).where(User.username == form_data.username))
    user = result.scalar_one_or_none()

    #проверка пароля
    if not user or not verify_password(form_data.password, user.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    #выдача токена
    access_token = create_access_token(data={"sub": user.username})
    return {"access_token": access_token, "token_type": "bearer"}


#тестовая ручка для проверки авторизации
@router.get("/users/me", response_model=UserResponse)
async def read_users_me(current_user: User = Depends(get_current_user)):
    return current_user
#админ ручка
@router.get("/admin_test", dependencies=[Depends(get_current_admin_user)])
async def admin_test():
    return {"message": "Вы вошли как администратор!"}
#история матчей
@router.get("/users/me/history", response_model=List[MatchHistoryResponse])
async def get_my_history(
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db)
):
    # Ищем матчи, где юзер был победителем ИЛИ проигравшим
    # Используем options(selectinload(...)), чтобы сразу подтянуть имена
    query = select(MatchHistory).where(
        or_(
            MatchHistory.winner_id == current_user.id,
            MatchHistory.loser_id == current_user.id
        )
    ).options(
        selectinload(MatchHistory.winner),
        selectinload(MatchHistory.loser)
    ).order_by(MatchHistory.played_at.desc())  # Сначала новые

    result = await db.execute(query)
    return result.scalars().all()


async def create_initial_achievements(db: AsyncSession):
    achievements_data = [
        {"name": "Первая кровь", "desc": "Победить в 1 матче", "icon": "🩸"},
        {"name": "Гладиатор", "desc": "Победить в 5 матчах", "icon": "⚔️"},
        {"name": "Пятый элемент", "desc": "Достичь 5 уровня", "icon": "🌟"},
    ]

    for ach in achievements_data:
        res = await db.execute(select(Achievement).where(Achievement.name == ach["name"]))
        if not res.scalar_one_or_none():
            db.add(Achievement(name=ach["name"], description=ach["desc"], icon=ach["icon"]))

    await db.commit()