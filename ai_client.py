import os
import json
import aiohttp
from pydantic import BaseModel
from typing import List, Optional
GOOGLE_API_KEY = "AIzaSyDsj6b818_aNRxE75GH4eULx4U245Wm_HA"
PROXY_URL = "http://zTw70a:nfwsgb@185.71.214.48:8000"
API_URL = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={GOOGLE_API_KEY}"


class AI_Task_Schema(BaseModel):
    title: str
    description: str
    difficulty: int
    task_type: str
    options: Optional[List[str]] = None
    correct_answer: str
    hints: List[str]


class AIService:
    async def generate_task(self, subject: str, topic: str) -> AI_Task_Schema:
        payload = {
            "contents": [{
                "parts": [{
                    "text": f"""
                    Ты — строгий тренер олимпиадной сборной.
                    Сгенерируй СЛОЖНУЮ задачу по предмету "{subject}" на тему "{topic}".

                    Требования:
                    1. Уровень сложности: Высокий (Олимпиада/Профильный экзамен).
                    2. Избегай банальных примеров типа "2+2" или "print('hello')".
                    3. Задача должна требовать логического мышления или знания нюансов синтаксиса.
                    4. Если это программирование — дай кусок кода с подвохом.
                    5. Избегай ответов текстом(из за автоматической проверки; давай инструкции как записать ответ правильно)

                    Верни ТОЛЬКО JSON:
                    {{
                        "title": "Интригующий заголовок",
                        "description": "Полное условие задачи (можно с кодом)",
                        "difficulty": 4 (ставь от 3 до 5),
                        "task_type": "choice" (тест) или "text" (ввод ответа),
                        "options": ["Вариант A", "Вариант B", "Вариант C", "Вариант D"] (если choice, иначе null),
                        "correct_answer": "Текст правильного ответа (не цифра варианта, а само значение!)",
                        "hints": ["Наводящая подсказка 1", "Почти ответ 2"]
                    }}
                    """
                }]
            }],
            "generationConfig": {"response_mime_type": "application/json", "temperature": 0.8}
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(API_URL, json=payload, proxy=PROXY_URL) as response:
                    if response.status != 200:
                        raise Exception(f"Google Error {response.status}")

                    result = await response.json()
                    raw_text = result['candidates'][0]['content']['parts'][0]['text']
                    data = json.loads(raw_text)

                    validated = AI_Task_Schema(**data)
                    # Гарантируем, что подсказок не больше 2
                    if validated.hints and len(validated.hints) > 2:
                        validated.hints = validated.hints[:2]
                    return validated

        except Exception as e:
            print(f"🔴 AI Error: {e}")
            return AI_Task_Schema(
                title="Сбой ИИ", description="Попробуйте еще раз...", difficulty=1,
                task_type="text", correct_answer="0", hints=[], options=None
            )


ai_service = AIService()