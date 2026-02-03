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
    task_type: str
    options: Optional[List[str]] = None
    correct_answer: str
    hints: List[str]


class AIService:
    def __init__(self):
        self.client = genai.Client(api_key=GOOGLE_API_KEY)

    async def generate_task(self, subject: str, topic: str, grade: int, difficulty: int) -> Optional[AI_Task_Schema]:
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
        3. ВАЖНО: Все математические формулы, степени и дроби пиши в формате LaTeX, обрамляя их знаком доллара. (НЕ ДАВАЙ ОТВЕТЫ В ФОРМАТЕ LaTeX).
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
            response = await self.client.aio.models.generate_content(
                model='gemini-2.5-flash',
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type='application/json',  #
                )
            )

            raw_json = response.text
            data = json.loads(raw_json)
            validated_task = AI_Task_Schema(**data)

            logger.info(f"✅ Задача сгенерирована: {validated_task.title}")
            return validated_task

        except Exception as e:
            logger.error(f"🔴 Ошибка генерации (Gemini): {e}")
            return None


ai_service = AIService()