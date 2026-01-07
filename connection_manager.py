from fastapi import WebSocket
from typing import List, Dict


class ConnectionManager:
    def __init__(self):
        # Список тех, кто ждет игру (очередь)
        self.waiting_queue: List[WebSocket] = []
        # Активные игры: {id_комнаты: [игрок1, игрок2]}
        self.active_matches: Dict[str, List[WebSocket]] = {}

    async def connect(self, websocket: WebSocket):
        await websocket.accept()

    def disconnect(self, websocket: WebSocket):
        # Если игрок был в очереди — убираем
        if websocket in self.waiting_queue:
            self.waiting_queue.remove(websocket)
        # (Доп. логику разрыва матча добавим позже)

    async def find_match(self, websocket: WebSocket):
        """
        Главная логика: ищем пару.
        Если в очереди никого нет -> встаем в очередь.
        Если кто-то есть -> создаем пару и начинаем игру!
        """
        if len(self.waiting_queue) > 0:
            # Нашли соперника!
            opponent = self.waiting_queue.pop(0)

            # Отправляем обоим сообщение "МАТЧ НАЙДЕН"
            await websocket.send_json({"type": "match_start", "opponent": "Player 2"})
            await opponent.send_json({"type": "match_start", "opponent": "Player 1"})

            # Возвращаем список игроков матча
            return [websocket, opponent]
        else:
            # Никого нет, ждем...
            self.waiting_queue.append(websocket)
            await websocket.send_json({"type": "waiting", "message": "Ожидание соперника..."})
            return None


# Создаем один экземпляр менеджера на всё приложение
manager = ConnectionManager()