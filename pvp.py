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


# --- ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ---
async def get_user_from_token(token: str, db: AsyncSession):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if not username: return None
    except JWTError:
        return None
    result = await db.execute(select(User).where(User.username == username))
    return result.scalar_one_or_none()


# --- ФУНКЦИЯ БЕЗОПАСНОЙ ОТПРАВКИ ---
async def send_msg(ws: WebSocket, msg: dict):
    try:
        await ws.send_json(msg)
        return True
    except Exception:
        return False  # Не удалось отправить (игрок вышел)


# --- РАСЧЕТ ELO ---
def calc_new_rating(rating_a: int, rating_b: int, actual_score: float):
    k = 32
    expected_a = 1 / (1 + 10 ** ((rating_b - rating_a) / 400))
    return int(rating_a + k * (actual_score - expected_a))


# =========================================================================
# ЧИТАТЕЛЬ СОКЕТА (PRODUCER)
# =========================================================================
async def socket_reader(ws: WebSocket, queue: asyncio.Queue, player_name: str):
    try:
        while True:
            data = await ws.receive_json()
            answer = data.get("answer")
            if answer is not None:
                await queue.put(str(answer).strip())
    except Exception:
        await queue.put(None)  # Сигнал разрыва


# =========================================================================
# ЭНДПОИНТ (ВХОД)
# =========================================================================
@router.websocket("/ws/pvp")
async def websocket_endpoint(
        websocket: WebSocket,
        subject: str = "python",
        token: str = Query(None),
        db: AsyncSession = Depends(get_db)
):
    if not token:
        await websocket.close(code=1008)
        return
    user = await get_user_from_token(token, db)
    if not user:
        await websocket.close(code=1008)
        return

    user_id = user.id
    logger.info(f"Игрок {user.username} подключился.")

    await manager.connect(websocket, user_id)

    # Личная очередь сообщений
    my_queue = asyncio.Queue()
    manager.user_queues[user_id] = my_queue

    # Запуск читателя
    reader_task = asyncio.create_task(socket_reader(websocket, my_queue, user.username))

    try:
        players_ids = await manager.find_match(user_id, subject)

        if players_ids:
            p1_id, p2_id = players_ids
            # Запуск игры
            asyncio.create_task(run_pvp_game(p1_id, p2_id, subject))

        # Ждем пока сокет жив
        await reader_task

    except Exception as e:
        logger.error(f"Ошибка сокета {user_id}: {e}")
    finally:
        reader_task.cancel()
        manager.disconnect(user_id)


