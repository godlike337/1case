import asyncio
from fastapi import WebSocket
from typing import List, Dict, Any, Optional


class ConnectionManager:
    def __init__(self):
        self.waiting_queues: Dict[str, List[dict]] = {
            "python": [],
            "math": []
        }
        self.active_connections: Dict[int, WebSocket] = {}
        self.user_queues: Dict[int, asyncio.Queue] = {}

    async def connect(self, websocket: WebSocket, user_id: int):
        await websocket.accept()
        self.active_connections[user_id] = websocket
        self.user_queues[user_id] = asyncio.Queue()

    def disconnect(self, user_id: int):
        if user_id in self.active_connections: del self.active_connections[user_id]
        if user_id in self.user_queues: del self.user_queues[user_id]

        for subject, queue in self.waiting_queues.items():
            self.waiting_queues[subject] = [u for u in queue if u['id'] != user_id]

    def get_socket(self, user_id: int):
        return self.active_connections.get(user_id)

    def get_queue(self, user_id: int):
        return self.user_queues.get(user_id)

    async def find_match(self, user_id: int, grade: int, subject: str) -> Optional[List[int]]:
        queue = self.waiting_queues.get(subject, [])

        queue = [u for u in queue if u['id'] != user_id]

        opponent_entry = None
        opponent_index = -1

        for i, entry in enumerate(queue):
            if abs(entry['grade'] - grade) <= 1:
                opponent_entry = entry
                opponent_index = i
                break

        if opponent_entry:
            queue.pop(opponent_index)
            self.waiting_queues[subject] = queue
            return [user_id, opponent_entry['id']]
        else:
            new_entry = {'id': user_id, 'grade': grade}
            queue.append(new_entry)
            self.waiting_queues[subject] = queue

            ws = self.get_socket(user_id)
            if ws:
                await ws.send_json(
                    {"type": "waiting", "message": f"Поиск соперника ({grade - 1}-{grade + 1} классы)..."})
            return None


manager = ConnectionManager()