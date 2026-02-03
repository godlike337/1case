from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_, func
from database import get_db
from models import User, MatchHistory, SolvedTask
from auth import get_current_user
from schemas import StatsResponse


router = APIRouter(prefix="/analytics", tags=["analytics"])



@router.get("/me", response_model=StatsResponse)
async def get_my_analytics(
        db: AsyncSession = Depends(get_db),
        user: User = Depends(get_current_user)
):
    matches_res = await db.execute(
        select(MatchHistory).where(or_(MatchHistory.p1_id == user.id, MatchHistory.p2_id == user.id)))
    matches = matches_res.scalars().all()
    res = await db.execute(
        select(SolvedTask.topic, func.count(SolvedTask.id))
        .where(SolvedTask.user_id == user.id)
        .group_by(SolvedTask.topic)
    )
    topic_stats = {row[0]: row[1] for row in res.all()}

    win_rate1 = (user.wins / len(matches)) * 100 if len(matches) > 0 else 0
    correct_answers1 = (user.cor_anws / user.anws) * 100 if user.anws > 0 else 0
    avg_time = user.total_time_spent / user.anws if user.anws > 0 else 0.0

    return StatsResponse(
        total_matches=len(matches),
        win_rate=win_rate1,
        total_solved_training=sum(topic_stats.values()),
        subject_stats={"topics": topic_stats},
        correct_answers=correct_answers1,
        avg_solving_time=round(avg_time, 2),
    )