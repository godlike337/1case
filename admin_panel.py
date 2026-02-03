from sqladmin import ModelView
from models import User, Task, MatchHistory
from auth import get_password_hash
from models import Achievement



class UserAdmin(ModelView, model=User):
    name = "Пользователь"
    name_plural = "Пользователи"
    icon = "fa-solid fa-user"

    column_list = [User.id, User.username, User.role, User.rating, User.wins, User.grade]

    form_columns = [User.username, User.role, User.rating, User.grade, User.xp, User.level, User.password]

    async def on_model_change(self, data, model, is_created, request):
        password = data.get("password")

        if password:
            data["password"] = get_password_hash(password)
        else:
            if "password" in data:
                del data["password"]

        return await super().on_model_change(data, model, is_created, request)


class TaskAdmin(ModelView, model=Task):
    name = "Задача"
    name_plural = "Задачи"
    icon = "fa-solid fa-list-check"
    column_list = [Task.id, Task.subject, Task.title, Task.difficulty, Task.task_type]
    form_columns = [Task.title, Task.description, Task.subject, Task.topic, Task.difficulty, Task.task_type,
                    Task.options, Task.correct_answer, Task.hints]


class MatchHistoryAdmin(ModelView, model=MatchHistory):
    name = "История матча"
    name_plural = "История матчей"
    icon = "fa-solid fa-clock-rotate-left"
    column_list = [MatchHistory.id, MatchHistory.subject, MatchHistory.player1, MatchHistory.p1_score,
                   MatchHistory.player2, MatchHistory.p2_score]
    can_create = False
    can_edit = False
    can_delete = True

class AchievementAdmin(ModelView, model=Achievement):
    name = "Достижение"
    name_plural = "Достижения"
    icon = "fa-solid fa-trophy"
    column_list = [Achievement.name, Achievement.description, Achievement.icon]