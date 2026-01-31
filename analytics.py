from fastapi import APIRouter, Depends
from rsa.pkcs1_v2 import mgf1
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

    wins = user.wins

    stmt = (
        select(SolvedTask.topic, func.count(SolvedTask.id))
        .where(SolvedTask.user_id == user.id)
        .group_by(SolvedTask.topic)
    )
    res = await db.execute(stmt)
    topic_stats = {row[0]: row[1] for row in res.all()}

    win_rate = (wins / len(matches)) * 100 if len(matches) > 0 else 0
    correct_answers = (user.cor_anws / user.anws) * 100 if user.anws > 0 else 0
    avg_time = 0.0
    if user.anws > 0:
        avg_time = user.total_time_spent / user.anws

    return StatsResponse(
        total_matches=len(matches),
        win_rate=win_rate,
        total_solved_training=sum(topic_stats.values()),
        subject_stats={"topics": topic_stats},
        correct_answers=correct_answers,
        avg_solving_time=round(avg_time, 2),
    )