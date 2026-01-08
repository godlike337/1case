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


# =========================================================================
# ГЛАВНЫЙ ЦИКЛ (ОН И ЧИТАТЕЛЬ, И ЗАПУСКАТЕЛЬ)
# =========================================================================
@router.websocket("/ws/pvp")
async def websocket_endpoint(
        websocket: WebSocket,
        subject: str = "python",
        token: str = Query(None),
        db: AsyncSession = Depends(get_db)
):
    # --- АВТОРИЗАЦИЯ ---
    if not token:
        await websocket.close(code=1008)
        return
    user = await get_user_from_token(token, db)
    if not user:
        await websocket.close(code=1008)
        return

    user_id = user.id
    logger.info(f"User {user_id} connected.")

    # 1. РЕГИСТРАЦИЯ В МЕНЕДЖЕРЕ
    await manager.connect(websocket, user_id)

    try:
        # 2. ПОИСК МАТЧА
        players_ids = await manager.find_match(user_id, subject)

        if players_ids:
            # Если матч найден, запускаем ИГРУ в фоне (create_task)
            # Запускает игру тот, кто нашел матч (второй игрок)
            p1_id, p2_id = players_ids
            logger.info(f"Match found: {p1_id} vs {p2_id}. Starting game loop...")
            asyncio.create_task(run_pvp_game(p1_id, p2_id, subject))

        # 3. БЕСКОНЕЧНЫЙ ЦИКЛ ЧТЕНИЯ (PRODUCER)
        # Мы читаем сообщения и кладем их в очередь менеджера.
        # Игра (Consumer) будет их оттуда забирать.
        queue = manager.get_queue(user_id)
        while True:
            data = await websocket.receive_json()
            answer = data.get("answer")
            if answer and str(answer).strip():
                # Кладем ответ в очередь, если игра идет - она его прочитает
                await queue.put(str(answer).strip())

    except WebSocketDisconnect:
        logger.info(f"User {user_id} disconnected.")
        manager.disconnect(user_id)
    except Exception as e:
        logger.error(f"Error socket {user_id}: {e}")
        manager.disconnect(user_id)


# =========================================================================
# ИГРОВАЯ ЛОГИКА (CONSUMER)
# =========================================================================
async def run_pvp_game(id1: int, id2: int, subject: str):
    logger.info(f"🎮 GAME STARTED: {id1} vs {id2}")

    ws1 = manager.get_socket(id1)
    ws2 = manager.get_socket(id2)
    q1 = manager.get_queue(id1)
    q2 = manager.get_queue(id2)

    if not ws1 or not ws2:
        logger.error("Один из сокетов потерян на старте.")
        return

    try:
        # Подготовка задач
        async with new_session() as session:
            result = await session.execute(select(Task).where(Task.subject == subject))
            all_tasks = result.scalars().all()

        # Если задач мало - берем сколько есть с повтором, или ошибку
        if not all_tasks:
            await ws1.send_json({"type": "error", "message": "Нет задач"})
            await ws2.send_json({"type": "error", "message": "Нет задач"})
            return

        game_tasks = random.sample(all_tasks, k=min(len(all_tasks), ROUNDS_COUNT))
        # Если задач меньше чем раундов, дополним рандомными
        while len(game_tasks) < ROUNDS_COUNT:
            game_tasks.append(random.choice(all_tasks))

        scores = {id1: 0, id2: 0}

        # --- ЦИКЛ РАУНДОВ ---
        for i, task in enumerate(game_tasks):
            # Очищаем очереди от старых ответов (на всякий случай)
            while not q1.empty(): q1.get_nowait()
            while not q2.empty(): q2.get_nowait()

            round_num = i + 1
            msg = {
                "type": "round_start",
                "round": round_num,
                "total": ROUNDS_COUNT,
                "title": task.title,
                "desc": task.description,
                "time": ROUND_TIME
            }
            # Отправка безопасна, так как send - thread-safe в uvicorn
            await ws1.send_json(msg)
            await ws2.send_json(msg)

            # ЖДЕМ ОТВЕТЫ ИЗ ОЧЕРЕДЕЙ
            answers = await wait_for_queues(q1, q2, ROUND_TIME)

            # Проверка
            correct = str(task.correct_answer).strip().lower()
            ans1 = answers.get("p1")
            ans2 = answers.get("p2")

            res1 = "correct" if ans1 and ans1.lower() == correct else "wrong"
            res2 = "correct" if ans2 and ans2.lower() == correct else "wrong"

            if res1 == "correct": scores[id1] += 1
            if res2 == "correct": scores[id2] += 1

            await ws1.send_json(
                {"type": "round_result", "you": res1, "enemy": res2, "correct_answer": task.correct_answer})
            await ws2.send_json(
                {"type": "round_result", "you": res2, "enemy": res1, "correct_answer": task.correct_answer})

            await asyncio.sleep(4)

        # --- ФИНАЛ ---
        s1, s2 = scores[id1], scores[id2]
        r1, r2 = ("draw", "draw")
        w_id, l_id = None, None

        if s1 > s2:
            r1, r2 = "win", "lose"
            w_id, l_id = id1, id2
        elif s2 > s1:
            r1, r2 = "lose", "win"
            w_id, l_id = id2, id1

        await ws1.send_json({"type": "game_over", "result": r1, "my_score": s1, "enemy_score": s2})
        await ws2.send_json({"type": "game_over", "result": r2, "my_score": s2, "enemy_score": s1})

        # Запись в БД
        async with new_session() as session:
            history = MatchHistory(
                subject=subject, winner_id=w_id, loser_id=l_id,
                winner_score=max(s1, s2), loser_score=min(s1, s2)
            )
            session.add(history)
            await session.commit()
            logger.info("History saved.")

    except Exception as e:
        logger.error(f"Game Loop Error: {e}")
    finally:
        # В конце игры не разрываем соединение жестко, пусть юзеры сами выходят
        # или можно выкинуть их в меню
        pass


async def wait_for_queues(q1: asyncio.Queue, q2: asyncio.Queue, timeout: int):
    """
    Ждем появления элементов в двух очередях.
    """
    start = time.time()
    res = {"p1": None, "p2": None}
    got1, got2 = False, False

    while True:
        now = time.time()
        left = (start + timeout) - now
        if left <= 0: break
        if got1 and got2: break

        # Проверяем очередь 1
        if not got1 and not q1.empty():
            res["p1"] = await q1.get()
            got1 = True

        # Проверяем очередь 2
        if not got2 and not q2.empty():
            res["p2"] = await q2.get()
            got2 = True

        await asyncio.sleep(0.1)

    return res