# =========================================================================
# ИГРОВОЙ ЦИКЛ (CONSUMER)
# =========================================================================
async def run_pvp_game(id1: int, id2: int, subject: str):
    logger.info(f"🎮 СТАРТ: {id1} vs {id2}")

    ws1 = manager.get_socket(id1)
    ws2 = manager.get_socket(id2)
    q1 = manager.get_queue(id1)
    q2 = manager.get_queue(id2)

    if not ws1 or not ws2: return

    try:
        # Подготовка задач
        async with new_session() as session:
            result = await session.execute(select(Task).where(Task.subject == subject))
            all_tasks = result.scalars().all()

        if not all_tasks:
            await send_msg(ws1, {"type": "error", "message": "Нет задач"})
            await send_msg(ws2, {"type": "error", "message": "Нет задач"})
            return

        game_tasks = random.sample(all_tasks, k=min(len(all_tasks), ROUNDS_COUNT))
        while len(game_tasks) < ROUNDS_COUNT: game_tasks.append(random.choice(all_tasks))

        scores = {id1: 0, id2: 0}

        # --- ЦИКЛ РАУНДОВ ---
        for i, task in enumerate(game_tasks):
            # Очистка очередей
            while not q1.empty(): q1.get_nowait()
            while not q2.empty(): q2.get_nowait()

            msg = {
                "type": "round_start",
                "round": i + 1,
                "total": ROUNDS_COUNT,
                "title": task.title,
                "desc": task.description,
                "time": ROUND_TIME
            }

            # Отправка (с проверкой на вылет)
            if not await send_msg(ws1, msg) or not await send_msg(ws2, msg):
                logger.warning("Игрок вышел при старте раунда")
                break

                # Ждем ответы
            answers = await wait_for_queues(q1, q2, ROUND_TIME)

            # Проверка на полный дисконнект (None в очереди)
            ans1 = answers.get("p1")
            ans2 = answers.get("p2")
            if ans1 is None or ans2 is None:
                logger.warning("Игрок отключился во время ожидания ответа")
                break

            # Проверка правильности
            correct = str(task.correct_answer).strip().lower()
            # Если ответ пустая строка ("") -> wrong, если текст -> проверяем
            res1 = "correct" if ans1 and str(ans1).strip().lower() == correct else "wrong"
            res2 = "correct" if ans2 and str(ans2).strip().lower() == correct else "wrong"

            if res1 == "correct": scores[id1] += 1
            if res2 == "correct": scores[id2] += 1

            # Отправка результатов
            await send_msg(ws1,
                           {"type": "round_result", "you": res1, "enemy": res2, "correct_answer": task.correct_answer})
            await send_msg(ws2,
                           {"type": "round_result", "you": res2, "enemy": res1, "correct_answer": task.correct_answer})

            await asyncio.sleep(4)

        # --- ФИНАЛ ---
        s1, s2 = scores[id1], scores[id2]
        r1, r2 = ("draw", "draw")

        async with new_session() as session:
            u1 = await session.get(User, id1)
            u2 = await session.get(User, id2)

            w_id, l_id = None, None

            if s1 > s2:
                r1, r2 = "win", "lose"
                w_id, l_id = id1, id2
                if u1 and u2:
                    u1.wins += 1;
                    u1.matches_played += 1
                    u2.losses += 1;
                    u2.matches_played += 1
                    u1.rating, u2.rating = calc_new_rating(u1.rating, u2.rating, 1.0), calc_new_rating(u2.rating,
                                                                                                       u1.rating, 0.0)
            elif s2 > s1:
                r1, r2 = "lose", "win"
                w_id, l_id = id2, id1
                if u1 and u2:
                    u2.wins += 1;
                    u2.matches_played += 1
                    u1.losses += 1;
                    u1.matches_played += 1
                    u1.rating, u2.rating = calc_new_rating(u1.rating, u2.rating, 0.0), calc_new_rating(u2.rating,
                                                                                                       u1.rating, 1.0)
            else:
                if u1 and u2:
                    u1.matches_played += 1;
                    u2.matches_played += 1
                    u1.rating, u2.rating = calc_new_rating(u1.rating, u2.rating, 0.5), calc_new_rating(u2.rating,
                                                                                                       u1.rating, 0.5)

            history = MatchHistory(subject=subject, winner_id=w_id, loser_id=l_id, winner_score=max(s1, s2),
                                   loser_score=min(s1, s2))
            session.add(history)
            await session.commit()

            # Отправляем результаты (если игроки еще тут)
            new_r1 = u1.rating if u1 else 0
            new_r2 = u2.rating if u2 else 0
            await send_msg(ws1,
                           {"type": "game_over", "result": r1, "my_score": s1, "enemy_score": s2, "new_rating": new_r1})
            await send_msg(ws2,
                           {"type": "game_over", "result": r2, "my_score": s2, "enemy_score": s1, "new_rating": new_r2})

    except Exception as e:
        logger.error(f"Game Error: {e}")
    finally:
        manager.disconnect(id1)
        manager.disconnect(id2)


async def wait_for_queues(q1: asyncio.Queue, q2: asyncio.Queue, timeout: int):
    start = time.time()
    res = {"p1": "", "p2": ""}
    got1, got2 = False, False

    while True:
        now = time.time()
        left = (start + timeout) - now
        if left <= 0: break
        if got1 and got2: break

        try:
            if not got1 and not q1.empty():
                res["p1"] = await q1.get()
                got1 = True
            if not got2 and not q2.empty():
                res["p2"] = await q2.get()
                got2 = True
            await asyncio.sleep(0.1)
        except Exception:
            break
    return res