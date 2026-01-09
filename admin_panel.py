from sqladmin import ModelView
from models import User, Task, MatchHistory
from auth import get_password_hash  # <--- ИМПОРТИРУЕМ ХЕШИРОВАНИЕ


class UserAdmin(ModelView, model=User):
    name = "Пользователь"
    name_plural = "Пользователи"
    icon = "fa-solid fa-user"

    column_list = [User.id, User.username, User.role, User.rating, User.wins]

    form_columns = [User.username, User.password, User.role, User.rating]

    async def on_model_change(self, data, model, is_created, request):
        password = data.get("password")
        if password:
            data["password"] = get_password_hash(password)
        return await super().on_model_change(data, model, is_created, request)


class TaskAdmin(ModelView, model=Task):
    name = "Задача"
    name_plural = "Задачи"
    icon = "fa-solid fa-list-check"
    column_list = [Task.id, Task.subject, Task.title, Task.difficulty]
    column_searchable_list = [Task.title]
    form_columns = [Task.title, Task.subject, Task.description, Task.difficulty, Task.correct_answer]


class MatchHistoryAdmin(ModelView, model=MatchHistory):
    name = "История матча"
    name_plural = "История матчей"
    icon = "fa-solid fa-clock-rotate-left"

    column_list = [
        MatchHistory.id,
        MatchHistory.subject,
        "winner.username",
        MatchHistory.winner_score,
        "loser.username",
        MatchHistory.loser_score,
        MatchHistory.played_at
    ]

    column_labels = {
        "winner.username": "Победитель",
        "loser.username": "Проигравший",
        MatchHistory.winner_score: "Счет (Win)",
        MatchHistory.loser_score: "Счет (Lose)"
    }

    can_create = False
    can_edit = False