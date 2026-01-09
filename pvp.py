import asyncio
import logging
import random
import time
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from jose import jwt, JWTError

from database import get_db, new_session
from models import Task, MatchHistory, User
from connection_manager import manager
from auth import SECRET_KEY, ALGORITHM
import gamification

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("PvP")

router = APIRouter()

ROUNDS_COUNT = 3
ROUND_TIME = 20

async def get_user_from_token(token: str, db: AsyncSession):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if not username: return None
    except JWTError:
        return None
    result = await db.execute(select(User).where(User.username == username))
    return result.scalar_one_or_none()


async def safe_send(ws: WebSocket, data: dict):
    try:
        await ws.send_json(data)
        return True
    except Exception:
        return False


def calc_new_rating(rating_a: int, rating_b: int, actual_score: float):
    k = 32
    expected_a = 1 / (1 + 10 ** ((rating_b - rating_a) / 400))
    return int(rating_a + k * (actual_score - expected_a))


async def wait_for_queues(q1: asyncio.Queue, q2: asyncio.Queue, timeout: int):
    async def get_from_q(q):
        return await q.get()

    task1 = asyncio.create_task(get_from_q(q1))
    task2 = asyncio.create_task(get_from_q(q2))

    done, pending = await asyncio.wait([task1, task2], timeout=timeout)

    for task in pending: task.cancel()

    return {
        "p1": task1.result() if task1 in done else None,
        "p2": task2.result() if task2 in done else None
    }


async def socket_reader(ws: WebSocket, queue: asyncio.Queue):
    try:
        while True:
            data = await ws.receive_json()
            answer = data.get("answer")
            if answer is not None:
                await queue.put(str(answer).strip())
    except Exception:
        await queue.put(None)


@router.websocket("/ws/pvp")
async def websocket_endpoint(
        websocket: WebSocket,
        subject: str = "python",
        token: str = Query(None),
        db: AsyncSession = Depends(get_db)
):
    if not token: await websocket.close(code=1008); return
    user = await get_user_from_token(token, db)
    if not user: await websocket.close(code=1008); return

    user_id = user.id
    logger.info(f"Игрок {user.username} (ID: {user.id}) подключился.")

    await manager.connect(websocket, user_id)
    my_queue = asyncio.Queue()
    manager.user_queues[user_id] = my_queue

    reader_task = asyncio.create_task(socket_reader(websocket, my_queue))

    try:
        players_ids = await manager.find_match(user_id, subject)
        if players_ids:
            p1_id, p2_id = players_ids
            asyncio.create_task(run_pvp_game(p1_id, p2_id, subject))
        await reader_task
    except Exception as e:
        logger.error(f"Error socket {user_id}: {e}")
    finally:
        reader_task.cancel()
        manager.disconnect(user_id)


async def run_pvp_game(id1: int, id2: int, subject: str):
    ws1, ws2 = manager.get_socket(id1), manager.get_socket(id2)
    q1, q2 = manager.get_queue(id1), manager.get_queue(id2)

    if not ws1 or not ws2: return

    name1, name2 = "Player 1", "Player 2"
    scores = {id1: 0, id2: 0}

    try:
        async with new_session() as session:
            res = await session.execute(select(User).where(User.id.in_([id1, id2])))
            users = {u.id: u for u in res.scalars().all()}
            if users.get(id1): name1 = users[id1].username
            if users.get(id2): name2 = users[id2].username

            t_res = await session.execute(select(Task).where(Task.subject == subject))
            all_tasks = t_res.scalars().all()

        if not all_tasks:
            await safe_send(ws1, {"type": "error", "message": "Нет задач"})
            await safe_send(ws2, {"type": "error", "message": "Нет задач"})
            return

        game_tasks = random.sample(all_tasks, k=min(len(all_tasks), ROUNDS_COUNT))

        await safe_send(ws1, {"type": "match_found", "opponent": name2, "time": 5})
        await safe_send(ws2, {"type": "match_found", "opponent": name1, "time": 5})
        await asyncio.sleep(5)

        for i, task in enumerate(game_tasks):
            while not q1.empty(): q1.get_nowait()
            while not q2.empty(): q2.get_nowait()

            msg = {
                "type": "round_start", "round": i + 1, "total": len(game_tasks),
                "title": task.title, "desc": task.description, "time": ROUND_TIME
            }
            if not await safe_send(ws1, msg) or not await safe_send(ws2, msg): break

            answers = await wait_for_queues(q1, q2, ROUND_TIME)
            ans1, ans2 = answers["p1"], answers["p2"]

            if ans1 is None and ans2 is None: break

            correct = str(task.correct_answer).strip().lower()
            r1 = "correct" if ans1 and str(ans1).strip().lower() == correct else "wrong"
            r2 = "correct" if ans2 and str(ans2).strip().lower() == correct else "wrong"

            if r1 == "correct": scores[id1] += 1
            if r2 == "correct": scores[id2] += 1

            await safe_send(ws1,
                            {"type": "round_result", "you": r1, "enemy": r2, "correct_answer": task.correct_answer})
            await safe_send(ws2,
                            {"type": "round_result", "you": r2, "enemy": r1, "correct_answer": task.correct_answer})
            await asyncio.sleep(4)

        s1, s2 = scores[id1], scores[id2]

        if s1 > s2:
            sc1, sc2, res1, res2, wid, lid = 1.0, 0.0, "win", "lose", id1, id2
        elif s2 > s1:
            sc1, sc2, res1, res2, wid, lid = 0.0, 1.0, "lose", "win", id2, id1
        else:
            sc1, sc2, res1, res2, wid, lid = 0.5, 0.5, "draw", "draw", None, None

        async with new_session() as session:
            res = await session.execute(select(User).where(User.id.in_([id1, id2])))
            u_map = {u.id: u for u in res.scalars().all()}
            u1, u2 = u_map.get(id1), u_map.get(id2)

            if u1 and u2:
                u1.rating = calc_new_rating(u1.rating, u2.rating, sc1)
                u2.rating = calc_new_rating(u2.rating, u1.rating, sc2)

                for u, r_type in [(u1, res1), (u2, res2)]:
                    u.matches_played += 1
                    if r_type == "win":
                        u.wins += 1
                        await gamification.process_xp(u, 15, session)
                    elif r_type == "lose":
                        u.losses += 1
                        await gamification.process_xp(u, 5, session)
                    else:
                        await gamification.process_xp(u, 5, session)

                session.add(MatchHistory(subject=subject, winner_id=wid, loser_id=lid, winner_score=max(s1, s2),
                                         loser_score=min(s1, s2)))
                await session.commit()

                await safe_send(ws1, {"type": "game_over", "result": res1, "my_score": s1, "enemy_score": s2,
                                      "new_rating": u1.rating})
                await safe_send(ws2, {"type": "game_over", "result": res2, "my_score": s2, "enemy_score": s1,
                                      "new_rating": u2.rating})

    except Exception as e:
        logger.error(f"PvP Error: {e}", exc_info=True)
    finally:
        manager.disconnect(id1)
        manager.disconnect(id2)