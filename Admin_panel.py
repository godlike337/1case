from sqladmin import ModelView
from models import User, Task

# Настройка отображения Пользователей
class UserAdmin(ModelView, model=User):
    column_list = [User.id, User.username, User.password] # Какие колонки показывать в списке
    column_searchable_list = [User.username] # Поиск по логину
    column_details_exclude_list = [User.password] # Не показывать хеш пароля в деталях (для красоты)
    name = "Пользователь"
    name_plural = "Пользователи"
    icon = "fa-solid fa-user" # Иконка (FontAwesome)

# Настройка отображения Задач
class TaskAdmin(ModelView, model=Task):
    column_list = [Task.id, Task.title, Task.difficulty]
    column_searchable_list = [Task.title]
    name = "Задача"
    name_plural = "Задачи"
    icon = "fa-solid fa-list-check"