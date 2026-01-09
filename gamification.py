from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from models import User, Achievement

XP_PER_LEVEL = 100


async def process_xp(user: User, amount: int, db: AsyncSession):
    user.xp += amount
    user.level = (user.xp // XP_PER_LEVEL) + 1
    existing_ach_names = {ach.name for ach in user.achievements}
    new_unlocked = []
    checks = [
        (user.wins >= 1, "Первая кровь"),
        (user.wins >= 5, "Гладиатор"),
        (user.level >= 5, "Пятый элемент"),
    ]

    for condition, name in checks:
        if condition and name not in existing_ach_names:
            result = await db.execute(select(Achievement).where(Achievement.name == name))
            ach_obj = result.scalar_one_or_none()
            if ach_obj:
                user.achievements.append(ach_obj)
                new_unlocked.append(name)

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