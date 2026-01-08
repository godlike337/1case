from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from database import get_db
from models import Task, User
from schemas import TaskCreate, TaskResponse, TaskAttempt
from auth import get_current_user

router = APIRouter(prefix="/tasks", tags=["tasks"])


@router.get("/", response_model=list[TaskResponse])
async def get_tasks(
        subject: str = None,
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    query = select(Task)
    if subject:
        query = query.where(Task.subject == subject)

    result = await db.execute(query)
    return result.scalars().all()



@router.post("/{task_id}/solve")
async def solve_task(
        task_id: int,
        attempt: TaskAttempt,
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    result = await db.execute(select(Task).where(Task.id == task_id))
    task = result.scalar_one_or_none()

    if not task:
        raise HTTPException(status_code=404, detail="Задача не найдена")


    user_ans = attempt.user_answer.strip().lower()
    correct_ans = task.correct_answer.strip().lower()

    if user_ans == correct_ans:
        return {"status": "correct", "message": "Верно!"}
    else:
        return {"status": "wrong", "message": "Неверно"}