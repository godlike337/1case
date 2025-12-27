from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from database import get_db
from models import Task, User
from schemas import TaskCreate, TaskResponse, TaskAttempt
from auth import get_current_user

router = APIRouter(prefix="/tasks", tags=["tasks"])


@router.post("/", response_model=TaskResponse)
async def create_task(
        task: TaskCreate,
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    new_task = Task(
        title=task.title,
        description=task.description,
        difficulty=task.difficulty,
        correct_answer=task.correct_answer
    )
    db.add(new_task)
    await db.commit()
    await db.refresh(new_task)
    return new_task


@router.get("/", response_model=list[TaskResponse])
async def get_tasks(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Task))
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

    is_correct = attempt.user_answer.strip().lower() == task.correct_answer.strip().lower()

    if is_correct:
        return {"status": "correct", "message": "Верно! +10 очков"}
    else:
        return {"status": "wrong", "message": "Неверно, попробуйте еще раз"}