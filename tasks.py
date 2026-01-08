from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from database import get_db
from models import Task, User, SolvedTask
from schemas import TaskCreate, TaskResponse, TaskAttempt
from auth import get_current_user
import gamification

router = APIRouter(prefix="/tasks", tags=["tasks"])


@router.get("/", response_model=list[TaskResponse])
async def get_tasks(
        subject: str = None,
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    # 1. Получаем задачи
    query = select(Task)
    if subject:
        query = query.where(Task.subject == subject)

    result = await db.execute(query)
    tasks = result.scalars().all()

    # 2. Получаем список ID решенных задач этим юзером
    solved_query = select(SolvedTask.task_id).where(SolvedTask.user_id == current_user.id)
    solved_res = await db.execute(solved_query)
    solved_ids = set(solved_res.scalars().all())

    # 3. Собираем ответ с флагом is_solved
    response = []
    for t in tasks:
        # Pydantic модель создаем вручную, добавляя флаг
        task_data = TaskResponse.model_validate(t)
        task_data.is_solved = (t.id in solved_ids)
        response.append(task_data)

    return response


@router.post("/{task_id}/solve")
async def solve_task(
        task_id: int,
        attempt: TaskAttempt,
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    # Ищем задачу
    result = await db.execute(select(Task).where(Task.id == task_id))
    task = result.scalar_one_or_none()

    if not task:
        raise HTTPException(status_code=404, detail="Задача не найдена")

    # Проверка ответа
    user_ans = attempt.user_answer.strip().lower()
    correct_ans = task.correct_answer.strip().lower()

    if user_ans == correct_ans:
        # ПРОВЕРКА НА ДЮП ОПЫТА
        # Проверяем, решал ли он её раньше
        check_solved = await db.execute(
            select(SolvedTask).where(
                and_(SolvedTask.user_id == current_user.id, SolvedTask.task_id == task_id)
            )
        )
        if check_solved.scalar_one_or_none():
            return {"status": "correct", "message": "Верно! (Задача уже была решена, опыт не начислен)"}

        # Если не решал:
        # 1. Записываем в решенные
        new_solved = SolvedTask(user_id=current_user.id, task_id=task_id)
        db.add(new_solved)

        # 2. Даем опыт
        new_achievements = await gamification.process_xp(current_user, 5, db)

        await db.commit()

        msg = "Верно! +5 XP"
        if new_achievements:
            msg += f" | Ачивка: {', '.join(new_achievements)}"

        return {"status": "correct", "message": msg}
    else:
        return {"status": "wrong", "message": "Неверно"}