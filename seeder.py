import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from models import Task, Base
import random

# Настройки БД
DATABASE_URL = "sqlite+aiosqlite:///./olympiad.db"
engine = create_async_engine(DATABASE_URL)
new_session = async_sessionmaker(engine, expire_on_commit=False)


async def seed_tasks():
    async with new_session() as session:
        print("--- ГЕНЕРАЦИЯ ЗАДАЧ ---")

        tasks_to_add = []

        # 1. МАТЕМАТИКА (Генерируем программно)
        for i in range(20):
            a = random.randint(1, 50)
            b = random.randint(1, 50)
            op = random.choice(['+', '-', '*'])

            if op == '+':
                ans = a + b
            elif op == '-':
                ans = a - b
            else:
                ans = a * b

            tasks_to_add.append(Task(
                title=f"Пример №{i + 1}",
                description=f"Сколько будет {a} {op} {b}?",
                difficulty=1,
                correct_answer=str(ans),
                subject="math"
            ))

        # 2. PYTHON (Заготовленный список)
        py_tasks = [
            ("Типы данных", "Как называется тип данных для целых чисел в Python?", "int"),
            ("Функции", "Ключевое слово для создания функции?", "def"),
            ("Списки", "Как узнать длину списка L?", "len(L)"),
            ("Циклы", "Какой цикл используется для перебора range?", "for"),
            ("Логика", "Результат True and False?", "False"),
            ("Строки", "Метод для приведения к нижнему регистру?", "lower"),
            ("Библиотеки", "Библиотека для случайных чисел?", "random"),
            ("Вывод", "Функция для вывода текста в консоль?", "print"),
            ("Условия", "Ключевое слово 'иначе'?", "else"),
            ("Импорт", "Команда для подключения модуля?", "import"),
        ]

        for t in py_tasks:
            tasks_to_add.append(Task(
                title=t[0],
                description=t[1],
                difficulty=1,
                correct_answer=t[2],
                subject="python"
            ))

        session.add_all(tasks_to_add)
        await session.commit()
        print(f"Добавлено {len(tasks_to_add)} задач!")


if __name__ == "__main__":
    asyncio.run(seed_tasks())