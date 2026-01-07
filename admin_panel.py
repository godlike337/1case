from sqladmin import ModelView
from models import User, Task

# Настройка отображения Пользователей
class UserAdmin(ModelView, model=User):
    column_list = [User.id, User.username, User.password]
    column_searchable_list = [User.username]
    column_details_exclude_list = [User.password]
    form_columns = [User.username, User.role]
    name = "Пользователь"
    name_plural = "Пользователи"
    icon = "fa-solid fa-user"

# Настройка отображения Задач
class TaskAdmin(ModelView, model=Task):
    column_list = [Task.id, Task.title, Task.difficulty]
    column_searchable_list = [Task.title]
    form_columns = [Task.title, Task.description, Task.difficulty, Task.correct_answer]
    name = "Задача"
    name_plural = "Задачи"
    icon = "fa-solid fa-list-check"