# -*- coding: utf-8 -*-
from aiogram import F
from aiogram.types import CallbackQuery

from keyboards.keyboards import main_keyboard
from system.system import router, accounts_db, ADMIN_IDS


# Просмотр аккаунтов
@router.callback_query(F.data == "my_accounts")
async def show_accounts(callback: CallbackQuery):
    """
    Обработчик кнопки просмотра аккаунтов

    Отображает список всех загруженных пользователем аккаунтов.
    Показывает статус, телефон и имя файла для каждого аккаунта

    :param callback: Объект callback-запроса
    :return: None
    """
    user_id = callback.from_user.id
    accounts = accounts_db.get(user_id, [])

    if not accounts:
        await callback.message.answer("У вас нет загруженных аккаунтов")
        await callback.answer()
        return

    text = "📋 Ваши аккаунты:\n\n"
    for idx, acc in enumerate(accounts, 1):
        status_emoji = "✅" if acc["status"] == "active" else "❓" if acc["status"] == "not_checked" else "❌"
        text += f"{idx}. {status_emoji} {acc['filename']}\n"
        text += f"   Телефон: {acc['phone']}\n"
        text += f"   Статус: {acc['status']}\n\n"

    await callback.message.answer(text, reply_markup=main_keyboard(user_id in ADMIN_IDS))
    await callback.answer()


def register_show_accounts():
    router.callback_query.register(show_accounts)
