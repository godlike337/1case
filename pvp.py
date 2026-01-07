from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from connection_manager import manager

router = APIRouter()


@router.websocket("/ws/pvp")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        # 1. Игрок подключился, ищем матч
        match_players = await manager.find_match(websocket)

        # 2. Слушаем сообщения от игрока (например, "Я решил задачу!")
        while True:
            data = await websocket.receive_json()
            # Тут будет обработка ответа (верно/неверно)
            # Пока просто эхо (отправляем назад то, что пришло)
            await websocket.send_json({"message": "Server received: " + str(data)})

    except WebSocketDisconnect:
        manager.disconnect(websocket)
        print("Игрок отключился")