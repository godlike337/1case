from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from models import User, Achievement

# Константы
XP_PER_LEVEL = 100  # Каждые 100 опыта = новый уровень

async def process_xp(user: User, amount: int, db: AsyncSession):
    """
    Начисляет опыт, повышает уровень и проверяет ачивки.
    Возвращает список новых полученных ачивок (строки).
    """
    user.xp += amount

    new_level = (user.xp // XP_PER_LEVEL) + 1
    if new_level > user.level:
        user.level = new_level

    new_unlocked = []

    if user.wins >= 1:
        await check_and_grant(user, "Первая кровь", db, new_unlocked)

    if user.wins >= 5:
        await check_and_grant(user, "Гладиатор", db, new_unlocked)

    if user.level >= 5:
        await check_and_grant(user, "Пятый элемент", db, new_unlocked)

    return new_unlocked

async def check_and_grant(user: User, achievement_name: str, db: AsyncSession, log_list: list):
    """Выдает ачивку, если её еще нет"""
    for ach in user.achievements:
        if ach.name == achievement_name:
            return

    result = await db.execute(select(Achievement).where(Achievement.name == achievement_name))
    ach_obj = result.scalar_one_or_none()
    
    if ach_obj:
        user.achievements.append(ach_obj)
        log_list.append(ach_obj.name)