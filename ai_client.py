import os
import json
import logging
from pydantic import BaseModel
from typing import List, Optional

from google import genai
from google.genai import types

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("AI_Client")

GOOGLE_API_KEY = "AIzaSyDsj6b818_aNRxE75GH4eULx4U245Wm_HA"


class AI_Task_Schema(BaseModel):
    title: str
    description: str
    difficulty: int
    task_type: str  # "choice" или "text"
    options: Optional[List[str]] = None
    correct_answer: str
    hints: List[str]


class AIService:
    def __init__(self):
        # Инициализируем клиента при старте сервера.
        # http_options=None означает, что мы идем напрямую, без прокси.
        self.client = genai.Client(api_key=GOOGLE_API_KEY)

    async def generate_task(self, subject: str, topic: str, grade: int, difficulty: int) -> Optional[AI_Task_Schema]:
        """
        Генерирует задачу, обращаясь к Google Gemini асинхронно.
        """

        # 1. Формируем Промпт (Задание для нейросети)
        # Мы четко описываем роль, контекст и требуемый формат JSON.
        prompt = f"""
        Ты — профессиональный методист и учитель олимпиадной подготовки.

        Контекст:
        - Ученик: {grade} класс.
        - Предмет: {subject}.
        - Тема: {topic}.
        - Желаемая сложность: {difficulty} из 5.

        Твоя задача:
        Сгенерируй ОДНУ уникальную задачу.

        Требования:
        1. Уровень должен соответствовать олимпиаде для {grade} класса.
        2. Не используй банальные примеры. Задача должна заставлять думать.
        3. ВАЖНО: Все математические формулы, степени и дроби пиши в формате LaTeX, обрамляя их знаком доллара. 
        4. Если task_type="choice", дай 4 варианта в options.
        5. Если task_type="text", убедись, что ответ можно записать коротко (числом или словом)(НЕ ДАВАЙ ОТВЕТЫ В ФОРМАТЕ LaTeX).

        Верни ответ СТРОГО в формате JSON, соответствующем этой схеме:
        {{
            "title": "Короткий заголовок",
            "description": "Текст условия",
            "difficulty": {difficulty},
            "task_type": "choice" или "text",
            "options": ["A", "B", "C", "D"] (или null, если text),
            "correct_answer": "Правильный ответ",
            "hints": ["Подсказка 1", "Подсказка 2"]
        }}
        """

        try:
            # 2. Отправляем запрос к Gemini
            # client.aio — это асинхронный интерфейс (важно для FastAPI, чтобы не блокировать сервер)
            response = await self.client.aio.models.generate_content(
                model='gemini-2.5-flash',
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type='application/json',  # Требуем JSON на уровне протокола
                )
            )

            # 3. Обрабатываем ответ
            # response.text содержит "сырую" строку JSON, которую вернул ИИ
            raw_json = response.text

            # Превращаем строку в словарь Python
            data = json.loads(raw_json)

            # Прогоняем через Pydantic для валидации типов
            validated_task = AI_Task_Schema(**data)


            logger.info(f"✅ Задача сгенерирована: {validated_task.title}")
            return validated_task

        except Exception as e:
            # Если что-то пошло не так (нет интернета, ключ неверный, ИИ вернул бред)
            logger.error(f"🔴 Ошибка генерации (Gemini): {e}")
            return None  # Возвращаем None, чтобы tasks.py знал об ошибке


# Создаем единственный экземпляр сервиса
ai_service = AIService()