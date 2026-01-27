from fastapi import APIRouter, Depends
from rsa.pkcs1_v2 import mgf1
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_, func
from database import get_db
from models import User, MatchHistory, SolvedTask
from auth import get_current_user
from pydantic import BaseModel
from typing import Dict

router = APIRouter(prefix="/analytics", tags=["analytics"])


class StatsResponse(BaseModel):
    total_matches: int
    win_rate: float
    total_solved_training: int
    subject_stats: Dict[str, dict]


@router.get("/me", response_model=StatsResponse)
async def get_my_analytics(
        db: AsyncSession = Depends(get_db),
        user: User = Depends(get_current_user)
):
    matches_res = await db.execute(
        select(MatchHistory).where(or_(MatchHistory.p1_id == user.id, MatchHistory.p2_id == user.id)))
    matches = matches_res.scalars().all()

    wins = 0
    subject_data = {}

    for m in matches:
        if m.p1_id == user.id:
            my_score = m.p1_score
            enemy_score = m.p2_score
        else:
            my_score = m.p2_score
            enemy_score = m.p1_score

        subj = m.subject
        if subj not in subject_data: subject_data[subj] = {"wins": 0, "total": 0}
        subject_data[subj]["total"] += 1
        if my_score > enemy_score: subject_data[subj]["wins"] += 1

    stmt = (
        select(SolvedTask.topic, func.count(SolvedTask.id))
        .where(SolvedTask.user_id == user.id)
        .group_by(SolvedTask.topic)
    )
    res = await db.execute(stmt)
    topic_stats = {row[0]: row[1] for row in res.all()}
    if len(matches) > 0:
        win_rate = (wins/len(matches))*100
    else:
        win_rate = 0

    return StatsResponse(
        total_matches=len(matches),
        win_rate=win_rate,
        total_solved_training=sum(topic_stats.values()),
        subject_stats={"topics": topic_stats}
    )