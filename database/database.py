# -*- coding: utf-8 -*-
from datetime import datetime

from peewee import SqliteDatabase, Model, IntegerField, CharField, BigIntegerField, TextField, DateTimeField

# База данных Peewee
db = SqliteDatabase('accounts.db')


class BaseModel(Model):
    """Базовая модель"""

    class Meta:
        database = db


class Account(BaseModel):
    """Модель аккаунта"""
    user_id = IntegerField(index=True)  # ID пользователя в боте
    phone = CharField(null=True)  # Номер телефона
    account_id = BigIntegerField(null=True, index=True)  # ID аккаунта в Telegram
    username = CharField(null=True)  # Username аккаунта
    first_name = CharField(null=True)  # Имя
    last_name = CharField(null=True)  # Фамилия
    session_file = CharField()  # Путь к файлу сессии
    original_filename = CharField(null=True)  # Оригинальное имя файла
    status = CharField(default='not_checked')  # active, unauthorized, error, dead
    error_message = TextField(null=True)  # Сообщение об ошибке
    last_checked = DateTimeField(default=datetime.now)  # Дата последней проверки
    created_at = DateTimeField(default=datetime.now)  # Дата добавления

    class Meta:
        table_name = 'accounts'
        indexes = (
            (('user_id', 'session_file'), True),  # Уникальная пара
        )


# Создаем таблицы
db.connect()
db.create_tables([Account], safe=True)
