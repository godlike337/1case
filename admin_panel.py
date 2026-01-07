from sqladmin import ModelView
from models import User, Task, MatchHistory

# Настройка отображения Пользователей
class UserAdmin(ModelView, model=User):
    name = "Пользователь"
    name_plural = "Пользователи"
    icon = "fa-solid fa-user"
    column_list = [User.id, User.username, User.role, User.rating, User.wins]
    form_columns = [User.username, User.role, User.rating]

# Настройка отображения Задач
class TaskAdmin(ModelView, model=Task):
    column_list = [Task.id, Task.title, Task.difficulty]
    column_searchable_list = [Task.title]
    form_columns = [Task.title, Task.description, Task.difficulty, Task.correct_answer]
    name = "Задача"
    name_plural = "Задачи"
    icon = "fa-solid fa-list-check"
