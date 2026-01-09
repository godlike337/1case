import asyncio
from fastapi import WebSocket
from typing import List, Dict, Any
from collections import defaultdict


class ConnectionManager:
    def __init__(self):
        self.waiting_queues: Dict[str, List[int]] = defaultdict(list)
        self.active_connections: Dict[int, WebSocket] = {}
        self.user_queues: Dict[int, asyncio.Queue] = {}

    async def connect(self, websocket: WebSocket, user_id: int):
        await websocket.accept()
        self.active_connections[user_id] = websocket
        self.user_queues[user_id] = asyncio.Queue()

    def disconnect(self, user_id: int):
        if user_id in self.active_connections:
            del self.active_connections[user_id]
        if user_id in self.user_queues:
            del self.user_queues[user_id]

        for subject, queue in self.waiting_queues.items():
            if user_id in queue:
                queue.remove(user_id)
                break

    def get_socket(self, user_id: int):
        return self.active_connections.get(user_id)

    def get_queue(self, user_id: int):
        return self.user_queues.get(user_id)

    async def find_match(self, user_id: int, subject: str):
        queue = self.waiting_queues[subject]

        if user_id in queue:
            queue.remove(user_id)

        if len(queue) > 0:
            opponent_id = queue.pop(0)
            return [user_id, opponent_id]
        else:
            queue.append(user_id)
            ws = self.get_socket(user_id)
            if ws:
                await ws.send_json({"type": "waiting", "message": "Поиск..."})
            return None


manager = ConnectionManager()