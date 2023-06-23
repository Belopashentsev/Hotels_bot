# После ввода команды пользователю выводится история поиска отелей. Сама история
# содержит:
# 1. Команду, которую вводил пользователь.
# 2. Дату и время ввода команды.
# 3. Отели, которые были найдены.
from datetime import datetime
from peewee import *

db = SqliteDatabase('history.db', pragmas={'foreign_keys': 1})


class Base(Model):
    class Meta:
        database = db


class User(Base):
    user_id = AutoField()


class History(Base):
    user = ForeignKeyField(User, related_name='history', on_delete='cascade')
    date = DateTimeField(default=datetime.now)
    command = CharField()
    value = TextField()

    class Meta:
        order_by = 'date'





