import asyncio
import logging
import random
import time
from fastapi import APIRouter, WebSocket, Query, Depends
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
MAX_ROUND_TIME_LIMIT = 1800


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


async def socket_reader(ws: WebSocket, queue: asyncio.Queue):
    try:
        while True:
            data = await ws.receive_json()
            answer = data.get("answer")
            if answer is not None:
                await queue.put(str(answer).strip())
    except Exception:
        await queue.put(None)


async def wait_with_pressure(q1: asyncio.Queue, q2: asyncio.Queue, ws1: WebSocket, ws2: WebSocket, pressure_time: int):
    start_time = time.time()

    async def get_task(q, name):
        val = await q.get()
        return name, val, time.time() - start_time

    t1 = asyncio.create_task(get_task(q1, "p1"))
    t2 = asyncio.create_task(get_task(q2, "p2"))
    pending = {t1, t2}

    results = {"p1": (None, 0.0), "p2": (None, 0.0)}

    done, pending = await asyncio.wait(pending, return_when=asyncio.FIRST_COMPLETED, timeout=MAX_ROUND_TIME_LIMIT)

    if not done:
        for t in pending: t.cancel()
        return results

    first_task = list(done)[0]
    player_key, answer, duration = first_task.result()
    results[player_key] = (answer, duration)

    if answer is None:
        for t in pending: t.cancel()
        return results

    slow_ws = ws2 if player_key == "p1" else ws1

    if not await safe_send(slow_ws, {
        "type": "pressure_timer",
        "seconds": pressure_time,
        "message": f"Время!"
    }):
        for t in pending: t.cancel()
        return results

    if pending:
        done_2, pending_2 = await asyncio.wait(pending, timeout=pressure_time)
        if done_2:
            pk2, ans2, dur2 = list(done_2)[0].result()
            results[pk2] = (ans2, dur2)
        else:
            for t in pending: t.cancel()
            other = "p2" if player_key == "p1" else "p1"
            results[other] = (None, float(pressure_time))

    return results


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
    user_grade = user.grade

    await manager.connect(websocket, user_id)
    my_queue = asyncio.Queue()
    manager.user_queues[user_id] = my_queue
    reader_task = asyncio.create_task(socket_reader(websocket, my_queue))

    try:
        players_ids = await manager.find_match(user_id, user_grade, subject)
        if players_ids:
            p1_id, p2_id = players_ids
            asyncio.create_task(run_pvp_game(p1_id, p2_id, subject))

        await reader_task
    except Exception as e:
        logger.error(f"WS Error: {e}")
    finally:
        reader_task.cancel()
        manager.disconnect(user_id)


