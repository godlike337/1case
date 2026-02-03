import asyncio
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from database import get_db
from models import Task, User, SolvedTask
from schemas import TaskResponse, TaskAttempt, HintResponse, GenerateRequest
from auth import get_current_user
import gamification
from ai_client import ai_service

router = APIRouter(prefix="/tasks", tags=["tasks"])


@router.post("/training/generate", response_model=TaskResponse)
async def generate_training_task(
        req: GenerateRequest,
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    ai_data = await ai_service.generate_task(
        req.subject, req.topic, current_user.grade, req.difficulty
    )

    if not ai_data:
        raise HTTPException(status_code=503, detail="ИИ не смог придумать задачу.")

    new_task = Task(
        subject=req.subject, topic=req.topic,
        title=ai_data.title, description=ai_data.description,
        difficulty=ai_data.difficulty, task_type=ai_data.task_type,
        options=ai_data.options, correct_answer=ai_data.correct_answer,
        hints=ai_data.hints
    )
    db.add(new_task)
    await db.commit()
    await db.refresh(new_task)

    resp = TaskResponse.model_validate(new_task)
    resp.hints_available = len(new_task.hints)
    return resp

@router.get("/{task_id}/hint", response_model=HintResponse)
async def get_hint(
        task_id: int,
        hint_number: int = Query(..., ge=1),
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    res = await db.execute(select(Task).where(Task.id == task_id))
    task = res.scalar_one_or_none()

    if not task or not task.hints:
        raise HTTPException(404, "Подсказок нет")

    idx = hint_number - 1
    if idx < 0 or idx >= len(task.hints):
        raise HTTPException(400, "Такой подсказки нет")

    return HintResponse(hint_text=task.hints[idx], hint_number=hint_number)


@router.post("/{task_id}/solve")
async def solve_task(
        task_id: int,
        attempt: TaskAttempt,
        db: AsyncSession = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    res = await db.execute(select(Task).where(Task.id == task_id))
    task = res.scalar_one_or_none()
    if not task: raise HTTPException(404, "Задача не найдена")

    def normalize(s):
        return str(s).strip().lower().replace(" ", "")

    user_ans = normalize(attempt.user_answer)
    correct_ans = normalize(task.correct_answer)

    is_correct = (user_ans == correct_ans)

    if not is_correct and task.task_type == "choice" and task.options:
        if user_ans in correct_ans or correct_ans in user_ans:
            is_correct = True

    if is_correct:
        check = await db.execute(select(SolvedTask).where(
            and_(SolvedTask.user_id == current_user.id, SolvedTask.task_id == task_id)
        ))
        if check.scalar_one_or_none():
            return {"status": "correct", "message": "Верно! (Уже решено)"}

        new_solved = SolvedTask(
            user_id=current_user.id,
            task_id=task_id,
            subject=task.subject,
            topic=task.topic
        )
        db.add(new_solved)

        await gamification.process_xp(current_user, 10 * task.difficulty, db)  # XP зависит от сложности!
        await db.commit()
        return {"status": "correct", "message": f"Верно! +{10 * task.difficulty} XP"}

    return {"status": "wrong", "message": "Неверно"}