async def run_pvp_game(id1: int, id2: int, subject: str):
    ws1, ws2 = manager.get_socket(id1), manager.get_socket(id2)
    q1, q2 = manager.get_queue(id1), manager.get_queue(id2)

    if not ws1 or not ws2: return

    scores = {id1: 0, id2: 0}
    disconnected_id = None

    try:
        async with new_session() as session:
            res = await session.execute(select(User).where(User.id.in_([id1, id2])))
            u_map = {u.id: u for u in res.scalars().all()}
            user1 = u_map.get(id1)
            user2 = u_map.get(id2)
            name1 = user1.username if user1 else "Player 1"
            name2 = user2.username if user2 else "Player 2"
            rating1 = user1.rating if user1 else 1000
            rating2 = user2.rating if user2 else 1000

            t_res = await session.execute(select(Task).where(Task.subject == subject))
            all_tasks = t_res.scalars().all()

        if not all_tasks:
            err = {"type": "error", "message": "Нет задач"}
            await safe_send(ws1, err)
            await safe_send(ws2, err)
            return

        count = min(len(all_tasks), ROUNDS_COUNT)
        game_tasks = random.sample(all_tasks, k=count)

        if not await safe_send(ws1, {"type": "match_found", "opponent": name2, "rating": rating2, "time": 5}):
            disconnected_id = id1
        elif not await safe_send(ws2, {"type": "match_found", "opponent": name1, "rating": rating1, "time": 5}):
            disconnected_id = id2

        if not disconnected_id:
            await asyncio.sleep(5)

        for i, task in enumerate(game_tasks):
            while not q1.empty(): q1.get_nowait()
            while not q2.empty(): q2.get_nowait()

            current_pressure = 30 + (task.difficulty * 10)

            msg = {
                "type": "round_start",
                "round": i + 1, "total": count,
                "title": task.title, "desc": task.description,
                "difficulty": task.difficulty,
                "time": None,
                "task_type": task.task_type,
                "options": task.options
            }
            if not await safe_send(ws1, msg): disconnected_id = id1; break
            if not await safe_send(ws2, msg): disconnected_id = id2; break

            answers = await wait_with_pressure(q1, q2, ws1, ws2, current_pressure)

            ans1, dur1 = answers["p1"]
            ans2, dur2 = answers["p2"]

            if ans1 is None and dur1 == 0: disconnected_id = id1; break
            if ans2 is None and dur2 == 0: disconnected_id = id2; break

            def normalize(s):
                return str(s).strip().lower().replace(" ", "")

            corr = normalize(task.correct_answer)

            r1 = "correct" if ans1 and normalize(ans1) == corr else "wrong"
            r2 = "correct" if ans2 and normalize(ans2) == corr else "wrong"

            if r1 == "correct": scores[id1] += 1
            if r2 == "correct": scores[id2] += 1

            async with new_session() as stat_session:
                u1 = await stat_session.get(User, id1)
                u2 = await stat_session.get(User, id2)

                if u1:
                    u1.anws += 1
                    u1.total_time_spent += dur1
                    if r1 == "correct": u1.cor_anws += 1

                if u2:
                    u2.anws += 1
                    u2.total_time_spent += dur2
                    if r2 == "correct": u2.cor_anws += 1

                await stat_session.commit()

            if not await safe_send(ws1, {"type": "round_result", "you": r1, "enemy": r2,
                                         "correct_answer": task.correct_answer}):
                disconnected_id = id1;
                break
            if not await safe_send(ws2, {"type": "round_result", "you": r2, "enemy": r1,
                                         "correct_answer": task.correct_answer}):
                disconnected_id = id2;
                break

            await asyncio.sleep(4)

        if disconnected_id:
            logger.info(f"Матч отменен. Игрок {disconnected_id} отключился.")
            survivor_ws = ws2 if disconnected_id == id1 else ws1
            await safe_send(survivor_ws, {
                "type": "error",
                "message": "Соперник отключился. Матч аннулирован."
            })
            return

        s1, s2 = scores[id1], scores[id2]
        if s1 > s2:
            sc1, sc2, res1, res2 = 1.0, 0.0, "win", "lose"
        elif s2 > s1:
            sc1, sc2, res1, res2 = 0.0, 1.0, "lose", "win"
        else:
            sc1, sc2, res1, res2 = 0.5, 0.5, "draw", "draw"

        async with new_session() as session:
            res = await session.execute(select(User).where(User.id.in_([id1, id2])))
            u_map = {u.id: u for u in res.scalars().all()}
            u1, u2 = u_map.get(id1), u_map.get(id2)

            if u1 and u2:
                u1.rating = calc_new_rating(u1.rating, u2.rating, sc1)
                u2.rating = calc_new_rating(u2.rating, u1.rating, sc2)

                for u, r in [(u1, res1), (u2, res2)]:
                    u.matches_played += 1
                    if r == "win":
                        u.wins += 1
                        await gamification.process_xp(u, 25, session)
                    elif r == "lose":
                        u.losses += 1
                        await gamification.process_xp(u, 5, session)
                    else:
                        await gamification.process_xp(u, 10, session)

                session.add(MatchHistory(subject=subject, p1_id=id1, p2_id=id2, p1_score=s1, p2_score=s2))
                await session.commit()

                await safe_send(ws1, {"type": "game_over", "result": res1, "my_score": s1, "enemy_score": s2,
                                      "new_rating": u1.rating})
                await safe_send(ws2, {"type": "game_over", "result": res2, "my_score": s2, "enemy_score": s1,
                                      "new_rating": u2.rating})

    except Exception as e:
        logger.error(f"PvP Fatal: {e}", exc_info=True)
    finally:
        manager.disconnect(id1)
        manager.disconnect(id2)